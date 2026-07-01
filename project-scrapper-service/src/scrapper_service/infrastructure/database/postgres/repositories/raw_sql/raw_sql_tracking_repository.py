from datetime import datetime

import asyncpg
from pydantic import HttpUrl

from scrapper_service.application.models.outbox_event import OutboxEvent
from scrapper_service.application.ports.tracking_repository_port import (
    TrackingRepositoryPort,
)
from scrapper_service.domain.models.link import Link
import structlog

from scrapper_service.infrastructure.observability.metrics_decorators import (
    observe_links_on_track,
    observe_request_duration,
)

logger = structlog.get_logger(__name__)


class RawSqlTrackingRepository(TrackingRepositoryPort):
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    @classmethod
    async def create(cls, database_url: str) -> "RawSqlTrackingRepository":
        pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=1,
            max_size=100,
        )
        return cls(pool)

    @observe_request_duration(scope="database", scope_type="chats")
    async def register_chat(self, chat_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chats(id)
                VALUES ($1)
                """,
                chat_id,
            )

    @observe_request_duration(scope="database", scope_type="chats")
    async def delete_chat(self, chat_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM chats
                WHERE id = $1
                """,
                chat_id,
            )

    @observe_request_duration(scope="database", scope_type="chats")
    async def chat_exists(self, chat_id: int) -> bool:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1
                FROM chats
                WHERE id = $1
                """,
                chat_id,
            )
            return row is not None

    @observe_request_duration(scope="database", scope_type="chats")
    async def get_chats(self) -> list[int]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id
                FROM chats
                ORDER BY id
                """
            )
            return [row["id"] for row in rows]

    @observe_request_duration(scope="database", scope_type="links")
    async def add_link(
        self,
        chat_id: int,
        url: HttpUrl,
        tags: list[str],
        filters: list[str],
        last_seen_update: datetime | None,
    ) -> Link:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                link_row = await conn.fetchrow(
                    """
                    INSERT INTO links(url, last_seen_update)
                    VALUES ($1, $2)
                    ON CONFLICT (url) DO UPDATE
                    SET url = EXCLUDED.url
                    RETURNING id, url, last_seen_update
                    """,
                    str(url),
                    last_seen_update,
                )

                await conn.execute(
                    """
                    INSERT INTO link_chat(chat_id, link_id)
                    VALUES ($1, $2)
                    """,
                    chat_id,
                    link_row["id"],
                )

                if tags:
                    await conn.executemany(
                        """
                        INSERT INTO link_tags(chat_id, link_id, tag_name)
                        VALUES ($1, $2, $3)
                        """,
                        [(chat_id, link_row["id"], tag) for tag in tags],
                    )

                if filters:
                    await conn.executemany(
                        """
                        INSERT INTO link_filters(chat_id, link_id, filter_name)
                        VALUES ($1, $2, $3)
                        """,
                        [(chat_id, link_row["id"], value) for value in filters],
                    )

                return Link(
                    id=link_row["id"],
                    url=url,
                    tags=tags,
                    filters=filters,
                    last_seen_update=last_seen_update,
                )

    @observe_request_duration(scope="database", scope_type="links")
    async def remove_link(self, chat_id: int, url: str) -> Link:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                link_row = await conn.fetchrow(
                    """
                    SELECT l.id, l.url, l.last_seen_update
                    FROM links l
                    JOIN link_chat lc ON lc.link_id = l.id
                    WHERE lc.chat_id = $1 AND l.url = $2
                    """,
                    chat_id,
                    url,
                )

                tag_rows = await conn.fetch(
                    """
                    SELECT tag_name
                    FROM link_tags
                    WHERE chat_id = $1 AND link_id = $2
                    ORDER BY tag_name
                    """,
                    chat_id,
                    link_row["id"],
                )
                filter_rows = await conn.fetch(
                    """
                    SELECT filter_name
                    FROM link_filters
                    WHERE chat_id = $1 AND link_id = $2
                    ORDER BY filter_name
                    """,
                    chat_id,
                    link_row["id"],
                )

                await conn.execute(
                    """
                    DELETE FROM link_chat
                    WHERE chat_id = $1 AND link_id = $2
                    """,
                    chat_id,
                    link_row["id"],
                )
                # link_tags и link_filters удалятся сами каскадом
                # от link_chat(chat_id, link_id)

                subscriber_row = await conn.fetchrow(
                    """
                    SELECT 1
                    FROM link_chat
                    WHERE link_id = $1
                    LIMIT 1
                    """,
                    link_row["id"],
                )

                # очистка бд от ссылки, если нет чата-подписчика
                if subscriber_row is None:
                    await conn.execute(
                        """
                        DELETE FROM links
                        WHERE id = $1
                        """,
                        link_row["id"],
                    )

                return Link(
                    id=link_row["id"],
                    url=HttpUrl(url),
                    tags=[row["tag_name"] for row in tag_rows],
                    filters=[row["filter_name"] for row in filter_rows],
                    last_seen_update=link_row["last_seen_update"],
                )

    @observe_request_duration(scope="database", scope_type="links")
    async def link_exists(self, chat_id: int, url: str) -> bool:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1
                FROM links l
                JOIN link_chat lc ON lc.link_id = l.id
                WHERE lc.chat_id = $1 AND l.url = $2
                """,
                chat_id,
                url,
            )
            return row is not None

    @observe_request_duration(scope="database", scope_type="links")
    async def get_links(self, chat_id: int) -> list[Link]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    l.id,
                    l.url,
                    l.last_seen_update,
                    COALESCE(array_agg(DISTINCT lt.tag_name)
                        FILTER (WHERE lt.tag_name IS NOT NULL), '{}') AS tags,
                    COALESCE(array_agg(DISTINCT lf.filter_name)
                        FILTER (WHERE lf.filter_name IS NOT NULL), '{}') AS filters
                FROM links l
                JOIN link_chat lc
                    ON lc.link_id = l.id
                LEFT JOIN link_tags lt
                    ON lt.chat_id = lc.chat_id
                   AND lt.link_id = lc.link_id
                LEFT JOIN link_filters lf
                    ON lf.chat_id = lc.chat_id
                   AND lf.link_id = lc.link_id
                WHERE lc.chat_id = $1
                GROUP BY l.id, l.url, l.last_seen_update
                ORDER BY l.id
                """,
                chat_id,
            )

            return [
                Link(
                    id=row["id"],
                    url=HttpUrl(row["url"]),
                    tags=sorted(row["tags"]),
                    filters=sorted(row["filters"]),
                    last_seen_update=row["last_seen_update"],
                )
                for row in rows
            ]

    @observe_request_duration(scope="database", scope_type="links")
    async def get_unique_links(
        self,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Link]:
        async with self.pool.acquire() as conn:
            base_query = """
                SELECT
                    l.id,
                    l.url,
                    l.last_seen_update,
                    COALESCE(
                        array_agg(DISTINCT lt.tag_name)
                        FILTER (WHERE lt.tag_name IS NOT NULL),
                        '{}'
                    ) AS tags,
                    COALESCE(
                        array_agg(DISTINCT lf.filter_name)
                        FILTER (WHERE lf.filter_name IS NOT NULL),
                        '{}'
                    ) AS filters
                FROM links l
                LEFT JOIN link_tags lt
                    ON lt.link_id = l.id
                LEFT JOIN link_filters lf
                    ON lf.link_id = l.id
                GROUP BY l.id, l.url, l.last_seen_update
                ORDER BY l.id
            """

            if limit is None:
                rows = await conn.fetch(base_query)
            else:
                rows = await conn.fetch(
                    base_query + " LIMIT $1 OFFSET $2",
                    limit,
                    offset,
                )

            return [
                Link(
                    id=row["id"],
                    url=row["url"],
                    tags=sorted(row["tags"]),
                    filters=sorted(row["filters"]),
                    last_seen_update=row["last_seen_update"],
                )
                for row in rows
            ]

    @observe_request_duration(scope="database", scope_type="link_chat")
    async def get_chat_ids_by_url(self, url: str) -> list[int]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT lc.chat_id
                FROM link_chat lc
                JOIN links l ON l.id = lc.link_id
                WHERE l.url = $1
                ORDER BY lc.chat_id
                """,
                url,
            )
            return [row["chat_id"] for row in rows]

    @observe_request_duration(scope="database", scope_type="links")
    async def update_last_seen(self, url: str, updated_at: datetime) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE links
                SET last_seen_update = $2
                WHERE url = $1
                """,
                url,
                updated_at,
            )

    @observe_request_duration(scope="database", scope_type="tags")
    async def create_tag(self, chat_id: int, url: str, tag_name: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO link_tags(chat_id, link_id, tag_name)
                SELECT $1, l.id, $3
                FROM links l
                JOIN link_chat lc ON lc.link_id = l.id
                WHERE lc.chat_id = $1 AND l.url = $2
                """,
                chat_id,
                url,
                tag_name,
            )

    @observe_request_duration(scope="database", scope_type="tags")
    async def get_tags(self, chat_id: int, url: str) -> list[str]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT lt.tag_name
                FROM link_tags lt
                JOIN links l ON l.id = lt.link_id
                WHERE lt.chat_id = $1 AND l.url = $2
                ORDER BY lt.tag_name
                """,
                chat_id,
                url,
            )
            return [row["tag_name"] for row in rows]

    @observe_request_duration(scope="database", scope_type="tags")
    async def rename_tag(self, chat_id: int, old_name: str, new_name: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE link_tags
                SET tag_name = $3
                WHERE chat_id = $1 AND tag_name = $2
                """,
                chat_id,
                old_name,
                new_name,
            )

    @observe_request_duration(scope="database", scope_type="tags")
    async def delete_tag(self, chat_id: int, tag_name: str) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM link_tags
                WHERE chat_id = $1 AND tag_name = $2
                """,
                chat_id,
                tag_name,
            )

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
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                link_row = await conn.fetchrow(
                    """
                    SELECT id
                    FROM links
                    WHERE url = $1
                    FOR UPDATE
                    """,
                    url,
                )

                if link_row is None:
                    return

                await conn.execute(
                    """
                    UPDATE links
                    SET last_seen_update = $2
                    WHERE url = $1
                    """,
                    url,
                    updated_at,
                )

                await conn.execute(
                    """
                    INSERT INTO update_events_outbox (
                        update_id,
                        url,
                        description,
                        author,
                        tg_chat_ids,
                        is_error
                    )
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (update_id) DO NOTHING
                    """,
                    update_id,
                    url,
                    description,
                    author,
                    tg_chat_ids,
                    is_error,
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
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO update_events_outbox (
                    update_id,
                    url,
                    description,
                    author,
                    tg_chat_ids,
                    is_error
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (update_id) DO NOTHING
                """,
                update_id,
                url,
                description,
                author,
                tg_chat_ids,
                is_error,
            )

    @observe_request_duration(scope="database", scope_type="outbox_events")
    async def get_pending_events(self) -> list[OutboxEvent]:
        async with self.pool.acquire() as conn:
            events = await conn.fetch(
                """
                SELECT * 
                FROM update_events_outbox
                WHERE sent_at IS NULL
                """
            )

            return [
                OutboxEvent(
                    id=event["id"],
                    update_id=event["update_id"],
                    url=event["url"],
                    description=event["description"],
                    author=event["author"],
                    tg_chat_ids=event["tg_chat_ids"],
                    is_error=event["is_error"],
                    created_at=event["created_at"],
                    sent_at=event["sent_at"],
                )
                for event in events
            ]

    @observe_request_duration(scope="database", scope_type="outbox_events")
    async def get_all_events(self) -> list[OutboxEvent]:
        async with self.pool.acquire() as conn:
            events = await conn.fetch(
                """
                SELECT * 
                FROM update_events_outbox
                """
            )

            return [
                OutboxEvent(
                    id=event["id"],
                    update_id=event["update_id"],
                    url=event["url"],
                    description=event["description"],
                    author=event["author"],
                    tg_chat_ids=event["tg_chat_ids"],
                    is_error=event["is_error"],
                    created_at=event["created_at"],
                    sent_at=event["sent_at"],
                )
                for event in events
            ]

    @observe_request_duration(scope="database", scope_type="outbox_events")
    async def mark_as_sent(self, outbox_event_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE update_events_outbox
                SET sent_at = NOW()
                WHERE id = $1
                  AND sent_at IS NULL
                """,
                outbox_event_id,
            )

    @observe_links_on_track()
    @observe_request_duration(scope="database", scope_type="links")
    async def count_links_by_source(self) -> dict[str, int]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    CASE
                        WHEN url LIKE '%github.com%' THEN 'github'
                        WHEN url LIKE '%stackoverflow.com%' THEN 'stackoverflow'
                        ELSE 'other'
                    END AS tracked_source,
                    COUNT(*) AS count
                FROM links
                GROUP BY tracked_source
                """
            )

            return {row["tracked_source"]: row["count"] for row in rows}

    async def aclose(self) -> None:
        await self.pool.close()
        logger.info("tracking_repository_connection_closed", access_type="raw sql")
