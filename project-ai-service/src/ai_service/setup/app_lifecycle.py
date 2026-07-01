import asyncio
import signal

import structlog

from ai_service.application.common.runners.base_runner import BaseRunner

logger = structlog.get_logger(__name__)


class ApplicationLifecycle:
    def __init__(self, runners: list[BaseRunner]) -> None:
        self.runners = runners
        self.shutdown_event = asyncio.Event()

    def request_shutdown(self) -> None:
        if not self.shutdown_event.is_set():
            logger.info("application_shutdown_requested")
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

        shutdown_task = asyncio.create_task(
            self.shutdown_event.wait(),
            name="shutdown-waiter",
        )

        runner_tasks: list[asyncio.Task] = []

        try:
            for runner in self.runners:
                await runner.start()

            logger.info("application_runners_started", count=len(self.runners))

            runner_tasks = [
                asyncio.create_task(
                    runner.wait(),
                    name=f"runner-wait-{runner.__class__.__name__}",
                )
                for runner in self.runners
            ]

            done, _ = await asyncio.wait(
                [shutdown_task, *runner_tasks],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if shutdown_task in done:
                logger.info("application_shutdown_event_received")
                return

            for task in done:
                exc = task.exception()

                if exc is not None:
                    logger.exception(
                        "application_runner_failed",
                        task=task.get_name(),
                        error=str(exc),
                    )
                    raise exc

                logger.warning(
                    "application_runner_stopped_unexpectedly",
                    task=task.get_name(),
                )
                self.request_shutdown()

        except KeyboardInterrupt:
            logger.info("application_shutdown_requested_keyboard_interrupt")
            self.request_shutdown()

        except asyncio.CancelledError:
            logger.info("application_shutdown_requested_cancelled")
            self.request_shutdown()
            raise

        finally:
            logger.info("application_stopping")

            self.request_shutdown()

            for runner in reversed(self.runners):
                try:
                    await runner.stop()
                except Exception as exc:
                    logger.warning(
                        "application_runner_stop_failed",
                        runner=runner.__class__.__name__,
                        error=str(exc),
                    )

            for task in runner_tasks:
                if not task.done():
                    task.cancel()

            if not shutdown_task.done():
                shutdown_task.cancel()

            await asyncio.gather(
                shutdown_task,
                *runner_tasks,
                return_exceptions=True,
            )

            logger.info("application_stopped")
