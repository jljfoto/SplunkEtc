import em_common as EMCommon
from em_savedsearch_manager import EMSavedSearchManager
from em_model_threshold import EMThreshold
from em_model_alert_action import EMEmailAlertAction, EMWriteAlertAction
from em_model_alert import EMAlert
from splunk.util import normalizeBoolean
from em_exceptions import AlertInternalException
import logging_utility

logger = logging_utility.getLogger()


class EMAlertInterfaceImpl(object):
    """
    Interface implementation for EMAlertInterface class
    """
    _manager = None

    def __init__(self, session_key):
        self._manager = EMSavedSearchManager(
            server_uri=EMCommon.get_server_uri(),
            session_key=session_key
        )

    def handleList(self, callerArgs, confInfo):
        """
        get info about an individual alert savedsearch if name is specified in callerArgs
        otherwise list existing savedsearches
        :param callerArgs:
        :param confInfo:
        :return:
        """
        name = callerArgs.id
        # get an individual alert savedsearch
        if name:
            response = self._manager.get(name)
            self._write_to_conf_info(response, confInfo)
        # list alert savedsearches
        else:
            count, offset = callerArgs.get('count', -1), callerArgs.get('offset', 0)
            response = self._manager.load(count, offset)
            self._write_to_conf_info(response, confInfo)

    def handleEdit(self, callerArgs, confInfo):
        """
        edit an existing alert savedsearch
        :param callerArgs:
        :param confInfo:
        :return:
        """
        name = callerArgs.id
        metric_spl = callerArgs.data.get('metric_spl', [None])[0]
        managed_by_id = callerArgs.data.get('managed_by_id', [None])[0]
        managed_by_type = callerArgs.data.get('managed_by_type', [None])[0]
        if name and metric_spl and managed_by_id:
            threshold = self._build_threshold(callerArgs.data)
            actions = self._build_alert_actions(callerArgs.data)
            alert = self._build_alert(
                name=name,
                managed_by=managed_by_id,
                managed_by_type=managed_by_type,
                metric_spl=metric_spl,
                threshold=threshold,
                actions=actions
            )
            alert_params = alert.to_params()
            # name in data body should be only used for creation
            del alert_params['name']
            response = self._manager.update(name, alert_params)
            self._write_to_conf_info(response, confInfo)
        else:
            raise AlertInternalException('Invalid arguments')

    def handleCreate(self, callerArgs, confInfo):
        """
        create new alert savedsearch
        :param callerArgs:
        :param confInfo:
        :return:
        """
        name = callerArgs.id
        metric_spl = callerArgs.data.get('metric_spl', [None])[0]
        managed_by_id = callerArgs.data.get('managed_by_id', [None])[0]
        managed_by_type = callerArgs.data.get('managed_by_type', [None])[0]
        if name and metric_spl and managed_by_id and managed_by_type:
            threshold = self._build_threshold(callerArgs.data)
            actions = self._build_alert_actions(callerArgs.data)
            alert = self._build_alert(
                name=name,
                managed_by=managed_by_id,
                managed_by_type=managed_by_type,
                metric_spl=metric_spl,
                threshold=threshold,
                actions=actions
            )
            response = self._manager.create(alert.to_params())
            self._write_to_conf_info(response, confInfo)
        else:
            raise AlertInternalException('Invalid arguments')

    def handleRemove(self, callerArgs, confInfo):
        """
        remove an alert savedsearch
        :param callerArgs:
        :param confInfo:
        :return:
        """
        name = callerArgs.id
        response = self._manager.delete(name)
        self._write_to_conf_info(response, confInfo)

    def _build_alert(self, name, managed_by, managed_by_type, metric_spl, threshold, actions):
        """
        build alert savedsearch spl
        :param name: name of the alert
        :param managed_by: id of the entity/group that this alert belongs to
        :param managed_by_type: type of object that manages this alert
        :param metric_spl: base SPL that extract metric data
        :param threshold: an instance of EMThreshold object
        :param actions: custom alert actions to take -- type: EMAlertAction or its subclass
        :return: an instance of EMAlert
        """
        if not isinstance(actions, list):
            actions = [actions]
        return EMAlert(
            name=name,
            managed_by=managed_by,
            managed_by_type=managed_by_type,
            metric_spl=metric_spl,
            threshold=threshold,
            actions=actions
        )

    def _build_threshold(self, threshold_info):
        """
        build a threshold object
        :param threshold_info: threshold info should contain threshold values like info_min, info_max etc
        :return: an instance of EMThreshold object
        """
        def get_threshold_value(name):
            return float(threshold_info.get(name, [None])[0])
        return EMThreshold(
            info_min=get_threshold_value('info_min'),
            info_max=get_threshold_value('info_max'),
            warning_min=get_threshold_value('warning_min'),
            warning_max=get_threshold_value('warning_max'),
            critical_min=get_threshold_value('critical_min'),
            critical_max=get_threshold_value('critical_max'),
        )

    def _build_alert_actions(self, alert_action_info):
        """
        build alert actions based on caller args
        :param alert_action_info: alert action info should contain require parameters for a specific alert action
        :return: an alert action object
        """
        email_enabled = normalizeBoolean(alert_action_info.get('email_enabled', [False])[0])
        actions = []
        # add em send email alert action if enabled
        if email_enabled:
            email_to_list = EMCommon.string_to_list(alert_action_info.get('email_to', [''])[0], sep=',')
            email_when_list = EMCommon.string_to_list(alert_action_info.get('email_when', [''])[0], sep=',')
            email_action = EMEmailAlertAction(
                email_to=email_to_list,
                email_when=email_when_list
            )
            actions.append(email_action)
        # add default write alert action
        write_alert_action = EMWriteAlertAction()
        actions.append(write_alert_action)
        return actions

    def _write_to_conf_info(self, response, confInfo):
        """
        write response from savedsearch manager to confInfo
        :param response: json response
        :param confInfo: confInfo object to write to
        :return:
        """
        entries = response.get('entry', [])
        for entry in entries:
            name, content = entry['name'], entry['content']
            for k, v in content.iteritems():
                confInfo[name][k] = v
