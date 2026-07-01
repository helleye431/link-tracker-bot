import structlog
from scrapper_service.application.ports.tracking_repository_port import (
    TrackingRepositoryPort,
)
from scrapper_service.application.services.notification_service import (
    NotificationService,
)

logger = structlog.get_logger(__name__)


class OutboxEventsProcessor:
    """
    Обрабатывает transactional outbox.

    Забирает события из outbox-таблицы,
    отправляет их во внешний брокер сообщений
    и заполняет им дату отправки.
    """

    def __init__(
        self,
        repository: TrackingRepositoryPort,
        notification_service: NotificationService,
    ) -> None:
        self.repository = repository
        self.notification_service = notification_service
        self.running = True

    async def process_current_events(self) -> int:
        events = await self.repository.get_pending_events()

        if not events:
            return 0

        logger.info(
            "outbox_events_loaded",
            count=len(events),
        )

        processed_count = 0

        for event in events:
            try:
                await self.notification_service.send_update_notification(
                    update_id=event.update_id,
                    url=event.url,
                    description=event.description,
                    author=event.author,
                    chat_ids=event.tg_chat_ids,
                    is_error=event.is_error,
                )

                await self.repository.mark_as_sent(
                    outbox_event_id=event.id,
                )

                processed_count += 1

                logger.info(
                    "outbox_event_sent",
                    outbox_event_id=event.id,
                    update_id=event.update_id,
                )

            except Exception as exc:

                logger.warning(
                    "outbox_event_send_failed",
                    outbox_event_id=event.id,
                    update_id=event.update_id,
                    error=str(exc),
                )

        return processed_count

    def stop(self) -> None:
        self.running = False
