import time
from aiomisc.circuit_breaker import CircuitBreakerStates
import pytest
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
def wm_server_with_delay():
    with wiremock_container(secure=False) as wm:
        Config.base_url = wm.get_url("__admin")

        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(
                    method="GET",
                    url_path="/links",
                    headers={"Tg-Chat-Id": {"equalTo": "123"}},
                ),
                response=MappingResponse(
                    status=200,
                    json_body={
                        "links": [
                            {
                                "id": 1,
                                "url": "https://github.com/example/repo",
                                "tags": ["github", "backend"],
                                "filters": ["python", "release"],
                                "last_seen_update": "2026-05-31T12:00:00Z",
                            },
                            {
                                "id": 2,
                                "url": "https://stackoverflow.com/questions/123456",
                                "tags": ["stackoverflow"],
                                "filters": [],
                                "last_seen_update": None,
                            },
                        ]
                    },
                    fixed_delay_milliseconds=50,
                ),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(
                    method="GET",
                    url_path="/links",
                    headers={"Tg-Chat-Id": {"equalTo": "456"}},
                ),
                response=MappingResponse(
                    status=400,
                    fixed_delay_milliseconds=50,
                ),
                persistent=False,
            )
        )
        yield wm


@pytest.fixture(scope="function")
def resilient_client_with_circuit_breaker():
    resilient_client = ResilientHttpClient(
        timeout_seconds=1,
        retry_attempts=1,
        retry_backoff_seconds=1,
        retry_enable_exponential_backoff=False,
        retryable_status_codes=[500],
        circuit_error_ratio=0.5,
        circuit_recovery_time=3,
        circuit_response_time=1,
        circuit_broken_time=3,
    )
    return resilient_client


@pytest.mark.slow
@pytest.mark.asyncio
async def test_circuit_breaker_broken(
    wm_server_with_delay,
    resilient_client_with_circuit_breaker,
):
    """
    TC-4.1 Переход в OPEN (BROKEN)
    Условие:
    Внешний сервис стабильно возвращает ошибку.

    Ожидаемый результат:
    После достижения error ratio Circuit Breaker переходит в BROKEN.
    Последующие вызовы завершаются мгновенно (без ожидания timeout).
    """
    scrapper_client = HttpScrapperClient(
        base_url=wm_server_with_delay.get_url(""),
        client=resilient_client_with_circuit_breaker,
    )

    while (
        scrapper_client.client.circuit_breaker.state is not CircuitBreakerStates.BROKEN
    ):
        try:
            await scrapper_client.get_links(456)
        except Exception:
            pass

    assert scrapper_client.client.circuit_breaker.state is CircuitBreakerStates.BROKEN

    start = time.perf_counter()
    for i in range(3):
        try:
            await scrapper_client.get_links(456)
        except Exception:
            pass
    end = time.perf_counter()

    # задержка сервиса 0.05
    assert end - start < 0.15


@pytest.mark.slow
@pytest.mark.asyncio
async def test_circuit_breaker_recovery_to_passing(
    wm_server_with_delay,
    resilient_client_with_circuit_breaker,
):
    """
    TC-4.2 HALF-OPEN (RECOVERY) → CLOSED (PASSING) состояние
    Инициировать переход Circuit Breaker в BROKEN

    Подождать broken time. Дождаться состояние RECOVERY

    Выполнить несколько пробных вызовов.
    Если процент ошибок не превышает error_ratio, то Circuit Breaker переходит в состояние PASSING.
    """
    scrapper_client = HttpScrapperClient(
        base_url=wm_server_with_delay.get_url(""),
        client=resilient_client_with_circuit_breaker,
    )

    async def request_400():
        try:
            await scrapper_client.get_links(456)
        except Exception:
            pass

    async def request_200():
        try:
            await scrapper_client.get_links(123)
        except Exception:
            pass

    while (
        scrapper_client.client.circuit_breaker.state is not CircuitBreakerStates.BROKEN
    ):
        await request_400()

    assert scrapper_client.client.circuit_breaker.state is CircuitBreakerStates.BROKEN

    while scrapper_client.client.circuit_breaker.state is CircuitBreakerStates.BROKEN:
        await request_400()

    assert (
        scrapper_client.client.circuit_breaker.state is CircuitBreakerStates.RECOVERING
    )

    while (
        scrapper_client.client.circuit_breaker.state is CircuitBreakerStates.RECOVERING
    ):
        await request_200()

    assert scrapper_client.client.circuit_breaker.state is CircuitBreakerStates.PASSING


@pytest.mark.slow
@pytest.mark.asyncio
async def test_circuit_breaker_recovery_to_broken(
    wm_server_with_delay,
    resilient_client_with_circuit_breaker,
):
    """
    TC-4.2 HALF-OPEN (RECOVERY) → OPEN (BROKEN) состояние
    Инициировать переход Circuit Breaker в BROKEN

    Подождать broken time. Дождаться состояние RECOVERY

    Выполнить несколько пробных вызовов.
    Если процент ошибок превышает error_ratio, то Circuit Breaker переходит в состояние BROKEN.
    """
    scrapper_client = HttpScrapperClient(
        base_url=wm_server_with_delay.get_url(""),
        client=resilient_client_with_circuit_breaker,
    )

    async def request_400():
        try:
            await scrapper_client.get_links(456)
        except Exception:
            pass

    while (
        scrapper_client.client.circuit_breaker.state is not CircuitBreakerStates.BROKEN
    ):
        await request_400()

    assert scrapper_client.client.circuit_breaker.state is CircuitBreakerStates.BROKEN

    while scrapper_client.client.circuit_breaker.state is CircuitBreakerStates.BROKEN:
        await request_400()

    assert (
        scrapper_client.client.circuit_breaker.state is CircuitBreakerStates.RECOVERING
    )

    while (
        scrapper_client.client.circuit_breaker.state is CircuitBreakerStates.RECOVERING
    ):
        await request_400()

    assert scrapper_client.client.circuit_breaker.state is CircuitBreakerStates.BROKEN
