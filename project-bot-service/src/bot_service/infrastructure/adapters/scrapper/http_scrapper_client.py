import httpx
import structlog
from pydantic import HttpUrl

from bot_service.application.exceptions.scrapper_exceptions import (
    ScrapperBadRequestError,
    ScrapperChatAlreadyExistsError,
    ScrapperChatNotFoundError,
    ScrapperLinkAlreadyExistsError,
    ScrapperLinkNotFoundError,
)
from bot_service.application.ports.scrapper_port import ScrapperPort
from bot_service.domain.models.link import Link
from bot_service.infrastructure.adapters.scrapper.utils.resilient_http_client import (
    ResilientHttpClient,
)

logger = structlog.get_logger(__name__)


class HttpScrapperClient(ScrapperPort):
    """
    HTTP-адаптер для взаимодействия с внешним scrapper_service-сервисом.

    Обрабатывает ответы от сервиса и
    преобразует коды ошибок во внутренние исключения приложения.
    """

    def __init__(self, base_url: str, client: ResilientHttpClient | None = None):
        self.base_url = base_url.rstrip("/")
        if client is None:
            self.client = httpx.AsyncClient(timeout=10)
        else:
            self.client = client

    async def register_chat(self, chat_id: int) -> None:
        try:
            response = await self.client.post(f"{self.base_url}/tg-chat/{chat_id}")
        except httpx.HTTPStatusError as exc:
            response = exc.response

        match response.status_code:
            case 200:
                logger.info("scrapper_register_chat_succeeded", chat_id=chat_id)
                return
            case 400:
                raise ScrapperBadRequestError()
            case 409:
                raise ScrapperChatAlreadyExistsError()
            case _:
                response.raise_for_status()

    async def delete_chat(self, chat_id: int) -> None:
        try:
            response = await self.client.delete(f"{self.base_url}/tg-chat/{chat_id}")
        except httpx.HTTPStatusError as exc:
            response = exc.response

        match response.status_code:
            case 200:
                logger.info("scrapper_delete_chat_succeeded", chat_id=chat_id)
                return
            case 400:
                raise ScrapperBadRequestError()
            case 404:
                raise ScrapperChatNotFoundError()
            case _:
                response.raise_for_status()

    async def add_link(self, chat_id: int, link: Link) -> None:
        payload = {
            "link": str(link.url),
            "tags": link.tags,
            "filters": link.filters,
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/links",
                json=payload,
                headers={"Tg-Chat-Id": str(chat_id)},
            )
        except httpx.HTTPStatusError as exc:
            response = exc.response

        match response.status_code:
            case 200:
                logger.info(
                    "scrapper_add_link_succeeded",
                    chat_id=chat_id,
                    url=str(link.url),
                )
                return
            case 400:
                raise ScrapperBadRequestError()
            case 404:
                raise ScrapperChatNotFoundError()
            case 409:
                raise ScrapperLinkAlreadyExistsError()
            case _:
                response.raise_for_status()

    async def remove_link(self, chat_id: int, url: HttpUrl) -> None:
        payload = {
            "link": str(url),
        }

        try:
            response = await self.client.request(
                "DELETE",
                f"{self.base_url}/links",
                json=payload,
                headers={"Tg-Chat-Id": str(chat_id)},
            )
        except httpx.HTTPStatusError as exc:
            response = exc.response

        match response.status_code:
            case 200:
                logger.info(
                    "scrapper_remove_link_succeeded",
                    chat_id=chat_id,
                    url=str(url),
                )
                return
            case 400:
                raise ScrapperBadRequestError()
            case 404:
                raise ScrapperLinkNotFoundError()
            case _:
                response.raise_for_status()

    async def get_links(self, chat_id: int) -> list[Link] | None:

        try:
            response = await self.client.get(
                f"{self.base_url}/links",
                headers={"Tg-Chat-Id": str(chat_id)},
            )
        except httpx.HTTPStatusError as exc:
            response = exc.response

        match response.status_code:
            case 200:
                data = response.json()
                links = [
                    Link(
                        id=item["id"],
                        url=item["url"],
                        tags=item.get("tags", []),
                        filters=item.get("filters", []),
                        last_seen_update=item.get("last_seen_update", None),
                    )
                    for item in data.get("links", [])
                ]

                logger.info(
                    "scrapper_get_links_succeeded",
                    chat_id=chat_id,
                    links_count=len(links),
                )
                return links
            case 400:
                raise ScrapperBadRequestError()
            case 404:
                raise ScrapperChatNotFoundError()
            case _:
                response.raise_for_status()
                return None

    async def aclose(self) -> None:
        await self.client.aclose()
        logger.info("scrapper_http_client_closed")
