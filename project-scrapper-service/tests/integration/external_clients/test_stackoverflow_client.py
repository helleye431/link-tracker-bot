from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pydantic import HttpUrl
from scrapper_service.application.exceptions.external_client_exceptions import (
    StackoverflowLinkValidationError,
    StackoverflowServiceError,
)
from scrapper_service.application.services.link_update_fetcher_service import (
    LinkUpdateFetcherService,
)
from scrapper_service.infrastructure.clients.stackoverflow_client import (
    StackoverflowClient,
)
from scrapper_service.setup.config.settings import Settings


@pytest.mark.asyncio
async def test_stackoverflow_validation_error_logged():
    """
    Проверка валидации ссылки
    на соответствие https://stackoverflow.com/questions/<n>
    """
    settings = Settings()

    stackoverflow_client = StackoverflowClient(str(settings.stackoverflow_base_url))
    update_fetcher_service = LinkUpdateFetcherService(
        external_clients=[stackoverflow_client],
    )

    with pytest.raises(StackoverflowLinkValidationError):
        await update_fetcher_service.get_last_update(
            HttpUrl("https://stackoverflow.com/questions/not-a-number/title")
        )

    await update_fetcher_service.close_clients()


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 403, 404, 500])
async def test_stackoverflow_service_error_logged_on_bad_status(status_code):
    """
    HTTP-клиент (Stackoverflow) отправляет некорректный ответ
    сервису Scrapper.

    Scrapper корректно обрабатывает ошибочные HTTP-статусы
    и не падает.
    """
    settings = Settings()

    stackoverflow_client = StackoverflowClient(str(settings.stackoverflow_base_url))

    request = httpx.Request("GET", "https://api.stackexchange.com/2.3/questions/123")
    response = MagicMock()
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message=f"{status_code} error",
        request=request,
        response=httpx.Response(status_code=status_code, request=request),
    )

    stackoverflow_client.client.get = AsyncMock(return_value=response)

    update_fetcher_service = LinkUpdateFetcherService(
        external_clients=[stackoverflow_client],
    )

    with pytest.raises(StackoverflowServiceError):
        await update_fetcher_service.get_last_update(
            HttpUrl("https://stackoverflow.com/questions/123/title")
        )

    await update_fetcher_service.close_clients()
