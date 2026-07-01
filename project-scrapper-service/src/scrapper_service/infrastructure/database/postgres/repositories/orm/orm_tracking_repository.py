from datetime import datetime

from pydantic import HttpUrl
from sqlalchemy import delete, select, update, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import selectinload

from scrapper_service.application.models.outbox_event import OutboxEvent
from scrapper_service.application.ports.tracking_repository_port import (
    TrackingRepositoryPort,
)
from scrapper_service.domain.models.link import Link
from scrapper_service.infrastructure.database.postgres.repositories.orm.models import (
    ChatOrm,
    LinkChatOrm,
    LinkFilterOrm,
    LinkOrm,
    LinkTagOrm,
    UpdateEventsOutboxOrm,
)
from scrapper_service.infrastructure.observability.metrics_decorators import (
    observe_links_on_track,
    observe_request_duration,
)

import structlog

logger = structlog.get_logger(__name__)


class OrmTrackingRepository(TrackingRepositoryPort):
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine: AsyncEngine = create_async_engine(
            self.database_url,
            pool_pre_ping=True,
        )
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @observe_request_duration(scope="database", scope_type="chats")
    async def register_chat(self, chat_id: int) -> None:
        async with self.session_factory() as session:
            session.add(ChatOrm(id=chat_id))
            await session.commit()

    @observe_request_duration(scope="database", scope_type="chats")
    async def delete_chat(self, chat_id: int) -> None:
        async with self.session_factory() as session:
            await session.execute(delete(ChatOrm).where(ChatOrm.id == chat_id))
            await session.commit()

    @observe_request_duration(scope="database", scope_type="chats")
    async def chat_exists(self, chat_id: int) -> bool:
        async with self.session_factory() as session:
            result = await session.scalar(
                select(ChatOrm.id).where(ChatOrm.id == chat_id)
            )
            return result is not None

    @observe_request_duration(scope="database", scope_type="chats")
    async def get_chats(self) -> list[int]:
        async with self.session_factory() as session:
            result = await session.scalars(select(ChatOrm.id).order_by(ChatOrm.id))
            return list(result.all())

    @observe_request_duration(scope="database", scope_type="links")
    async def add_link(
        self,
        chat_id: int,
        url: HttpUrl,
        tags: list[str],
        filters: list[str],
        last_seen_update: datetime | None,
    ) -> Link:
        async with self.session_factory() as session:
            async with session.begin():
                link = await session.scalar(
                    select(LinkOrm).where(LinkOrm.url == str(url))
                )

                if link is None:
                    link = LinkOrm(
                        url=str(url),
                        last_seen_update=last_seen_update,
                    )
                    session.add(link)
                    await session.flush()

                session.add(LinkChatOrm(chat_id=chat_id, link_id=link.id))
                await session.flush()

                if tags:
                    session.add_all(
                        [
                            LinkTagOrm(
                                chat_id=chat_id,
                                link_id=link.id,
                                tag_name=tag,
                            )
                            for tag in tags
                        ]
                    )

                if filters:
                    session.add_all(
                        [
                            LinkFilterOrm(
                                chat_id=chat_id,
                                link_id=link.id,
                                filter_name=value,
                            )
                            for value in filters
                        ]
                    )

            return Link(
                id=link.id,
                url=url,
                tags=sorted(tags),
                filters=sorted(filters),
                last_seen_update=last_seen_update,
            )

    @observe_request_duration(scope="database", scope_type="links")
    async def remove_link(self, chat_id: int, url: str) -> Link:
        async with self.session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    select(LinkChatOrm)
                    .join(LinkOrm, LinkOrm.id == LinkChatOrm.link_id)
                    .options(
                        selectinload(LinkChatOrm.link),
                        selectinload(LinkChatOrm.tags),
                        selectinload(LinkChatOrm.filters),
                    )
                    .where(
                        LinkChatOrm.chat_id == chat_id,
                        LinkOrm.url == url,
                    )
                )
                subscription = result.scalar_one()
                link = subscription.link

                tags = sorted(tag.tag_name for tag in subscription.tags)
                filters = sorted(flt.filter_name for flt in subscription.filters)

                await session.delete(subscription)
                await session.flush()

                still_exists = await session.scalar(
                    select(LinkChatOrm.chat_id)
                    .where(LinkChatOrm.link_id == link.id)
                    .limit(1)
                )
                if still_exists is None:
                    await session.delete(link)

            return Link(
                id=link.id,
                url=HttpUrl(url),
                tags=tags,
                filters=filters,
                last_seen_update=link.last_seen_update,
            )

    @observe_request_duration(scope="database", scope_type="links")
    async def link_exists(self, chat_id: int, url: str) -> bool:
        async with self.session_factory() as session:
            result = await session.scalar(
                select(LinkChatOrm.chat_id)
                .join(LinkOrm, LinkOrm.id == LinkChatOrm.link_id)
                .where(
                    LinkChatOrm.chat_id == chat_id,
                    LinkOrm.url == url,
                )
                .limit(1)
            )
            return result is not None

    @observe_request_duration(scope="database", scope_type="links")
    async def get_links(self, chat_id: int) -> list[Link]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(LinkChatOrm)
                .options(
                    selectinload(LinkChatOrm.link),
                    selectinload(LinkChatOrm.tags),
                    selectinload(LinkChatOrm.filters),
                )
                .where(LinkChatOrm.chat_id == chat_id)
                .order_by(LinkChatOrm.link_id)
            )
            subscriptions = result.scalars().all()

            return [
                Link(
                    id=sub.link.id,
                    url=HttpUrl(sub.link.url),
                    tags=sorted(tag.tag_name for tag in sub.tags),
                    filters=sorted(flt.filter_name for flt in sub.filters),
                    last_seen_update=sub.link.last_seen_update,
                )
                for sub in subscriptions
            ]

    @observe_request_duration(scope="database", scope_type="links")
    async def get_unique_links(
        self,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Link]:
        async with self.session_factory() as session:
            query = (
                select(LinkOrm)
                .options(
                    selectinload(LinkOrm.subscriptions).selectinload(LinkChatOrm.tags),
                    selectinload(LinkOrm.subscriptions).selectinload(
                        LinkChatOrm.filters
                    ),
                )
                .order_by(LinkOrm.id)
                .offset(offset)
            )

            if limit is not None:
                query = query.limit(limit)

            result = await session.execute(query)
            links = result.scalars().all()

            payload = []
            for link in links:
                tags = sorted(
                    {tag.tag_name for sub in link.subscriptions for tag in sub.tags}
                )
                filters = sorted(
                    {
                        flt.filter_name
                        for sub in link.subscriptions
                        for flt in sub.filters
                    }
                )
                payload.append(
                    Link(
                        id=link.id,
                        url=link.url,
                        tags=tags,
                        filters=filters,
                        last_seen_update=link.last_seen_update,
                    )
                )

            return payload

    @observe_request_duration(scope="database", scope_type="link_chat")
    async def get_chat_ids_by_url(self, url: str) -> list[int]:
        async with self.session_factory() as session:
            result = await session.scalars(
                select(LinkChatOrm.chat_id)
                .join(LinkOrm, LinkOrm.id == LinkChatOrm.link_id)
                .where(LinkOrm.url == url)
                .order_by(LinkChatOrm.chat_id)
            )
            return list(result.all())

    @observe_request_duration(scope="database", scope_type="links")
    async def update_last_seen(self, url: str, updated_at: datetime) -> None:
        async with self.session_factory() as session:
            link = await session.scalar(select(LinkOrm).where(LinkOrm.url == url))
            if link is not None:
                link.last_seen_update = updated_at
                await session.commit()

    @observe_request_duration(scope="database", scope_type="outbox_events")
    async def update_last_seen_and_create_outbox_event(
        self,
        update_id: int,
        url: str,
        description: str,
        author: str,
        updated_at: datetime,
        tg_chat_ids: list[int],
        is_error: bool,
    ) -> None:
        async with self.session_factory() as session:
            async with session.begin():

                link = await session.scalar(
                    select(LinkOrm).where(LinkOrm.url == url).with_for_update()
                )

                if link is None:
                    return

                link.last_seen_update = updated_at

                session.add(
                    UpdateEventsOutboxOrm(
                        update_id=update_id,
                        url=url,
                        description=description,
                        author=author,
                        tg_chat_ids=tg_chat_ids,
                        is_error=is_error,
                    )
                )

    @observe_request_duration(scope="database", scope_type="outbox_events")
    async def create_outbox_event(
        self,
        update_id: int,
        url: str,
        description: str,
        author: str,
        tg_chat_ids: list[int],
        is_error: bool,
    ) -> None:
        async with self.session_factory() as session:
            async with session.begin():
                session.add(
                    UpdateEventsOutboxOrm(
                        update_id=update_id,
                        url=url,
                        author=author,
                        description=description,
                        tg_chat_ids=tg_chat_ids,
                        is_error=is_error,
                    )
                )

    @observe_request_duration(scope="database", scope_type="outbox_events")
    async def get_pending_events(self) -> list[OutboxEvent]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(UpdateEventsOutboxOrm)
                .where(UpdateEventsOutboxOrm.sent_at.is_(None))
                .order_by(UpdateEventsOutboxOrm.created_at)
            )

            events = result.scalars().all()

            return [
                OutboxEvent(
                    id=event.id,
                    update_id=event.update_id,
                    url=event.url,
                    description=event.description,
                    author=event.author,
                    tg_chat_ids=event.tg_chat_ids,
                    is_error=event.is_error,
                    created_at=event.created_at,
                    sent_at=event.sent_at,
                )
                for event in events
            ]

    @observe_request_duration(scope="database", scope_type="outbox_events")
    async def get_all_events(self) -> list[OutboxEvent]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(UpdateEventsOutboxOrm).order_by(UpdateEventsOutboxOrm.created_at)
            )

            events = result.scalars().all()

            return [
                OutboxEvent(
                    id=event.id,
                    update_id=event.update_id,
                    url=event.url,
                    description=event.description,
                    author=event.author,
                    tg_chat_ids=event.tg_chat_ids,
                    is_error=event.is_error,
                    created_at=event.created_at,
                    sent_at=event.sent_at,
                )
                for event in events
            ]

    @observe_request_duration(scope="database", scope_type="outbox_events")
    async def mark_as_sent(self, outbox_event_id: int) -> None:
        async with self.session_factory() as session:
            async with session.begin():
                await session.execute(
                    update(UpdateEventsOutboxOrm)
                    .where(UpdateEventsOutboxOrm.id == outbox_event_id)
                    .where(UpdateEventsOutboxOrm.sent_at.is_(None))
                    .values(sent_at=func.now())
                )

    @observe_request_duration(scope="database", scope_type="tags")
    async def create_tag(self, chat_id: int, url: str, tag_name: str) -> None:
        async with self.session_factory() as session:
            async with session.begin():
                subscription = await session.scalar(
                    select(LinkChatOrm)
                    .join(LinkOrm, LinkOrm.id == LinkChatOrm.link_id)
                    .where(
                        LinkChatOrm.chat_id == chat_id,
                        LinkOrm.url == url,
                    )
                )
                if subscription is None:
                    return

                session.add(
                    LinkTagOrm(
                        chat_id=chat_id,
                        link_id=subscription.link_id,
                        tag_name=tag_name,
                    )
                )

    @observe_request_duration(scope="database", scope_type="tags")
    async def get_tags(self, chat_id: int, url: str) -> list[str]:
        async with self.session_factory() as session:
            result = await session.scalars(
                select(LinkTagOrm.tag_name)
                .join(LinkOrm, LinkOrm.id == LinkTagOrm.link_id)
                .where(
                    LinkTagOrm.chat_id == chat_id,
                    LinkOrm.url == url,
                )
                .order_by(LinkTagOrm.tag_name)
            )
            return list(result.all())

    @observe_request_duration(scope="database", scope_type="tags")
    async def rename_tag(self, chat_id: int, old_name: str, new_name: str) -> None:
        async with self.session_factory() as session:
            tags = await session.scalars(
                select(LinkTagOrm).where(
                    LinkTagOrm.chat_id == chat_id,
                    LinkTagOrm.tag_name == old_name,
                )
            )
            for tag in tags:
                tag.tag_name = new_name
            await session.commit()

    @observe_request_duration(scope="database", scope_type="tags")
    async def delete_tag(self, chat_id: int, tag_name: str) -> None:
        async with self.session_factory() as session:
            await session.execute(
                delete(LinkTagOrm).where(
                    LinkTagOrm.chat_id == chat_id,
                    LinkTagOrm.tag_name == tag_name,
                )
            )
            await session.commit()

    @observe_links_on_track()
    @observe_request_duration(scope="database", scope_type="links")
    async def count_links_by_source(self) -> dict[str, int]:
        async with self.session_factory() as session:
            result = await session.scalars(select(LinkOrm.url))
            urls = list(result.all())

        counts = {"github": 0, "stackoverflow": 0}

        for url in urls:
            if "github.com" in url:
                counts["github"] += 1
            elif "stackoverflow.com" in url:
                counts["stackoverflow"] += 1

        return counts

    async def aclose(self) -> None:
        await self.engine.dispose()
        logger.info("tracking_repository_connection_closed", access_type="orm")
