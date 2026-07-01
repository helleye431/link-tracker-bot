from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from bot_service.infrastructure.adapters.telegram.handler_interfaces.command_handler import (
    CommandHandler,
)
import structlog

logger = structlog.get_logger(__name__)


class UnknownHandler(CommandHandler):
    """
    Обработчик неизвестных команд

    Вызывается, если команда начинается с '/',
    но отсутствует среди зарегистрированных.
    """

    @property
    def name(self) -> str:
        return "unknown"

    @property
    def description(self) -> str:
        return "Обработка неизвестных команд"

    async def handle(self, message: Message, state: FSMContext) -> None:
        user = message.from_user.id if message.from_user else None

        logger.warning("unknown command", text=message.text, user_id=user)
        await state.clear()
        await message.answer("Неизвестная команда. Воспользуйтесь /help.")
