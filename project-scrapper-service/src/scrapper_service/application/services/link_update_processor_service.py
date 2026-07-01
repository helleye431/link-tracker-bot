import asyncio
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import structlog

from scrapper_service.application.common.contexts.update_processor_worker_context import (
    UpdateProcessorWorkerContext,
)
from scrapper_service.application.ports.tracking_repository_port import (
    TrackingRepositoryPort,
)
from scrapper_service.application.services.link_update_fetcher_service import (
    LinkUpdateFetcherService,
)
from scrapper_service.application.services.notification_service import (
    NotificationService,
)
from scrapper_service.domain.models.link import Link
from scrapper_service.domain.models.link_update_event import LinkUpdateEvent
from hashlib import sha256

logger = structlog.get_logger(__name__)

TrackingRepositoryFactory = Callable[[], Awaitable[TrackingRepositoryPort]]
UpdateProcessorWorkerContextFactory = Callable[
    [],
    Awaitable[UpdateProcessorWorkerContext],
]


class LinkUpdateProcessorService:
    """
    Сервис обработки обновлений по отслеживаемым ссылкам

    Отвечает за пакетную загрузку ссылок,
    их параллельную обработку,
    отправку уведомлений об обновлениях
    и отправку сообщений об ошибках обработки


    """

    def __init__(
        self,
        tracking_repository_factory: TrackingRepositoryFactory,
        update_processor_worker_context_factory: UpdateProcessorWorkerContextFactory,
        batch_size: int,
        workers_count: int,
        transactional_outbox_mode: bool,
    ) -> None:
        self.tracking_repository_factory = tracking_repository_factory
        self.update_processor_worker_context_factory = (
            update_processor_worker_context_factory
        )
        self.batch_size = batch_size
        self.workers_count = workers_count
        self.transactional_outbox_mode = transactional_outbox_mode

    @staticmethod
    def _format_message(event: LinkUpdateEvent) -> str:
        return (
            f"Произошли изменения по ссылке {event.url}\n"
            f"Событие: {event.event_type}\n"
            f"Тема: {event.title}\n"
            f"Пользователь: {event.author}\n"
            f"Время создания: {event.created_at.isoformat()}\n"
            f"Превью: {event.preview}"
        )

    @staticmethod
    def _make_update_id(
        url: str,
        event_type: str,
        created_at: datetime,
    ):
        raw = f"{url}:{event_type}:{created_at}"

        event_hash = sha256(raw.encode("utf-8")).digest()

        # приведение к формату BIGINT
        return int.from_bytes(event_hash, byteorder="big") & ((1 << 63) - 1)

    async def process_updates(self) -> list[str]:
        failed_urls: list[str] = []
        offset = 0

        tracking_repository = await self.tracking_repository_factory()

        await tracking_repository.count_links_by_source()

        try:
            while True:
                links = await tracking_repository.get_unique_links(
                    limit=self.batch_size,
                    offset=offset,
                )

                if not links:
                    break

                logger.info(
                    "updates_batch_loaded",
                    offset=offset,
                    batch_size=len(links),
                    workers_count=self.workers_count,
                )

                chunk_size = max(
                    1,
                    (len(links) + self.workers_count - 1) // self.workers_count,
                )
                chunks = [
                    links[i : i + chunk_size] for i in range(0, len(links), chunk_size)
                ]

                batch_failed = await asyncio.to_thread(
                    self.process_batch_in_threads,
                    chunks,
                )
                failed_urls.extend(batch_failed)

                offset += self.batch_size
        finally:
            await tracking_repository.aclose()

        if failed_urls:
            logger.warning(
                "updates_processing_finished_with_failures",
                failed_count=len(failed_urls),
                failed_urls=failed_urls,
            )
        else:
            logger.info("updates_processing_finished_successfully")

        return failed_urls

    def process_batch_in_threads(self, chunks: list[list[Link]]) -> list[str]:
        failed_urls: list[str] = []

        with ThreadPoolExecutor(max_workers=self.workers_count) as executor:
            futures = [
                executor.submit(self.run_chunk_in_thread, chunk) for chunk in chunks
            ]

            for future in as_completed(futures):
                try:
                    failed_urls.extend(future.result())
                except Exception as exc:
                    logger.warning("batch_chunk_failed", error=str(exc))

        return failed_urls

    def run_chunk_in_thread(self, chunk: list[Link]) -> list[str]:
        return asyncio.run(self.process_chunk_async(chunk))

    async def process_chunk_async(self, links: list[Link]) -> list[str]:
        context = await self.update_processor_worker_context_factory()

        try:
            failed_urls = []

            for link in links:
                try:
                    await self.process_single_link(
                        link=link,
                        tracking_repository=context.tracking_repository,
                        update_fetcher_service=context.update_fetcher_service,
                        notification_service=context.notification_service,
                    )

                except Exception as exc:
                    logger.warning(
                        "link_update_processing_failed",
                        url=str(link.url),
                        error=exc.__class__.__name__,
                    )
                    failed_urls.append(str(link.url))

                    await self._send_error_report(context=context, link=link)

            return failed_urls
        finally:
            await context.aclose()

    async def _send_error_report(
        self, context: UpdateProcessorWorkerContext, link: Link
    ) -> None:

        update_id = self._make_update_id(
            url=str(link.url), event_type="error", created_at=datetime.now()
        )
        try:
            chat_ids = await context.tracking_repository.get_chat_ids_by_url(
                str(link.url)
            )

            if self.transactional_outbox_mode:
                await context.tracking_repository.create_outbox_event(
                    update_id=update_id,
                    url=str(link.url),
                    description="",
                    author="",
                    tg_chat_ids=chat_ids,
                    is_error=True,
                )
            else:
                await context.notification_service.send_update_notification(
                    update_id=update_id,
                    url=str(link.url),
                    description="",
                    author="",
                    chat_ids=chat_ids,
                    is_error=True,
                )
        except Exception as notification_exc:
            logger.warning(
                "failed_processing_report_send_failed",
                url=str(link.url),
                exception_name=notification_exc.__class__.__name__,
                exception_message=str(notification_exc),
            )

    async def process_single_link(
        self,
        link: Link,
        tracking_repository: TrackingRepositoryPort,
        update_fetcher_service: LinkUpdateFetcherService,
        notification_service: NotificationService,
    ) -> None:

        event = await update_fetcher_service.get_latest_event(link.url)

        if event is None:
            return None

        url = str(link.url)

        if link.last_seen_update is None:
            await tracking_repository.update_last_seen(url, event.created_at)
            logger.info(
                "last_seen_initialized",
                url=url,
                updated_at=event.created_at.isoformat(),
            )
            return None

        if event.created_at <= link.last_seen_update:
            return None

        chat_ids = await tracking_repository.get_chat_ids_by_url(url)
        description = self._format_message(event)
        update_id = self._make_update_id(
            url=event.url,
            event_type=event.event_type,
            created_at=event.created_at,
        )
        author = event.author

        if self.transactional_outbox_mode:
            await tracking_repository.update_last_seen_and_create_outbox_event(
                update_id=update_id,
                url=url,
                updated_at=event.created_at,
                description=description,
                author=author,
                tg_chat_ids=chat_ids,
                is_error=False,
            )

            logger.info(
                "link_update_outbox_event_created",
                update_id=update_id,
                link_id=link.id,
                url=url,
                chats_count=len(chat_ids),
                updated_at=event.created_at.isoformat(),
                event_type=event.event_type,
            )

            return None
        else:
            await notification_service.send_update_notification(
                update_id=update_id,
                url=url,
                description=description,
                author=author,
                chat_ids=chat_ids,
                is_error=False,
            )

            await tracking_repository.update_last_seen(url, event.created_at)
            logger.info(
                "link_updated_notification_sent",
                link_id=link.id,
                url=url,
                chats_count=len(chat_ids),
                updated_at=event.created_at.isoformat(),
                event_type=event.event_type,
            )
            return None
