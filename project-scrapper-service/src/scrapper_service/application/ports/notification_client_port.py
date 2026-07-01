from abc import ABC, abstractmethod


class NotificationClientPort(ABC):

    @abstractmethod
    async def send_update(
        self,
        update_id: int,
        url: str,
        description: str,
        author: str,
        chat_ids: list[int],
        is_error: bool,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def aclose(self) -> None:
        raise NotImplementedError
