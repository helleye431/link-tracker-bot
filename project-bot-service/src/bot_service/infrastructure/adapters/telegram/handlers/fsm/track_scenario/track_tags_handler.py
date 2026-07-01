from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot_service.infrastructure.adapters.telegram.handler_interfaces.fsm_handler import (
    FSMHandler,
)
from bot_service.infrastructure.adapters.telegram.states.track_states import TrackStates
from bot_service.infrastructure.adapters.telegram.markups.skip_markup import (
    skip_keyboard_markup,
)
import structlog

logger = structlog.get_logger(__name__)


class TrackTagsHandler(FSMHandler):

    @property
    def state(self):
        return TrackStates.waiting_for_tags

    async def handle(self, message: Message, state: FSMContext):

        text = message.text

        if text is None:
            await message.answer("Что-то пошло не так. Попробуйте ещё раз")
            return
        elif text == "" or text.strip().lower() == "пропустить":
            tags = []
        else:
            tags = [tag.strip() for tag in text.split(",")]

        await state.update_data(tags=tags)

        await message.answer(
            "Введите фильтры через запятую.\n"
            "Если хотите пропустить — напишите 'Пропустить'",
            reply_markup=skip_keyboard_markup,
        )

        await state.set_state(TrackStates.waiting_for_filters)
