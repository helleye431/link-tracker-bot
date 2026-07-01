from abc import abstractmethod, ABC

from ai_service.domain.models.processed_update import ProcessedUpdate
from ai_service.domain.models.raw_update import RawUpdate


class UpdateProcessorPort(ABC):

    @abstractmethod
    def process_update(self, update: RawUpdate) -> ProcessedUpdate:
        raise NotImplementedError
