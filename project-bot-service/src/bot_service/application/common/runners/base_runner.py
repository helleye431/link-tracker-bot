from abc import ABC, abstractmethod


class BaseRunner(ABC):
    """
    Базовый интерфейс для компонентов, управляющих жизненным циклом
    серверов
    """

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def wait(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass
