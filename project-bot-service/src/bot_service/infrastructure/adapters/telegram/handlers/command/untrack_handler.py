from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from bot_service.infrastructure.adapters.telegram.handler_interfaces.command_handler import (
    CommandHandler,
)
from bot_service.infrastructure.adapters.telegram.states.track_states import TrackStates
import structlog

logger = structlog.get_logger(__name__)


class UntrackHandler(CommandHandler):

    @property
    def name(self):
        return "untrack"

    @property
    def description(self):
        return "Прекратить отслеживание ссылки"

    async def handle(self, message: Message, state: FSMContext):
        user = message.from_user.id if message.from_user else None
        logger.info(
            "untrack command received",
            user_id=user,
        )

        await state.set_state(TrackStates.waiting_for_untrack_link)
        logger.info(
            "set state: waiting for untrack link",
            user_id=user,
        )
        await message.answer("Напишите ссылку для прекращения отслеживания")
