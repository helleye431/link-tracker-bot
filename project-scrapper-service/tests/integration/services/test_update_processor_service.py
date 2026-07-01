import datetime

import pytest
import pytest_asyncio
from wiremock.constants import Config
from wiremock.resources.mappings.models import (
    Mapping,
    MappingRequest,
    MappingResponse,
)
from wiremock.resources.mappings.resource import Mappings
from wiremock.testing.testcontainer import wiremock_container

from scrapper_service.application.common.contexts.update_processor_worker_context import (
    UpdateProcessorWorkerContext,
)
from scrapper_service.application.services.link_update_fetcher_service import (
    LinkUpdateFetcherService,
)
from scrapper_service.application.services.link_update_processor_service import (
    LinkUpdateProcessorService,
)
from scrapper_service.infrastructure.clients.github_client import GithubClient
from scrapper_service.infrastructure.clients.stackoverflow_client import (
    StackoverflowClient,
)
from scrapper_service.infrastructure.database.postgres.repositories.raw_sql.raw_sql_tracking_repository import (
    RawSqlTrackingRepository,
)


@pytest.fixture
def wm_server():
    with wiremock_container(secure=False) as wm:
        Config.base_url = wm.get_url("__admin")

        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(
                    method="GET",
                    url_path="/repos/helleye431/asteroids/issues",
                    query_parameters={
                        "state": {"equalTo": "all"},
                        "sort": {"equalTo": "created"},
                        "direction": {"equalTo": "desc"},
                        "per_page": {"equalTo": "1"},
                    },
                ),
                response=MappingResponse(
                    status=200,
                    json_body=[
                        {
                            "title": "Http api contract issue",
                            "user": {"login": "boss"},
                            "created_at": "2021-01-01T00:00:00Z",
                            "body": "Need to fix one http api bug in your code",
                        }
                    ],
                ),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(
                    method="GET",
                    url_path="/questions/123",
                    query_parameters={
                        "site": {"equalTo": "stackoverflow"},
                        "sort": {"equalTo": "creation"},
                        "order": {"equalTo": "desc"},
                    },
                ),
                response=MappingResponse(
                    status=200,
                    json_body={
                        "items": [
                            {
                                "title": "Mocked from WireMock library",
                            }
                        ]
                    },
                ),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(
                    method="GET",
                    url_path="/questions/123/answers",
                    query_parameters={
                        "site": {"equalTo": "stackoverflow"},
                        "sort": {"equalTo": "creation"},
                        "order": {"equalTo": "desc"},
                        "filter": {"equalTo": "withbody"},
                    },
                ),
                response=MappingResponse(
                    status=200,
                    json_body={
                        "items": [
                            {
                                "creation_date": 1609459200,
                                "body": "This is mocked stackoverflow answer preview",
                                "owner": {"display_name": "Mocked SO User"},
                            }
                        ]
                    },
                ),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(
                    method="GET",
                    url_path="/questions/123/comments",
                    query_parameters={
                        "site": {"equalTo": "stackoverflow"},
                        "sort": {"equalTo": "creation"},
                        "order": {"equalTo": "desc"},
                    },
                ),
                response=MappingResponse(
                    status=200,
                    json_body={"items": []},
                ),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(
                    method="GET",
                    url_path="/repos/broken/repo/issues",
                    query_parameters={
                        "state": {"equalTo": "all"},
                        "sort": {"equalTo": "created"},
                        "direction": {"equalTo": "desc"},
                        "per_page": {"equalTo": "1"},
                    },
                ),
                response=MappingResponse(
                    status=500,
                    json_body={"message": "Internal Server Error"},
                ),
                persistent=False,
            )
        )

        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(
                    method="GET",
                    url_path="/questions/999",
                    query_parameters={
                        "site": {"equalTo": "stackoverflow"},
                        "sort": {"equalTo": "creation"},
                        "order": {"equalTo": "desc"},
                    },
                ),
                response=MappingResponse(
                    status=503,
                    json_body={"error_id": 503, "error_message": "Service unavailable"},
                ),
                persistent=False,
            )
        )

        yield wm


@pytest_asyncio.fixture(scope="function")
async def tracking_repository_factory(postgres_container, apply_migrations, clear_db):
    database_url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://",
        "postgresql://",
    )

    created_repositories = []

    async def factory() -> RawSqlTrackingRepository:
        repo = await RawSqlTrackingRepository.create(database_url)
        created_repositories.append(repo)
        return repo

    try:
        yield factory
    finally:
        for repo in created_repositories:
            await repo.aclose()


@pytest.fixture
def update_processor_worker_context_factory(
    tracking_repository_factory,
    notification_service,
    wm_server,
):
    async def factory() -> UpdateProcessorWorkerContext:
        repository = await tracking_repository_factory()

        github_client = GithubClient(wm_server.get_url(""))
        stackoverflow_client = StackoverflowClient(wm_server.get_url(""))

        update_fetcher_service = LinkUpdateFetcherService(
            external_clients=[github_client, stackoverflow_client]
        )

        return UpdateProcessorWorkerContext(
            tracking_repository=repository,
            update_fetcher_service=update_fetcher_service,
            notification_service=notification_service,
        )

    return factory


@pytest.mark.asyncio
async def test_processor_builds_correct_descriptions_for_github_and_stackoverflow(
    tracking_repository_factory,
    update_processor_worker_context_factory,
    mock_bot_client,
):
    """
    Mock GitHub API возвращает новый Issue

    Scrapper формирует сообщение с названием, автором, превью

    Mock StackOverflow API возвращает новый ответ

    Аналогично


    Проверка сценария, что link_update_processor_service при проверке обновления по ссылкам
    формирует правильно сообщение
    """
    github_repo_url = "https://github.com/helleye431/asteroids"
    stackoverflow_question_url = "https://stackoverflow.com/questions/123/mock-title"

    setup_repo = await tracking_repository_factory()

    await setup_repo.register_chat(100)
    await setup_repo.register_chat(200)

    await setup_repo.add_link(
        chat_id=100,
        url=github_repo_url,
        tags=[],
        filters=[],
        last_seen_update=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
    )
    await setup_repo.add_link(
        chat_id=200,
        url=stackoverflow_question_url,
        tags=[],
        filters=[],
        last_seen_update=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
    )

    processor = LinkUpdateProcessorService(
        tracking_repository_factory=tracking_repository_factory,
        update_processor_worker_context_factory=update_processor_worker_context_factory,
        batch_size=100,
        workers_count=1,
        transactional_outbox_mode=False,
    )

    failed_urls = await processor.process_updates()

    assert failed_urls == []
    assert mock_bot_client.send_update.await_count == 2

    calls = mock_bot_client.send_update.await_args_list
    github_call = next(call for call in calls if call.kwargs["chat_ids"] == [100])
    stackoverflow_call = next(
        call for call in calls if call.kwargs["chat_ids"] == [200]
    )
    github_description = github_call.kwargs["description"]
    stackoverflow_description = stackoverflow_call.kwargs["description"]

    assert "Http api contract issue" in github_description
    assert "boss" in github_description
    assert "Need to fix one http api bug in your code" in github_description

    assert "Mocked from WireMock library" in stackoverflow_description
    assert "Mocked SO User" in stackoverflow_description
    assert "This is mocked stackoverflow answer preview" in stackoverflow_description

    await setup_repo.aclose()


@pytest.mark.asyncio
async def test_processor_handles_external_api_errors_and_sends_error_notifications(
    tracking_repository_factory,
    update_processor_worker_context_factory,
    mock_bot_client,
):
    """
    Mock внешнего API имитирует недоступность ресурса

    Бот корректно обрабатывает эту ситуацию

    Проверка того, что все необработанные ссылки добавились в список, и пользователям были
    отправлены отчёты об ошибке обработки ссылки"""
    broken_github_url = "https://github.com/broken/repo"
    broken_stackoverflow_url = "https://stackoverflow.com/questions/999/broken-question"

    setup_repo = await tracking_repository_factory()

    await setup_repo.register_chat(300)

    await setup_repo.add_link(
        chat_id=300,
        url=broken_github_url,
        tags=[],
        filters=[],
        last_seen_update=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
    )
    await setup_repo.add_link(
        chat_id=300,
        url=broken_stackoverflow_url,
        tags=[],
        filters=[],
        last_seen_update=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
    )

    processor = LinkUpdateProcessorService(
        tracking_repository_factory=tracking_repository_factory,
        update_processor_worker_context_factory=update_processor_worker_context_factory,
        batch_size=100,
        workers_count=1,
        transactional_outbox_mode=False,
    )

    failed_urls = await processor.process_updates()

    assert broken_github_url in failed_urls
    assert broken_stackoverflow_url in failed_urls

    error_calls = [
        call
        for call in mock_bot_client.send_update.await_args_list
        if call.kwargs.get("is_error") is True
    ]

    assert len(error_calls) >= 1

    sent_chat_ids = []
    for call in error_calls:
        sent_chat_ids.extend(call.kwargs.get("chat_ids", []))

    assert 300 in sent_chat_ids


@pytest.mark.asyncio
async def test_processor_processes_links_in_batches_correctly(
    tracking_repository_factory,
    update_processor_worker_context_factory,
    mock_bot_client,
):
    """Пакетная обработка

    Батч корректно формируется и обрабатывается

    Проверка того, что при количестве батчей > 1 корректно отрабатывает сервис"""
    setup_repo = await tracking_repository_factory()

    github_repo_url = "https://github.com/helleye431/asteroids"
    stackoverflow_question_url = "https://stackoverflow.com/questions/123/mock-title"

    await setup_repo.register_chat(10)
    await setup_repo.register_chat(20)

    await setup_repo.add_link(
        chat_id=10,
        url=github_repo_url,
        tags=[],
        filters=[],
        last_seen_update=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
    )
    await setup_repo.add_link(
        chat_id=20,
        url=stackoverflow_question_url,
        tags=[],
        filters=[],
        last_seen_update=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
    )

    processor = LinkUpdateProcessorService(
        tracking_repository_factory=tracking_repository_factory,
        update_processor_worker_context_factory=update_processor_worker_context_factory,
        batch_size=1,
        workers_count=1,
        transactional_outbox_mode=False,
    )

    failed_urls = await processor.process_updates()

    assert failed_urls == []
    assert mock_bot_client.send_update.await_count == 2

    calls = mock_bot_client.send_update.await_args_list
    sent_chat_ids = [call.kwargs["chat_ids"] for call in calls]

    assert [10] in sent_chat_ids
    assert [20] in sent_chat_ids


@pytest.mark.asyncio
async def test_processor_isolates_errors_and_continues_processing_other_links(
    tracking_repository_factory,
    update_processor_worker_context_factory,
    mock_bot_client,
):
    """
    Пакетная обработка: часть ссылок не удалось обработать

    Ошибки изолированы, остальные ссылки обработаны

    Проверка того, что сервис корректно отработал, отправлены сообщения с отчётами по ошибкам и об
    обновлении ссылок, сервис не упал, список необработанных ссылок наполнен
    """
    setup_repo = await tracking_repository_factory()

    good_github_url = "https://github.com/helleye431/asteroids"
    broken_github_url = "https://github.com/broken/repo"
    good_stackoverflow_url = "https://stackoverflow.com/questions/123/mock-title"

    await setup_repo.register_chat(1)
    await setup_repo.register_chat(2)
    await setup_repo.register_chat(3)

    await setup_repo.add_link(
        chat_id=1,
        url=good_github_url,
        tags=[],
        filters=[],
        last_seen_update=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
    )
    await setup_repo.add_link(
        chat_id=2,
        url=broken_github_url,
        tags=[],
        filters=[],
        last_seen_update=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
    )
    await setup_repo.add_link(
        chat_id=3,
        url=good_stackoverflow_url,
        tags=[],
        filters=[],
        last_seen_update=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
    )

    processor = LinkUpdateProcessorService(
        tracking_repository_factory=tracking_repository_factory,
        update_processor_worker_context_factory=update_processor_worker_context_factory,
        batch_size=2,
        workers_count=2,
        transactional_outbox_mode=False,
    )

    failed_urls = await processor.process_updates()

    assert broken_github_url in failed_urls
    assert good_github_url not in failed_urls
    assert good_stackoverflow_url not in failed_urls

    calls = mock_bot_client.send_update.await_args_list

    success_calls = [call for call in calls if call.kwargs.get("is_error") is False]
    error_calls = [call for call in calls if call.kwargs.get("is_error") is True]

    assert len(success_calls) == 2
    assert len(error_calls) == 1

    success_chat_ids = [call.kwargs["chat_ids"] for call in success_calls]
    assert [1] in success_chat_ids
    assert [3] in success_chat_ids

    error_chat_ids = [call.kwargs["chat_ids"] for call in error_calls]
    assert [2] in error_chat_ids


@pytest.mark.asyncio
async def test_transactional_outbox_node_correctly_written(
    tracking_repository_factory,
    update_processor_worker_context_factory,
    mock_bot_client,
):
    """Transactional Outbox: формирование записи
    При создании уведомления формируется соответствующая запись в outbox-таблице"""
    setup_repo = await tracking_repository_factory()

    good_github_url = "https://github.com/helleye431/asteroids"

    await setup_repo.register_chat(1)

    await setup_repo.add_link(
        chat_id=1,
        url=good_github_url,
        tags=[],
        filters=[],
        last_seen_update=datetime.datetime(2020, 1, 1, tzinfo=datetime.UTC),
    )

    processor = LinkUpdateProcessorService(
        tracking_repository_factory=tracking_repository_factory,
        update_processor_worker_context_factory=update_processor_worker_context_factory,
        batch_size=100,
        workers_count=1,
        transactional_outbox_mode=True,
    )

    await processor.process_updates()

    events = await setup_repo.get_pending_events()

    assert events is not None

    event = events[0]

    assert event.url == good_github_url
    assert event.tg_chat_ids == [1]
    assert not event.is_error
    assert event.sent_at is None
