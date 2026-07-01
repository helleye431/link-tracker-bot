import json
import asyncio

import structlog
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import MessageField, SerializationContext

from ai_service.application.ports.update_sender_port import (
    UpdateSenderPort,
)
from ai_service.domain.models.processed_update import ProcessedUpdate

logger = structlog.get_logger(__name__)


class KafkaUpdateSender(UpdateSenderPort):
    def __init__(
        self,
        bootstrap_servers: str,
        processed_updates_topic: str,
        schema_registry_url: str,
    ) -> None:
        self.topic = processed_updates_topic
        self.producer = Producer({"bootstrap.servers": bootstrap_servers})
        self.schema_registry_client = SchemaRegistryClient({"url": schema_registry_url})
        self.link_update_schema = json.dumps(
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
                        "type": ["null", "string"],
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
        self.avro_serializer = AvroSerializer(
            schema_registry_client=self.schema_registry_client,
            schema_str=self.link_update_schema,
            conf={"auto.register.schemas": True},
        )

    async def send_update(self, update: ProcessedUpdate) -> None:
        payload = {
            "id": update.id,
            "url": str(update.url) if update.url else None,
            "description": update.description,
            "tgChatIds": update.tgChatIds,
            "is_error": update.is_error,
            "priority": update.priority,
        }

        value = self.avro_serializer(
            payload,
            SerializationContext(self.topic, MessageField.VALUE),
        )

        self.producer.produce(
            topic=self.topic,
            key=str(update.id).encode("utf-8"),
            value=value,
            callback=self._delivery_report,
        )

        remaining = await asyncio.to_thread(self.producer.flush, 3)

        if remaining > 0:
            raise RuntimeError("Kafka message was not delivered")

    @staticmethod
    def _delivery_report(err, msg) -> None:
        if err:
            logger.warning("Message delivery failed", error=str(err))
            raise

        logger.info(
            "Message delivered succeeded",
            topic=msg.topic(),
            partition=msg.partition(),
            offset=msg.offset(),
        )

    async def aclose(self) -> None:
        await asyncio.to_thread(self.producer.flush, 5)
