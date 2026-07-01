from confluent_kafka import Consumer, KafkaError, Producer
import asyncio
import structlog
import base64
import json
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import MessageField, SerializationContext
from ai_service.application.exceptions.processing_exceptions import (
    MessageDeserializationError,
)
from pydantic import ValidationError

from ai_service.application.services.update_processing_service import (
    UpdateProcessingService,
)
from ai_service.domain.models.raw_update import RawUpdate

logger = structlog.get_logger(__name__)


class KafkaUpdateProcessingConsumer:
    def __init__(
        self,
        bootstrap_servers: str,
        group_id: str,
        auto_offset_reset: str,
        enable_auto_commit: bool,
        topic: str,
        dlq_topic: str,
        max_processing_retries: int,
        update_processing_service: UpdateProcessingService,
        schema_registry_url: str,
    ):
        self.update_processing_service = update_processing_service
        self.topic = topic
        self.running = True
        self.enable_auto_commit = enable_auto_commit
        self.dlq_topic = dlq_topic
        self.max_processing_retries = max_processing_retries
        self.consumer = Consumer(
            {
                "bootstrap.servers": bootstrap_servers,
                "group.id": group_id,
                "auto.offset.reset": auto_offset_reset,
                "enable.auto.commit": enable_auto_commit,
                "auto.commit.interval.ms": 5000,
                "session.timeout.ms": 30000,
                "max.poll.interval.ms": 300000,
            }
        )
        self.producer = Producer({"bootstrap.servers": bootstrap_servers})
        self.schema_registry_client = SchemaRegistryClient(
            {
                "url": schema_registry_url,
            }
        )

        self.avro_deserializer = AvroDeserializer(
            schema_registry_client=self.schema_registry_client,
        )

    def _start_subscribe(self):
        self.consumer.subscribe([self.topic])
        logger.info("start subscribing to topic", topic=self.topic)

    async def start_consumption(self) -> None:
        self._start_subscribe()
        try:
            while self.running:
                await self._consume()

        except asyncio.CancelledError:
            logger.info("Kafka consumer cancelled")
            self.running = False
            raise

        except Exception as exc:
            logger.exception("Error during kafka consumption", error=str(exc))
            raise

        finally:
            await asyncio.to_thread(self.close)

    async def _consume(self) -> None:
        msg = await asyncio.to_thread(self.consumer.poll, 1)

        if msg is None:
            return

        error = msg.error()

        if error:
            if error.code() == KafkaError._PARTITION_EOF:
                logger.debug(
                    "Reached end of partition",
                    topic=msg.topic(),
                    partition=msg.partition(),
                )
            else:
                logger.error("Kafka error", error=error)
            return

        for attempt in range(self.max_processing_retries + 1):
            try:
                await self._process_update(msg)

                await self._commit(msg)
                break
            except (ValidationError, MessageDeserializationError, TypeError) as exc:
                await self._send_to_dlq(
                    msg=msg,
                    reason="Validation/Serialization error",
                    error_message=str(exc),
                )
                await self._commit(msg)

                break
            except Exception as exc:
                logger.warning(
                    "Kafka message processing failed",
                    attempt=attempt,
                    error=str(exc),
                    topic=msg.topic(),
                    partition=msg.partition(),
                    offset=msg.offset(),
                )
                continue
        else:
            try:
                await self._send_to_dlq(
                    msg=msg, reason="All attempts have been exhausted"
                )
                await self._commit(msg)
            except Exception as exc:
                logger.warning(
                    "Send to dlq failed",
                    error=str(exc),
                    topic=msg.topic(),
                    partition=msg.partition(),
                    offset=msg.offset(),
                )

    async def _process_update(self, msg) -> None:
        try:
            raw_value = msg.value()

            if raw_value is None:
                raise MessageDeserializationError("Kafka message value is empty")

            try:
                link_update = self.avro_deserializer(
                    raw_value,
                    SerializationContext(msg.topic(), MessageField.VALUE),
                )
            except Exception as exc:
                raise MessageDeserializationError(str(exc))

            validated_raw_update = RawUpdate.model_validate(link_update)

            logger.info(
                "Correct message received",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
            )

            await self.update_processing_service.process_update(
                update=validated_raw_update
            )

        except (ValidationError, TypeError) as exc:
            logger.warning(
                "Validation error of message",
                error=exc.__class__.__name__,
                message=str(exc),
            )
            raise
        except MessageDeserializationError as exc:
            logger.warning(
                "Serialized error of message",
                error=exc.__class__.__name__,
                message=str(exc),
            )
            raise
        except Exception as exc:
            logger.warning(
                "Update_processing_service_error",
                error=exc.__class__.__name__,
                message=str(exc),
            )
            raise

    async def _commit(self, msg) -> None:
        if self.enable_auto_commit:
            return

        await asyncio.to_thread(
            self.consumer.commit,
            message=msg,
            asynchronous=False,
        )

    @staticmethod
    def _dlq_delivery_report(err, msg):
        if err:
            logger.warning("Message delivery to dead letter queue failed", error=err)
        else:
            logger.info(
                "Message delivered to dead letter queue succeeded",
                topic=msg.topic(),
                partition=msg.partition(),
            )

    async def _send_to_dlq(
        self,
        msg,
        reason: str,
        error_message: str | None = None,
    ) -> None:

        dlq_payload = {
            "reason": reason,
            "error_message": error_message,
            "original_topic": msg.topic(),
            "original_partition": msg.partition(),
            "original_offset": msg.offset(),
            "original_key": self._decode(msg.key()),
            "original_value": self._decode(msg.value()),
        }

        self.producer.produce(
            topic=self.dlq_topic,
            key=msg.key(),
            value=json.dumps(dlq_payload, ensure_ascii=False).encode("utf-8"),
            callback=self._dlq_delivery_report,
        )

        remaining = await asyncio.to_thread(self.producer.flush, 5)

        if remaining > 0:
            raise RuntimeError("DLQ message was not delivered")

    @staticmethod
    def _decode(value: bytes | None) -> str | None:
        if value is None:
            return None

        return base64.b64encode(value).decode("ascii")

    def stop(self) -> None:
        self.running = False

    def close(self) -> None:
        self.consumer.close()
        logger.info("Consumer closed")
