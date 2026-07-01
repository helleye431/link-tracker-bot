from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot_service.application.exceptions.service_exceptions import ServiceError
from bot_service.application.services.tracking_service import TrackingService
from bot_service.infrastructure.adapters.telegram.states.track_states import TrackStates
from bot_service.infrastructure.adapters.telegram.handler_interfaces.fsm_handler import (
    FSMHandler,
)


class TrackFiltersHandler(FSMHandler):

    def __init__(self, tracking_service: TrackingService):
        self.tracking_service = tracking_service

    @property
    def state(self):
        return TrackStates.waiting_for_filters

    async def handle(self, message: Message, state: FSMContext):

        text = message.text

        if text is None:
            await message.answer("Что-то пошло не так. Попробуйте ещё раз")
            return
        elif text == "" or text.strip().lower() == "пропустить":
            filters = []
        else:
            filters = [f.strip() for f in text.split(",")]

        data = await state.get_data()
        try:
            await self.tracking_service.track_link(
                chat_id=message.chat.id,
                url=data["link"],
                tags=data["tags"],
                filters=filters,
            )
        except ServiceError as exc:
            await message.answer(str(exc))
            return

        await message.answer("Ссылка успешно добавлена")

        await state.clear()
