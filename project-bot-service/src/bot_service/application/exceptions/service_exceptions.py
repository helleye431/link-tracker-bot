class ServiceException(Exception):
    pass


class ChatAlreadyExistsError(ServiceException):
    def __init__(self, chat_id: int) -> None:
        self.chat_id = chat_id
        super().__init__(f"Чат {chat_id} уже зарегистрирован")


class ChatNotFoundError(ServiceException):
    def __init__(self, chat_id: int) -> None:
        self.chat_id = chat_id
        super().__init__(f"Чат {chat_id} не найден")


class LinkAlreadyExistsError(ServiceException):
    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(f"Ссылка {url} уже отслеживается")


class LinkNotFoundError(ServiceException):
    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(f"Ссылка {url} не найдена")


class LinkInvalidError(ServiceException):
    def __init__(self, url: str):
        self.url = url
        super().__init__(f"Ссылка {url} некорректна")


class LinkDomainNotSupported(ServiceException):
    def __init__(self, url: str):
        self.url = url
        super().__init__(f"Домен ссылки {url} не поддерживается")


class ServiceError(ServiceException):
    def __init__(self):
        super().__init__("Сервис сейчас недоступен, попробуйте позже")
