import structlog
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot_service.application.exceptions.service_exceptions import (
    ChatAlreadyExistsError,
    ServiceError,
)
from bot_service.infrastructure.adapters.telegram.handler_interfaces.command_handler import (
    CommandHandler,
)
from bot_service.application.services.tracking_service import TrackingService

logger = structlog.get_logger(__name__)


class StartHandler(CommandHandler):
    """Обработчик команды /start"""

    def __init__(self, tracking_service: TrackingService):
        self.tracking_service = tracking_service

    @property
    def name(self) -> str:
        return "start"

    @property
    def description(self) -> str:
        return "Начать работу"

    async def handle(self, message: Message, state: FSMContext):
        try:
            await self.tracking_service.register_chat(message.chat.id)
        except ChatAlreadyExistsError:
            pass
        except ServiceError as exc:
            await message.answer(str(exc))
            return

        user = message.from_user.id if message.from_user else None
        logger.info("start command received", user_id=user)
        await state.clear()
        await message.answer("Добро пожаловать!\nИспользуйте /help.")
