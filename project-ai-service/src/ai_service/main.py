from ai_service.application.services.update_sending_service import UpdateSendingService
from ai_service.infrastructure.background_workers.scheduler.update_sending_scheduler import (
    UpdateSendingScheduler,
)
from ai_service.infrastructure.background_workers.scheduler.update_sending_scheduler_runner import (
    UpdateSendingSchedulerRunner,
)
from ai_service.infrastructure.database.repositories.in_memory_pending_updates_repository import (
    InMemoryPendingUpdatesRepository,
)
from ai_service.presentation.kafka.kafka_consumer_runner import KafkaConsumerRunner
from ai_service.presentation.kafka.kafka_notification_consumer import (
    KafkaUpdateProcessingConsumer,
)
from ai_service.setup.app_lifecycle import ApplicationLifecycle
from ai_service.setup.config.setup_logger import setup_logger
from application.services.update_processing_service import UpdateProcessingService
from infrastructure.clients.kafka_update_sender import KafkaUpdateSender
from infrastructure.processors.ai_processor import AIProcessor
from ai_service.setup.config.settings import Settings
import structlog
import asyncio

setup_logger()
logger = structlog.get_logger(__name__)


async def main():

    settings = Settings()
    update_processor = AIProcessor(
        token=settings.ai_token.get_secret_value(),
        model=settings.ai_agent_processing_model,
        stop_words=settings.ai_agent_filtering_stop_words,
        excluded_authors=settings.ai_agent_filtering_excluded_authors,
        min_length=settings.ai_agent_filtering_min_length,
        summarization_threshold=settings.ai_agent_summarization_threshold,
        high_keywords=settings.ai_agent_prioritization_high_keywords,
        low_keywords=settings.ai_agent_prioritization_low_keywords,
    )

    pending_updates_repository = InMemoryPendingUpdatesRepository()

    update_processing_service = UpdateProcessingService(
        pending_updates_repository=pending_updates_repository,
        update_processor=update_processor,
    )

    update_sender = KafkaUpdateSender(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        processed_updates_topic=settings.kafka_processed_updates_topic,
        schema_registry_url=settings.schema_registry_url,
    )

    update_sending_service = UpdateSendingService(
        pending_update_repository=pending_updates_repository,
        update_sender=update_sender,
    )

    scheduler = UpdateSendingScheduler(
        update_sending_service=update_sending_service,
        interval_milliseconds=settings.ai_agent_grouping_window_ms,
    )

    scheduler_runner = UpdateSendingSchedulerRunner(scheduler=scheduler)

    kafka_consumer = KafkaUpdateProcessingConsumer(
        update_processing_service=update_processing_service,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_updates_consumer_group,
        auto_offset_reset=settings.kafka_auto_offset_reset,
        enable_auto_commit=settings.kafka_enable_auto_commit,
        topic=settings.kafka_raw_updates_topic,
        dlq_topic=settings.kafka_raw_updates_dlq_topic,
        max_processing_retries=settings.kafka_max_processing_retries,
        schema_registry_url=settings.schema_registry_url,
    )

    kafka_runner = KafkaConsumerRunner(consumer=kafka_consumer)

    runners = [kafka_runner, scheduler_runner]

    app_lifecycle = ApplicationLifecycle(runners=runners)

    try:
        logger.info("ai_service_application_started")
        await app_lifecycle.run()

    except Exception as exc:
        logger.exception("ai_service_application_crashed", error=str(exc))
        raise

    finally:
        logger.info("ai_service_application_closed")
        await update_sender.aclose()
        await update_processor.aclose()


if __name__ == "__main__":
    asyncio.run(main())
