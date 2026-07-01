from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot_service.application.exceptions.service_exceptions import (
    ChatNotFoundError,
    ServiceError,
)
from bot_service.infrastructure.adapters.telegram.handler_interfaces.command_handler import (
    CommandHandler,
)
from bot_service.application.services.tracking_service import TrackingService
import structlog

logger = structlog.get_logger(__name__)


class ListHandler(CommandHandler):
    def __init__(self, tracking_service: TrackingService):
        self.tracking_service = tracking_service

    @property
    def name(self) -> str:
        return "list"

    @property
    def description(self) -> str:
        return "Получить список отслеживаемых ссылок"

    async def handle(self, message: Message, state: FSMContext):
        await state.clear()
        chat_id = message.chat.id

        if not message.text:
            await message.answer("Некорректный ввод. Попробуйте ещё раз")
            return
        text = message.text.strip()
        text_parts = text.split()

        if len(text_parts) == 2:
            tag = text_parts[1]
        elif len(text_parts) == 1:
            tag = None
        else:
            await message.answer(
                "Некорректный ввод команды.\n"
                "Для использования команды с параметром необходимо написать /list <tag>"
            )
            return

        try:
            links = await self.tracking_service.get_list_links(chat_id, tag)
        except ChatNotFoundError:
            await message.answer(
                "Чат не зарегистрирован, воспользуйтесь командой /start"
            )
        except ServiceError as exc:
            await message.answer(str(exc))

        else:
            if not links:
                await message.answer("Отслеживаемых ссылок нет")
                return

            msg = "Список отслеживаемых ссылок:\n\n" + "\n".join(
                f"{link.url}\n"
                f"Последнее отслеживание: {link.last_seen_update or 'не поддерживается'}\n"
                f"Теги: {', '.join(link.tags)}\n"
                f"Фильтры: {', '.join(link.filters)}\n\n"
                for link in links
            )
            await message.answer(msg)
