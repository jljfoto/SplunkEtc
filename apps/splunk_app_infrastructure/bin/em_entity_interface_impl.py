from splunk.util import normalizeBoolean
from em_kvstore_manager import EMKVStoreManager
from em_savedsearch_manager import EMSavedSearchManager
import em_constants
import em_common as EMCommon
from em_search_manager import EMSearchManager
from em_exceptions import EntityAlreadyExistsException, EntityInternalException, \
    EntityNotFoundException, ArgValidationException
from em_common import get_locale_specific_display_names
from em_correlation_filters import serialize, create_entity_log_filter
import json
import time
import logging_utility

logger = logging_utility.getLogger()


class EmEntityInterfaceImpl(object):
    """The Entity Interface that allows CRUD operations on entities."""
    VALID_ENTITY_STATES = ['active', 'inactive', 'disabled']
    DIMENSION_TYPES = ['informational_dimensions', 'identifier_dimensions']

    def _setup_kv_store(self, handler):
        # Sets up the Entity KV Store
        logger.info('Setting up the Entity KV Store...')
        self.entity_store = EMKVStoreManager(collection=em_constants.STORE_ENTITIES,
                                             server_uri=EMCommon.get_server_uri(),
                                             session_key=handler.getSessionKey(),
                                             app=em_constants.APP_NAME)
        self.collector_store = EMKVStoreManager(collection=em_constants.STORE_COLLECTORS,
                                                server_uri=EMCommon.get_server_uri(),
                                                session_key=handler.getSessionKey(),
                                                app=em_constants.APP_NAME)

    def _setup_savedsearch_manager(self, handler):
        self.savedsearch_manager = EMSavedSearchManager(server_uri=EMCommon.get_server_uri(),
                                                        session_key=handler.getSessionKey())

    def handleList(self, handler, confInfo):
        entity = handler.callerArgs.id
        count = handler.callerArgs.get('count', 0)
        offset = handler.callerArgs.get('offset', 0)
        display_name_locale = handler.callerArgs.get(
            'display_name_locale', ['en-us'])[0]

        # Make sure that if informational or identifier dimensions requested, to also request
        # "dimensions" to KV Store
        input_fields = handler.callerArgs.data.get('fields', [''])[0]
        kvstore_query = EMCommon.get_query_from_request_args(
            handler.callerArgs.data.get('query', [''])[0])
        fields = ''
        if input_fields and len(input_fields) > 0:
            fields = self._modifyFieldsRequested(input_fields)

        logger.info('User triggered action "list" with key=%s' % entity)
        self._setup_kv_store(handler)

        collector_configs = self._handleListAllConfigs(confInfo)

        if entity is not None:
            selected_entity = self._handleListKey(confInfo, entity)
            if selected_entity is not None:
                self._extractRelevantFields(
                    selected_entity, confInfo, collector_configs, display_name_locale)
        else:
            query_params = {'query': kvstore_query}
            all_entities = self._handleListAll(
                confInfo, fields, query_params, count, offset)
            if all_entities is not None:
                map(lambda entity: self._extractRelevantFields(entity, confInfo, collector_configs,
                                                               display_name_locale), all_entities)

    def handleRemove(self, handler, confInfo):
        entity_name = handler.callerArgs.id
        logger.info('User triggered action "remove" with key=%s' % entity_name)
        self._setup_kv_store(handler)

        try:
            self.entity_store.delete(entity_name)
        except Exception:
            raise EntityNotFoundException(
                'Cannot find the entity with id %s!' % entity_name)

    def handleEdit(self, handler, confInfo):
        entity_name = handler.callerArgs.id
        logger.info('User triggered action "edit" with key=%s' % entity_name)
        self._setup_kv_store(handler)

        existing_entity = self.entity_store.get(entity_name)
        if existing_entity is None:
            raise EntityNotFoundException(
                'Cannot modify an entity that does not exist!')
        else:
            # Make sure dimension lists and dimension objects are valid JSON
            identifier = handler.callerArgs.data.get(
                'identifier_dimensions', ['[]'])[0]
            informational = handler.callerArgs.data.get(
                'informational_dimensions', ['[]'])[0]
            dimensions = handler.callerArgs.data.get('dimensions', ['{}'])[0]

            dimensions, informational_dimensions, identifier_dimensions = \
                self._validateDimensionsValidJson(
                    identifier, informational, dimensions)

            self._validateDimensionsExist(dimensions, informational_dimensions)
            self._validateDimensionsExist(dimensions, identifier_dimensions)

            data_payload = {}

            # First, make sure that the entity is set to a valid state
            entity_state = handler.callerArgs.data.get(
                'state', ['disabled'])[0]
            self._validateEntityState(entity_state)

            data_payload['state'] = entity_state
            data_payload['title'] = handler.callerArgs.data.get('title', [''])[
                0]
            data_payload['identifier_dimensions'] = identifier_dimensions
            data_payload['informational_dimensions'] = informational_dimensions
            data_payload['dimensions'] = dimensions
            data_payload['imported_date'] = handler.callerArgs.data.get(
                'imported_date', [''])[0]
            data_payload['updated_date'] = time.time()

            try:
                self.entity_store.update(entity_name, data_payload)
            except Exception:
                raise EntityInternalException(
                    'Failed to update the entity %s!' % entity_name)

    def handleCreate(self, handler, confInfo):
        entity_name = handler.callerArgs.id
        logger.info('User triggered action "create" with key=%s' % entity_name)
        self._setup_kv_store(handler)

        # Make sure that the entity that is being created does not already
        # exist
        existing_entity = self.entity_store.get(entity_name)
        if existing_entity is not None:
            raise EntityAlreadyExistsException(
                'Cannot create an entity that already exists!')
        else:
            # Make sure dimension lists and dimension objects are valid JSON
            identifier = handler.callerArgs.data.get(
                'identifier_dimensions', ['[]'])[0]
            informational = handler.callerArgs.data.get(
                'informational_dimensions', ['[]'])[0]
            dimensions = handler.callerArgs.data.get('dimensions', ['{}'])[0]

            dimensions, informational_dimensions, identifier_dimensions = \
                self._validateDimensionsValidJson(
                    identifier, informational, dimensions)

            self._validateDimensionsExist(dimensions, informational_dimensions)
            self._validateDimensionsExist(dimensions, identifier_dimensions)

            data_payload = {}

            # First, make sure that the entity is set to a valid state
            entity_state = handler.callerArgs.data.get(
                'state', ['disabled'])[0]
            self._validateEntityState(entity_state)

            data_payload['state'] = entity_state
            data_payload['title'] = handler.callerArgs.data.get('title', [''])[0]
            data_payload['identifier_dimensions'] = identifier_dimensions
            data_payload['informational_dimensions'] = informational_dimensions
            data_payload['dimensions'] = dimensions
            data_payload['imported_date'] = time.time()

            # Time created is the same as time updated for a new entity
            data_payload['updated_date'] = data_payload['imported_date']
            try:
                self.entity_store.create(entity_name, data_payload)
            except Exception:
                raise EntityInternalException(
                    'Failed to create the entity %s!' % entity_name)

    def handleBulkDelete(self, handler, confInfo):
        """
        :param handler instance of the en_entity_interface:
        :param confInfo confInfo for the current request:
        :return:

        Delete the entities based on a query and calls list as response.
        Query param is required for bulk delete.
        """
        self._setup_kv_store(handler)
        self._setup_savedsearch_manager(handler)
        kvstore_delete_query = EMCommon.get_query_from_request_args(
            handler.callerArgs.data.get('delete_query', [''])[0])
        if not kvstore_delete_query:
            raise ArgValidationException('Delete query can not be empty')
        delete_query = {
            'query': kvstore_delete_query
        }
        entities_deleted_list = self._handleListAll(confInfo, fields='_key', query_params=delete_query)
        savedsearch_delete_query = EMCommon.get_list_of_admin_managedby(
            entities_deleted_list, em_constants.APP_NAME)
        logger.info('User triggered action "bulk_delete" on entities')
        self.entity_store.bulk_delete(query=delete_query)
        self.savedsearch_manager.bulk_delete(savedsearch_query=savedsearch_delete_query)
        handler.callerArgs.data.pop('delete_query')
        self.handleList(handler, confInfo)

    def handleMetadata(self, handler, confInfo):
        """
        Return metadata about the entities
        """
        self._setup_kv_store(handler)
        # for now just using below default query and fields as we need to fetch
        # all entities
        fields = ["dimensions"]
        query = {"query": ""}
        entities = self._handleListAll(confInfo, ','.join(fields), query)
        dimensions = [entity['dimensions'] for entity in entities if 'dimensions' in entity]
        merged_dimensions = self._constructDimensionsMap(dimensions)
        for key, value in merged_dimensions.iteritems():
            confInfo["dimensions"][key] = value

    def handleMetricName(self, handler, confInfo):
        """
        Return metric names of the entities
        """
        self._setup_kv_store(handler)
        search_query = handler.callerArgs.data.get('query', '')
        if search_query:
            search_query = self._load_valid_metric_names_query_param(search_query[0])

        count = handler.callerArgs.get('count', 0)
        search_manager = EMSearchManager(
            EMCommon.get_server_uri(), handler.getSessionKey(), em_constants.APP_NAME)
        search_results_list = search_manager.get_metric_names_by_dim_names(dimensions=search_query,
                                                                           count=count)
        metrics_list = []
        if search_results_list:
            for result in search_results_list:
                single_metric = {
                    result.get('metric_name'): {
                        'min': result.get('min'),
                        'max': result.get('max')
                    }
                }
                metrics_list.append(single_metric)
        # Availability should always be the first metric
        metrics_list.insert(0, {em_constants.DEFAULT_METRIC_FOR_COLOR_BY: {'min': '0.00', 'max': '1.00'}})
        confInfo['metric_names']['metric_names'] = json.dumps(metrics_list)

    def handleMetricData(self, handler, confInfo):
        """
        Return metric metadata by entity name
        """
        count = handler.callerArgs.get('count', 0)
        query_params = handler.callerArgs.data.get('query', '')
        if not query_params:
            raise ArgValidationException('Missing required key: query')
        query_params = self._load_valid_metric_metadata_query(query_params[0])
        self._setup_kv_store(handler)
        dimensions = query_params.get('dimensions', {})
        execute_search = normalizeBoolean(query_params.get('executeSearch', True))
        reformated_dimensions = dimensions
        if dimensions:
            reformated_dimensions = {'dimensions.{}'.format(key): value for key, value in dimensions.iteritems()}
        kvstore_query = EMCommon.get_query_from_request_args(json.dumps(reformated_dimensions))
        filtered_entities = self._handleListAll(
            confInfo, fields='_key,dimensions,collectors.name', query_params={'query': kvstore_query})
        collectors = self._handleListAllConfigs(confInfo, fields='name,title_dimension')
        collector_config = {
            collector.get('name'): collector.get('title_dimension') for collector in collectors
        }
        search_manager = EMSearchManager(
            EMCommon.get_server_uri(), handler.getSessionKey(), em_constants.APP_NAME)
        search_res = search_manager.get_avg_metric_val_by_entity(
            execute_search=execute_search,
            metric_name=query_params['metric_name'],
            entities=filtered_entities,
            collector_config=collector_config,
            count=count)
        confInfo['metric_data']['metric_data'] = \
            json.dumps({
                ret.get('key'): ret.get('value') for ret in search_res
            }) if isinstance(search_res, list) else search_res

    def _constructDimensionsMap(self, dimensions):
        """
        Format the data to remove duplicates and return a map of dimensions with values
        ex : {
            "host": ["a", "b"],
            "location": ["seattle"]
        }
        :param dimensions {dict} dimensions on each entity from kvstore:
        :return:
        """
        merged_dimensions = {}
        for dimension in dimensions:
            for key, value in dimension.iteritems():
                if key in merged_dimensions:
                    if isinstance(value, list):
                        merged_dimensions[key] = list(
                            set(merged_dimensions[key]) | set(value))
                    elif value not in merged_dimensions[key]:
                        merged_dimensions[key].append(value)
                else:
                    merged_dimensions[key] = value if isinstance(value, list) else [
                        value]
        return merged_dimensions

    def _validateEntityState(self, entity_state):
        if entity_state not in self.VALID_ENTITY_STATES:
            raise ArgValidationException(
                'Invalid entity state: must be %s' % self.VALID_ENTITY_STATES)

    def _modifyFieldsRequested(self, fields):
        fields_array = fields.split(',')

        # Always need the field "_key" regardless
        if len(fields_array) > 0:
            fields_array.append('_key')

        if 'informational_dimensions' in fields_array or 'identifier_dimensions' in fields_array:
            fields_array.append('dimensions')
        return ','.join(fields_array)

    def _getMappedDimensions(self, dimension_type, dimensions_list, dimensions_obj):
        dimensions_mapped = {}
        for dimension in dimensions_list:
            if type(dimensions_obj[dimension]) is not list:
                dimensions_obj[dimension] = [dimensions_obj[dimension]]
            dimensions_mapped[dimension] = dimensions_obj[dimension]
        dimensions_mapped = json.dumps(dimensions_mapped)
        return dimensions_mapped

    def _validateDimensionsValidJson(self, identifier, informational, dimensions):
        try:
            identifier_dimensions = json.loads(identifier) if type(
                identifier) is str else identifier
            informational_dimensions = json.loads(informational) if type(
                informational) is str else informational
            dimensions = json.loads(dimensions) if type(
                dimensions) is str else dimensions
        except Exception:
            raise ArgValidationException(
                'Invalid JSON supplied to REST handler!')

        # Make sure the correct arg types are provided for the endpoint
        if type(dimensions) is not dict:
            raise ArgValidationException(
                'Dimensions provided should be JSON object!')
        if type(informational_dimensions) is not list:
            raise ArgValidationException(
                'Informational dimensions provided should be list!')
        if type(identifier_dimensions) is not list:
            raise ArgValidationException(
                'Identifier dimensions provided should be list!')

        # If all the checks pass without exception, return the dimensions as
        # valid objects
        return (dimensions, informational_dimensions, identifier_dimensions)

    def _validateDimensionsExist(self, dimensionsObj, dimensionList):
        for dimension in dimensionList:
            if dimension not in dimensionsObj:
                message = 'Dimension "%s" provided does not exist in dimensions object!' % dimension
                raise ArgValidationException(message)

    def _get_related_collector_configs(self, entity, collector_configs):
        collector_names = set(collector['name'] for collector in entity.get('collectors'))
        return filter(lambda cc: cc['_key'] in collector_names, collector_configs)

    def _extractRelevantFields(self, entity, confInfo, collector_configs, locale):
        if 'title' in entity:
            confInfo[entity['_key']]['title'] = entity.get('title')
        if 'state' in entity:
            confInfo[entity['_key']]['state'] = entity.get('state')
        if 'imported_date' in entity:
            confInfo[entity['_key']][
                'imported_date'] = entity.get('imported_date')
        if 'updated_date' in entity:
            confInfo[entity['_key']][
                'updated_date'] = entity.get('updated_date')
        if 'collectors' in entity:
            confInfo[entity['_key']]['collectors'] = json.dumps(entity.get('collectors'))

            # From the collector(s), get the display names by locale and the vital metrics.
            all_display_names = []
            all_vital_metrics = []
            related_collector_configs = self._get_related_collector_configs(entity, collector_configs)
            for collector_config in related_collector_configs:
                dimension_display_names = collector_config.get(
                    'dimension_display_names', [])
                display_names = get_locale_specific_display_names(dimension_display_names,
                                                                  locale,
                                                                  collector_config['_key'])
                all_display_names.extend(display_names)
                vital_metrics = collector_config.get('vital_metrics', [])
                all_vital_metrics.extend(vital_metrics)
            confInfo[entity['_key']][
                'dimension_display_names'] = json.dumps(all_display_names)
            confInfo[entity['_key']][
                'vital_metrics'] = json.dumps(all_vital_metrics)

            # Add in event search filter
            search_filter = create_entity_log_filter(entity, related_collector_configs)
            confInfo[entity['_key']]['log_search'] = serialize(search_filter) if search_filter else None

        # Parse and validate the dimensions JSON
        informational = entity.get('informational_dimensions', [])
        identifier = entity.get('identifier_dimensions', [])
        dimensions = entity.get('dimensions', {})

        if 'informational_dimensions' in entity or 'identifier_dimensions' in entity:
            dimensions, informational_dimensions, identifier_dimensions = \
                self._validateDimensionsValidJson(
                    identifier, informational, dimensions)

            if 'informational_dimensions' in entity:
                informational_dimensions = \
                    self._getMappedDimensions(
                        'informational_dimensions', informational_dimensions, dimensions)
                confInfo[entity['_key']][
                    'informational_dimensions'] = informational_dimensions

            if 'identifier_dimensions' in entity:
                identifier_dimensions = \
                    self._getMappedDimensions(
                        'identifier_dimensions', identifier_dimensions, dimensions)
                confInfo[entity['_key']][
                    'identifier_dimensions'] = identifier_dimensions

    def _load_valid_metric_names_query_param(self, query_param):
        """
        Query params are expected to be a dictionary with dimension name as key, list of dimension values as value
        """
        message = ('Cannot parse query parameter: %s. ' % query_param +
                   'Expected format is {<dimension name>: [ <dimension values, wildcards>]}')
        # Check if it's a valid json string
        try:
            query_param = json.loads(query_param)
        except:
            raise ArgValidationException(message)
        if isinstance(query_param, dict):
            # Check if key is string and value is list
            is_query_param_valid = all(
                isinstance(key, basestring) and isinstance(value, list) for key, value in query_param.items())
            if is_query_param_valid is False:
                raise ArgValidationException(message)
        else:
            raise ArgValidationException(message)

        return query_param

    def _load_valid_metric_metadata_query(self, query_param):
        # {metric_name:cpu.idle, dimensions:{os:["ubuntu"]}}
        message = ('Cannot parse query parameter: %s. ' % query_param +
                   'Expected format is {metric_name: [metric_name], ' +
                   'dimensions: {<dimension name>: [ <dimension values, wildcards>]}}')
        # Check if it's a valid json string
        try:
            query_param = json.loads(query_param)
        except:
            raise ArgValidationException(message)
        if isinstance(query_param, dict):
            # Check if both metric_name and dimensions exist
            if 'metric_name' not in query_param:
                raise ArgValidationException('Missing required key: metric_name')
            metric_name = query_param['metric_name']
            dimensions = query_param.get('dimensions')
            # Check type for required key - metric_name
            if not isinstance(metric_name, basestring):
                raise ArgValidationException(
                    'Expected metric name to be a string.')
            if dimensions:
                # Check type for optional key - dimensions
                if not isinstance(dimensions, dict):
                    raise ArgValidationException(
                        'Expected dimensions to be a dict.')
                # Check if each key in dimensions is a string and each value is a list
                is_query_param_valid = all(
                    isinstance(key, basestring) and isinstance(value, list) for key, value in dimensions.iteritems())
                if is_query_param_valid is False:
                    raise ArgValidationException(
                        'Expected each key in dimensions to be a string, each value to be a list')
        else:
            raise ArgValidationException('Expected query param to be a dict')

        return query_param

    def _handleListAllConfigs(self, confInfo, count=0, offset=0, fields='', params={}):
        try:
            return self.collector_store.load(count=count, offset=offset, fields=fields, params=params)
        except Exception:
            raise EntityInternalException(
                'Cannot list all of the collector configurations saved!')

    def _handleListKey(self, confInfo, key):
        try:
            return self.entity_store.get(key)
        except Exception:
            raise EntityNotFoundException(
                'Cannot find the entity with id %s!' % key)

    def _handleListAll(self, confInfo, fields='', query_params={}, count=0, offset=0):
        try:
            return self.entity_store.load(count=count, offset=offset, fields=fields, params=query_params)
        except Exception:
            raise EntityInternalException(
                'Cannot list all of the entities saved!')
