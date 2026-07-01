import asyncio
import grpc

from bot_service.application.common.runners.base_runner import BaseRunner


class GrpcServerRunner(BaseRunner):
    """
    Управляет жизненным циклом gRPC-сервера:
    запуском, ожиданием завершения и остановкой.
    """

    def __init__(self, server: grpc.aio.Server):
        self.server = server
        self.task: asyncio.Task | None = None

    async def start(self) -> None:
        await self.server.start()
        self.task = asyncio.create_task(
            self.server.wait_for_termination(),
            name="grpc-server",
        )

    async def wait(self) -> None:
        if self.task is not None:
            await self.task

    async def stop(self) -> None:
        await self.server.stop(grace=5)

        if self.task is not None and not self.task.done():
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
