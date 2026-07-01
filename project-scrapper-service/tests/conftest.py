import pytest
import asyncpg
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from scrapper_service.application.services.notification_service import (
    NotificationService,
)
from scrapper_service.application.services.link_update_fetcher_service import (
    LinkUpdateFetcherService,
)
from scrapper_service.infrastructure.database.valkey.utils.valkey_client import (
    ValkeyClient,
)
from scrapper_service.presentation.http.app_factory import create_app
from scrapper_service.application.ports.scheduler_port import SchedulerPort
from scrapper_service.application.ports.notification_client_port import (
    NotificationClientPort,
)
from scrapper_service.application.services.tracking_service import TrackingService
from scrapper_service.infrastructure.database.postgres.repositories.in_memory.in_memory_tracking_repository import (
    InMemoryTrackingRepository,
)
from scrapper_service.infrastructure.database.postgres.repositories.orm.orm_tracking_repository import (
    OrmTrackingRepository,
)
from scrapper_service.infrastructure.database.postgres.repositories.raw_sql.raw_sql_tracking_repository import (
    RawSqlTrackingRepository,
)
from alembic import command
from alembic.config import Config
from testcontainers.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.kafka import KafkaContainer


class DummyScheduler(SchedulerPort):
    def run(self):
        return None


@pytest.fixture(scope="function")
def mock_bot_client():
    client = AsyncMock(spec=NotificationClientPort)
    client.send_update.return_value = None
    client.aclose.return_value = None
    return client


@pytest.fixture(scope="function")
def notification_service(mock_bot_client) -> NotificationService:
    return NotificationService(notification_clients=[mock_bot_client])


@pytest.fixture
def mock_link_update_fetcher_service():
    fetcher = AsyncMock(spec=LinkUpdateFetcherService)

    fetcher.get_last_update.return_value = None
    fetcher.get_latest_event.return_value = None
    fetcher.close_clients.return_value = None

    return fetcher


@pytest.fixture
def client(mock_link_update_fetcher_service):
    repo = InMemoryTrackingRepository()

    tracking_service = TrackingService(repo, mock_link_update_fetcher_service)

    app = create_app(
        title="Scrapper API",
        version="1.0.0",
        contact_name="Kirill Kravchuk",
        contact_url="https://github.com",
        tracking_service=tracking_service,
        request_limit=1000,
        request_limit_period="hour",
    )

    app.state.tracking_service = tracking_service

    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def migration_sync_url(postgres_container) -> str:
    return postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://",
        "postgresql+psycopg://",
    )


@pytest.fixture(scope="session", autouse=True)
def apply_migrations(migration_sync_url: str):
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", migration_sync_url)
    command.upgrade(alembic_cfg, "head")
    yield


@pytest_asyncio.fixture
async def clear_db(postgres_container, apply_migrations):
    database_url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://",
        "postgresql://",
    )

    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute(
            "TRUNCATE TABLE link_filters, link_tags, link_chat, links, chats, update_events_outbox RESTART IDENTITY CASCADE;"
        )
        yield
        await conn.execute(
            "TRUNCATE TABLE link_filters, link_tags, link_chat, links, chats, update_events_outbox RESTART IDENTITY CASCADE;"
        )
    finally:
        await conn.close()


@pytest_asyncio.fixture(scope="function")
async def raw_sql_repository(postgres_container, apply_migrations, clear_db):
    database_url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://",
        "postgresql://",
    )

    repo = await RawSqlTrackingRepository.create(database_url)
    try:
        yield repo
    finally:
        await repo.aclose()


@pytest_asyncio.fixture(scope="function")
async def orm_repository(postgres_container, apply_migrations, clear_db):
    database_url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://",
        "postgresql+asyncpg://",
    )

    repo = OrmTrackingRepository(database_url)
    try:
        yield repo
    finally:
        await repo.aclose()


@pytest.fixture(scope="session")
def kafka_with_schema_registry():
    with Network() as network:
        kafka = (
            KafkaContainer("confluentinc/cp-kafka:7.3.2")
            .with_network(network)
            .with_network_aliases("kafka")
        )

        with kafka:
            schema_registry = (
                DockerContainer("confluentinc/cp-schema-registry:7.3.2")
                .with_network(network)
                .with_network_aliases("schema-registry")
                .with_exposed_ports(8081)
                .with_env("SCHEMA_REGISTRY_HOST_NAME", "schema-registry")
                .with_env("SCHEMA_REGISTRY_LISTENERS", "http://0.0.0.0:8081")
                .with_env(
                    "SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS",
                    "PLAINTEXT://kafka:9092",
                )
                .waiting_for(
                    LogMessageWaitStrategy("Server started, listening for requests")
                )
            )

            with schema_registry:

                schema_registry_url = f"http://{schema_registry.get_container_host_ip()}:{schema_registry.get_exposed_port(8081)}"

                yield {
                    "bootstrap_servers": kafka.get_bootstrap_server(),
                    "schema_registry_url": schema_registry_url,
                }


@pytest.fixture(scope="session")
def valkey_cluster():
    command = """
    sh -c '
      mkdir -p /tmp/valkey-17000 /tmp/valkey-17001 /tmp/valkey-17002

      cat > /tmp/valkey-17000/valkey.conf <<EOF
port 17000
dir /tmp/valkey-17000
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 5000
appendonly no
protected-mode no
bind 0.0.0.0
daemonize yes
EOF

      cat > /tmp/valkey-17001/valkey.conf <<EOF
port 17001
dir /tmp/valkey-17001
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 5000
appendonly no
protected-mode no
bind 0.0.0.0
daemonize yes
EOF

      cat > /tmp/valkey-17002/valkey.conf <<EOF
port 17002
dir /tmp/valkey-17002
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 5000
appendonly no
protected-mode no
bind 0.0.0.0
daemonize yes
EOF

      valkey-server /tmp/valkey-17000/valkey.conf
      valkey-server /tmp/valkey-17001/valkey.conf
      valkey-server /tmp/valkey-17002/valkey.conf

      until valkey-cli -p 17000 ping; do sleep 0.2; done
      until valkey-cli -p 17001 ping; do sleep 0.2; done
      until valkey-cli -p 17002 ping; do sleep 0.2; done

      yes yes | valkey-cli --cluster create \
        127.0.0.1:17000 \
        127.0.0.1:17001 \
        127.0.0.1:17002 \
        --cluster-replicas 0

      echo VALKEY_CLUSTER_READY

      tail -f /dev/null
    '
    """

    with (
        DockerContainer("valkey/valkey:8-alpine")
        .with_bind_ports(17000, 17000)
        .with_bind_ports(17001, 17001)
        .with_bind_ports(17002, 17002)
        .with_command(command)
        .waiting_for(LogMessageWaitStrategy("VALKEY_CLUSTER_READY"))
    ) as container:
        yield {
            "container": container,
            "addresses": [
                ("127.0.0.1", 17000),
                ("127.0.0.1", 17001),
                ("127.0.0.1", 17002),
            ],
        }


@pytest_asyncio.fixture(scope="function")
async def valkey_client_factory(valkey_cluster):
    addresses = valkey_cluster["addresses"]

    async def factory(
        enable_client_cache: bool = False,
        client_cache_ttl: int = 0,
        client_cache_maxsize: int = 0,
    ) -> ValkeyClient:

        client = await ValkeyClient.create(
            valkey_addresses=addresses,
            enable_client_cache=enable_client_cache,
            client_cache_ttl=client_cache_ttl,
            client_cache_maxsize=client_cache_maxsize,
        )

        return client

    return factory


def pytest_collection_modifyitems(items):
    slow_tests = []
    normal_tests = []

    for item in items:
        if item.get_closest_marker("slow"):
            slow_tests.append(item)
        else:
            normal_tests.append(item)

    items[:] = normal_tests + slow_tests
