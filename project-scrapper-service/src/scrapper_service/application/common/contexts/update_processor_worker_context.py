from dataclasses import dataclass
from scrapper_service.application.ports.tracking_repository_port import (
    TrackingRepositoryPort,
)
from scrapper_service.application.services.link_update_fetcher_service import (
    LinkUpdateFetcherService,
)
from scrapper_service.application.services.notification_service import (
    NotificationService,
)


@dataclass(slots=True)
class UpdateProcessorWorkerContext:
    """
    Объект контекста с сервисами и инфраструктурой, работающих в рамках одного потока
    """

    tracking_repository: TrackingRepositoryPort
    update_fetcher_service: LinkUpdateFetcherService
    notification_service: NotificationService

    async def aclose(self) -> None:
        await self.tracking_repository.aclose()
        await self.update_fetcher_service.close_clients()

        for client in self.notification_service.notification_clients:
            await client.aclose()
