from abc import ABC, abstractmethod
from scrapper_service.domain.models.link import Link


class LinksStoragePort(ABC):
    @abstractmethod
    async def get_links(self, chat_id: int) -> list[Link]:
        raise NotImplementedError

    @abstractmethod
    async def set_links(self, chat_id: int, links: list[Link]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_links(self, chat_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError
