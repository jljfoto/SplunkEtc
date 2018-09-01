import splunk.admin as admin

import logging_utility
from em_groups_interface_impl import EmGroupsInterfaceImpl
from em_common import Enum

logger = logging_utility.getLogger()


class EmGroupsInterface(admin.MConfigHandler):

    REQUIRED_PARAMS = ['title', 'filter']
    READ_OPTIONAL_PARAMS = ['query', 'filter_by_entity_ids', 'filter_by_entity_names']
    CUSTOM_ACTIONS = Enum(
        BULK_DELETE='bulk_delete',
        METADATA='metadata')

    def setup(self):
        # First, make sure specific args are allowed when using this interface
        # only with POST capability
        if self.requestedAction == admin.ACTION_CREATE or \
           self.requestedAction == admin.ACTION_EDIT:
            for arg in self.REQUIRED_PARAMS:
                self.supportedArgs.addReqArg(arg)
        elif self.customAction == self.CUSTOM_ACTIONS.BULK_DELETE:
            self.supportedArgs.addOptArg('query')
            self.supportedArgs.addReqArg('delete_query')
        if self.requestedAction == admin.ACTION_LIST and not self.customAction:
            for arg in self.READ_OPTIONAL_PARAMS:
                self.supportedArgs.addOptArg(arg)

    def handleCreate(self, confInfo):
        interface = EmGroupsInterfaceImpl()
        interface.handleCreate(self, confInfo)

    def handleList(self, confInfo):
        interface = EmGroupsInterfaceImpl()
        interface.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        interface = EmGroupsInterfaceImpl()
        interface.handleEdit(self, confInfo)

    def handleRemove(self, confInfo):
        interface = EmGroupsInterfaceImpl()
        interface.handleRemove(self, confInfo)

    def handleCustom(self, confInfo, **params):
        interface = EmGroupsInterfaceImpl()
        # check action type is bulk_delete
        if self.customAction == self.CUSTOM_ACTIONS.BULK_DELETE:
            interface.handleBulkDelete(self, confInfo)
        elif self.customAction == self.CUSTOM_ACTIONS.METADATA:
            interface.handleMetadata(self, confInfo)


admin.init(EmGroupsInterface, admin.CONTEXT_APP_ONLY)
