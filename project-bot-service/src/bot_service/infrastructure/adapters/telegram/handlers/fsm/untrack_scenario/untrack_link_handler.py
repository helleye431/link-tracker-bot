from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot_service.application.services.tracking_service import TrackingService
from bot_service.application.exceptions.service_exceptions import (
    LinkInvalidError,
    ServiceError,
    LinkNotFoundError,
)

from bot_service.infrastructure.adapters.telegram.handler_interfaces.fsm_handler import (
    FSMHandler,
)
from bot_service.infrastructure.adapters.telegram.states.track_states import TrackStates
import structlog

logger = structlog.get_logger(__name__)


class UntrackLinkHandler(FSMHandler):
    def __init__(self, tracking_service: TrackingService):
        self.tracking_service = tracking_service

    @property
    def state(self):
        return TrackStates.waiting_for_untrack_link

    async def handle(self, message: Message, state: FSMContext):

        url = message.text

        try:
            await self.tracking_service.untrack_link(
                chat_id=message.chat.id,
                url=url,
            )

        except LinkInvalidError:

            await message.answer(
                "Ссылка некорректна.\n"
                "Проверьте её и отправьте заново.\n\n"
                "Для отмены используйте /cancel"
            )
            return

        except LinkNotFoundError:

            await message.answer(
                "Ссылка не найдена.\n"
                "Попробуйте другую ссылку.\n\n"
                "Для отмены используйте /cancel"
            )
            return
        except ServiceError as exc:
            await message.answer(str(exc))
            return

        await state.clear()

        await message.answer("Ссылка убрана из отслеживания.\n" "Список команд - /help")
