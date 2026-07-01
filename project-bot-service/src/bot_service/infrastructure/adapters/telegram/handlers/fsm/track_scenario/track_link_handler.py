from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot_service.application.services.tracking_service import TrackingService
from bot_service.application.exceptions.service_exceptions import (
    LinkInvalidError,
    LinkAlreadyExistsError,
    ServiceError,
    ChatNotFoundError,
    LinkDomainNotSupported,
)
from bot_service.infrastructure.adapters.telegram.markups.skip_markup import (
    skip_keyboard_markup,
)
from bot_service.infrastructure.adapters.telegram.handler_interfaces.fsm_handler import (
    FSMHandler,
)
from bot_service.infrastructure.adapters.telegram.states.track_states import TrackStates
import structlog

logger = structlog.get_logger(__name__)


class TrackLinkHandler(FSMHandler):
    def __init__(self, tracking_service: TrackingService):
        self.tracking_service = tracking_service

    @property
    def state(self):
        return TrackStates.waiting_for_link

    async def handle(self, message: Message, state: FSMContext):

        url = message.text

        try:
            validated_url = await self.tracking_service.validate_new_link(
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

        except LinkDomainNotSupported:

            await message.answer(
                "Домен ссылки не поддерживается.\n"
                "Пожалуйста, выберите другую ссылку для отслеживания.\n"
                f"Поддерживаемые домены на текущий момент: "
                f"{', '.join(self.tracking_service.validated_domains)}\n"
                "Для отмены используйте /cancel"
            )
        except LinkAlreadyExistsError:

            await message.answer(
                "Эта ссылка уже отслеживается.\n"
                "Попробуйте другую ссылку.\n\n"
                "Для отмены используйте /cancel"
            )
            return
        except ChatNotFoundError:
            await message.answer("Чат не зарегистрирован.\n" "Введите команду /start")
        except ServiceError as exc:
            await message.answer(str(exc))
            return

        else:
            # передача http url дальше
            await state.update_data(link=validated_url)

            await message.answer(
                "Введите теги через запятую.\n"
                "Если хотите пропустить — напишите 'Пропустить'",
                reply_markup=skip_keyboard_markup,
            )

            await state.set_state(TrackStates.waiting_for_tags)
