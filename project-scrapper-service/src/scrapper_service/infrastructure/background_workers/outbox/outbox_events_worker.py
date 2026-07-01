import asyncio
import structlog

from scrapper_service.application.services.outbox_events_processor import (
    OutboxEventsProcessor,
)

logger = structlog.get_logger(__name__)


class OutboxEventsWorker:

    def __init__(
        self,
        processor: OutboxEventsProcessor,
        outbox_processing_delay: float,
    ) -> None:
        self.processor = processor
        self.outbox_processing_delay = outbox_processing_delay
        self.running = True

    async def run(self) -> None:
        logger.info(
            "outbox_events_worker_started",
            delay_seconds=self.outbox_processing_delay,
        )

        while self.running:
            logger.info("outbox_events_worker_iteration_started")
            try:
                processed_count = await self.processor.process_current_events()

                if processed_count:
                    logger.info(
                        "outbox_processor_processed_events",
                        events_count=processed_count,
                    )

            except asyncio.CancelledError:
                logger.info("outbox_processor_runner_cancelled")
                self.running = False
                raise

            except Exception as exc:
                logger.exception(
                    "outbox_processor_iteration_failed",
                    error=str(exc),
                )
            finally:
                logger.info(
                    "outbox_processor_iteration_finished",
                )
            await asyncio.sleep(self.outbox_processing_delay)

        logger.info("outbox_processor_runner_stopped")

    def stop(self) -> None:
        self.running = False
