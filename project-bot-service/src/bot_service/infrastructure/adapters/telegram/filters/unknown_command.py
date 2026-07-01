from aiogram.filters import BaseFilter
from aiogram.types import Message


class UnknownCommandFilter(BaseFilter):
    """
    Фильтр неизвестных команд

    Пропускает сообщения:
    - начинающиеся с '/'
    - отсутствующие в списке известных команд
    """

    def __init__(self, known_commands: list[str]):
        self.known_commands = set(known_commands)

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False

        if not message.text.startswith("/"):
            return False

        command = message.text.split()[0][1:].lower()
        return command not in self.known_commands
