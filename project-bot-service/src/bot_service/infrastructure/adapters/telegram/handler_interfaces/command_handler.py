from abc import abstractmethod
from bot_service.infrastructure.adapters.telegram.handler_interfaces.handler import (
    Handler,
)


class CommandHandler(Handler):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        raise NotImplementedError
