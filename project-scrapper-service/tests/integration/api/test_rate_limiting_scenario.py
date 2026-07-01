import pytest
from fastapi.testclient import TestClient
import time
from scrapper_service.presentation.http.app_factory import create_app
from scrapper_service.application.services.tracking_service import TrackingService
from scrapper_service.infrastructure.database.postgres.repositories.in_memory.in_memory_tracking_repository import (
    InMemoryTrackingRepository,
)
from scrapper_service.presentation.http.utils.rate_limiter import rate_limiter


@pytest.fixture
def client_for_api_with_rate(mock_link_update_fetcher_service):
    repo = InMemoryTrackingRepository()

    tracking_service = TrackingService(repo, mock_link_update_fetcher_service)

    app = create_app(
        title="Scrapper API",
        version="1.0.0",
        contact_name="Kirill Kravchuk",
        contact_url="https://github.com",
        tracking_service=tracking_service,
        request_limit=3,
        request_limit_period="second",
    )

    app.state.tracking_service = tracking_service
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
        response = client.post(f"/tg-chat/{i}")
        status_codes.append(response.status_code)

    time.sleep(1)
    assert status_codes == result_status_codes
