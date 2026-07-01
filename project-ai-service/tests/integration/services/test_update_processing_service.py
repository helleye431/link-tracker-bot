from ai_service.application.services.update_processing_service import (
    UpdateProcessingService,
)
from ai_service.domain.models.raw_update import RawUpdate
from ai_service.infrastructure.processors.ai_processor import AIProcessor
import pytest
from pydantic import HttpUrl


@pytest.mark.asyncio
async def test_process_update_include_stop_word(
    mock_pending_updates_repository, mocker
):
    """
    TC-2.1 Фильтрация по стоп-словам
    Условие:
    Текст обновления содержит стоп-слово из конфигурации.

    Ожидаемый результат:
    Обновление игнорируется
    Сообщение не публикуется в link.processed-updates"""

    processor = AIProcessor(
        token="",
        model="",
        stop_words=["github"],
        excluded_authors=[],
        min_length=5,
        summarization_threshold=100,
        high_keywords=[],
        low_keywords=[],
    )

    processor.base_url = ""

    spy_process_updates = mocker.spy(processor, "process_update")

    service = UpdateProcessingService(
        update_processor=processor,
        pending_updates_repository=mock_pending_updates_repository,
    )

    test_update = RawUpdate(
        id=1,
        url=HttpUrl("https://github.com/helleye431/asteroids"),
        description="New issue on github",
        author="helleye431",
        tgChatIds=[1111, 2222],
        is_error=False,
        priority="MEDIUM",
    )

    await service.process_update(update=test_update)

    assert spy_process_updates.spy_return is None
    assert mock_pending_updates_repository.add_update.call_count == 0


@pytest.mark.asyncio
async def test_process_update_include_excluded_author(
    mock_pending_updates_repository, mocker
):
    """
    TC-2.2 Фильтрация по автору
    Условие:
    Автор обновления входит в список исключённых авторов из конфигурации.

    Ожидаемый результат:
    Обновление игнорируется
    Сообщение не публикуется
    """

    processor = AIProcessor(
        token="",
        model="",
        stop_words=[],
        excluded_authors=["helleye431"],
        min_length=5,
        summarization_threshold=100,
        high_keywords=[],
        low_keywords=[],
    )

    processor.base_url = ""

    spy_process_updates = mocker.spy(processor, "process_update")

    service = UpdateProcessingService(
        update_processor=processor,
        pending_updates_repository=mock_pending_updates_repository,
    )

    test_update = RawUpdate(
        id=1,
        url=HttpUrl("https://github.com/helleye431/asteroids"),
        description="New issue on github",
        author="helleye431",
        tgChatIds=[1111, 2222],
        is_error=False,
        priority="MEDIUM",
    )

    await service.process_update(update=test_update)

    assert spy_process_updates.spy_return is None
    assert mock_pending_updates_repository.add_update.call_count == 0


@pytest.mark.asyncio
async def test_process_update_have_short_description(
    mock_pending_updates_repository, mocker
):
    """
    TC-2.3 Фильтрация по минимальной длине
    Условие:
    Длина текста обновления меньше установленного значения min-length.

    Ожидаемый результат:
    Обновление игнорируется
    Сообщение не публикуется
    """
    processor = AIProcessor(
        token="",
        model="",
        stop_words=[],
        excluded_authors=[],
        min_length=40,
        summarization_threshold=100,
        high_keywords=[],
        low_keywords=[],
    )

    processor.base_url = ""

    spy_process_updates = mocker.spy(processor, "process_update")

    service = UpdateProcessingService(
        update_processor=processor,
        pending_updates_repository=mock_pending_updates_repository,
    )

    test_update = RawUpdate(
        id=1,
        url=HttpUrl("https://github.com/helleye431/asteroids"),
        description="New issue on github",
        author="helleye431",
        tgChatIds=[1111, 2222],
        is_error=False,
        priority="MEDIUM",
    )

    await service.process_update(update=test_update)

    assert spy_process_updates.spy_return is None
    assert mock_pending_updates_repository.add_update.call_count == 0


@pytest.mark.asyncio
async def test_process_update_success(mock_pending_updates_repository, mocker):
    """
    TC-2.4 Обновление проходит фильтрацию
    Условие:
    Обновление не содержит стоп-слов, автор не исключён, длина достаточная.

    Ожидаемый результат:
    Обновление передаётся на следующий этап обработки
    """
    processor = AIProcessor(
        token="",
        model="",
        stop_words=["git", "pro"],
        excluded_authors=["kirill"],
        min_length=10,
        summarization_threshold=15,
        high_keywords=[],
        low_keywords=[],
    )

    processor.base_url = ""

    spy_process_updates = mocker.spy(processor, "process_update")
    spy_summarize_text = mocker.spy(processor, "_summarize_text")

    service = UpdateProcessingService(
        update_processor=processor,
        pending_updates_repository=mock_pending_updates_repository,
    )

    test_update = RawUpdate(
        id=1,
        url=HttpUrl("https://github.com/helleye431/asteroids"),
        description="Тестовый issue на github",
        author="helleye431",
        tgChatIds=[1111, 2222],
        is_error=False,
        priority="MEDIUM",
    )

    await service.process_update(update=test_update)

    # процессор обработал и вернул не None(значит все прошло успешно)
    assert spy_process_updates.spy_return is not None

    # этап суммаризации после фильтра был затронут
    assert spy_summarize_text.call_count == 1

    # обновление было отправлено в хранилище для отправки
    assert mock_pending_updates_repository.add_update.call_count == 1
