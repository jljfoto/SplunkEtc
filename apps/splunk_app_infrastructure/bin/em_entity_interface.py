import splunk.admin as admin

from em_entity_interface_impl import EmEntityInterfaceImpl
from em_common import Enum


class EmEntityInterface(admin.MConfigHandler):

    WRITE_OPTIONAL_PARAMS = ['title', 'state', 'identifier_dimensions',
                             'informational_dimensions', 'dimensions']
    READ_OPTIONAL_PARAMS = ['query', 'fields', 'display_name_locale']
    CUSTOM_ACTIONS = Enum(
        BULK_DELETE='bulk_delete',
        METADATA='metadata',
        METRIC_NAME='metric_name',
        METRIC_DATA='metric_data')

    def setup(self):
        ra = self.requestedAction
        ca = self.customAction
        if ra == admin.ACTION_CREATE or ra == admin.ACTION_EDIT:
            for arg in self.WRITE_OPTIONAL_PARAMS:
                self.supportedArgs.addOptArg(arg)
        if ra == admin.ACTION_LIST and not ca:
            for arg in self.READ_OPTIONAL_PARAMS:
                self.supportedArgs.addOptArg(arg)
        elif ca == self.CUSTOM_ACTIONS.BULK_DELETE:
            self.supportedArgs.addOptArg('query')
            self.supportedArgs.addReqArg('delete_query')
        elif ca == self.CUSTOM_ACTIONS.METRIC_NAME or ca == self.CUSTOM_ACTIONS.METRIC_DATA:
            self.supportedArgs.addOptArg('query')

    def handleList(self, confInfo):
        interface = EmEntityInterfaceImpl()
        interface.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        interface = EmEntityInterfaceImpl()
        interface.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        interface = EmEntityInterfaceImpl()
        interface.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        interface = EmEntityInterfaceImpl()
        interface.handleRemove(self, confInfo)

    def handleCustom(self, confInfo, **params):
        interface = EmEntityInterfaceImpl()
        if self.customAction == self.CUSTOM_ACTIONS.BULK_DELETE:
            interface.handleBulkDelete(self, confInfo)
        elif self.customAction == self.CUSTOM_ACTIONS.METADATA:
            interface.handleMetadata(self, confInfo)
        elif self.customAction == self.CUSTOM_ACTIONS.METRIC_NAME:
            interface.handleMetricName(self, confInfo)
        elif self.customAction == self.CUSTOM_ACTIONS.METRIC_DATA:
            interface.handleMetricData(self, confInfo)


admin.init(EmEntityInterface, admin.CONTEXT_APP_ONLY)
