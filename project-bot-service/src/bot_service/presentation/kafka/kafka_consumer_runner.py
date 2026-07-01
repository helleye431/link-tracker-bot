import asyncio

from bot_service.presentation.kafka.kafka_notification_consumer import (
    KafkaNotificationConsumer,
)
from bot_service.application.common.runners.base_runner import BaseRunner


class KafkaConsumerRunner(BaseRunner):
    def __init__(self, consumer: KafkaNotificationConsumer):
        self.consumer = consumer
        self.task: asyncio.Task | None = None

    async def start(self) -> None:
        self.task = asyncio.create_task(
            self.consumer.start_consumption(),
            name="kafka-consumer",
        )

    async def wait(self) -> None:
        if self.task is not None:
            await self.task

    async def stop(self) -> None:
        self.consumer.stop()

        if self.task is not None and not self.task.done():
            self.task.cancel()

        if self.task is not None:
            await asyncio.gather(self.task, return_exceptions=True)
