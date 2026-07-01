from ai_service.application.ports.pendings_updates_repository_port import (
    PendingUpdatesRepositoryPort,
)
from ai_service.application.ports.update_processor_port import UpdateProcessorPort
from ai_service.domain.models.raw_update import RawUpdate
import structlog

logger = structlog.get_logger(__name__)


class UpdateProcessingService:
    def __init__(
        self,
        pending_updates_repository: PendingUpdatesRepositoryPort,
        update_processor: UpdateProcessorPort,
    ):
        self.pending_updates_repository = pending_updates_repository
        self.update_processor = update_processor

    async def process_update(self, update: RawUpdate) -> None:
        try:
            processed_update = await self.update_processor.process_update(update)
            if processed_update is None:
                logger.info("update_processing_skipped", raw_update=update)
                return

            logger.info("update_processing_success", processed_update=processed_update)

        except Exception as exc:
            logger.info(
                "update_processor_has_any_error",
                error=exc.__class__.__name__,
                message=str(exc),
            )
            raise

        self.pending_updates_repository.add_update(processed_update)

        logger.info("update_sent_to_window_storage", processed_update=processed_update)
