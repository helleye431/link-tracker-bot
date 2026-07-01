import pytest

from scrapper_service.application.exceptions.link_exceptions import (
    LinkAlreadyExistsError,
)
from scrapper_service.application.services.tracking_service import TrackingService
from scrapper_service.domain.models.link import Link


@pytest.mark.asyncio
async def test_add_duplicate_link_with_raw_sql_repository(
    raw_sql_repository,
    mock_link_update_fetcher_service,
):
    chat_id = 1001
    service = TrackingService(
        tracking_repository=raw_sql_repository,
        update_fetcher_service=mock_link_update_fetcher_service,
    )

    link = Link(
        id=None,
        url="https://github.com/helleye431/asteroids",
        tags=["github", "backend"],
        filters=["hw"],
        last_seen_update=None,
    )

    await service.register_chat(chat_id)
    await service.add_link(
        chat_id=chat_id,
        url=str(link.url),
        tags=link.tags,
        filters=link.filters,
    )

    with pytest.raises(LinkAlreadyExistsError):
        await service.add_link(
            chat_id=chat_id,
            url=str(link.url),
            tags=link.tags,
            filters=link.filters,
        )


@pytest.mark.asyncio
async def test_add_duplicate_link_with_orm_repository(
    orm_repository,
    mock_link_update_fetcher_service,
):
    chat_id = 2001
    service = TrackingService(
        tracking_repository=orm_repository,
        update_fetcher_service=mock_link_update_fetcher_service,
    )

    link = Link(
        id=None,
        url="https://github.com/helleye431/asteroids",
        tags=["github", "backend"],
        filters=["hw"],
        last_seen_update=None,
    )

    await service.register_chat(chat_id)
    await service.add_link(
        chat_id=chat_id,
        url=str(link.url),
        tags=link.tags,
        filters=link.filters,
    )

    with pytest.raises(LinkAlreadyExistsError):
        await service.add_link(
            chat_id=chat_id,
            url=str(link.url),
            tags=link.tags,
            filters=link.filters,
        )
