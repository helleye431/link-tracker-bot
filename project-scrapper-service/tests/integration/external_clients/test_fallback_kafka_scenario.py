import os
import pytest
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import MessageField, SerializationContext
from confluent_kafka import Consumer
from scrapper_service.application.services.notification_service import (
    NotificationService,
)
from scrapper_service.infrastructure.clients.http_bot_client import HttpBotClient
from scrapper_service.infrastructure.clients.kafka_notification_client import (
    KafkaNotificationClient,
)
from scrapper_service.setup.config.setup_logger import setup_logger


@pytest.fixture
def notification_test_topic_env(monkeypatch):
    monkeypatch.setenv("kafka_notification_test_topic", "bot.notification.fallback")


@pytest.mark.slow
@pytest.mark.asyncio
async def test_correct_fallback_kafka_delivery(
    caplog, kafka_with_schema_registry, notification_test_topic_env
):
    """
    Тестирование FR-10: Fallback
    TC-5.1 Падение основного транспорта
    Условие:
    Основной транспорт (HTTP) недоступен.

    Ожидаемый результат:
    Используется альтернативный (Kafka) транспорт.
    Ошибка не теряется молча.
    """

    setup_logger()

    test_update_id = 1
    test_url = "https://github.com/helleye431"
    test_description = "new_isssue author: helleye431"
    test_tg_chat_ids = [1, 2]
    test_is_error = False

    # берём заведомо недоступный хост
    bot_client = HttpBotClient(base_url="http://localhost")

    test_topic = os.getenv("kafka_notification_test_topic")
    kafka_client = KafkaNotificationClient(
        bootstrap_servers=kafka_with_schema_registry["bootstrap_servers"],
        topic=test_topic,
        schema_registry_url=kafka_with_schema_registry["schema_registry_url"],
    )

    notification_service = NotificationService(
        notification_clients=[bot_client, kafka_client]
    )

    await notification_service.send_update_notification(
        update_id=test_update_id,
        url=test_url,
        description=test_description,
        author="",
        chat_ids=test_tg_chat_ids,
        is_error=test_is_error,
    )

    kafka_test_consumer = Consumer(
        {
            "bootstrap.servers": kafka_with_schema_registry["bootstrap_servers"],
            "group.id": "123",
            "auto.offset.reset": "earliest",
        }
    )

    kafka_test_consumer.subscribe(topics=[test_topic])
    msg = kafka_test_consumer.poll(timeout=3)

    schema_registry_client = SchemaRegistryClient(
        {"url": kafka_with_schema_registry["schema_registry_url"]}
    )
    avro_deserializer = AvroDeserializer(
        schema_registry_client=schema_registry_client,
    )

    value = avro_deserializer(
        msg.value(),
        SerializationContext(msg.topic(), MessageField.VALUE),
    )

    assert value["id"] == test_update_id
    assert value["url"] == test_url
    assert value["description"] == test_description
    assert value["tgChatIds"] == test_tg_chat_ids
    assert value["is_error"] == test_is_error

    assert "sender_client_has_any_error" in caplog.text

    kafka_test_consumer.close()
