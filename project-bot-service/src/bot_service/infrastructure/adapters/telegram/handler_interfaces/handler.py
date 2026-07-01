from abc import ABC, abstractmethod
from aiogram.types import Message
from aiogram.fsm.context import FSMContext


class Handler(ABC):
    @abstractmethod
    async def handle(self, message: Message, state: FSMContext) -> None:
        """Метод обработки входящего сообщения"""
        pass
