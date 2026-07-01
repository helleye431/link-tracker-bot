from abc import ABC, abstractmethod
from pydantic import HttpUrl
from bot_service.domain.models.link import Link


class ScrapperPort(ABC):

    @abstractmethod
    async def register_chat(self, chat_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_chat(self, chat_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def add_link(self, chat_id: int, link: Link) -> None:
        raise NotImplementedError

    @abstractmethod
    async def remove_link(self, chat_id: int, url: HttpUrl) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_links(self, chat_id: int) -> list[Link]:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError
