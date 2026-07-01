import structlog
from datetime import datetime
from pydantic import HttpUrl

from scrapper_service.application.models.outbox_event import OutboxEvent
from scrapper_service.domain.models.link import Link
from scrapper_service.application.ports.tracking_repository_port import (
    TrackingRepositoryPort,
)

logger = structlog.get_logger(__name__)


class InMemoryTrackingRepository(TrackingRepositoryPort):
    """In-memory реализация хранилища чатов и отслеживаемых ссылок.

    Артефакт прошлых дз, оставлен для поддержки тестов из предыдущих дз
    """

    def __init__(self) -> None:
        self._storage: dict[int, dict[str, Link]] = {}
        self._link_id_seq: int = 1

    def _next_link_id(self) -> int:
        link_id = self._link_id_seq
        self._link_id_seq += 1
        return link_id

    async def register_chat(self, chat_id: int) -> None:
        self._storage.setdefault(chat_id, {})
        logger.info("tracking_repository_chat_registered", chat_id=chat_id)

    async def delete_chat(self, chat_id: int) -> None:
        self._storage.pop(chat_id, None)
        logger.info("tracking_repository_chat_deleted", chat_id=chat_id)

    async def chat_exists(self, chat_id: int) -> bool:
        exists = chat_id in self._storage
        logger.info(
            "tracking_repository_chat_exists_checked", chat_id=chat_id, exists=exists
        )
        return exists

    async def get_chats(self) -> list[int]:
        chats = list(self._storage.keys())
        logger.info("tracking_repository_chats_loaded", chats_count=len(chats))
        return chats

    async def add_link(
        self,
        chat_id: int,
        url: HttpUrl,
        tags: list[str],
        filters: list[str],
        last_seen_update: datetime | None,
    ) -> Link:

        created_link = Link(
            id=self._next_link_id(),
            url=url,
            tags=tags,
            filters=filters,
            last_seen_update=last_seen_update,
        )
        self._storage[chat_id][str(url)] = created_link
        logger.info(
            "tracking_repository_link_added",
            chat_id=chat_id,
            url=url,
            link_id=created_link.id,
        )
        return created_link

    async def remove_link(self, chat_id: int, url: str) -> Link:
        link = self._storage[chat_id].pop(url)
        logger.info(
            "tracking_repository_link_removed",
            chat_id=chat_id,
            url=url,
            link_id=link.id,
        )
        return link

    async def link_exists(self, chat_id: int, url: str) -> bool:
        exists = url in self._storage.get(chat_id, {})
        logger.info(
            "tracking_repository_link_exists_checked",
            chat_id=chat_id,
            url=url,
            exists=exists,
        )
        return exists

    async def get_links(self, chat_id: int) -> list[Link]:
        links = list(self._storage.get(chat_id, {}).values())
        logger.info(
            "tracking_repository_links_loaded", chat_id=chat_id, links_count=len(links)
        )
        return links

    async def get_unique_links(
        self,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Link]:
        distinct: dict[str, Link] = {}

        for links_by_url in self._storage.values():
            for url, link in links_by_url.items():
                if url not in distinct:
                    distinct[url] = link

        unique_links = list(distinct.values())
        unique_links = unique_links[offset:]

        if limit is not None:
            unique_links = unique_links[:limit]

        logger.info(
            "tracking_repository_unique_links_loaded",
            unique_links_count=len(unique_links),
            offset=offset,
            limit=limit,
        )
        return unique_links

    async def get_chat_ids_by_url(self, url: str) -> list[int]:
        result: list[int] = []

        for chat_id, links_by_url in self._storage.items():
            if url in links_by_url:
                result.append(chat_id)

        logger.info(
            "tracking_repository_chat_ids_by_url_loaded",
            url=url,
            chats_count=len(result),
        )
        return result

    async def update_last_seen(self, url: str, updated_at: datetime) -> None:
        for links_by_url in self._storage.values():
            if url in links_by_url:
                links_by_url[url].last_seen_update = updated_at

        logger.info(
            "tracking_repository_last_seen_updated", url=url, updated_at=str(updated_at)
        )

    async def update_last_seen_and_create_outbox_event(
        self,
        update_id: int,
        url: str,
        description: str,
        updated_at: datetime,
        tg_chat_ids: list[int],
        is_error: bool,
    ) -> None:
        return None

    async def create_outbox_event(
        self,
        update_id: int,
        url: str,
        description: str,
        tg_chat_ids: list[int],
        is_error: bool,
    ) -> None:
        return None

    async def get_pending_events(self) -> list[OutboxEvent]:
        return []

    async def get_all_events(self) -> list[OutboxEvent]:
        return []

    async def mark_as_sent(self, outbox_event_id: int) -> None:
        return None

    async def count_links_by_source(self) -> dict[str, int]:
        return {}

    async def aclose(self) -> None:
        return None
