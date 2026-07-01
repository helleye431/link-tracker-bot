from abc import ABC, abstractmethod


class TelegramPort(ABC):
    @abstractmethod
    async def send_message(self, chat_id: int, message: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def run(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def shutdown(self) -> None:
        raise NotImplementedError
