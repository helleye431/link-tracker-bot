from redis.asyncio import Redis

from bot_service.application.ports.delivered_notifications_storage_port import (
    DeliveredNotificationsStoragePort,
)


class RedisDeliveredNotificationsStorage(DeliveredNotificationsStoragePort):
    def __init__(self, redis_url: str, ttl_seconds: int) -> None:
        self.redis = Redis.from_url(
            redis_url,
            decode_responses=True,
        )
        self.ttl_seconds = ttl_seconds

    async def is_delivered(self, update_id: int, chat_id: int) -> bool:
        key = self._make_key(update_id, chat_id)

        return bool(await self.redis.exists(key))

    async def mark_delivered(self, update_id: int, chat_id: int) -> None:
        key = self._make_key(update_id, chat_id)

        await self.redis.set(
            name=key,
            value="1",
            ex=self.ttl_seconds,
        )

    async def close(self) -> None:
        await self.redis.aclose()

    @staticmethod
    def _make_key(event_id: int, chat_id: int) -> str:
        return f"delivered_notification:{event_id}:{chat_id}"
