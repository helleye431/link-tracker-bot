from bot_service.infrastructure.adapters.telegram.handler_interfaces.handler import (
    Handler,
)
from abc import abstractmethod


class FSMHandler(Handler):

    @property
    @abstractmethod
    def state(self):
        raise NotImplementedError
