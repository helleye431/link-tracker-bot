import asyncio
import threading
import structlog

from scrapper_service.application.ports.scheduler_port import SchedulerPort
from scrapper_service.application.services.link_update_processor_service import (
    LinkUpdateProcessorService,
)

logger = structlog.get_logger(__name__)


class LinkScheduler(SchedulerPort):
    def __init__(
        self,
        processor: LinkUpdateProcessorService,
        interval_seconds: int = 60,
    ) -> None:
        self.processor = processor
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()

    def run(self) -> None:
        logger.info("scheduler_started", interval_seconds=self.interval_seconds)

        while not self._stop_event.is_set():
            try:
                logger.info("scheduler_iteration_started")
                failed_urls = asyncio.run(self.processor.process_updates())

                if failed_urls:
                    logger.warning(
                        "scheduler_iteration_finished_with_failures",
                        failed_count=len(failed_urls),
                        failed_urls=failed_urls,
                    )
                else:
                    logger.info("scheduler_iteration_finished")
            except Exception as exc:
                logger.exception("scheduler_iteration_failed", error=str(exc))

            self._stop_event.wait(self.interval_seconds)

        logger.info("scheduler_stopped")

    def stop(self) -> None:
        self._stop_event.set()
