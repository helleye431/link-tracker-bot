import structlog
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from bot_service.infrastructure.adapters.telegram.handler_interfaces.command_handler import (
    CommandHandler,
)

logger = structlog.get_logger(__name__)


class HelpHandler(CommandHandler):
    """Обработчик команды /help"""

    def __init__(self):
        self._handlers = []

    def set_handlers(self, handlers: list[CommandHandler]) -> None:
        self._handlers = handlers

    @property
    def name(self) -> str:
        return "help"

    @property
    def description(self) -> str:
        return "Список команд"

    async def handle(self, message: Message, state: FSMContext):

        user = message.from_user.id if message.from_user else None
        logger.info(
            "help command received",
            user_id=user,
        )

        # Авто-генерация на основе существующих обработчиков

        text = "Доступные команды\n" + "\n".join(
            f"/{handler.name} - {handler.description}" for handler in self._handlers
        )
        await state.clear()
        await message.answer(text)
