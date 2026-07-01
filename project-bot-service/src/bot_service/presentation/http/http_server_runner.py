import asyncio
import uvicorn
from bot_service.application.common.runners.base_runner import BaseRunner


class HttpServerRunner(BaseRunner):
    """
    Управляет жизненным циклом HTTP-сервера:
    запуском, ожиданием завершения и остановкой.
    """

    def __init__(self, server: uvicorn.Server):
        self.server = server
        self.task: asyncio.Task | None = None

    async def start(self) -> None:
        self.task = asyncio.create_task(
            self.server.serve(),
            name="http-server",
        )

    async def wait(self) -> None:
        if self.task is not None:
            await self.task

    async def stop(self) -> None:
        self.server.should_exit = True

        if self.task is not None:
            await asyncio.gather(self.task, return_exceptions=True)
