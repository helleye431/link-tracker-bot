import httpx
import pytest
import json
from tenacity import wait_fixed, wait_exponential
from wiremock.constants import Config
from wiremock.resources.mappings.models import (
    Mapping,
    MappingRequest,
    MappingResponse,
)
from wiremock.resources.mappings.resource import Mappings
from wiremock.testing.testcontainer import wiremock_container

from scrapper_service.application.exceptions.external_client_exceptions import (
    GithubServiceError,
    StackoverflowServiceError,
)
from scrapper_service.infrastructure.clients.http_bot_client import HttpBotClient
from scrapper_service.infrastructure.clients.stackoverflow_client import (
    StackoverflowClient,
)
from scrapper_service.infrastructure.clients.utils.resilient_http_client import (
    ResilientHttpClient,
)
from scrapper_service.infrastructure.clients.github_client import GithubClient


@pytest.fixture
def wm_server_with_states():
    with wiremock_container(secure=False) as wm:
        Config.base_url = wm.get_url("__admin")

        github_params = {
            "state": {"equalTo": "all"},
            "sort": {"equalTo": "created"},
            "direction": {"equalTo": "desc"},
            "per_page": {"equalTo": "1"},
        }

        Mappings.create_mapping(
            Mapping(
                scenario_name="github scenario",
                required_scenario_state="Started",
                new_scenario_state="First request",
                request=MappingRequest(
                    method="GET",
                    url_path="/repos/helleye431/asteroids/issues",
                    query_parameters=github_params,
                ),
                response=MappingResponse(
                    status=500,
                ),
                persistent=False,
            ),
        )

        Mappings.create_mapping(
            Mapping(
                scenario_name="github scenario",
                required_scenario_state="First request",
                new_scenario_state="Second request",
                request=MappingRequest(
                    method="GET",
                    url_path="/repos/helleye431/asteroids/issues",
                    query_parameters=github_params,
                ),
                response=MappingResponse(
                    status=500,
                ),
                persistent=False,
            ),
        )
        Mappings.create_mapping(
            Mapping(
                scenario_name="github scenario",
                required_scenario_state="Second request",
                new_scenario_state="Third request",
                request=MappingRequest(
                    method="GET",
                    url_path="/repos/helleye431/asteroids/issues",
                    query_parameters=github_params,
                ),
                response=MappingResponse(
                    status=200,
                    json_body=[
                        {
                            "title": "Http api contract issue",
                            "user": {"login": "boss"},
                            "created_at": "2021-01-01T00:00:00Z",
                            "body": "Need to fix one http api bug in your code",
                        }
                    ],
                ),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                scenario_name="github scenario",
                required_scenario_state="Third request",
                new_scenario_state="Third request",
                request=MappingRequest(
                    method="GET",
                    url_path="/repos/helleye431/asteroids/issues",
                    query_parameters=github_params,
                ),
                response=MappingResponse(
                    status=400,
                ),
                persistent=False,
            ),
        )

        stackoverflow_params = {
            "site": {"equalTo": "stackoverflow"},
        }

        Mappings.create_mapping(
            Mapping(
                scenario_name="stackoverflow scenario",
                required_scenario_state="Started",
                new_scenario_state="First request",
                request=MappingRequest(
                    method="GET",
                    url_path="/questions/123",
                    query_parameters=stackoverflow_params,
                ),
                response=MappingResponse(
                    status=500,
                ),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                scenario_name="stackoverflow scenario",
                required_scenario_state="First request",
                new_scenario_state="Second request",
                request=MappingRequest(
                    method="GET",
                    url_path="/questions/123",
                    query_parameters=stackoverflow_params,
                ),
                response=MappingResponse(
                    status=500,
                ),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                scenario_name="stackoverflow scenario",
                required_scenario_state="Second request",
                new_scenario_state="Third request",
                request=MappingRequest(
                    method="GET",
                    url_path="/questions/123",
                    query_parameters=stackoverflow_params,
                ),
                response=MappingResponse(
                    status=200,
                    json_body={
                        "items": [
                            {
                                "last_activity_date": 1609459200,
                            }
                        ]
                    },
                ),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                scenario_name="stackoverflow scenario",
                required_scenario_state="Third request",
                new_scenario_state="Third request",
                request=MappingRequest(
                    method="GET",
                    url_path="/questions/123",
                    query_parameters=stackoverflow_params,
                ),
                response=MappingResponse(
                    status=400,
                ),
                persistent=False,
            )
        )

        bot_params = [
            {
                "equalToJson": json.dumps(
                    {
                        "id": 123,
                        "url": "https://github.com/helleye431/asteroids",
                        "description": "Произошли обновления",
                        "tgChatIds": [1111111, 2222222],
                        "is_error": False,
                        "priority": "MEDIUM",
                    },
                    ensure_ascii=False,
                )
            }
        ]

        Mappings.create_mapping(
            Mapping(
                scenario_name="bot scenario",
                required_scenario_state="Started",
                new_scenario_state="First request",
                request=MappingRequest(
                    method="POST",
                    url_path="/updates",
                    headers={
                        "Content-Type": {"contains": "application/json"},
                    },
                    body_patterns=bot_params,
                ),
                response=MappingResponse(status=500),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                scenario_name="bot scenario",
                required_scenario_state="First request",
                new_scenario_state="Second request",
                request=MappingRequest(
                    method="POST",
                    url_path="/updates",
                    headers={
                        "Content-Type": {"contains": "application/json"},
                    },
                    body_patterns=bot_params,
                ),
                response=MappingResponse(status=500),
                persistent=False,
            )
        )
        Mappings.create_mapping(
            Mapping(
                scenario_name="bot scenario",
                required_scenario_state="Second request",
                new_scenario_state="Third request",
                request=MappingRequest(
                    method="POST",
                    url_path="/updates",
                    headers={
                        "Content-Type": {"contains": "application/json"},
                    },
                    body_patterns=bot_params,
                ),
                response=MappingResponse(
                    status=200,
                ),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                scenario_name="bot scenario",
                required_scenario_state="Third request",
                new_scenario_state="Third request",
                request=MappingRequest(
                    method="POST",
                    url_path="/updates",
                    headers={
                        "Content-Type": {"contains": "application/json"},
                    },
                    body_patterns=bot_params,
                ),
                response=MappingResponse(status=400),
                persistent=False,
            )
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


"""
Последующие 3 теста тестируют два объединённых сценария 
на разных клиентах:

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


@pytest.mark.asyncio
async def test_github_client_retry(
    wm_server_with_states, resilient_client_with_constant_retry, mocker
):

    github_client = GithubClient(
        base_url=wm_server_with_states.get_url(""),
        client=resilient_client_with_constant_retry,
    )
    spy_get = mocker.spy(resilient_client_with_constant_retry.client, "request")

    event = await github_client.get_latest_event(
        "https://github.com/helleye431/asteroids"
    )
    assert event is not None
    assert spy_get.call_count == 3

    # проверка при 400
    with pytest.raises(GithubServiceError):
        await github_client.get_latest_event("https://github.com/helleye431/asteroids")

    assert spy_get.call_count == 4


@pytest.mark.asyncio
async def test_stackoverflow_client_retry(
    wm_server_with_states, resilient_client_with_constant_retry, mocker
):
    stackoverflow_client = StackoverflowClient(
        base_url=wm_server_with_states.get_url(""),
        client=resilient_client_with_constant_retry,
    )
    spy_get = mocker.spy(resilient_client_with_constant_retry.client, "request")

    event = await stackoverflow_client.get_last_update(
        "https://stackoverflow.com/questions/123"
    )
    assert event is not None
    assert spy_get.call_count == 3

    # проверка при 400
    with pytest.raises(StackoverflowServiceError):
        await stackoverflow_client.get_last_update(
            "https://stackoverflow.com/questions/123"
        )

    assert spy_get.call_count == 4


@pytest.mark.asyncio
async def test_bot_client_retry(
    wm_server_with_states, resilient_client_with_constant_retry, mocker
):
    bot_client = HttpBotClient(
        base_url=wm_server_with_states.get_url(""),
        client=resilient_client_with_constant_retry,
    )
    spy_get = mocker.spy(resilient_client_with_constant_retry.client, "request")

    result = await bot_client.send_update(
        update_id=123,
        url="https://github.com/helleye431/asteroids",
        description="Произошли обновления",
        author="",
        chat_ids=[1111111, 2222222],
        is_error=False,
    )

    assert result is None
    assert spy_get.call_count == 3

    # проверка при 400
    with pytest.raises(httpx.HTTPError):
        await bot_client.send_update(
            update_id=123,
            url="https://github.com/helleye431/asteroids",
            description="Произошли обновления",
            author="",
            chat_ids=[1111111, 2222222],
            is_error=False,
        )

    assert spy_get.call_count == 4
