class ChatAlreadyExistsError(Exception):
    def __init__(self, chat_id: int) -> None:
        self.chat_id = chat_id
        super().__init__(f"Чат {chat_id} уже существует")


class ChatNotFoundError(Exception):
    def __init__(self, chat_id: int) -> None:
        self.chat_id = chat_id
        super().__init__(f"Чат {chat_id} не найден")
