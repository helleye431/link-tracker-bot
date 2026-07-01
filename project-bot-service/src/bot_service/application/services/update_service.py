from pydantic import HttpUrl
from bot_service.application.ports.telegram_port import TelegramPort
import structlog

logger = structlog.get_logger(__name__)


class UpdateService:
    """
    Сервис доставки уведомлений пользователям Telegram.

    Принимает информацию об обновлении ссылки и рассылает
    уведомления всем указанным chat_id.
    Ошибки доставки отдельным пользователям не прерывают
    рассылку остальным.
    """

    def __init__(self, telegram_service: TelegramPort):
        self.telegram_service = telegram_service

    async def send_updates(
        self, url: HttpUrl | None, tg_chat_ids: list[int], description: str | None
    ) -> None:
        # обработка при объединённых обновлениях
        if url is None:
            message = (
                f"Получено несколько обновлений"
                f"\nОписания:"
                f"\n{description}"
                f"\nПроверьте изменения при необходимости"
                f"\nВоспользуйтесь /list для получения списка ссылок c подробной информацией"
            )
        else:
            message = (
                f"Получено обновление"
                f"\nОписание:"
                f"\n{description}"
                f"\nПроверьте изменения при необходимости"
                f"\nВоспользуйтесь /list для получения списка ссылок c подробной информацией"
            )
        for chat_id in tg_chat_ids:

            try:
                await self.telegram_service.send_message(
                    chat_id=chat_id, message=message
                )
            except Exception as exc:
                logger.warning("bot client error", exception=str(exc), chat_id=chat_id)
                raise

    async def send_error_report(
        self, url: HttpUrl, tg_chat_ids: list[int], description: str | None
    ):
        for chat_id in tg_chat_ids:
            message = (
                f"Произошла ошибка обработки ссылки {url}\n"
                f"Подробное описание:\n"
                f"{description}"
            )
            try:
                await self.telegram_service.send_message(
                    chat_id=chat_id, message=message
                )
            except Exception as exc:
                logger.warning("bot client error", exception=str(exc), chat_id=chat_id)
                raise
