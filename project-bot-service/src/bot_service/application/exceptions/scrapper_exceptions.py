class ScrapperClientError(Exception):
    pass


class ScrapperBadRequestError(ScrapperClientError):
    pass


class ScrapperChatNotFoundError(ScrapperClientError):
    pass


class ScrapperChatAlreadyExistsError(ScrapperClientError):
    pass


class ScrapperLinkAlreadyExistsError(ScrapperClientError):
    pass


class ScrapperLinkNotFoundError(ScrapperClientError):
    pass
