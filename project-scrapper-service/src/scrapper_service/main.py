import asyncio
import structlog

from scrapper_service.application.services.link_update_fetcher_service import (
    LinkUpdateFetcherService,
)
from scrapper_service.application.services.link_update_processor_service import (
    LinkUpdateProcessorService,
)
from scrapper_service.application.services.notification_service import (
    NotificationService,
)
from scrapper_service.application.services.outbox_events_processor import (
    OutboxEventsProcessor,
)
from scrapper_service.infrastructure.background_workers.outbox.outbox_events_worker import (
    OutboxEventsWorker,
)
from scrapper_service.infrastructure.background_workers.outbox.outbox_events_worker_runner import (
    OutboxEventsWorkerRunner,
)
from scrapper_service.infrastructure.clients.github_client import GithubClient
from scrapper_service.infrastructure.clients.stackoverflow_client import (
    StackoverflowClient,
)
from scrapper_service.infrastructure.database.postgres.common.alembic_runner import (
    run_migrations,
)
from scrapper_service.setup.ioc.repository_builder import (
    build_repository,
)
from scrapper_service.infrastructure.background_workers.scheduler.link_scheduler import (
    LinkScheduler,
)
from scrapper_service.presentation.http.app_factory import create_app
from scrapper_service.application.common.runners.base_runner import BaseRunner
from scrapper_service.setup.app_lifecycle import ApplicationLifecycle
from scrapper_service.setup.config.settings import Settings
from scrapper_service.setup.ioc.notification_client_builder import (
    build_notification_client,
)
from scrapper_service.setup.ioc.server_runner_factory import build_server_runner
from scrapper_service.setup.ioc.tracking_repository_factory import (
    make_tracking_repository_factory,
)
from scrapper_service.setup.ioc.tracking_service_builder import build_tracking_service
from scrapper_service.setup.ioc.update_processor_worker_context_factory import (
    make_update_processor_worker_context_factory,
)
from scrapper_service.setup.config.setup_logger import setup_logger
from scrapper_service.infrastructure.background_workers.scheduler.link_scheduler_runner import (
    LinkSchedulerRunner,
)

setup_logger()
logger = structlog.get_logger(__name__)


async def main() -> None:
    settings = Settings()
    logger.info("scrapper_starting")

    run_migrations(settings.database_url_psycopg)
    logger.info("migrations_applied")

    bot_client = build_notification_client(
        notification_transport=settings.notification_transport,
        bot_grpc_target=settings.bot_grpc_target,
        bot_http_url=str(settings.bot_http_url),
        kafka_bootstrap_servers=settings.kafka_bootstrap_servers,
        kafka_topic=settings.kafka_notification_topic,
        schema_registry_url=settings.schema_registry_url,
        timeout_seconds=settings.timeout_seconds,
        retry_attempts=settings.retry_attempts,
        retry_backoff_seconds=settings.retry_backoff_seconds,
        retry_enable_exponential_backoff=settings.retry_enable_exponential_backoff,
        retryable_status_codes=settings.retryable_status_codes_list,
        circuit_error_ratio=settings.circuit_error_ratio,
        circuit_response_time=settings.circuit_response_time,
        circuit_recovery_time=settings.circuit_recovery_time,
        circuit_broken_time=settings.circuit_broken_time,
    )

    github_client = GithubClient(str(settings.github_base_url))
    stackoverflow_client = StackoverflowClient(str(settings.stackoverflow_base_url))

    tracking_repository = await build_repository(
        access_type=settings.access_type,
        orm_url=settings.database_url_asyncpg,
        raw_sql_url=settings.database_url_asyncpg_driver,
    )
    logger.info("tracking_repo_created", access_type=settings.access_type)

    update_fetcher_service = LinkUpdateFetcherService(
        external_clients=[github_client, stackoverflow_client]
    )

    tracking_service = await build_tracking_service(
        tracking_repository=tracking_repository,
        valkey_addresses=settings.valkey_addresses_list,
        update_fetcher_service=update_fetcher_service,
        enable_cache=settings.enable_cache,
        valkey_enable_client_cache=settings.valkey_enable_client_cache,
        valkey_cache_ttl=settings.valkey_cache_ttl,
        valkey_client_cache_ttl=settings.valkey_client_cache_ttl,
        valkey_client_cache_maxsize=settings.valkey_client_cache_maxsize,
    )

    tracking_repository_factory = make_tracking_repository_factory(
        access_type=settings.access_type,
        orm_url=settings.database_url_asyncpg,
        raw_sql_url=settings.database_url_asyncpg_driver,
    )

    update_processor_worker_context_factory = (
        make_update_processor_worker_context_factory(
            access_type=settings.access_type,
            orm_url=settings.database_url_asyncpg,
            raw_sql_url=settings.database_url_asyncpg_driver,
            github_base_url=str(settings.github_base_url),
            stackoverflow_base_url=str(settings.stackoverflow_base_url),
            interservice_transport=settings.notification_transport,
            bot_grpc_target=settings.bot_grpc_target,
            bot_http_url=str(settings.bot_http_url),
            kafka_bootstrap_servers=settings.kafka_bootstrap_servers,
            kafka_notification_topic=settings.kafka_notification_topic,
            schema_registry_url=settings.schema_registry_url,
            timeout_seconds=settings.timeout_seconds,
            retry_attempts=settings.retry_attempts,
            retry_backoff_seconds=settings.retry_backoff_seconds,
            retry_enable_exponential_backoff=settings.retry_enable_exponential_backoff,
            retryable_status_codes=settings.retryable_status_codes_list,
            circuit_error_ratio=settings.circuit_error_ratio,
            circuit_response_time=settings.circuit_response_time,
            circuit_recovery_time=settings.circuit_recovery_time,
            circuit_broken_time=settings.circuit_broken_time,
        )
    )

    processor = LinkUpdateProcessorService(
        tracking_repository_factory=tracking_repository_factory,
        update_processor_worker_context_factory=update_processor_worker_context_factory,
        batch_size=settings.scheduler_batch_size,
        workers_count=settings.scheduler_workers_count,
        transactional_outbox_mode=settings.transactional_outbox_mode,
    )

    scheduler = LinkScheduler(
        processor=processor,
        interval_seconds=settings.scheduler_interval_seconds,
    )

    app = create_app(
        title="Scrapper API",
        version="1.0.0",
        contact_name="Kravchuk Kirill",
        contact_url="https://t.me/yukizzz000",
        tracking_service=tracking_service,
        request_limit=settings.request_limit,
        request_limit_period=settings.request_limit_period,
    )

    server_runner: BaseRunner = build_server_runner(
        interservice_transport=settings.interservice_transport,
        tracking_service=tracking_service,
        scrapper_grpc_host=settings.scrapper_grpc_host,
        scrapper_grpc_port=settings.scrapper_grpc_port,
        scrapper_http_host=settings.scrapper_http_url.host,
        scrapper_http_port=settings.scrapper_http_url.port,
        app=app,
    )

    scheduler_runner = LinkSchedulerRunner(scheduler=scheduler)

    notification_service = NotificationService(notification_clients=[bot_client])

    runners: list[BaseRunner] = [
        server_runner,
        scheduler_runner,
    ]

    if settings.transactional_outbox_mode:
        outbox_events_processor = OutboxEventsProcessor(
            repository=tracking_repository, notification_service=notification_service
        )

        outbox_event_worker = OutboxEventsWorker(
            processor=outbox_events_processor,
            outbox_processing_delay=settings.outbox_processing_delay,
        )

        outbox_runner = OutboxEventsWorkerRunner(
            outbox_processor_runner=outbox_event_worker,
        )

        runners.append(outbox_runner)

    lifecycle = ApplicationLifecycle(runners=runners)

    try:
        await lifecycle.run()

    except Exception as exc:
        logger.exception("scrapper_application_crashed", error=str(exc))
        raise

    finally:
        logger.info("scrapper_stopping")

        await tracking_repository.aclose()
        await bot_client.aclose()
        await update_fetcher_service.close_clients()

        logger.info("scrapper_stopped")


if __name__ == "__main__":
    asyncio.run(main())
