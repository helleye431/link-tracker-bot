import pytest
from fastapi.testclient import TestClient
import time


from bot_service.presentation.http.app_factory import create_app
from bot_service.presentation.http.utils.rate_limiter import rate_limiter


@pytest.fixture
def client_for_api_with_rate(mock_update_service):

    app = create_app(
        title="Scrapper API",
        version="1.0.0",
        contact_name="Kirill Kravchuk",
        contact_url="https://github.com",
        update_service=mock_update_service,
        request_limit=3,
        request_limit_period="second",
    )

    app.state.update_service = mock_update_service
    app.state.limiter = rate_limiter(request_limit=3, request_limit_period="second")
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize(
    "response_count, result_status_codes",
    [(5, [200, 200, 200, 429, 429]), (2, [200, 200])],
)
def test_rate_limit(client_for_api_with_rate, response_count, result_status_codes):
    """
    TC-3.1 Превышение лимита
    Условие:
    С одного IP отправляется количество запросов больше установленного лимита.

    Ожидаемый результат:
    Превышающие запросы получают HTTP 429.
    В пределах лимита запросы обрабатываются успешно.
    """
    client = client_for_api_with_rate

    status_codes = []
    for i in range(response_count):
        response = client.post(
            url="updates",
            json={
                "id": "1",
                "url": "https://github.com/helleye431/asteroids",
                "description": "new issue",
                "tgChatIds": [1, 2, 3],
                "is_error": False,
                "priority": "MEDIUM",
            },
        )
        status_codes.append(response.status_code)

    time.sleep(1)
    assert status_codes == result_status_codes
