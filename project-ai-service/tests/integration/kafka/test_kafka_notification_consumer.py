import os
from pydantic import HttpUrl
from uuid import uuid4
import pytest
from ai_service.domain.models.raw_update import RawUpdate
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import MessageField, SerializationContext
from confluent_kafka import Producer, Consumer
import logging

import json
import base64

from ai_service.presentation.kafka.kafka_notification_consumer import (
    KafkaUpdateProcessingConsumer,
)
from ai_service.setup.config.setup_logger import setup_logger

SCHEMA = json.dumps(
    {
        "type": "record",
        "name": "RawLinkUpdateEvent",
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
                "name": "author",
                "type": "string",
                "doc": "Автор изменений",
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
                "type": ["null", "string"],
                "doc": "Приоритет обновления",
            },
        ],
    }
)


@pytest.fixture
def raw_updates_topic_and_dlq_env(monkeypatch):
    monkeypatch.setenv("kafka_raw_updates_topic", "notifications.raw_updates")
    monkeypatch.setenv("kafka_raw_updates_dlq_topic", "notifications.raw_updates.dlq")


@pytest.mark.asyncio
async def test_correct_consume_message_success_processed(
    kafka_with_schema_registry,
    raw_updates_topic_and_dlq_env,
    mock_update_processing_service,
):
    """
    TC-1.1 Получение события из link.raw-updates
    Условие:
    Scrapper Service публикует корректное сообщение в Kafka topic link.raw-updates.

    Ожидаемый результат:
    AI Agent (service) получает сообщение
    Сообщение передаётся в обработку
    Ошибок десериализации не возникает
    """

    raw_updates_topic = os.getenv("kafka_raw_updates_topic") + str(uuid4())
    dlq_topic = os.getenv("kafka_raw_updates_dlq_topic") + str(uuid4())
    group = f"consumer_group_{uuid4()}"
    kafka_consumer = KafkaUpdateProcessingConsumer(
        bootstrap_servers=kafka_with_schema_registry["bootstrap_servers"],
        group_id=group,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        topic=raw_updates_topic,
        dlq_topic=dlq_topic,
        max_processing_retries=5,
        update_processing_service=mock_update_processing_service,
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
    test_author = "helleye431"
    test_chat_ids = [3]
    test_is_error = False
    test_priority = None

    value = avro_serializer(
        {
            "id": test_update_id,
            "url": test_url,
            "tgChatIds": test_chat_ids,
            "description": test_description,
            "author": test_author,
            "is_error": test_is_error,
            "priority": test_priority,
        },
        SerializationContext(raw_updates_topic, MessageField.VALUE),
    )

    test_producer.produce(topic=raw_updates_topic, value=value)

    test_producer.flush(5)

    kafka_consumer._start_subscribe()

    await kafka_consumer._consume()

    mock_update_processing_service.process_update.assert_awaited_once_with(
        update=RawUpdate(
            id=test_update_id,
            url=HttpUrl(test_url),
            description=test_description,
            author=test_author,
            tgChatIds=test_chat_ids,
            is_error=test_is_error,
            priority=test_priority,
        )
    )


@pytest.mark.asyncio
async def test_consume_message_has_serialization_or_validation_error(
    kafka_with_schema_registry,
    raw_updates_topic_and_dlq_env,
    mock_update_processing_service,
    caplog,
):
    """
    TC-1.2 Некорректный формат сообщения
    Условие:
    В topic публикуется сообщение с некорректной структурой.

    Ожидаемый результат:
    Сообщение не приводит к падению сервиса
    Ошибка логируется + сообщение отправляется в dlq"""

    setup_logger()
    caplog.set_level(logging.INFO)

    raw_updates_topic = os.getenv("kafka_raw_updates_topic") + str(uuid4())
    dlq_topic = os.getenv("kafka_raw_updates_dlq_topic") + str(uuid4())
    group = f"consumer_group_{uuid4()}"
    kafka_consumer = KafkaUpdateProcessingConsumer(
        bootstrap_servers=kafka_with_schema_registry["bootstrap_servers"],
        group_id=group,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        topic=raw_updates_topic,
        dlq_topic=dlq_topic,
        max_processing_retries=5,
        update_processing_service=mock_update_processing_service,
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

    test_update_id = 1
    test_url = "https://github.com/helleye431/asteroids"
    test_description = "new_issue"
    test_chat_ids = [3]
    test_is_error = False
    test_priority = "MEDIUM"

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

    test_producer.produce(topic=raw_updates_topic, value=value)

    test_producer.flush(5)

    kafka_consumer._start_subscribe()
    await kafka_consumer._consume()

    test_consumer.subscribe([dlq_topic])

    dlq_message = test_consumer.poll(timeout=5)

    # сообщение в логах
    assert "Serialized error of message" in caplog.text
    assert dlq_message is not None
    assert dlq_message.error() is None

    dlq_payload = json.loads(dlq_message.value().decode("utf-8"))
    assert dlq_payload["reason"] == "Validation/Serialization error"
    assert dlq_payload["original_topic"] == raw_updates_topic
    assert dlq_payload["original_value"] == base64.b64encode(value).decode("ascii")
