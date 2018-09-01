# Copyright 2016 Splunk Inc. All rights reserved.
# Environment configuration
# N/A
# Standard Python Libraries
import json
# Third-Party Libraries
import splunk.rest as rest
import em_common
import em_constants as EMConstants
from em_exceptions import ArgValidationException
# Custom Libraries
# N/A
import logging_utility

logger = logging_utility.getLogger()


class EMSearchManager(object):
    """
    Search REST Endpoint service
    """

    CUSTOM_SEARCH_CMD = 'emgroupentitymatch'

    def __init__(self,
                 server_uri,
                 session_key,
                 app,
                 owner='nobody'):
        """
        Return object of SearchManager service
        """
        self.server_uri = server_uri
        self.session_key = session_key
        self.app = app
        self.owner = owner

    def search_uri(self):
        """
        :return: uri
        """
        return '%s/servicesNS/%s/%s/search/jobs' % (self.server_uri,
                                                    self.owner,
                                                    self.app)

    def search_one_shot(self,
                        spl='',
                        earliest='-24h',
                        latest='now',
                        count=0):
        """
        Search and get result by one shot

        :param spl: SPL query
        :param earliest: earliest time
        :param latest: latest time
        :param count: limit number of result
        :return: result object
        """
        data = {
            'search': spl,
            'output_mode': 'json',
            'exec_mode': 'oneshot',
            'earliest_time': earliest,
            'latest_time': latest,
            'count': count,
        }

        response, content = rest.simpleRequest(
            self.search_uri(),
            sessionKey=self.session_key,
            method="POST",
            postargs=data)

        result = json.loads(content)
        return result

    def get_search_template(self):
        return {
            'count_of_entities_by_group': '| inputlookup %s \
                | %s selectedGroupIds="%s"\
                | stats count, count(eval(state="%s")) as active_entities, \
                count(eval(state="%s")) as inactive_entities, \
                count(eval(state="%s")) as disabled_entities by group_id',
            'filter_groups_by': '| inputlookup %s where %s \
                | rename title as entity_title \
                | %s \
                | stats count, count(eval(state="%s")) as active_entities, \
                count(eval(state="%s")) as inactive_entities, \
                count(eval(state="%s")) as disabled_entities by group_id',
            'entities_and_collector_names_by_group': '| inputlookup %s \
                | rename title as entity_title \
                | %s selectedGroupIds="%s" \
                | rename collectors.name as collector_names \
                | fields + dimensions.* collector_names'
        }

    def get_all_dims_from_dims_name(self,
                                    predicate='',
                                    id_dims_name=[],
                                    dims_name=[],
                                    earliest='-24h',
                                    latest='now',
                                    count=0):
        """
        Get list of dimensions name-value for all entities

        :param predicate: What metric to search for.
            i.e. cpu.* (All metric has metric_name starts by cpu.*)
        :param id_dims_name: Set of dimensions to identify entity
            i.e. ['ip','host']
        :pram dims_name: Set of dimensions name to search for
            i.e. ['ip', 'db_instance_id','host']
        :param earliest: earliest time
        :param latest: latest time
        :param count: limit number of result
        :return: list of dimensions for all entities
        """
        id_predicate = ','.join(id_dims_name)
        values_part = ''
        for d in dims_name:
            if d not in id_dims_name:
                values_part += 'values(%s) as %s ' % (d, d)
        spl = '| mcatalog %s WHERE metric_name=%s BY %s' % (
            values_part, predicate, id_predicate)
        results = self.search_one_shot(spl, earliest, latest, count)
        res = []
        if 'results' in results and len(results['results']) > 0:
            res = results['results']
            logger.info('Received dimensions for all entities')
        return em_common.always_list(res)

    def get_dimension_names_by_id_dims(self,
                                       predicate='',
                                       id_dims_name=[],
                                       earliest='-24h',
                                       latest='now',
                                       count=0):
        """
        Get dimension names by identifier_dimensions

        :param predicate: What metric to search for.
            i.e. cpu.* (All metric has metric_name starts by cpu.*)
        :param id_dims_name: List of dimensions name to identify entity
            i.e. ['ip', 'host']
        :param earliest: earliest time
        :param latest: latest time
        :param count: limit number of result
        :return: [{dims:['os','tag']}, {dims:['os','env']}]
        """
        iden_fields = set(id_dims_name)
        fields_part = ''
        for iden in iden_fields:
            fields_part += 'values(%s) ' % iden
        fields_list = ', '.join(iden_fields)
        spl = '| mcatalog %s, values(_dims) as dims WHERE metric_name=%s BY %s | table dims' % (
            fields_part, predicate, fields_list)
        results = self.search_one_shot(spl, earliest, latest, count)
        res = []
        if 'results' in results and len(results['results']) > 0:
            res = results['results']
            logger.info('Retrieved dimension names by identifier dimensions')
        return em_common.always_list(res)

    def get_count_of_entities_by_group(self,
                                       groups,
                                       earliest='-24h',
                                       latest='now',
                                       count=0):
        """
        Get entities of a group based on group filter

        :param group: group object
        :param earliest: earliest time
        :param latest: latest time
        :param count: limit number of result
        :return: {'test-1': 1, 'test-2': 5, ....}
        """
        groups_title_filter = ','.join(g.get('name', '') for g in groups)
        spl = self.get_search_template().get('count_of_entities_by_group') % \
            (EMConstants.STORE_ENTITIES,
             self.CUSTOM_SEARCH_CMD,
             groups_title_filter,
             EMConstants.ACTIVE,
             EMConstants.INACTIVE,
             EMConstants.DISABLED)
        results = self.search_one_shot(spl, earliest, latest, count)
        logger.info('retrieved count of entities by group')
        return EMSearchManager.parse_group_entites_count_results(results)

    def get_metric_names_by_dim_names(self,
                                      dimensions={},
                                      earliest='-24h',
                                      latest='now',
                                      count=0):
        """
        Get metric names by dimension names

        :param dimensions: Dictionary of dimension name and values.
            Dimension values should support *
            i.e. {'location': ['seattle', 'san francisco'], 'os': ['ubuntu', '*']}
        :param earliest: earliest time
        :param latest: latest time
        :param count: limit number of result
        :return: [{metric_names:['cpu.idle','cpu.nice']}]
        """
        # mstats requires metric_name keyword after WHERE
        mstats_base_command = '| mstats min(_value) as min, max(_value) as max WHERE metric_name=*'
        eval_round_command = '| eval min=round(min,2), max=round(max,2)'
        if not dimensions:
            spl = '%s BY metric_name %s' % (mstats_base_command, eval_round_command)
        else:
            filter_fields = []
            for dim_name, dim_values in dimensions.iteritems():
                # First add double quotes to each dimension value
                dimensions[dim_name] = map('"{}"'.format, dim_values)
                # Values of the same dimension name should be "OR"
                filter_fields.append(
                    ' OR '.join('{0}={1}'.format(*dim_pair) for dim_pair in zip(
                        [dim_name] * len(dim_values), dim_values)))

            # Values between dimension names should be "AND"
            dim_filter = ' AND '.join(map('({})'.format, filter_fields))
            spl = '%s AND %s BY metric_name %s' % (mstats_base_command, dim_filter, eval_round_command)
        results = self.search_one_shot(spl, earliest, latest, count)
        res = []
        if 'results' in results and len(results['results']) > 0:
            res = results['results']
            logger.info('Retrieved metric names by dimension names')
        return em_common.always_list(res)

    def get_avg_metric_val_by_entity(self,
                                     execute_search=True,
                                     metric_name='',
                                     entities=[],
                                     collector_config={},
                                     earliest='-24h',
                                     latest='now',
                                     count=0):
        """
        Get average metric value by entity

        NOTE: This assumes that each entity is associated with a collector.
        For entities without a collector (created via REST), this doesn't return any result.

        The sample generated spl search:

        | mstats avg(_value) as value WHERE metric_name=* AND (InstanceId=abc) BY InstanceId
        | rename InstanceId as title | append [
            | mstats avg(_value) as value WHERE metric_name=* AND (host=34e00aa51d81 OR host=maine.usa.com) BY host
            | rename host as title
        ] | eval value=round(value,2) | table title, value | lookup em_entities title OUTPUT _key as key
        | fields key, value

        :param metric_name: Selected single metric name to calculate average value for
            i.e. 'cpu.idle'
        :param entities: Entities to calulate metric value from
        :param collector_config: collector name-title mapping.
            Used to map collector name of entities to title dimensions of collectors
        :param earliest: earliest time
        :param latest: latest time
        :param count: limit number of result
        :return: [{'key': 'asdasd', 'value': '49.78'},
                  {'key': 'fghfgh', 'value': '48.96'}...]
        """
        if not entities or not collector_config:
            return []
        else:
            base_mstats_cmd = '| mstats avg(_value) as value'
            eval_cmd = '| eval value=round(value,2)'
            table_cmd = '| table title, value'
            lookup_cmd = '| lookup em_entities title OUTPUT _key as key | fields key, value'
            cur_collector_name_set = set([entity['collectors'][0].values()[0] for entity in entities])
            title_dimension_set = set([collector_config[collector_name] for collector_name in cur_collector_name_set])
            mstats_cmds = []
            # Create mstats command for each title dimension
            for title in title_dimension_set:
                filtered_entities = [
                    entity for entity in entities if collector_config[entity['collectors'][0].values()[0]] == title]
                filter_fields = ['{0}={1}'.format(
                    title, entity['dimensions'].get(title)) for entity in filtered_entities]
                where_clause = 'WHERE metric_name=%s AND (%s)' % (metric_name, ' OR '.join(filter_fields))
                by_cmd = 'BY %s' % title
                rename_cmd = 'rename %s as title' % title
                mstats_for_cur_title_dim = ' '.join([base_mstats_cmd, where_clause, by_cmd])
                complete_spl = ' | '.join([mstats_for_cur_title_dim, rename_cmd])
                mstats_cmds.append(complete_spl)

            # Synax reformat - wrap mstats cmd with [] except for the first one
            for idx, cmd in enumerate(mstats_cmds):
                if idx != 0:
                    mstats_cmds[idx] = '[ %s ]' % cmd

            final_spl = ' '.join([' | append '.join(mstats_cmds), eval_cmd, table_cmd, lookup_cmd])
            if execute_search:
                results = self.search_one_shot(final_spl, earliest, latest, count)
                res = []
                if 'results' in results and len(results['results']) > 0:
                    res = results['results']
                    logger.info('Retrieved metric value per entity')
                return res
            else:
                return final_spl

    BY_ENTITY_IDS = 0
    BY_ENTITY_NAMES = 1

    def filter_groups_by(self,
                         criteria,
                         earliest='-24h',
                         latest='now',
                         count=0):

        spl_template = self.get_search_template().get('filter_groups_by')

        def by_entity_ids(entity_ids):
            entity_predicate = ' OR '.join(
                map(lambda e: '_key="%s"' % e, entity_ids))
            return execute_spl(entity_predicate)

        def by_entity_names(entity_names):
            entity_predicate = ' OR '.join(
                map(lambda e: 'title="%s"' % e, entity_names))
            return execute_spl(entity_predicate)

        def execute_spl(entity_predicate):
            spl = spl_template % (EMConstants.STORE_ENTITIES,
                                  entity_predicate,
                                  self.CUSTOM_SEARCH_CMD,
                                  EMConstants.ACTIVE,
                                  EMConstants.INACTIVE,
                                  EMConstants.DISABLED)
            results = self.search_one_shot(spl, earliest, latest, count)
            return EMSearchManager.parse_group_entites_count_results(results)

        if criteria == EMSearchManager.BY_ENTITY_IDS:
            return by_entity_ids
        elif criteria == EMSearchManager.BY_ENTITY_NAMES:
            return by_entity_names
        else:
            raise ArgValidationException('Filter criteria specified is not allowed!')

    @staticmethod
    def parse_group_entites_count_results(results):
        res = {}
        if 'results' in results and len(results['results']) > 0:
            for record in results['results']:
                res[record.get('group_id')] = {}
                res[record.get('group_id')]['count'] = int(record.get('count'))
                res[record.get('group_id')]['inactive'] = int(record.get('inactive_entities'))
                res[record.get('group_id')]['active'] = int(record.get('active_entities'))
                res[record.get('group_id')]['disabled'] = int(record.get('disabled_entities'))
        return res

    def get_entities_and_collector_names_by_group(self,
                                                  group_name,
                                                  earliest='-24h',
                                                  latest='now',
                                                  count=0):
        """
        get entities and collector information about a group

        :param group_name: str, the id/name of the group (not title)
        :param earliest: earliest time
        :param latest: latest time
        :param count: limit number of result
        :return: a dictionary with keys being collector names & values being the list of entities in
                 this group and were discovered by this collector.

                 example:
                 { 'os': [
                        { 'dimensions': {'location': 'seattle', 'tag': 'planets', 'host': 'mars.planets.com', ...}},
                        { 'dimensions': {'location': 'seattle', 'tag': 'planets', 'host': 'mars.planets.com', ...}}
                    ],
                   'aws_cloudwatch_ec2': [
                        { <dimensions about an ec2 instance entity>.... },
                        { .... }
                    ]
                 }
        """
        spl_template = self.get_search_template().get('entities_and_collector_names_by_group')
        spl = spl_template % (EMConstants.STORE_ENTITIES,
                              self.CUSTOM_SEARCH_CMD,
                              group_name)
        results = self.search_one_shot(spl, earliest, latest, count)
        res = {}
        if 'results' in results and len(results['results']) > 0:
            for record in results['results']:
                collector_names = em_common.always_list(record.get('collector_names', []))
                for collector_name in collector_names:
                    entity_info = {'dimensions': {}}
                    for dim, val in record.iteritems():
                        if dim.startswith('dimensions.'):
                            entity_info['dimensions'][dim[len('dimensions.'):]] = em_common.always_list(record[dim])
                    res.setdefault(collector_name, []).append(entity_info)
        return res
