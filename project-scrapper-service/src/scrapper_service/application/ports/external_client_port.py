from abc import ABC, abstractmethod
from scrapper_service.domain.models.link_update_event import LinkUpdateEvent
from datetime import datetime


class ExternalClientPort(ABC):

    @property
    @abstractmethod
    def domain(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def get_last_update(self, url: str) -> datetime | None:
        raise NotImplementedError

    @abstractmethod
    async def get_latest_event(self, url: str) -> LinkUpdateEvent | None:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError
