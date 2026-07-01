import pytest
from unittest.mock import AsyncMock, MagicMock

from bot_service.application.ports.scrapper_port import ScrapperPort
from testcontainers.core.network import Network
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy
from testcontainers.kafka import KafkaContainer

from bot_service.application.services.tracking_service import TrackingService
from bot_service.application.services.update_service import UpdateService


class FakeFSMContext:
    def __init__(self):
        self.data = {}
        self.current_state = None

    async def set_state(self, state):
        self.current_state = state

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return self.data

    async def clear(self):
        self.data.clear()
        self.current_state = None


@pytest.fixture
def base_fsm_context():
    state = FakeFSMContext()
    return state


@pytest.fixture
def base_message():
    message = MagicMock()
    message.answer = AsyncMock()

    user = MagicMock()
    user.id = 67
    message.from_user = user

    chat = MagicMock()
    chat.id = 12345
    message.chat = chat

    message.text = None
    return message


@pytest.fixture
def fake_scrapper():
    scrapper = AsyncMock(spec=ScrapperPort)
    scrapper.get_links.return_value = []
    scrapper.add_link.return_value = None
    scrapper.remove_link.return_value = None
    scrapper.register_chat.return_value = None
    scrapper.delete_chat.return_value = None
    return scrapper


@pytest.fixture
def mock_update_service():
    update_service = AsyncMock(spec=UpdateService)
    update_service.send_updates = AsyncMock(return_value=None)
    update_service.send_error_report = AsyncMock(return_value=None)
    return update_service


@pytest.fixture
def tracking_service(fake_scrapper):
    validated_domains = ["github.com", "stackoverflow.com"]
    service = TrackingService(fake_scrapper, validated_domains)
    return service


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


def pytest_collection_modifyitems(items):
    slow_tests = []
    normal_tests = []

    for item in items:
        if item.get_closest_marker("slow"):
            slow_tests.append(item)
        else:
            normal_tests.append(item)

    items[:] = normal_tests + slow_tests
