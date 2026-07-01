from scrapper_service.application.exceptions.chat_exceptions import (
    ChatAlreadyExistsError,
    ChatNotFoundError,
)
from scrapper_service.application.exceptions.external_client_exceptions import (
    ExternalServiceException,
)
from scrapper_service.application.exceptions.link_exceptions import (
    LinkAlreadyExistsError,
    LinkNotFoundError,
)
from pydantic import HttpUrl

from scrapper_service.application.ports.links_storage_port import LinksStoragePort
from scrapper_service.domain.models.link import Link
from scrapper_service.application.ports.tracking_repository_port import (
    TrackingRepositoryPort,
)
from scrapper_service.application.services.link_update_fetcher_service import (
    LinkUpdateFetcherService,
)
import structlog

logger = structlog.get_logger(__name__)


class TrackingService:
    """
    Сервис управления чатами и отслеживаемыми ссылками

    Отвечает за регистрацию и удаление чатов, получение списка ссылок,
    добавление новых ссылок в отслеживание и удаление существующих

    """

    def __init__(
        self,
        tracking_repository: TrackingRepositoryPort,
        update_fetcher_service: LinkUpdateFetcherService,
        enable_cache: bool = False,
        links_cache_storage: LinksStoragePort | None = None,
    ) -> None:
        self.tracking_repository = tracking_repository
        self.update_fetcher_service = update_fetcher_service
        self.enable_cache = enable_cache
        self.links_cache_storage = links_cache_storage

        if self.enable_cache and self.links_cache_storage is None:
            raise ValueError("LinksCacheStorage is required when cache is enabled")

    def _get_links_cache_storage(self) -> LinksStoragePort:
        if self.links_cache_storage is None:
            raise RuntimeError("Links cache storage is not configured")

        return self.links_cache_storage

    async def register_chat(self, chat_id: int) -> None:
        logger.info("register_chat_started", chat_id=chat_id)

        if await self.tracking_repository.chat_exists(chat_id):
            logger.warning("register_chat_conflict", chat_id=chat_id)
            raise ChatAlreadyExistsError(chat_id)

        await self.tracking_repository.register_chat(chat_id)
        logger.info("register_chat_succeeded", chat_id=chat_id)

    async def delete_chat(self, chat_id: int) -> None:
        logger.info("delete_chat_started", chat_id=chat_id)

        if not await self.tracking_repository.chat_exists(chat_id):
            logger.warning("delete_chat_not_found", chat_id=chat_id)
            raise ChatNotFoundError(chat_id)

        await self.tracking_repository.delete_chat(chat_id)

        if self.enable_cache:
            cache_storage = self._get_links_cache_storage()
            await cache_storage.delete_links(chat_id)
            logger.info("links_cache_invalidated", chat_id=chat_id)

        logger.info("delete_chat_succeeded", chat_id=chat_id)

    async def get_links(self, chat_id: int) -> list[Link]:
        logger.info("get_links_started", chat_id=chat_id)

        if self.enable_cache:
            cache_storage = self._get_links_cache_storage()

            cached_links = await cache_storage.get_links(chat_id)
            if cached_links is not None:
                logger.info(
                    "get_links_succeeded_from_cache",
                    chat_id=chat_id,
                    links_count=len(cached_links),
                )
                return cached_links

        if not await self.tracking_repository.chat_exists(chat_id):
            logger.warning("get_links_chat_not_found", chat_id=chat_id)
            raise ChatNotFoundError(chat_id)

        links = await self.tracking_repository.get_links(chat_id)

        if self.enable_cache:
            cache_storage = self._get_links_cache_storage()
            await cache_storage.set_links(chat_id, links)

            logger.info(
                "links_cache_updated",
                chat_id=chat_id,
                links_count=len(links),
            )

        logger.info("get_links_succeeded", chat_id=chat_id, links_count=len(links))
        return links

    async def add_link(
        self,
        chat_id: int,
        url: str,
        tags: list[str],
        filters: list[str],
    ) -> Link:
        if not await self.tracking_repository.chat_exists(chat_id):
            logger.warning("add_link_chat_not_found", chat_id=chat_id, url=url)
            raise ChatNotFoundError(chat_id)

        if await self.tracking_repository.link_exists(chat_id, url):
            logger.warning("add_link_conflict", chat_id=chat_id, url=url)
            raise LinkAlreadyExistsError(url)

        url = HttpUrl(url)
        try:
            last_seen_update = await self.update_fetcher_service.get_last_update(url)
        except ExternalServiceException:
            last_seen_update = None

        link = await self.tracking_repository.add_link(
            chat_id=chat_id,
            url=url,
            tags=tags,
            filters=filters,
            last_seen_update=last_seen_update,
        )

        if self.enable_cache:
            cache_storage = self._get_links_cache_storage()
            await cache_storage.delete_links(chat_id)
            logger.info("links_cache_invalidated", chat_id=chat_id)

        return link

    async def remove_link(self, chat_id: int, url: str) -> Link:
        logger.info("remove_link_started", chat_id=chat_id, url=url)

        if not await self.tracking_repository.chat_exists(chat_id):
            logger.warning("remove_link_chat_not_found", chat_id=chat_id, url=url)
            raise ChatNotFoundError(chat_id)

        if not await self.tracking_repository.link_exists(chat_id, url):
            logger.warning("remove_link_not_found", chat_id=chat_id, url=url)
            raise LinkNotFoundError(url)

        link = await self.tracking_repository.remove_link(chat_id, url)
        if self.enable_cache:
            cache_storage = self._get_links_cache_storage()
            await cache_storage.delete_links(chat_id)
            logger.info("links_cache_invalidated", chat_id=chat_id)

        logger.info("remove_link_succeeded", chat_id=chat_id, url=url, link_id=link.id)
        return link
