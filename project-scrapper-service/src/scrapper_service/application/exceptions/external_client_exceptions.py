class ExternalServiceException(Exception):
    pass


class GithubServiceError(ExternalServiceException):
    pass


class StackoverflowServiceError(ExternalServiceException):
    pass


class GithubLinkValidationError(ExternalServiceException):
    pass


class StackoverflowLinkValidationError(ExternalServiceException):
    pass


class ClientForLinkNotFoundError(ExternalServiceException):
    pass
