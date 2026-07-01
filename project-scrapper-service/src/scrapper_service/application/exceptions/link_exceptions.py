class LinkAlreadyExistsError(Exception):
    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(f"Ссылка {url} уже существует")


class LinkNotFoundError(Exception):
    def __init__(self, url: str) -> None:
        self.url = url
        super().__init__(f"Ссылка {url} не найдена")
