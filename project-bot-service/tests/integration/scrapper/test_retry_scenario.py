import pytest
from tenacity import wait_fixed, wait_exponential
from wiremock.constants import Config
from wiremock.resources.mappings.models import (
    Mapping,
    MappingRequest,
    MappingResponse,
)
from wiremock.resources.mappings.resource import Mappings
from wiremock.testing.testcontainer import wiremock_container

from bot_service.application.exceptions.scrapper_exceptions import (
    ScrapperBadRequestError,
)
from bot_service.infrastructure.adapters.scrapper.http_scrapper_client import (
    HttpScrapperClient,
)
from bot_service.infrastructure.adapters.scrapper.utils.resilient_http_client import (
    ResilientHttpClient,
)


@pytest.fixture
def wm_server_with_states():
    with wiremock_container(secure=False) as wm:
        Config.base_url = wm.get_url("__admin")

        Mappings.create_mapping(
            Mapping(
                scenario_name="scrapper scenario",
                required_scenario_state="Started",
                new_scenario_state="First request",
                request=MappingRequest(
                    method="GET",
                    url_path="/links",
                    headers={"Tg-Chat-Id": {"equalTo": "123"}},
                ),
                response=MappingResponse(
                    status=500,
                ),
                persistent=False,
            ),
        )

        Mappings.create_mapping(
            Mapping(
                scenario_name="scrapper scenario",
                required_scenario_state="First request",
                new_scenario_state="Second request",
                request=MappingRequest(
                    method="GET",
                    url_path="/links",
                    headers={"Tg-Chat-Id": {"equalTo": "123"}},
                ),
                response=MappingResponse(
                    status=500,
                ),
                persistent=False,
            ),
        )

        Mappings.create_mapping(
            Mapping(
                scenario_name="scrapper scenario",
                required_scenario_state="Second request",
                new_scenario_state="Third request",
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
                ),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                scenario_name="scrapper scenario",
                required_scenario_state="Third request",
                new_scenario_state="Third request",
                request=MappingRequest(
                    method="GET",
                    url_path="/links",
                    headers={"Tg-Chat-Id": {"equalTo": "123"}},
                ),
                response=MappingResponse(
                    status=400,
                ),
                persistent=False,
            ),
        )

        yield wm


@pytest.fixture(scope="function")
def resilient_client_with_constant_retry():
    resilient_client = ResilientHttpClient(
        timeout_seconds=1,
        retry_attempts=4,
        retry_backoff_seconds=1,
        retry_enable_exponential_backoff=False,
        retryable_status_codes=[500],
        circuit_error_ratio=0.5,
        circuit_recovery_time=1,
        circuit_response_time=1,
        circuit_broken_time=1,
    )
    return resilient_client


@pytest.mark.parametrize(
    "retry_backoff_seconds, retry_enable_exponential_backoff, retry_scenario",
    [(4, False, wait_fixed), (4, True, wait_exponential)],
)
@pytest.mark.asyncio
async def test_choose_retry_backoff_scenario(
    retry_backoff_seconds, retry_enable_exponential_backoff, retry_scenario
):
    """
    TC-2.3 Соблюдение интервала retry
    Условие:
    Настроен constant backoff = x мс.
    + в конфигурации определён параметр retry_enable_exponential_backoff

    Ожидаемый результат:

    При retry_enable_exponential_backoff = false:
    интервал между попытками = x мс, сценарий wait_fixed (constant backoff)

    При retry_enable_exponential_backoff = true:
    интервал между попытками = 2^i * x mc, сценарий wait_exponential (exponential backoff)
    """
    resilient_client = ResilientHttpClient(
        timeout_seconds=1,
        retry_attempts=5,
        retry_backoff_seconds=retry_backoff_seconds,
        retry_enable_exponential_backoff=retry_enable_exponential_backoff,
        retryable_status_codes=[500],
        circuit_error_ratio=0.5,
        circuit_recovery_time=1,
        circuit_response_time=4,
        circuit_broken_time=1,
    )

    assert isinstance(resilient_client.wait_scenario, retry_scenario)


@pytest.mark.asyncio
async def test_scrapper_client_retry(
    wm_server_with_states, resilient_client_with_constant_retry, mocker
):
    """
    Тестирование FR-2: Retry
    TC-2.1 Retry на 5xx

    Условие:
    Внешний сервис возвращает:
    500
    500
    200

    Ожидаемый результат:
    Запрос выполняется 3 раза.
    Итоговый ответ успешный.

    +здесь же
    TC-2.2 Отсутствие Retry на 4xx
        Условие:
        Внешний сервис возвращает 400.

        Ожидаемый результат:
        Retry НЕ выполняется.
        Запрос выполнен n раз.
    """
    scrapper_client = HttpScrapperClient(
        base_url=wm_server_with_states.get_url(""),
        client=resilient_client_with_constant_retry,
    )
    spy_get = mocker.spy(resilient_client_with_constant_retry.client, "request")

    event = await scrapper_client.get_links(123)
    assert event is not None
    assert spy_get.call_count == 3

    # проверка при 400
    with pytest.raises(ScrapperBadRequestError):
        await scrapper_client.get_links(123)

    assert spy_get.call_count == 4
