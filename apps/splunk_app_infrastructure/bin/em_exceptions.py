import splunk.admin as admin

import logging_utility

logger = logging_utility.getLogger()


class EmException(admin.AdminManagerException):
    """
    Generic exception class
    """

    def __init__(self, message):
        super(EmException, self).__init__(message)
        self.message = message
        logger.error(message)


class SavedsearchInternalException(EmException):

    def __init__(self, message):
        super(SavedsearchInternalException, self).__init__(message)


class AlertInternalException(EmException):

    def __init__(self, message):
        super(AlertInternalException, self).__init__(message)


class AlertActionInvalidArgsException(EmException):

    def __init__(self, message):
        super(AlertActionInvalidArgsException, self).__init__(message)


class ThresholdInvalidArgsException(EmException):

    def __init__(self, message):
        super(ThresholdInvalidArgsException, self).__init__(message)


class ArgValidationException(EmException):

    def __init__(self, message):
        super(ArgValidationException, self).__init__(message)


class EntityAlreadyExistsException(EmException):

    def __init__(self, message):
        super(EntityAlreadyExistsException, self).__init__(message)


class EntityInternalException(EmException):

    def __init__(self, message):
        super(EntityInternalException, self).__init__(message)


class EntityNotFoundException(EmException):

    def __init__(self, message):
        super(EntityNotFoundException, self).__init__(message)


class GroupInternalException(EmException):

    def __init__(self, message):
        super(GroupInternalException, self).__init__(message)


class GroupNotFoundException(EmException):

    def __init__(self, message):
        super(GroupNotFoundException, self).__init__(message)


class CollectorConfigurationInternalException(EmException):

    def __init__(self, message):
        super(CollectorConfigurationInternalException, self).__init__(message)


class CollectorConfigurationNotFoundException(EmException):

    def __init__(self, message):
        super(CollectorConfigurationNotFoundException, self).__init__(message)
