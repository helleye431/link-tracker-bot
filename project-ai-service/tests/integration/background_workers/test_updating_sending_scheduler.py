import pytest
from pydantic import HttpUrl
import contextlib
import asyncio
from ai_service.application.services.update_processing_service import (
    UpdateProcessingService,
)
from ai_service.application.services.update_sending_service import UpdateSendingService
from ai_service.domain.models.raw_update import RawUpdate
from ai_service.infrastructure.background_workers.scheduler.update_sending_scheduler import (
    UpdateSendingScheduler,
)
from ai_service.infrastructure.database.repositories.in_memory_pending_updates_repository import (
    InMemoryPendingUpdatesRepository,
)
from ai_service.infrastructure.processors.ai_processor import AIProcessor


@pytest.mark.asyncio
async def test_updates_grouping_per_time_window(
    mock_pending_updates_repository, mock_update_sender
):
    """
    TC-2.1 Группировка нескольких обновлений
    Условие:
    За определенное временное окно содержится несколько обновлений для одного tgChatId.

    Ожидаемый результат:

    AI Agent объединяет их в одно итоговое сообщение
    description содержит нумерованный список
    priority - максимальный среди сгруппированных
    """
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
        update_sender=mock_update_sender,
    )

    scheduler = UpdateSendingScheduler(
        update_sending_service=update_sending_service,
        interval_milliseconds=200,
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

    scheduler_task = asyncio.create_task(
        asyncio.to_thread(scheduler.run),
        name="test-update-sending-scheduler",
    )

    await asyncio.sleep(0.25)

    scheduler.stop()
    with contextlib.suppress(asyncio.CancelledError):
        await scheduler_task

    mock_update_sender.send_update.assert_awaited_once()

    sent_update = mock_update_sender.send_update.await_args.kwargs["update"]

    assert sent_update.tgChatIds == [1111]
    assert sent_update.priority == "HIGH"
    assert sent_update.url is None
    assert sent_update.description == (
        "1.\nПервое длинное обновление github\n\n"
        "2.\nВторое простое длинное обновление\n\n"
    )


@pytest.mark.asyncio
async def test_solo_update_time_window(
    mock_pending_updates_repository, mock_update_sender
):
    """
    TC-2.2 Одиночное обновление
    Условие:
    Для данного tgChatId за определенное временное окно только одно обновление.

    Ожидаемый результат:
    Группировка не применяется
    Сообщение передаётся без изменений
    """
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
        update_sender=mock_update_sender,
    )

    scheduler = UpdateSendingScheduler(
        update_sending_service=update_sending_service,
        interval_milliseconds=200,
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

    scheduler_task = asyncio.create_task(
        asyncio.to_thread(scheduler.run),
        name="test-update-sending-scheduler",
    )

    await asyncio.sleep(0.25)

    scheduler.stop()
    with contextlib.suppress(asyncio.CancelledError):
        await scheduler_task

    mock_update_sender.send_update.assert_awaited_once()

    sent_update = mock_update_sender.send_update.await_args.kwargs["update"]

    assert sent_update.tgChatIds == [1111]
    assert sent_update.priority == "HIGH"
    assert sent_update.url == HttpUrl("https://github.com/helleye431/asteroids")
    assert sent_update.description == "Первое длинное обновление github"
