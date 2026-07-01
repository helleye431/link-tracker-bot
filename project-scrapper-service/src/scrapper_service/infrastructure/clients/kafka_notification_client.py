import json
import asyncio

import structlog
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import MessageField, SerializationContext

from scrapper_service.application.ports.notification_client_port import (
    NotificationClientPort,
)
from scrapper_service.infrastructure.observability.metrics_decorators import (
    observe_request_duration,
)

logger = structlog.get_logger(__name__)


class KafkaNotificationClient(NotificationClientPort):
    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        schema_registry_url: str,
    ) -> None:
        self.topic = topic
        self.producer = Producer({"bootstrap.servers": bootstrap_servers})
        self.schema_registry_client = SchemaRegistryClient({"url": schema_registry_url})
        self.link_update_schema = json.dumps(
            {
                "type": "record",
                "name": "RawUpdateEvent",
                "namespace": "nofications.updates",
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
                    {"name": "author", "type": "string", "doc": "Автор изменений"},
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
        self.avro_serializer = AvroSerializer(
            schema_registry_client=self.schema_registry_client,
            schema_str=self.link_update_schema,
            conf={"auto.register.schemas": True},
        )

    @observe_request_duration(scope="external_source", scope_type="kafka")
    async def send_update(
        self,
        update_id: int,
        url: str,
        description: str,
        author: str,
        chat_ids: list[int],
        is_error: bool,
    ) -> None:

        payload = {
            "id": update_id,
            "url": url,
            "description": description,
            "author": author,
            "tgChatIds": chat_ids,
            "is_error": is_error,
            "priority": None,
        }

        value = self.avro_serializer(
            payload,
            SerializationContext(self.topic, MessageField.VALUE),
        )

        self.producer.produce(
            topic=self.topic,
            key=str(update_id).encode("utf-8"),
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
            return

        logger.info(
            "Message delivered succeeded",
            topic=msg.topic(),
            partition=msg.partition(),
            offset=msg.offset(),
        )

    async def aclose(self) -> None:
        await asyncio.to_thread(self.producer.flush, 5)
