# Copyright 2016 Splunk Inc. All rights reserved.
# Environment configuration
import em_declare  # noqa
# Standard Python Libraries
import sys
import time
# Third-Party Libraries
import modinput_wrapper.base_modinput
from splunklib import modularinput as smi
# Custom Libraries
from em_entity_discovery_controller import EMEntityDiscoveryController
from em_kvstore_manager import EMKVStoreManager
import em_constants
import em_common


class EMEntityManager(modinput_wrapper.base_modinput.SingleInstanceModInput):
    """
    Entity Manager modular input
    This ModInput is responsible for:
        - Entity Discovery: By fetching metrics/dimensions from Metrics Catalog API

    """

    def __init__(self):
        """
        Init modular input for entity discovery
        """
        super(EMEntityManager, self).__init__('em', 'entity_manager')

    def get_scheme(self):
        """
        Overloaded splunklib modularinput method
        """
        scheme = smi.Scheme('em_entity_manager')
        scheme.title = ('Splunk Insights for Infrastructure - Entity Manager')
        scheme.description = (
            'Entity Manager helps to discover and manage your entities')
        log_level = 'The logging level of the modular input. Defaults to DEBUG'
        scheme.add_argument(smi.Argument('log_level', title='Log Level',
                                         description=log_level,
                                         required_on_create=False))

        return scheme

    def get_app_name(self):
        """
        Overloaded splunklib modularinput method
        """
        return em_constants.APP_NAME

    def validate_input(self, definition):
        """
        Overloaded splunklib modularinput method
        """
        pass

    def add_fixture(self):
        """
        Add fixture data

        :return: void
        """
        collector_store = EMKVStoreManager(
            em_constants.STORE_COLLECTORS,
            em_common.get_server_uri(),
            self.session_key,
            app=em_constants.APP_NAME)
        collectors = collector_store.load()
        existing_collector_names = set(c['name'] for c in collectors)
        all_collector_names = set(c['name'] for c in em_constants.COLLECTORS)
        common = existing_collector_names.intersection(all_collector_names)
        # create new collectors
        for c in em_constants.COLLECTORS:
            if c['name'] not in common:
                collector_store.create(key=c['name'], data=c)
        # delete outdated collectors
        for c in collectors:
            if c['name'] not in all_collector_names:
                collector_store.delete(key=c['name'])

    def init_stores(self):
        """
        Initialize stores

        :return: void
        """
        # Init local session key
        self.session_key = self._input_definition.metadata['session_key']
        # Add fixture data
        self.add_fixture()

    def collect_events(self, inputs, ew):
        """
        Main loop function, run every "interval" seconds

        :return: void
        """
        input_stanza, stanza_args = inputs.inputs.popitem()

        # Initialize stores
        self.init_stores()

        # Initialize controller
        self.entityDiscoveryController = EMEntityDiscoveryController(
            self.session_key)
        # Discovery new entities
        self.entityDiscoveryController.discover_entities()


if __name__ == '__main__':
    # Wait till KVStore's ready
    time.sleep(3)

    exitcode = EMEntityManager().run(sys.argv)
    sys.exit(exitcode)
    pass
