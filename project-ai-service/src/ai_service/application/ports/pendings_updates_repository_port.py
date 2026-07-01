from abc import ABC, abstractmethod

from ai_service.application.common.models.grouped_updates_info import GroupedUpdatesInfo
from ai_service.domain.models.processed_update import ProcessedUpdate


class PendingUpdatesRepositoryPort(ABC):

    @abstractmethod
    def add_update(self, update: ProcessedUpdate) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_grouped_updates_info_with_keys(
        self,
    ) -> list[tuple[int, GroupedUpdatesInfo]]:
        raise NotImplementedError

    @abstractmethod
    def clear_storage(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def clear_storage_by_keys(self, keys) -> None:
        raise NotImplementedError
