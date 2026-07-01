from unittest.mock import AsyncMock
import pytest
from testcontainers.core.network import Network
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy
from testcontainers.kafka import KafkaContainer

from ai_service.application.ports.pendings_updates_repository_port import (
    PendingUpdatesRepositoryPort,
)
from ai_service.application.ports.update_sender_port import UpdateSenderPort
from ai_service.application.services.update_processing_service import (
    UpdateProcessingService,
)


@pytest.fixture
def mock_update_processing_service():
    service = AsyncMock(spec=UpdateProcessingService)
    service.process_update = AsyncMock(return_value=None)
    return service


@pytest.fixture(scope="function")
def mock_pending_updates_repository():
    pending_updates_repository = AsyncMock(spec=PendingUpdatesRepositoryPort)
    pending_updates_repository.add_update = AsyncMock(return_value=None)
    return pending_updates_repository


@pytest.fixture(scope="function")
def mock_update_sender():
    sender = AsyncMock(spec=UpdateSenderPort)
    sender.send_update = AsyncMock(return_value=None)
    return sender


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
                .with_exposed_ports(8091)
                .with_env("SCHEMA_REGISTRY_HOST_NAME", "schema-registry")
                .with_env("SCHEMA_REGISTRY_LISTENERS", "http://0.0.0.0:8091")
                .with_env(
                    "SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS",
                    "PLAINTEXT://kafka:9092",
                )
                .waiting_for(
                    LogMessageWaitStrategy("Server started, listening for requests")
                )
            )

            with schema_registry:

                schema_registry_url = f"http://{schema_registry.get_container_host_ip()}:{schema_registry.get_exposed_port(8091)}"

                yield {
                    "bootstrap_servers": kafka.get_bootstrap_server(),
                    "schema_registry_url": schema_registry_url,
                }
