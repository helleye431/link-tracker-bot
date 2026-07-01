import asyncio
import contextlib

from scrapper_service.application.common.runners.base_runner import BaseRunner
from scrapper_service.infrastructure.background_workers.outbox.outbox_events_worker import (
    OutboxEventsWorker,
)
from structlog import get_logger

logger = get_logger(__name__)


class OutboxEventsWorkerRunner(BaseRunner):
    def __init__(self, outbox_processor_runner: OutboxEventsWorker) -> None:
        self.outbox_processor_runner = outbox_processor_runner
        self.task: asyncio.Task | None = None

    async def start(self) -> None:
        logger.info("outbox_runner_starting")

        self.task = asyncio.create_task(
            self.outbox_processor_runner.run(),
            name="outbox-processor-runner",
        )

        logger.info(
            "outbox_runner_started",
            task_done=self.task.done(),
        )

    async def wait(self) -> None:
        if self.task is not None:
            await self.task

    async def stop(self) -> None:
        self.outbox_processor_runner.stop()

        if self.task is not None and not self.task.done():
            self.task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await self.task
