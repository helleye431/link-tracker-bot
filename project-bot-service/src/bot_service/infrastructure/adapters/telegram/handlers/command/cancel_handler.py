import structlog
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from bot_service.infrastructure.adapters.telegram.handler_interfaces.command_handler import (
    CommandHandler,
)

logger = structlog.get_logger(__name__)


class CancelHandler(CommandHandler):
    """Обработчик команды /cancel"""

    @property
    def name(self) -> str:
        return "cancel"

    @property
    def description(self) -> str:
        return "Отменить действие"

    async def handle(self, message: Message, state: FSMContext):
        user = message.from_user.id if message.from_user else None
        logger.info(
            "cancel command received",
            user_id=user,
        )

        await state.clear()
        await message.answer(
            "Действие отменено\nВоспользуйтесь /help для дальнейшей работы"
        )
