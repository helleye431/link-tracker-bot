import asyncio
import threading
import structlog

from ai_service.application.ports.scheduler_port import SchedulerPort
from ai_service.application.services.update_sending_service import UpdateSendingService

logger = structlog.get_logger(__name__)


class UpdateSendingScheduler(SchedulerPort):
    def __init__(
        self,
        update_sending_service: UpdateSendingService,
        interval_milliseconds: int,
    ) -> None:
        self.update_sending_service = update_sending_service
        self.interval_milliseconds = interval_milliseconds
        self._stop_event = threading.Event()

    def run(self) -> None:

        logger.info(
            "scheduler_started",
            interval_milliseconds=self.interval_milliseconds,
        )

        while not self._stop_event.is_set():
            self._stop_event.wait(self.interval_milliseconds / 1000)

            logger.info("scheduler_iteration_started")

            try:
                asyncio.run(self.update_sending_service.send_pending_updates())
            except ExceptionGroup as exc:
                logger.warning(
                    "scheduler_iteration_finished_with_failures",
                    error=str(exc),
                    errors_count=len(exc.exceptions),
                )
            except Exception as exc:
                logger.exception(
                    "scheduler_iteration_failed",
                    error=str(exc),
                )
            else:
                logger.info("scheduler_iteration_finished")

        logger.info("scheduler_stopped")

    def stop(self) -> None:
        self._stop_event.set()
