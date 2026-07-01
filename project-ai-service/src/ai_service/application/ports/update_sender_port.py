from abc import ABC, abstractmethod
from ai_service.domain.models.processed_update import ProcessedUpdate


class UpdateSenderPort(ABC):

    @abstractmethod
    async def send_update(self, update: ProcessedUpdate) -> None:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError
