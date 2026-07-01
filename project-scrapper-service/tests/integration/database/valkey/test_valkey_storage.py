from unittest.mock import AsyncMock
import pytest
import time
from scrapper_service.application.services.tracking_service import TrackingService
from scrapper_service.domain.models.link import Link
from scrapper_service.infrastructure.database.valkey.valkey_links_storage import (
    ValkeyLinksStorage,
)
from scrapper_service.presentation.http.app_factory import create_app
from httpx import AsyncClient, ASGITransport

from scrapper_service.presentation.http.utils.rate_limiter import rate_limiter


@pytest.mark.asyncio
async def test_correct_message_get_with_valkey(
    raw_sql_repository, mock_link_update_fetcher_service, valkey_client_factory
):
    """
    Данные кэшируются в Valkey, в том формате, который вы ожидаете

    Регистрируем ссылку на 1 пользователя,
    1-ый раз получаем - сервис берёт из postgresql
    2-ый раз получаем - сервис берёт из кэша valkey, данные совпадают по структуре с первым разом
    """
    valkey_client = await valkey_client_factory(enable_client_cache=False)

    original_set = valkey_client.set
    valkey_client.set = AsyncMock(wraps=original_set)

    original_get_links = raw_sql_repository.get_links
    raw_sql_repository.get_links = AsyncMock(wraps=original_get_links)

    valkey_storage = ValkeyLinksStorage(client=valkey_client, ttl_seconds=30)

    chat_id = 1001
    service = TrackingService(
        tracking_repository=raw_sql_repository,
        update_fetcher_service=mock_link_update_fetcher_service,
        enable_cache=True,
        links_cache_storage=valkey_storage,
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

    first_value = await service.get_links(chat_id)
    second_value = await service.get_links(chat_id)

    assert first_value == second_value

    assert raw_sql_repository.get_links.await_count == 1

    valkey_client.set.assert_awaited_once()

    await valkey_storage.aclose()


@pytest.mark.asyncio
async def test_clear_cache_after_ttl(
    raw_sql_repository, mock_link_update_fetcher_service, valkey_client_factory
):
    """
    по истечению TTL данные
    автоматически удаляются их кэша, и при обращении к API вызывается сервис для формирования ответа

    проверяется, что при двух вызовах с разницей больше чем ttl вызывается репозиторий для postgres
    """
    valkey_client = await valkey_client_factory(enable_client_cache=False)

    original_get_links = raw_sql_repository.get_links
    raw_sql_repository.get_links = AsyncMock(wraps=original_get_links)

    valkey_storage = ValkeyLinksStorage(client=valkey_client, ttl_seconds=1)

    chat_id = 1001
    service = TrackingService(
        tracking_repository=raw_sql_repository,
        update_fetcher_service=mock_link_update_fetcher_service,
        enable_cache=True,
        links_cache_storage=valkey_storage,
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

    await service.get_links(chat_id)

    time.sleep(2)

    await service.get_links(chat_id)

    assert raw_sql_repository.get_links.await_count == 2

    await valkey_storage.aclose()


@pytest.mark.asyncio
async def test_clear_cache_after_api_add_link(
    raw_sql_repository, mock_link_update_fetcher_service, valkey_client_factory
):
    """
    в случае изменения пользовательских ссылок через API,
     данные автоматически удаляются из кэша, и при обращении к API вызывается сервис для формирования ответа

    проверяется, что при выполнении api запроса (post) происходит инвалидация кэша
    """

    repo = raw_sql_repository

    valkey_client = await valkey_client_factory(enable_client_cache=False)

    valkey_storage = ValkeyLinksStorage(client=valkey_client, ttl_seconds=30)
    tracking_service = TrackingService(
        tracking_repository=repo,
        update_fetcher_service=mock_link_update_fetcher_service,
        enable_cache=True,
        links_cache_storage=valkey_storage,
    )

    app = create_app(
        title="Scrapper API",
        version="1.0.0",
        contact_name="Kirill Kravchuk",
        contact_url="https://github.com",
        tracking_service=tracking_service,
        request_limit=1000,
        request_limit_period="hour",
    )

    app.state.tracking_service = tracking_service
    app.state.limiter = rate_limiter(request_limit=1000, request_limit_period="hour")
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:

        link = "https://github.com/helleye431/asteroids"
        link2 = "https://github.com/helleye431/snake"
        header = {"tg-chat-id": "1"}
        key = "links:1"

        await client.post("/tg-chat/1")
        await client.post(
            "/links",
            json={"link": link, "tags": ["test1", "test2"], "filters": ["test_filter"]},
            headers=header,
        )

        await client.get("/links", headers=header)

        assert await valkey_client.get(key) is not None

        await client.post(
            "/links",
            json={"link": link2, "tags": ["test1"], "filters": ["test_filter"]},
            headers=header,
        )

        assert await valkey_client.get(key) is None

        await valkey_storage.aclose()
