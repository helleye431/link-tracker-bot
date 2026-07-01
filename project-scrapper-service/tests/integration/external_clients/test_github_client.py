from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pydantic import HttpUrl
from scrapper_service.application.exceptions.external_client_exceptions import (
    GithubLinkValidationError,
    GithubServiceError,
)
from scrapper_service.application.services.link_update_fetcher_service import (
    LinkUpdateFetcherService,
)
from scrapper_service.infrastructure.clients.github_client import GithubClient
from scrapper_service.setup.config.settings import Settings


@pytest.mark.asyncio
async def test_github_validation_error_logged():
    """
    Проверка валидации ссылки
    на соответствие https://github.com/<owner>/<repo>
    """
    settings = Settings()
    github_client = GithubClient(str(settings.github_base_url))
    update_fetcher_service = LinkUpdateFetcherService(
        external_clients=[github_client],
    )

    with pytest.raises(GithubLinkValidationError):
        await github_client.get_last_update("https://github.com/owner")

    await update_fetcher_service.close_clients()


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [301, 403, 404])
async def test_github_service_error_logged_on_bad_status(status_code):
    """
    HTTP-клиент (GitHub) отправляет некорректный ответ
    сервису Scrapper (HTTP-код не 2xx или тело ответа не соответствует заявленной схеме)

    Scrapper корректно обрабатывает ошибочные HTTP-статусы
    и некорректные тела ответов от внешних API (GitHub),
    не приводя к падению приложения.
    """
    settings = Settings()

    github_client = GithubClient(str(settings.github_base_url))

    request = httpx.Request("GET", "https://api.github.com/repos/user/repo")
    response = MagicMock()
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message=f"{status_code} error",
        request=request,
        response=httpx.Response(status_code=status_code, request=request),
    )

    github_client.client.get = AsyncMock(return_value=response)

    update_fetcher_service = LinkUpdateFetcherService(
        external_clients=[github_client],
    )

    with pytest.raises(GithubServiceError):
        await update_fetcher_service.get_last_update(
            HttpUrl("https://github.com/user/repo")
        )

    await update_fetcher_service.close_clients()
