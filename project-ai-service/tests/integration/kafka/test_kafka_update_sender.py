import os

from confluent_kafka.admin import AdminClient
from confluent_kafka.cimpl import NewTopic
from pydantic import HttpUrl
from uuid import uuid4
import pytest
from ai_service.application.services.update_processing_service import (
    UpdateProcessingService,
)
from ai_service.application.services.update_sending_service import UpdateSendingService
from ai_service.domain.models.raw_update import RawUpdate
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import MessageField, SerializationContext
from confluent_kafka import Consumer
from ai_service.infrastructure.clients.kafka_update_sender import KafkaUpdateSender
from ai_service.infrastructure.database.repositories.in_memory_pending_updates_repository import (
    InMemoryPendingUpdatesRepository,
)
from ai_service.infrastructure.processors.ai_processor import AIProcessor


@pytest.fixture
def processed_update_topic_env(monkeypatch):
    monkeypatch.setenv(
        "kafka_processed_updates_topic", "notifications.processed_updates"
    )


@pytest.mark.asyncio
async def test_processed_update_is_produced_successfully(
    kafka_with_schema_registry,
    processed_update_topic_env,
):
    """
    TC-3.1 Успешная публикация
    Условие:
    Сообщение прошло все этапы обработки (приоритизация + группировка).

    Ожидаемый результат:
    Сообщение публикуется в topic link.processed-updates
    Bot Service может получить это сообщение
    """

    processed_updates_topic = os.getenv("kafka_processed_updates_topic") + str(uuid4())
    group = f"consumer_group_{uuid4()}"

    update_sender = KafkaUpdateSender(
        bootstrap_servers=kafka_with_schema_registry["bootstrap_servers"],
        processed_updates_topic=processed_updates_topic,
        schema_registry_url=kafka_with_schema_registry["schema_registry_url"],
    )
    pending_updates_repository = InMemoryPendingUpdatesRepository()
    processor = AIProcessor(
        token="",
        model="",
        stop_words=[],
        excluded_authors=[],
        min_length=10,
        summarization_threshold=1000,
        high_keywords=["github"],
        low_keywords=[],
    )
    processor.base_url = ""

    processing_service = UpdateProcessingService(
        update_processor=processor,
        pending_updates_repository=pending_updates_repository,
    )

    update_sending_service = UpdateSendingService(
        pending_update_repository=pending_updates_repository,
        update_sender=update_sender,
    )

    test_update1 = RawUpdate(
        id=1,
        url=HttpUrl("https://github.com/helleye431/asteroids"),
        description="Первое длинное обновление github",
        author="helleye431",
        tgChatIds=[1111],
        is_error=False,
        priority=None,
    )

    test_update2 = RawUpdate(
        id=2,
        url=HttpUrl("https://github.com/helleye431/asteroids"),
        description="Второе простое длинное обновление",
        author="helleye431",
        tgChatIds=[1111],
        is_error=False,
        priority=None,
    )

    await processing_service.process_update(update=test_update1)
    await processing_service.process_update(update=test_update2)

    await update_sending_service.send_pending_updates()

    kafka_test_consumer = Consumer(
        {
            "bootstrap.servers": kafka_with_schema_registry["bootstrap_servers"],
            "group.id": group,
            "auto.offset.reset": "earliest",
        }
    )

    kafka_test_consumer.subscribe(topics=[processed_updates_topic])

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

    assert value["id"] == 2
    assert value["url"] is None
    assert value["description"] == (
        "1.\nПервое длинное обновление github\n\n"
        "2.\nВторое простое длинное обновление\n\n"
    )
    assert value["tgChatIds"] == [1111]
    assert not value["is_error"]
    assert value["priority"] == "HIGH"

    kafka_test_consumer.close()
    await update_sender.aclose()


@pytest.mark.asyncio
async def test_filtered_update_is_not_published_to_output_topic(
    kafka_with_schema_registry,
    processed_update_topic_env,
):
    """
    TC-3.2 Отсутствие публикации при фильтрации
    Условие:
    Обновление было отфильтровано на этапе фильтрации (часть 1).

    Ожидаемый результат:
    Сообщение не публикуется в выходной topic
    """

    processed_updates_topic = os.getenv("kafka_processed_updates_topic") + str(uuid4())
    group = f"consumer_group_{uuid4()}"

    update_sender = KafkaUpdateSender(
        bootstrap_servers=kafka_with_schema_registry["bootstrap_servers"],
        processed_updates_topic=processed_updates_topic,
        schema_registry_url=kafka_with_schema_registry["schema_registry_url"],
    )
    pending_updates_repository = InMemoryPendingUpdatesRepository()
    processor = AIProcessor(
        token="",
        model="",
        stop_words=["github"],
        excluded_authors=[],
        min_length=10,
        summarization_threshold=1000,
        high_keywords=[],
        low_keywords=[],
    )
    processor.base_url = ""

    processing_service = UpdateProcessingService(
        update_processor=processor,
        pending_updates_repository=pending_updates_repository,
    )

    update_sending_service = UpdateSendingService(
        pending_update_repository=pending_updates_repository,
        update_sender=update_sender,
    )

    test_update1 = RawUpdate(
        id=1,
        url=HttpUrl("https://github.com/helleye431/asteroids"),
        description="Первое длинное обновление github",
        author="helleye431",
        tgChatIds=[1111],
        is_error=False,
        priority=None,
    )

    await processing_service.process_update(update=test_update1)

    await update_sending_service.send_pending_updates()

    # предварительное создание топика
    admin_client = AdminClient(
        {
            "bootstrap.servers": kafka_with_schema_registry["bootstrap_servers"],
        }
    )

    topic = NewTopic(
        topic=processed_updates_topic,
        num_partitions=1,
        replication_factor=1,
    )

    future = admin_client.create_topics([topic])[processed_updates_topic]
    future.result(timeout=10)

    kafka_test_consumer = Consumer(
        {
            "bootstrap.servers": kafka_with_schema_registry["bootstrap_servers"],
            "group.id": group,
            "auto.offset.reset": "earliest",
        }
    )

    kafka_test_consumer.subscribe(topics=[processed_updates_topic])

    msg = kafka_test_consumer.poll(timeout=3)

    assert msg is None

    kafka_test_consumer.close()
    await update_sender.aclose()
