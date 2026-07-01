import os
import pytest
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import MessageField, SerializationContext
from confluent_kafka import Consumer
from scrapper_service.infrastructure.clients.kafka_notification_client import (
    KafkaNotificationClient,
)


@pytest.fixture
def notification_topic_env(monkeypatch):
    monkeypatch.setenv("kafka_notification_topic", "bot.notification")


@pytest.mark.asyncio
async def test_correct_produced_message(
    kafka_with_schema_registry, notification_topic_env
):
    """Scrapper отправляет уведомление через Kafka
    Нотификация отправляется в нужный Kafka topic в ожидаемом формате"""

    test_update_id = 1
    test_url = "https://github.com/helleye431"
    test_description = "new_isssue author: helleye431"
    test_author = "helleye431"
    test_tg_chat_ids = [1, 2]
    test_is_error = False

    test_topic = os.getenv("kafka_notification_topic")
    kafka_client = KafkaNotificationClient(
        bootstrap_servers=kafka_with_schema_registry["bootstrap_servers"],
        topic=test_topic,
        schema_registry_url=kafka_with_schema_registry["schema_registry_url"],
    )

    kafka_test_consumer = Consumer(
        {
            "bootstrap.servers": kafka_with_schema_registry["bootstrap_servers"],
            "group.id": "123",
            "auto.offset.reset": "earliest",
        }
    )

    await kafka_client.send_update(
        update_id=test_update_id,
        url=test_url,
        description=test_description,
        author=test_author,
        chat_ids=test_tg_chat_ids,
        is_error=test_is_error,
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

    kafka_test_consumer.close()
