import time

import pytest
from httpx import TimeoutException
from wiremock.constants import Config
from wiremock.resources.mappings.models import (
    Mapping,
    MappingRequest,
    MappingResponse,
)
from wiremock.resources.mappings.resource import Mappings
from wiremock.testing.testcontainer import wiremock_container

from bot_service.infrastructure.adapters.scrapper.http_scrapper_client import (
    HttpScrapperClient,
)
from bot_service.infrastructure.adapters.scrapper.utils.resilient_http_client import (
    ResilientHttpClient,
)


@pytest.fixture
def wm_server_with_effects():
    with wiremock_container(secure=False) as wm:
        Config.base_url = wm.get_url("__admin")

        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(method="POST", url_path="/tg-chat/1"),
                response=MappingResponse(
                    status=200,
                    fixed_delay_milliseconds=3000,
                ),
                persistent=False,
            )
        )

        yield wm


@pytest.fixture
def resilient_client_without_retry():
    resilient_client = ResilientHttpClient(
        timeout_seconds=2,
        retry_attempts=1,
        retry_backoff_seconds=1,
        retry_enable_exponential_backoff=False,
        retryable_status_codes=[],
        circuit_error_ratio=0.5,
        circuit_recovery_time=1,
        circuit_response_time=1,
        circuit_broken_time=1,
    )
    return resilient_client


@pytest.mark.asyncio
async def test_scrapper_client_timeout(
    wm_server_with_effects, resilient_client_without_retry
):
    """
    TC-1.1 Превышение времени ожидания
    Условие:
    Внешний сервис отвечает с задержкой больше, чем установленный timeout.

    Ожидаемый результат:
    Запрос завершается ошибкой timeout.
    Время ответа меньше, чем задержка внешнего сервиса.
    """
    scrapper_client = HttpScrapperClient(
        base_url=wm_server_with_effects.get_url(""),
        client=resilient_client_without_retry,
    )

    start = time.perf_counter()
    with pytest.raises(TimeoutException):
        await scrapper_client.register_chat(1)

    end = time.perf_counter()

    assert end - start < 3
