# Copyright 2016 Splunk Inc. All rights reserved.
# Standard Python Libraries
# Third-Party Libraries
# N/A
# Custom Libraries
from em_model_collector import EMCollector
from em_model_entity import EMEntity
from em_kvstore_manager import EMKVStoreManager
import em_constants
import em_common
import logging_utility

logger = logging_utility.getLogger()


class EMEntityDiscoveryController(object):
    """
    Entity Discovery Controller

    Attributes:
      session_key: Session key for the current job

    """

    def __init__(self, session_key=''):
        """
        Return EMEntityDiscoveryController object
        """
        self.session_key = session_key
        self.collector_store = EMKVStoreManager(
            em_constants.STORE_COLLECTORS,
            em_common.get_server_uri(),
            self.session_key,
            app=em_constants.APP_NAME)
        self.entity_store = EMKVStoreManager(
            em_constants.STORE_ENTITIES,
            em_common.get_server_uri(),
            self.session_key,
            app=em_constants.APP_NAME)
        self.all_collectors = self._get_all_collectors()
        self.all_entities = self._get_all_entities()

    def _is_valid_collector(self, c):
        """
        Validate whether the collector should be evaluted
        """
        if not c.is_valid():
            return False
        if c.disabled == 1:
            return False
        return True

    def _get_all_collectors(self):
        """
        Get all available collectors from KVStore

        :return: List of collectors in KVSTore
        """
        collectors = []
        for c in self.collector_store.load():
            cx = None
            try:
                cx = EMCollector(session_key=self.session_key, **c)
                if self._is_valid_collector(cx):
                    collectors.append(cx)
            except Exception, e:
                logger.error('Invalid collector record from KVStore: %s' % str(cx))
                logger.error(str(e))
        return collectors

    def _get_all_entities(self):
        """
        Get all available entities from KVStore

        :return: List of entities in KVSTore
        """
        # This is heavv load but there is no way to update
        # entity state if we don't load all entities
        entities = []
        for e in self.entity_store.load():
            try:
                ex = EMEntity(**e)
                entities.append(ex)
            except Exception:
                logger.error('Invalid entity record from KVStore: %s' % str(e))
        return entities

    def discover_entities(self):
        """
        Discover entities
        """
        logger.debug('Start discover entities...')
        available_entities = []
        for c in self.all_collectors:
            logger.debug('Collector: %s', c.name)
            available_entities.extend(c.discover_entities())
        self.update_entity_availability(available_entities)
        logger.debug('Finish discover entities...')

    def update_entity_availability(self, available_entities=None):
        """
        Update availability for entities in KVStore.
        Mark Active for one we received
        events, inactive for one not received events

        :params available_entities: available entities
        :return: void
        """
        data_list = []
        inactive_entity_keys = (set([entity._key for entity in self.all_entities]) -
                                set([aval_entity._key for aval_entity in available_entities]))

        # Update all available entities
        for entity in available_entities:
            entity.set_active()
            data_list.append(entity.get_raw_data())

        # Update all inactive entities
        for entity in self.all_entities:
            if entity._key in inactive_entity_keys:
                entity.set_inactive()
                data_list.append(entity.get_raw_data())

        self.entity_store.batch_save(data_list)
