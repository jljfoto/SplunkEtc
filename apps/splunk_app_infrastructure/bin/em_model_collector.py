# Copyright 2016 Splunk Inc. All rights reserved.
# Standard Python Libraries
import time
# Third-Party Libraries
# N/A
# Custom Libraries
from em_search_manager import EMSearchManager
from em_kvstore_manager import EMKVStoreManager
import em_constants
import em_common
import em_model_entity
import logging_utility

logger = logging_utility.getLogger()


class EMCollector(object):
    """
    Collector Model

    Attributes:
        session_key: Splunkd session_key
        _key: Primary key of collector in KVStore.
        _user: Owner of collector in KVStore.
        name: An unique string representing identifier of this collector in KVStore collection
        title: Title of entity.
        source_predicate: Predicate to discover entities from metric index.
          i.e. cpu.* (i.e. all metrics has metric_name start with cpu is OS metrics)
        title_dimension: Dimension to identify title field in entity model. i.e. host
        identifier_dimensions: Dimensions to identify identifier fields in entity model
        informational_dimensions: An array of dimension's name
            or '*' for everything except identifier dimensions.
            Dimensions to informational identifier fields in entity model
        monitoring_lag: It's possible there is a lag time
          when events hit HEC endpoint until events are indexed. Default is 15 seconds
        monitoring_calculation_window: Search timerange, how long does the search look back.
            Default is 3 minutes.
        dimension_display_names: array of dimension value to display names by dimension->locale
        disabled: Enabled or Disabled
        vital_metrics: Vital metrics for associated entities.
        correlated_event_data: object specifies base search filter and entity filter to get correlated
        log data to this collector
    """

    def __init__(self,
                 session_key=None,
                 _key=None,
                 _user=None,
                 name='',
                 title='',
                 source_predicate='',
                 title_dimension='',
                 identifier_dimensions=None,
                 informational_dimensions=None,
                 blacklisted_dimensions=None,
                 monitoring_lag=15,
                 monitoring_calculation_window=60 * 3,
                 dimension_display_names=None,
                 disabled=1,
                 correlated_event_data=None,
                 vital_metrics=None):
        """
        Return collector object
        """
        self.session_key = session_key
        self.name = name
        self.title = title
        self.source_predicate = source_predicate
        self.title_dimension = title_dimension
        self.identifier_dimensions = identifier_dimensions
        self.informational_dimensions = informational_dimensions
        self.blacklisted_dimensions = blacklisted_dimensions
        self.monitoring_lag = int(monitoring_lag)
        self.monitoring_calculation_window = int(monitoring_calculation_window)
        self.disabled = int(disabled)
        self.dimension_display_names = dimension_display_names if dimension_display_names else []
        self.correlated_event_data = correlated_event_data if correlated_event_data else {}
        self.vital_metrics = vital_metrics if vital_metrics else []
        if _key is None:
            self._key = name
        else:
            self._key = _key

    def is_valid(self):
        """
        Validate collector
        """
        is_valid = True
        if type(self.name) is not unicode:
            logger.error('EMCollector::Invalid type of name, unicode is required.')
            is_valid = False
        if type(self.title) is not unicode:
            logger.error('EMCollector::Invalid type of title, unicode is required.')
            is_valid = False
        if type(self.source_predicate) is not unicode:
            logger.error(
                'EMCollector::Invalid type of source_predicate, unicode is required.')
            is_valid = False
        if type(self.title_dimension) is not unicode:
            logger.error(
                'EMCollector::Invalid type of title_dimension, unicode is required.')
            is_valid = False
        if not (type(self.identifier_dimensions) is
                list or (type(self.identifier_dimensions) is unicode and
                         self.identifier_dimensions == '*')):
            logger.error(
                'EMCollector::Invalid type of identifier_dimensions, array or "*" is required.')
            is_valid = False
        if not (type(self.informational_dimensions) is
                list or (type(self.informational_dimensions) is unicode and
                         (self.informational_dimensions == '*' or
                          self.informational_dimensions == ''))):
            logger.error(
                'EMCollector::Invalid type of informational_dimensions, array or "*" or "" is required.')
            is_valid = False
        if not (type(self.blacklisted_dimensions) is
                list or (type(self.blacklisted_dimensions) is unicode and
                         self.blacklisted_dimensions == '')):
            logger.error(
                'EMCollector::Invalid type of blacklisted_dimensions, array or "" is required.')
            is_valid = False
        if type(self.monitoring_lag) is not int:
            logger.error(
                'EMCollector::Invalid type of monitoring_lag, number is required.')
            is_valid = False
        if type(self.monitoring_calculation_window) is not int:
            logger.error(
                'EMCollector::Invalid type of monitoring_calculation_window, number is required.')
            is_valid = False
        if type(self.dimension_display_names) is not list:
            logger.error(
                'EMCollector::Invalid type of dimension_display_names, must be a list')
            is_valid = False
        if not (type(self.disabled) is int or (self.disabled < 0 or self.disabled > 1)):
            logger.error(
                'EMCollector::Invalid type of disabled, 0 or 1 is required.')
            is_valid = False
        if type(self.vital_metrics) is not list:
            logger.error(
                'EMCollector::Invalid type of vital_metrics, must be a list')
            is_valid = False

        if not type(self.correlated_event_data) is dict:
            logger.error(
                'EMCollector::Invalid type of correlated_event_data, dict is required')
            is_valid = False
        return is_valid

    def get_entity(self, entity_dimensions):
        """
        Get entity from metrics idx by identifier dimensions.

        :param entity_dimensions: All dimensions (including identifier_dimensions) that are
            associated with a specific entity
            i.e. {
                    'host': 'wyoming.sa.com',
                    'server': 'staging',
                    'tag': ['USA', 'datagen', 'states'],
                    'ip': '10.10.0.49',
                    'os_version': '11.0',
                    'location': 'north americas',
                    'os': 'ubuntu'
                 }
        :return: EMEntity object
        """
        if entity_dimensions is None or self.session_key is None:
            return None
        entity_store = EMKVStoreManager(
            em_constants.STORE_ENTITIES,
            em_common.get_server_uri(),
            self.session_key,
            app=em_constants.APP_NAME)

        # dimension_names contains identifier_dimension name
        dimension_names = entity_dimensions.keys()
        id_dims = {id_dim: entity_dimensions.get(id_dim) for id_dim in self.identifier_dimensions}

        # This assumes that title_dimension should be an existing dimension
        entity_title = entity_dimensions.get(self.title_dimension)

        # If this entity exists then imported_date should be retained
        _key = em_common.get_key_from_dims(id_dims)
        entity = entity_store.get(key=_key)
        current_time = time.time()
        imported_date = current_time
        if entity is not None:
            imported_date = entity['imported_date']

        # Define entity dimensions
        entity_id_dims = None
        entity_info_dims = None

        # Merge identifier dimensions
        if type(self.identifier_dimensions) is list:
            entity_id_dims = list(
                set(self.identifier_dimensions) & set(dimension_names))
        elif type(self.identifier_dimensions) is unicode and self.identifier_dimensions == '*':
            entity_id_dims = dimension_names
        else:
            entity_id_dims = []

        # Merge informational dimensions
        if type(self.informational_dimensions) is list:
            entity_info_dims = list(
                set(self.informational_dimensions) & set(dimension_names))
        elif type(self.informational_dimensions) is unicode and self.informational_dimensions == '*':
            entity_info_dims = list(set(dimension_names) - set(entity_id_dims))
        else:
            entity_info_dims = []

        # Merge collector information
        collectors = [] if entity is None else entity.get('collectors', [])
        try:
            existing_collector_info_index = [x['name'] for x in collectors].index(self.name)
        except ValueError:
            existing_collector_info_index = -1

        if existing_collector_info_index == -1:
            collectors.append({'name': self.name, 'updated_date': current_time})
        else:
            collectors[existing_collector_info_index]['updated_date'] = current_time

        return em_model_entity.EMEntity(title=entity_title,
                                        dimensions=entity_dimensions,
                                        identifier_dimensions=entity_id_dims,
                                        informational_dimensions=entity_info_dims,
                                        state='active',
                                        imported_date=imported_date,
                                        updated_date=current_time,
                                        collectors=collectors)

    def discover_entities(self):
        """
        Discover entities from identifier dimensions

        :return: list of entities
        """
        search_manager = EMSearchManager(
            em_common.get_server_uri(), self.session_key, em_constants.APP_NAME)
        earliest = '-%ss' % (self.monitoring_calculation_window +
                             self.monitoring_lag)
        latest = '-%ss' % self.monitoring_lag

        dims_list = search_manager.get_dimension_names_by_id_dims(predicate=self.source_predicate,
                                                                  id_dims_name=self.identifier_dimensions,
                                                                  earliest=earliest,
                                                                  latest=latest,
                                                                  count=0)
        dimension_names = []
        for dims in dims_list:
            dimension_names += dims.get('dims', [])
        # Remove duplicates
        dimension_names = list(set(dimension_names))
        # Filter out black_listed dimensions
        dimension_names = filter(
            lambda d: d not in self.blacklisted_dimensions, dimension_names)

        # | mcatalog values(_dims) doesn't return native splunk dimensions
        # There are 3 native dimensions: host, source, sourcetype
        # If user wants to identify entity by those host then this search
        # won't work.
        # Hence, we need to add host to the list as dimension.
        if len(filter(lambda d: d == 'host', dimension_names)) == 0:
            dimension_names += ['host']

        # Get dimension name-value pairs for all entities
        entities_dimensions_list = search_manager.get_all_dims_from_dims_name(predicate=self.source_predicate,
                                                                              id_dims_name=self.identifier_dimensions,
                                                                              dims_name=dimension_names,
                                                                              earliest=earliest,
                                                                              latest=latest)
        entities = []
        for entity_dimensions in entities_dimensions_list:
            entities.append(self.get_entity(entity_dimensions))
        return entities
