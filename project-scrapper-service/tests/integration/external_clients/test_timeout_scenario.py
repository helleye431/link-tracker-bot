import pytest
import json
import time
from httpx import TimeoutException
from wiremock.constants import Config
from wiremock.resources.mappings.models import (
    Mapping,
    MappingRequest,
    MappingResponse,
)
from wiremock.resources.mappings.resource import Mappings
from wiremock.testing.testcontainer import wiremock_container

from scrapper_service.infrastructure.clients.http_bot_client import HttpBotClient
from scrapper_service.infrastructure.clients.stackoverflow_client import (
    StackoverflowClient,
)
from scrapper_service.infrastructure.clients.utils.resilient_http_client import (
    ResilientHttpClient,
)
from scrapper_service.infrastructure.clients.github_client import GithubClient


@pytest.fixture
def wm_server_with_effects():
    with wiremock_container(secure=False) as wm:
        Config.base_url = wm.get_url("__admin")

        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(
                    method="GET",
                    url_path="/repos/helleye431/asteroids/issues",
                    query_parameters={
                        "state": {"equalTo": "all"},
                        "sort": {"equalTo": "created"},
                        "direction": {"equalTo": "desc"},
                        "per_page": {"equalTo": "1"},
                    },
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
                    fixed_delay_milliseconds=3000,
                ),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(
                    method="GET",
                    url_path="/questions/123",
                    query_parameters={
                        "site": {"equalTo": "stackoverflow"},
                        "sort": {"equalTo": "creation"},
                        "order": {"equalTo": "desc"},
                    },
                ),
                response=MappingResponse(
                    status=200,
                    json_body={
                        "items": [
                            {
                                "title": "Mocked from WireMock library",
                            }
                        ]
                    },
                    fixed_delay_milliseconds=3000,
                ),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(
                    method="POST",
                    url_path="/updates",
                    headers={
                        "Content-Type": {"contains": "application/json"},
                    },
                    body_patterns=[
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
                    ],
                ),
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
async def test_github_client_timeout(
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

    github_client = GithubClient(
        base_url=wm_server_with_effects.get_url(""),
        client=resilient_client_without_retry,
    )

    with pytest.raises(TimeoutException):
        await github_client.get_latest_event("https://github.com/helleye431/asteroids")

    start = time.perf_counter()
    with pytest.raises(TimeoutException):
        await github_client.get_latest_event("https://github.com/helleye431/asteroids")

    end = time.perf_counter()

    assert end - start < 3


@pytest.mark.asyncio
async def test_stackoverflow_client_timeout(
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
    stackoverflow_client = StackoverflowClient(
        base_url=wm_server_with_effects.get_url(""),
        client=resilient_client_without_retry,
    )

    with pytest.raises(TimeoutException):
        await stackoverflow_client.get_latest_event(
            "https://stackoverflow.com/questions/123"
        )

    start = time.perf_counter()
    with pytest.raises(TimeoutException):
        await stackoverflow_client.get_latest_event(
            "https://stackoverflow.com/questions/123"
        )

    end = time.perf_counter()

    assert end - start < 3


@pytest.mark.asyncio
async def test_bot_client_timeout(
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
    bot_client = HttpBotClient(
        base_url=wm_server_with_effects.get_url(""),
        client=resilient_client_without_retry,
    )

    with pytest.raises(TimeoutException):
        await bot_client.send_update(
            update_id=123,
            url="https://github.com/helleye431/asteroids",
            description="Произошли обновления",
            author="",
            chat_ids=[1111111, 2222222],
            is_error=False,
        )

    start = time.perf_counter()
    with pytest.raises(TimeoutException):
        await bot_client.send_update(
            update_id=123,
            url="https://github.com/helleye431/asteroids",
            description="Произошли обновления",
            author="",
            chat_ids=[1111111, 2222222],
            is_error=False,
        )

    end = time.perf_counter()

    assert end - start < 3
