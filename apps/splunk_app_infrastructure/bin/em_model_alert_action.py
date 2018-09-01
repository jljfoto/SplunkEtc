from abc import ABCMeta, abstractmethod
import re
from em_exceptions import AlertActionInvalidArgsException


class EMAlertAction(object):
    """
    Abstract class of all alert actions
    """

    __metaclass__ = ABCMeta

    def __init__(self, action_name, **action_params):
        self.action_name = action_name
        for k, v in action_params.iteritems():
            setattr(self, k, v)
        self.validate()

    @abstractmethod
    def validate(self):
        """
        Override this method to validate action parameters
        :return:
        """
        pass

    def to_params(self):
        """
        turn action into savedsearch conf params foramt
        :return: dict
        """
        res = {}
        action_param = 'action.%s' % self.action_name
        for k, v in vars(self).iteritems():
            if k is not 'action_name':
                param_key = '%s.param.%s' % (action_param, k)
                if isinstance(v, list):
                    v = ','.join(v)
                res[param_key] = v
        return res


class EMEmailAlertAction(EMAlertAction):
    """
    Email alert action class
    """
    ACTION_NAME = 'em_send_email'
    SUPPORTED_EMAIL_NOTIFICATION_CRITERIA = ['improve', 'degrade']

    def __init__(self, email_to, email_when):
        if not isinstance(email_when, list):
            email_when = [email_when]
        if not isinstance(email_to, list):
            email_to = [email_to]
        super(EMEmailAlertAction, self).__init__(
            action_name=EMEmailAlertAction.ACTION_NAME,
            email_to=email_to,
            email_when=email_when
        )

    def validate(self):
        for criteria in self.email_when:
            if criteria not in EMEmailAlertAction.SUPPORTED_EMAIL_NOTIFICATION_CRITERIA:
                raise AlertActionInvalidArgsException("email notification criteria %s is not one of "
                                                      "the supported criteria %s" %
                                                      (criteria,
                                                       EMEmailAlertAction.SUPPORTED_EMAIL_NOTIFICATION_CRITERIA))

        if len(self.email_to) == 0:
            raise AlertActionInvalidArgsException("No email_to provided")

        for email_address in self.email_to:
            if not email_address or not re.match(r"[^@]+@[^@]+\.[^@]+", email_address):
                raise AlertActionInvalidArgsException("Invalid email address: %s" % email_address)


class EMWriteAlertAction(EMAlertAction):
    """
    Write alert to alert index custom action
    """
    ACTION_NAME = 'em_write_alerts'

    def __init__(self):
        super(EMWriteAlertAction, self).__init__(action_name=EMWriteAlertAction.ACTION_NAME)

    def validate(self):
        pass
