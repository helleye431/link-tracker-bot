import asyncio
import contextlib

from ai_service.application.common.runners.base_runner import BaseRunner


class UpdateSendingSchedulerRunner(BaseRunner):
    def __init__(self, scheduler) -> None:
        self.scheduler = scheduler
        self.task: asyncio.Task | None = None

    async def start(self) -> None:
        self.task = asyncio.create_task(
            asyncio.to_thread(self.scheduler.run),
            name="scheduler-runners",
        )

    async def wait(self) -> None:
        if self.task is not None:
            await self.task

    async def stop(self) -> None:
        self.scheduler.stop()

        if self.task is not None and not self.task.done():
            self.task.cancel()

            with contextlib.suppress(asyncio.CancelledError):
                await self.task
