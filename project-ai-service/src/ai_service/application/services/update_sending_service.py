from ai_service.application.ports.pendings_updates_repository_port import (
    PendingUpdatesRepositoryPort,
)
from ai_service.application.ports.update_sender_port import UpdateSenderPort
from ai_service.domain.models.processed_update import ProcessedUpdate
import structlog

logger = structlog.get_logger(__name__)


class UpdateSendingService:
    def __init__(
        self,
        pending_update_repository: PendingUpdatesRepositoryPort,
        update_sender: UpdateSenderPort,
    ):
        self.pending_update_repository = pending_update_repository
        self.update_sender = update_sender

    async def send_pending_updates(self) -> None:
        grouped_updates_info_list = (
            self.pending_update_repository.get_grouped_updates_info_with_keys()
        )

        processed_chat_ids: list[int] = []
        exceptions: list[Exception] = []

        for chat_id, grouped_updates_info in grouped_updates_info_list:
            processed_update = ProcessedUpdate(
                id=grouped_updates_info.id,
                description=grouped_updates_info.description,
                tgChatIds=[chat_id],
                is_error=grouped_updates_info.have_error,
                priority=grouped_updates_info.priority,
                url=grouped_updates_info.url,
            )

            try:
                await self.update_sender.send_update(update=processed_update)
            except Exception as exc:
                logger.warning(
                    "update_sending_error",
                    chat_id=chat_id,
                    update_id=grouped_updates_info.id,
                    error=exc.__class__.__name__,
                    message=str(exc),
                )
                exceptions.append(exc)
            else:
                processed_chat_ids.append(chat_id)

        self.pending_update_repository.clear_storage_by_keys(keys=processed_chat_ids)
        if exceptions:
            raise ExceptionGroup(
                "notification_sender_fails",
                exceptions,
            )
