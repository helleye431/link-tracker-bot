from abc import ABC, abstractmethod


class DeliveredNotificationsStoragePort(ABC):
    @abstractmethod
    async def is_delivered(self, update_id: int, chat_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def mark_delivered(self, update_id: int, chat_id: int) -> None:
        raise NotImplementedError
