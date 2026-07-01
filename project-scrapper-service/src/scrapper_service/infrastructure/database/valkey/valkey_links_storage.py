import json

import structlog
from scrapper_service.application.ports.links_storage_port import LinksStoragePort
from scrapper_service.domain.models.link import Link
from scrapper_service.infrastructure.database.valkey.utils.valkey_client import (
    ValkeyClient,
)

logger = structlog.get_logger(__name__)


class ValkeyLinksStorage(LinksStoragePort):
    def __init__(
        self,
        client: ValkeyClient,
        ttl_seconds: int,
    ) -> None:
        self.client = client
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _get_chat_id_key(chat_id: int) -> str:
        return f"links:{chat_id}"

    async def get_links(self, chat_id: int) -> list[Link] | None:
        cache_key = self._get_chat_id_key(chat_id)

        try:
            raw_links = await self.client.get(cache_key)

            if raw_links is None:
                return None

            raw_links_decoded = raw_links.decode("utf-8")
            links_data = json.loads(raw_links_decoded)

            links = [
                Link(
                    id=link["id"],
                    url=link["url"],
                    tags=link.get("tags", []),
                    filters=link.get("filters", []),
                    last_seen_update=link.get("last_seen_update", None),
                )
                for link in links_data
            ]

            logger.info(
                "links_cache_successfully_get",
                chat_id=chat_id,
                links_count=len(links),
            )
            return links

        except Exception as exc:
            logger.warning(
                "links_cache_get_failed",
                chat_id=chat_id,
                error=exc.__class__.__name__,
                message=str(exc),
            )
            return None

    async def set_links(
        self,
        chat_id: int,
        links: list[Link],
    ) -> None:
        cache_key = self._get_chat_id_key(chat_id)

        try:
            value = json.dumps(
                [link.model_dump(mode="json") for link in links],
                ensure_ascii=False,
            )

            await self.client.set(
                cache_key,
                value,
            )

            await self.client.expire(
                cache_key,
                self.ttl_seconds,
            )

            logger.info(
                "links_cache_successfully_set",
                chat_id=chat_id,
                links_count=len(links),
                ttl_seconds=self.ttl_seconds,
            )

        except Exception as exc:
            logger.warning(
                "links_cache_set_failed",
                chat_id=chat_id,
                error=exc.__class__.__name__,
                message=str(exc),
            )

    async def delete_links(self, chat_id: int) -> None:
        cache_key = self._get_chat_id_key(chat_id)

        try:
            await self.client.delete(cache_key)

            logger.info(
                "links_cache_successfully_deleted",
                chat_id=chat_id,
            )

        except Exception as exc:
            logger.warning(
                "links_cache_delete_failed",
                chat_id=chat_id,
                error=exc.__class__.__name__,
                message=str(exc),
            )

    async def aclose(self) -> None:
        await self.client.close()
        logger.info("valkey_client_closed")
