from scrapper_service.setup.config.settings import Settings
import pytest
from scrapper_service.setup.ioc.notification_client_builder import (
    build_notification_client,
)
from scrapper_service.infrastructure.clients.http_bot_client import HttpBotClient
from scrapper_service.infrastructure.clients.kafka_notification_client import (
    KafkaNotificationClient,
)


@pytest.mark.parametrize(
    "key, value, client_type",
    [
        ("notification_transport", "http", HttpBotClient),
        ("notification_transport", "kafka", KafkaNotificationClient),
    ],
)
def test_correct_notification_client_selection(key, value, client_type, monkeypatch):
    """Scrapper использует реализацию отправки уведомлений в зависимости от notification_transport

    В зависимости от значения параметра вызывается нужная реализация отправки нотификаций в Bot
    """
    monkeypatch.setenv(key, value)

    settings = Settings()

    notification_client = build_notification_client(
        notification_transport=settings.notification_transport,
        bot_grpc_target=settings.bot_grpc_target,
        bot_http_url=str(settings.bot_http_url),
        kafka_bootstrap_servers=settings.kafka_bootstrap_servers,
        kafka_topic=settings.kafka_notification_topic,
        schema_registry_url=settings.schema_registry_url,
        timeout_seconds=5,
        retry_attempts=5,
        retry_backoff_seconds=3,
        retry_enable_exponential_backoff=False,
        retryable_status_codes=[500, 400],
        circuit_error_ratio=0.5,
        circuit_response_time=5,
        circuit_recovery_time=10,
        circuit_broken_time=20,
    )

    assert isinstance(notification_client, client_type)
