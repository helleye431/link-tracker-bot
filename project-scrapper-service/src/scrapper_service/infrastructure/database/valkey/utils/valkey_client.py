from glide import (
    GlideClusterClient,
    GlideClusterClientConfiguration,
    NodeAddress,
)
from cachetools import TTLCache


class ValkeyClient:
    """
    Класс обёртка valkey client с возможностью memory client side cache (TTL only)
    """

    def __init__(
        self,
        client: GlideClusterClient,
        enable_client_cache: bool = False,
        client_cache_ttl: int = 5,
        client_cache_maxsize: int = 10_000,
    ) -> None:
        self.client = client
        self.enable_cache_storage = enable_client_cache

        self.cache: TTLCache[str, bytes | None] = TTLCache(
            maxsize=client_cache_maxsize,
            ttl=client_cache_ttl,
        )

    @classmethod
    async def create(
        cls,
        valkey_addresses: list[tuple[str, int]],
        enable_client_cache: bool = False,
        client_cache_ttl: int = 5,
        client_cache_maxsize: int = 10_000,
    ) -> "ValkeyClient":
        addresses = [
            NodeAddress(host=valkey_host, port=valkey_port)
            for valkey_host, valkey_port in valkey_addresses
        ]

        config = GlideClusterClientConfiguration(
            addresses=addresses,
            request_timeout=500,
        )

        client = await GlideClusterClient.create(config)

        return cls(
            client=client,
            enable_client_cache=enable_client_cache,
            client_cache_ttl=client_cache_ttl,
            client_cache_maxsize=client_cache_maxsize,
        )

    async def get(self, key: str) -> bytes | None:
        if self.enable_cache_storage and key in self.cache:
            return self.cache[key]

        value = await self.client.get(key)

        if self.enable_cache_storage:
            self.cache[key] = value

        return value

    async def set(self, key: str, value: str | bytes) -> None:
        if self.enable_cache_storage:
            self.cache.pop(key, None)

        await self.client.set(key, value)

    async def expire(self, key: str, ttl_seconds: int) -> None:
        await self.client.expire(key, ttl_seconds)

    async def delete(self, key: str) -> None:
        if self.enable_cache_storage:
            self.cache.pop(key, None)

        await self.client.delete([key])

    async def close(self):
        await self.client.close()
