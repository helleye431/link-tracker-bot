from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import HttpUrl

from scrapper_service.application.models.outbox_event import OutboxEvent
from scrapper_service.domain.models.link import Link


class TrackingRepositoryPort(ABC):
    @abstractmethod
    async def register_chat(self, chat_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_chat(self, chat_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def chat_exists(self, chat_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_chats(self) -> list[int]:
        raise NotImplementedError

    @abstractmethod
    async def add_link(
        self,
        chat_id: int,
        url: HttpUrl,
        tags: list[str],
        filters: list[str],
        last_seen_update: datetime | None,
    ) -> Link:
        raise NotImplementedError

    @abstractmethod
    async def remove_link(self, chat_id: int, url: str) -> Link:
        raise NotImplementedError

    @abstractmethod
    async def link_exists(self, chat_id: int, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_links(self, chat_id: int) -> list[Link]:
        raise NotImplementedError

    @abstractmethod
    async def get_unique_links(
        self, limit: int | None = None, offset: int = 0
    ) -> list[Link]:
        raise NotImplementedError

    @abstractmethod
    async def get_chat_ids_by_url(self, url: str) -> list[int]:
        raise NotImplementedError

    @abstractmethod
    async def update_last_seen(self, url: str, updated_at: datetime) -> None:
        raise NotImplementedError

    async def create_tag(self, chat_id: int, url: str, tag_name: str) -> None:
        raise NotImplementedError

    async def get_tags(self, chat_id: int, url: str) -> list[str]:
        raise NotImplementedError

    async def rename_tag(self, chat_id: int, old_name: str, new_name: str) -> None:
        raise NotImplementedError

    async def delete_tag(self, chat_id: int, tag_name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update_last_seen_and_create_outbox_event(
        self,
        update_id: int,
        url: str,
        description: str,
        author: str,
        updated_at: datetime,
        tg_chat_ids: list[int],
        is_error: bool,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create_outbox_event(
        self,
        update_id: int,
        url: str,
        description: str,
        author: str,
        tg_chat_ids: list[int],
        is_error: bool,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_pending_events(self) -> list[OutboxEvent]:
        raise NotImplementedError

    @abstractmethod
    async def get_all_events(self) -> list[OutboxEvent]:
        raise NotImplementedError

    @abstractmethod
    async def mark_as_sent(self, outbox_event_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def count_links_by_source(self) -> dict[str, int]:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError
