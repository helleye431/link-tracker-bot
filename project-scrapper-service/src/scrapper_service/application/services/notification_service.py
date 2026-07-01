import structlog

from scrapper_service.application.ports.notification_client_port import (
    NotificationClientPort,
)

logger = structlog.get_logger(__name__)


class NotificationService:
    """
    Сервис отправки уведомлений.

    Отвечает за отправку сообщений об обновлениях
    и сообщений об ошибках обработки ссылок
    через подключённые notification-клиенты.


    в параметр notification_client клиенты передавать строго в нужной очерёдности
    для задания fallback механизма
    """

    def __init__(self, notification_clients: list[NotificationClientPort]) -> None:
        self.notification_clients = notification_clients

    async def send_update_notification(
        self,
        update_id: int,
        url: str,
        description: str,
        author: str,
        chat_ids: list[int],
        is_error: bool = False,
    ) -> None:
        exceptions: list[Exception] = []
        for client in self.notification_clients:
            try:
                await client.send_update(
                    update_id=update_id,
                    url=url,
                    description=description,
                    author=author,
                    chat_ids=chat_ids,
                    is_error=is_error,
                )

                # в случае успешной отправки - fallback не применяем
                break

            except Exception as exc:
                logger.warning(
                    "sender_client_has_any_error",
                    client=client.__class__.__name__,
                    exception_name=exc.__class__.__name__,
                    exception_message=str(exc),
                    update_id=update_id,
                    url=url,
                    chat_ids=chat_ids,
                    is_error=is_error,
                )

                exceptions.append(exc)
        else:
            if exceptions:
                raise ExceptionGroup(
                    "notification_clients_failed",
                    exceptions,
                )
