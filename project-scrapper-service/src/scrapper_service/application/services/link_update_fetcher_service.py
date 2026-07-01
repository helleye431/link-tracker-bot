from datetime import datetime

import structlog
from pydantic import HttpUrl

from scrapper_service.application.exceptions.external_client_exceptions import (
    ClientForLinkNotFoundError,
)
from scrapper_service.application.ports.external_client_port import ExternalClientPort
from scrapper_service.domain.models.link_update_event import LinkUpdateEvent

logger = structlog.get_logger(__name__)


class LinkUpdateFetcherService:
    """
    Сервис работы с внешними клиентами

    Отвечает за выбор клиента по домену ссылки,
    получение последнего обновления
    и получение последнего события по ссылке
    """

    def __init__(self, external_clients: list[ExternalClientPort]) -> None:
        self.external_clients = {client.domain: client for client in external_clients}

    async def get_last_update(self, url: HttpUrl) -> datetime | None:
        client = self.external_clients.get(url.host)

        if client is None:
            logger.warning(
                "scheduler_client_not_found_for_url",
                url=str(url),
                host=url.host,
            )
            raise ClientForLinkNotFoundError

        return await client.get_last_update(str(url))

    async def get_latest_event(self, url: HttpUrl) -> LinkUpdateEvent | None:
        client = self.external_clients.get(url.host)

        if client is None:
            logger.warning(
                "scheduler_client_not_found_for_url",
                url=str(url),
                host=url.host,
            )
            raise ClientForLinkNotFoundError

        return await client.get_latest_event(str(url))

    async def close_clients(self) -> None:
        for client in self.external_clients.values():
            await client.aclose()
