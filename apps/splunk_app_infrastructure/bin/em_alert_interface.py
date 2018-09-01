import splunk.admin as admin

from em_alert_interface_impl import EMAlertInterfaceImpl


class EMAlertInterface(admin.MConfigHandler):
    """
    Alert interface for CRUD operation
    """
    # threshold info , critical and warning min and max values
    WRITE_REQUIRED_PARAMS = ['metric_spl',
                             'managed_by_id',
                             'managed_by_type',
                             'info_min', 'info_max',
                             'warning_min', 'warning_max',
                             'critical_min', 'critical_max']
    READ_OPTIONAL_PARAMS = [
        # notification settings
        'email_enabled', 'email_to', 'email_when',
        # read param
        'count', 'offset'
    ]
    _interface_impl = None

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self._interface_impl = EMAlertInterfaceImpl(self.getSessionKey())

    def setup(self):
        if self.requestedAction == admin.ACTION_CREATE or self.requestedAction == admin.ACTION_EDIT:
            for arg in self.WRITE_REQUIRED_PARAMS:
                self.supportedArgs.addReqArg(arg)
        if self.requestedAction != admin.ACTION_REMOVE:
            for arg in self.READ_OPTIONAL_PARAMS:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        self._interface_impl.handleList(self.callerArgs, confInfo)

    def handleEdit(self, confInfo):
        self._interface_impl.handleEdit(self.callerArgs, confInfo)

    def handleCreate(self, confInfo):
        self._interface_impl.handleCreate(self.callerArgs, confInfo)

    def handleRemove(self, confInfo):
        self._interface_impl.handleRemove(self.callerArgs, confInfo)

admin.init(EMAlertInterface, admin.CONTEXT_APP_ONLY)
