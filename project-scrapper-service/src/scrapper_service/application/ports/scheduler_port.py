from abc import ABC, abstractmethod


class SchedulerPort(ABC):

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError
