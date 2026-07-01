import os

from pydantic import HttpUrl
from uuid import uuid4
from bot_service.application.ports.delivered_notifications_storage_port import (
    DeliveredNotificationsStoragePort,
)
import pytest
from unittest.mock import AsyncMock
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import MessageField, SerializationContext
from confluent_kafka import Producer, Consumer

from bot_service.application.services.update_service import UpdateService
from bot_service.presentation.kafka.kafka_notification_consumer import (
    KafkaNotificationConsumer,
)
import json
import base64

SCHEMA = json.dumps(
    {
        "type": "record",
        "name": "ClearLinkUpdateEvent",
        "namespace": "com.example.notification",
        "fields": [
            {
                "name": "id",
                "type": "long",
                "doc": "ID обновления",
            },
            {
                "name": "url",
                "type": "string",
                "doc": "Ссылка",
            },
            {
                "name": "description",
                "type": "string",
                "doc": "Описание изменений",
            },
            {
                "name": "tgChatIds",
                "type": {
                    "type": "array",
                    "items": "long",
                },
                "doc": "ИД чатов",
            },
            {
                "name": "is_error",
                "type": "boolean",
                "doc": "флаг ошибки",
            },
            {
                "name": "priority",
                "type": "string",
                "doc": "Приоритет обновления",
            },
        ],
    }
)


@pytest.fixture
def update_service_with_always_error():
    update_service = AsyncMock(spec=UpdateService)
    update_service.send_updates = AsyncMock(side_effect=RuntimeError)
    update_service.send_error_report = AsyncMock(return_value=None)
    return update_service


@pytest.fixture
def mock_delivered_notification_storage():
    delivered_notification_storage = AsyncMock(spec=DeliveredNotificationsStoragePort)
    delivered_notification_storage.is_delivered = AsyncMock(return_value=False)
    delivered_notification_storage.mark_delivered = AsyncMock(return_value=None)
    return delivered_notification_storage


@pytest.fixture
def notification_topic_and_dlq_env(monkeypatch):
    monkeypatch.setenv("kafka_notification_topic", "notifications.clear_updates")
    monkeypatch.setenv(
        "kafka_notification_dlq_topic", "notifications.clear_updates.dlq"
    )


@pytest.mark.asyncio
async def test_correct_consume_message_success_processed(
    kafka_with_schema_registry,
    notification_topic_and_dlq_env,
    tracking_service,
    mock_update_service,
    mock_delivered_notification_storage,
):
    """Bot consumer получает валидное сообщение

    Сообщение успешно обрабатывается (отправляется через update service)"""

    notification_topic = os.getenv("kafka_notification_topic") + str(uuid4())
    dlq_topic = os.getenv("kafka_notification_dlq_topic") + str(uuid4())
    group = f"consumer_group_{uuid4()}"
    kafka_consumer = KafkaNotificationConsumer(
        bootstrap_servers=kafka_with_schema_registry["bootstrap_servers"],
        group_id=group,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        topic=notification_topic,
        dlq_topic=dlq_topic,
        max_processing_retries=5,
        update_service=mock_update_service,
        delivered_notifications_storage=mock_delivered_notification_storage,
        schema_registry_url=kafka_with_schema_registry["schema_registry_url"],
    )

    test_producer = Producer(
        {"bootstrap.servers": kafka_with_schema_registry["bootstrap_servers"]}
    )

    schema_registry_client = SchemaRegistryClient(
        {"url": kafka_with_schema_registry["schema_registry_url"]}
    )

    avro_serializer = AvroSerializer(
        schema_registry_client=schema_registry_client,
        schema_str=SCHEMA,
        conf={"auto.register.schemas": True},
    )

    test_update_id = 1
    test_url = "https://github.com/helleye431/asteroids"
    test_description = "new_issue"
    test_chat_ids = [3]
    test_is_error = False
    test_priority = "MEDIUM"

    value = avro_serializer(
        {
            "id": test_update_id,
            "url": test_url,
            "tgChatIds": test_chat_ids,
            "description": test_description,
            "is_error": test_is_error,
            "priority": test_priority,
        },
        SerializationContext(notification_topic, MessageField.VALUE),
    )

    test_producer.produce(topic=notification_topic, value=value)

    test_producer.flush(5)

    kafka_consumer._start_subscribe()

    await kafka_consumer._consume()

    mock_update_service.send_updates.assert_awaited_once_with(
        url=HttpUrl(test_url), tg_chat_ids=test_chat_ids, description=test_description
    )


@pytest.mark.parametrize("scenario", ["serialization_error", "validation_error"])
@pytest.mark.asyncio
async def test_consume_message_has_serialization_or_validation_error(
    scenario,
    kafka_with_schema_registry,
    notification_topic_and_dlq_env,
    tracking_service,
    mock_update_service,
    mock_delivered_notification_storage,
):
    """Bot consumer получает невалидное сообщение по формату или структуре

    Сообщение не обрабатывается и отправляется в DLQ

    1: serialization_error
    сообщение поступает не в avro формате

    Сообщение не обрабатывается и отправляется в DLQ

    2: validation error
    сообщение по структуре некорректно

    Сообщение не обрабатывается и отправляется в DLQ"""

    notification_topic = os.getenv("kafka_notification_topic") + str(uuid4())
    dlq_topic = os.getenv("kafka_notification_dlq_topic") + str(uuid4())
    group = f"consumer_group_{uuid4()}"
    kafka_consumer = KafkaNotificationConsumer(
        bootstrap_servers=kafka_with_schema_registry["bootstrap_servers"],
        group_id=group,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        topic=notification_topic,
        dlq_topic=dlq_topic,
        max_processing_retries=5,
        update_service=mock_update_service,
        delivered_notifications_storage=mock_delivered_notification_storage,
        schema_registry_url=kafka_with_schema_registry["schema_registry_url"],
    )

    test_producer = Producer(
        {"bootstrap.servers": kafka_with_schema_registry["bootstrap_servers"]}
    )

    test_consumer_group = f"consumer_group_{uuid4()}"
    test_consumer = Consumer(
        {
            "bootstrap.servers": kafka_with_schema_registry["bootstrap_servers"],
            "group.id": test_consumer_group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )

    schema_registry_client = SchemaRegistryClient(
        {"url": kafka_with_schema_registry["schema_registry_url"]}
    )

    avro_serializer = AvroSerializer(
        schema_registry_client=schema_registry_client,
        schema_str=SCHEMA,
        conf={"auto.register.schemas": True},
    )

    test_update_id = 1
    test_url = "https://github.com/helleye431/asteroids"
    test_description = "new_issue"
    test_chat_ids = [3]
    test_is_error = False
    test_priority = "MEDIUM"

    if scenario == "serialization_error":
        value = json.dumps(
            {
                "id": test_update_id,
                "url": test_url,
                "tgChatIds": test_chat_ids,
                "description": test_description,
                "is_error": test_is_error,
                "priority": test_priority,
            }
        ).encode("utf-8")
    else:
        test_url = "github/helleye431"
        value = avro_serializer(
            {
                "id": test_update_id,
                "url": test_url,
                "tgChatIds": test_chat_ids,
                "description": test_description,
                "is_error": test_is_error,
                "priority": test_priority,
            },
            SerializationContext(notification_topic, MessageField.VALUE),
        )

    test_producer.produce(topic=notification_topic, value=value)

    test_producer.flush(5)

    kafka_consumer._start_subscribe()
    await kafka_consumer._consume()

    test_consumer.subscribe([dlq_topic])

    dlq_message = test_consumer.poll(timeout=5)

    assert dlq_message is not None
    assert dlq_message.error() is None

    dlq_payload = json.loads(dlq_message.value().decode("utf-8"))
    assert dlq_payload["reason"] == "Validation/Serialization error"
    assert dlq_payload["original_topic"] == notification_topic
    assert dlq_payload["original_value"] == base64.b64encode(value).decode("ascii")


@pytest.mark.asyncio
async def test_consume_message_has_processing_error(
    kafka_with_schema_registry,
    notification_topic_and_dlq_env,
    tracking_service,
    update_service_with_always_error,
    mock_delivered_notification_storage,
):
    """
    Ошибка при обработке сообщения в Bot consumer

    Выполняются повторные попытки обработки; после исчерпания попыток сообщение отправляется в DLQ
    """

    notification_topic = os.getenv("kafka_notification_topic") + str(uuid4())
    dlq_topic = os.getenv("kafka_notification_dlq_topic") + str(uuid4())
    group = f"consumer_group_{uuid4()}"
    max_processing_retries = 5
    kafka_consumer = KafkaNotificationConsumer(
        bootstrap_servers=kafka_with_schema_registry["bootstrap_servers"],
        group_id=group,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        topic=notification_topic,
        dlq_topic=dlq_topic,
        max_processing_retries=max_processing_retries,
        update_service=update_service_with_always_error,
        delivered_notifications_storage=mock_delivered_notification_storage,
        schema_registry_url=kafka_with_schema_registry["schema_registry_url"],
    )

    test_producer = Producer(
        {"bootstrap.servers": kafka_with_schema_registry["bootstrap_servers"]}
    )

    schema_registry_client = SchemaRegistryClient(
        {"url": kafka_with_schema_registry["schema_registry_url"]}
    )

    avro_serializer = AvroSerializer(
        schema_registry_client=schema_registry_client,
        schema_str=SCHEMA,
        conf={"auto.register.schemas": True},
    )

    test_update_id = 1
    test_url = "https://github.com/helleye431/asteroids"
    test_description = "new_issue"
    test_chat_ids = [3]
    test_is_error = False
    test_priority = "MEDIUM"

    value = avro_serializer(
        {
            "id": test_update_id,
            "url": test_url,
            "tgChatIds": test_chat_ids,
            "description": test_description,
            "is_error": test_is_error,
            "priority": test_priority,
        },
        SerializationContext(notification_topic, MessageField.VALUE),
    )

    test_consumer_group = f"consumer_group_{uuid4()}"
    test_consumer = Consumer(
        {
            "bootstrap.servers": kafka_with_schema_registry["bootstrap_servers"],
            "group.id": test_consumer_group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )

    test_producer.produce(topic=notification_topic, value=value)

    test_producer.flush(5)

    kafka_consumer._start_subscribe()

    await kafka_consumer._consume()

    assert (
        update_service_with_always_error.send_updates.await_count
        == max_processing_retries + 1
    )

    test_consumer.subscribe([dlq_topic])
    dlq_message = test_consumer.poll(timeout=5)

    assert dlq_message is not None
    assert dlq_message.error() is None

    dlq_payload = json.loads(dlq_message.value().decode("utf-8"))
    assert dlq_payload["reason"] == "All attempts have been exhausted"
    assert dlq_payload["original_topic"] == notification_topic
    assert dlq_payload["original_value"] == base64.b64encode(value).decode("ascii")
