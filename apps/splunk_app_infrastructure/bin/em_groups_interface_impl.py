import json

# Custom Libraries
from em_kvstore_manager import EMKVStoreManager
from em_search_manager import EMSearchManager
from em_savedsearch_manager import EMSavedSearchManager
from em_exceptions import GroupInternalException, GroupNotFoundException, ArgValidationException
import em_constants as EMConstants
import em_common as EMCommon
import logging_utility
from em_correlation_filters import serialize, create_group_log_filter

logger = logging_utility.getLogger()


class EmGroupsInterfaceImpl(object):
    """ The Groups interface that allows CRUD operations on groups """

    def handleCreate(self, handler, confInfo):
        # Get the name of the group the user wants to create
        group_name = handler.callerArgs.id
        logger.info('User triggered action "create" with key=%s' % group_name)
        self._setupKVStore(handler)

        data = self._setupDataPayload(handler)
        try:
            self.groups_store.create(group_name, data)
        except Exception:
            raise GroupInternalException(
                'Failed to create the group %s!' % group_name)

    def handleList(self, handler, confInfo):
        # Get the name of the group the user wants to fetch
        key = handler.callerArgs.id
        count = handler.callerArgs.get('count', 0)
        offset = handler.callerArgs.get('offset', 0)
        fields = handler.callerArgs.get('fields', '')
        kvstore_query = EMCommon.get_query_from_request_args(handler.callerArgs.get('query', [''])[0])
        filter_entity_ids = handler.callerArgs.get(
            'filter_by_entity_ids', [''])[0]
        filter_entity_names = handler.callerArgs.get(
            'filter_by_entity_names', [''])[0]

        self._setupKVStore(handler)
        self._setupSearchManager(handler)

        # This will list only the group that was requested
        if key is not None:
            logger.info('User triggered action "list" with key=%s' % key)
            selected_group = self._handleListKey(key)
            if selected_group is not None:
                group_entities_count = self._getNumOfEntitiesInGroups(
                    [selected_group])
                collector_names_with_entities = self._getCollectorNamesAndEntitiesInGroup(key)
                self._extractRelevantFields(
                    selected_group,
                    group_entities_count,
                    confInfo,
                    collector_entities_match=collector_names_with_entities
                )
        else:
            # This will list groups filtered by entity ids or names
            if filter_entity_ids != '' or filter_entity_names != '':
                if filter_entity_ids != '':
                    filter_info = filter_entity_ids
                    group_keys, group_entities_count = self._getGroupFilteredByEntity(EMSearchManager.BY_ENTITY_IDS,
                                                                                      filter_info)
                else:
                    filter_info = filter_entity_names
                    group_keys, group_entities_count = self._getGroupFilteredByEntity(EMSearchManager.BY_ENTITY_NAMES,
                                                                                      filter_info)
                kvstore_query = {'$or': [{'_key': group_key}
                                         for group_key in group_keys]}
                query_params = self._buildParamsObjectForLoad(
                    json.dumps(kvstore_query))
                groups = self._handleListAll(
                    fields, query_params, count, offset)
            else:
                # This will list all of the groups saved
                query_params = self._buildParamsObjectForLoad(kvstore_query)
                groups = self._handleListAll(
                    fields, query_params, count, offset)
                group_entities_count = self._getNumOfEntitiesInGroups(groups)
            if groups is not None:
                map(lambda group: self._extractRelevantFields(
                    group, group_entities_count, confInfo), groups)

    def handleEdit(self, handler, confInfo):
        # Get the name of the group the user wants to fetch
        group_name = handler.callerArgs.id
        logger.info('User triggered action "edit" with key=%s' % group_name)
        self._setupKVStore(handler)

        existing_group = self.groups_store.get(group_name)

        # Make sure that the group we're trying to edit exists
        if existing_group is None:
            raise GroupNotFoundException(
                'Cannot modify a group that does not exist!')
        else:
            data = self._setupDataPayload(handler)
            try:
                self.groups_store.update(group_name, data)
            except Exception:
                raise GroupInternalException(
                    'Failed to update the group %s!' % group_name)

    def handleRemove(self, handler, confInfo):
        # Get the name of the group the user wants to delete
        group_name = handler.callerArgs.id
        logger.info('User triggered action "remove" with key=%s' % group_name)
        self._setupKVStore(handler)

        try:
            self.groups_store.delete(group_name)
        except Exception:
            raise GroupNotFoundException(
                'Cannot find the group with id %s!' % group_name)

    def handleBulkDelete(self, handler, confInfo):
        """
        :param handler instance of the em_group_interface:
        :param confInfo confInfo for the current request:
        :return:

        Delete the groups based on a query and calls list as response.
        Query param is required for bulk delete.
        """
        self._setupKVStore(handler)
        self._setupSavedSearchManager(handler)
        groups_deleted_list = json.loads(handler.callerArgs.data.get('delete_query', ['{}'])[0])
        if not groups_deleted_list:
            # If no query is provided, delete all groups, and therefore all saved
            # searches associated with all groups
            groups_deleted_list = self._handleListAll(fields='_key')
        savedsearch_delete_query = EMCommon.get_list_of_admin_managedby(
            groups_deleted_list, EMConstants.APP_NAME)
        kvstore_delete_query = EMCommon.get_query_from_request_args(
            handler.callerArgs.data.get('delete_query', [''])[0])
        if not kvstore_delete_query:
            raise ArgValidationException('Delete query can not be empty')
        logger.info('User triggered action "bulk_delete" on groups')
        delete_query = {"query": kvstore_delete_query}
        self.groups_store.bulk_delete(query=delete_query)
        self.savedsearch_manager.bulk_delete(savedsearch_query=savedsearch_delete_query)
        handler.callerArgs.data.pop('delete_query')
        self.handleList(handler, confInfo)

    def handleMetadata(self, handler, confInfo):
        """
        Return metadata about the groups
        """
        self._setupKVStore(handler)
        fields = ["title"]
        query = {"query": ""}
        groups = self._handleListAll(','.join(fields), query)
        confInfo["groups"]["titles"] = list(
            {group["title"] for group in groups})

    def _setupSavedSearchManager(self, handler):
        self.savedsearch_manager = EMSavedSearchManager(server_uri=EMCommon.get_server_uri(),
                                                        session_key=handler.getSessionKey())

    def _setupKVStore(self, handler):
        # Sets up the KV store from which we will be conducting operations
        logger.info('Setting up the Groups KV Store...')
        self.groups_store = EMKVStoreManager(
            collection=EMConstants.STORE_GROUPS,
            server_uri=EMCommon.get_server_uri(),
            session_key=handler.getSessionKey(),
            app=EMConstants.APP_NAME)
        self.collector_store = EMKVStoreManager(collection=EMConstants.STORE_COLLECTORS,
                                                server_uri=EMCommon.get_server_uri(),
                                                session_key=handler.getSessionKey(),
                                                app=EMConstants.APP_NAME)

    def _setupSearchManager(self, handler):
        # Sets up the search manager
        logger.info('Setting up the EM Search Manager...')
        self.search_manager = EMSearchManager(
            server_uri=EMCommon.get_server_uri(),
            session_key=handler.getSessionKey(),
            app=EMConstants.APP_NAME)

    def _setupDataPayload(self, handler):
        data = {}
        data['name'] = handler.callerArgs.id
        data['title'] = handler.callerArgs.data['title'][0]
        data['filter'] = handler.callerArgs.data['filter'][0]
        return data

    def _buildParamsObjectForLoad(self, kvstore_query):
        query_params = {}
        if kvstore_query:
            query_params['query'] = kvstore_query
        return query_params

    def _extractRelevantFields(self, group, group_entities_count, confInfo, collector_entities_match=None):
        confInfo[group['_key']]['filter'] = group.get('filter', '')
        confInfo[group['_key']]['name'] = group.get('name', '')
        confInfo[group['_key']]['title'] = group.get('title', '')

        entity_state_counts = group_entities_count.get(group['_key'], {})
        confInfo[group['_key']]['entities_count'] = entity_state_counts.get('count', 0)
        confInfo[group['_key']]['inactive_entities_count'] = entity_state_counts.get('inactive', 0)
        confInfo[group['_key']]['active_entities_count'] = entity_state_counts.get('active', 0)
        confInfo[group['_key']]['disabled_entities_count'] = entity_state_counts.get('disabled', 0)
        confInfo[group['_key']][
            'workspace_url_path'] = "/app/%s/metrics_analysis" % EMConstants.APP_NAME

        if collector_entities_match:
            collector_configs = self._handleListAllCollectorConfigs(collector_entities_match.keys())
            group_logs_filter = create_group_log_filter(collector_entities_match, collector_configs)
            confInfo[group['_key']]['log_search'] = serialize(group_logs_filter) if group_logs_filter else None

    def _handleListKey(self, key):
        try:
            return self.groups_store.get(key)
        except Exception:
            raise GroupNotFoundException(
                'Cannot find the group with id %s!' % key)

    def _handleListAll(self, fields='', query_params={}, count=0, offset=0):
        try:
            return self.groups_store.load(count, offset, fields, params=query_params)
        except Exception:
            raise GroupInternalException(
                'Cannot list all of the groups saved!')

    def _handleListAllCollectorConfigs(self, collector_names, fields='', count=0, offset=0):
        try:
            kvstore_query = {'$or': [{'_key': collector_name} for collector_name in collector_names]}
            query_params = self._buildParamsObjectForLoad(json.dumps(kvstore_query))
            return self.collector_store.load(count, offset, fields, params=query_params)
        except Exception as e:
            raise GroupInternalException(
                'Cannot list collector configs: %s' % e.message)

    def _getNumOfEntitiesInGroups(self, groups):
        try:
            return self.search_manager.get_count_of_entities_by_group(groups)
        except Exception:
            raise GroupInternalException(
                'Cannot get count of groups')

    def _getCollectorNamesAndEntitiesInGroup(self, group_name):
        try:
            return self.search_manager.get_entities_and_collector_names_by_group(group_name)
        except Exception:
            raise GroupInternalException(
                'Cannot get collector or entities info from group \'%s\'' % group_name)

    def _getGroupFilteredByEntity(self, by=EMSearchManager.BY_ENTITY_IDS, entity_info=None):
        if by == EMSearchManager.BY_ENTITY_IDS:
            filter_search = self.search_manager.filter_groups_by(
                EMSearchManager.BY_ENTITY_IDS)
        else:
            filter_search = self.search_manager.filter_groups_by(
                EMSearchManager.BY_ENTITY_NAMES)
        try:
            entity_info_list = map(lambda e: e.strip(), entity_info.split(','))
            groups_with_count = filter_search(entity_info_list)
            group_keys = groups_with_count.keys()
            if not len(group_keys):
                raise GroupNotFoundException('No groups found.')
            return group_keys, groups_with_count
        except Exception:
            raise GroupInternalException(
                'Cannot get matching groups with given entity information')
