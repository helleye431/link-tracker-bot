import asyncio
from bot_service.application.ports.telegram_port import TelegramPort
from bot_service.application.common.runners.base_runner import BaseRunner
import structlog
import signal

logger = structlog.get_logger(__name__)


class ApplicationLifecycle:
    def __init__(
        self,
        telegram_client: TelegramPort,
        server_runners: list[BaseRunner],
    ) -> None:
        self.telegram_client = telegram_client
        self.server_runners = server_runners
        self.shutdown_event = asyncio.Event()

    def request_shutdown(self) -> None:
        if not self.shutdown_event.is_set():
            logger.info("bot_shutdown_requested")
            self.shutdown_event.set()

    def setup_signal_handlers(self) -> None:
        loop = asyncio.get_running_loop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self.request_shutdown)
            except NotImplementedError:
                pass

    async def run(self) -> None:
        self.setup_signal_handlers()

        bot_task = asyncio.create_task(
            self.telegram_client.run(),
            name="telegram-bot",
        )

        shutdown_task = asyncio.create_task(
            self.shutdown_event.wait(),
            name="shutdown-waiter",
        )

        server_tasks: list[asyncio.Task] = []

        try:
            for runner in self.server_runners:
                await runner.start()

            logger.info(
                "bot_server_runners_started",
                count=len(self.server_runners),
            )

            server_tasks = [
                asyncio.create_task(
                    runner.wait(),
                    name=f"server-runner-{runner.__class__.__name__}",
                )
                for runner in self.server_runners
            ]

            done, _ = await asyncio.wait(
                [shutdown_task, bot_task, *server_tasks],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if shutdown_task in done:
                logger.info("bot_shutdown_event_received")
                return

            for task in done:
                if task.cancelled():
                    logger.info(
                        "bot_task_cancelled",
                        task=task.get_name(),
                    )
                    self.request_shutdown()
                    continue

                exc = task.exception()

                if exc is not None:
                    logger.exception(
                        "bot_task_failed",
                        task=task.get_name(),
                        error=str(exc),
                    )
                    raise exc

                logger.warning(
                    "bot_task_stopped_unexpectedly",
                    task=task.get_name(),
                )
                self.request_shutdown()

        except KeyboardInterrupt:
            logger.info("bot_shutdown_requested_keyboard_interrupt")
            self.request_shutdown()

        except asyncio.CancelledError:
            logger.info("bot_shutdown_requested_cancelled")
            self.request_shutdown()
            raise

        except Exception as exc:
            logger.exception("bot_application_crashed", error=str(exc))
            raise

        finally:
            logger.info("bot_stopping")

            self.request_shutdown()

            for runner in reversed(self.server_runners):
                try:
                    await runner.stop()
                except Exception as exc:
                    logger.warning(
                        "bot_server_runner_stop_failed",
                        runner=runner.__class__.__name__,
                        error=str(exc),
                    )

            try:
                await self.telegram_client.shutdown()
            except Exception as exc:
                logger.warning(
                    "telegram_client_shutdown_failed",
                    error=str(exc),
                )

            for task in [bot_task, *server_tasks]:
                if not task.done():
                    task.cancel()

            if not shutdown_task.done():
                shutdown_task.cancel()

            await asyncio.gather(
                shutdown_task,
                bot_task,
                *server_tasks,
                return_exceptions=True,
            )

            logger.info("bot_stopped")
