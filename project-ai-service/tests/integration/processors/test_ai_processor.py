from pydantic import HttpUrl
from wiremock.testing.testcontainer import wiremock_container
from wiremock.constants import Config
from wiremock.client import (
    Mappings,
    MappingResponse,
    MappingRequest,
    HttpMethods,
    Mapping,
)
import pytest
from ai_service.domain.models.raw_update import RawUpdate
from ai_service.infrastructure.processors.ai_processor import AIProcessor


@pytest.fixture
def wiremock_ai_server():
    with wiremock_container(secure=False) as wm:
        Config.base_url = wm.get_url("__admin")

        ai_response_body = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1710000000,
            "model": "Qwen/Qwen3-4B-Instruct-2507",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": (
                            "Тема: test_issue\n"
                            "Пользователь: helleye431\n"
                            "Время создания: 2026-06-11T17:48:39+00:00\n"
                            "Превью: Краткое описание тестовой issue."
                        ),
                    },
                    "finish_reason": "stop",
                }
            ],
        }

        Mappings.create_mapping(
            Mapping(
                request=MappingRequest(
                    method=HttpMethods.POST,
                    url="/v1/chat/completions",
                ),
                response=MappingResponse(
                    status=200,
                    json_body=ai_response_body,
                    headers={"Content-Type": "application/json"},
                    persistent=False,
                ),
            )
        )

        yield wm


@pytest.mark.asyncio
async def test_summarization_success(wiremock_ai_server, mocker):
    """
    TC-3.1 Суммаризация длинного текста
    Условие:
    Длина текста превышает установленный порог для суммаризации.

    Ожидаемый результат:
    Выполняется суммаризация
    Возвращается сокращённый текст
    Исходный текст не передаётся полностью
    """
    processor = AIProcessor(
        token="",
        model="",
        stop_words=["git", "pro"],
        excluded_authors=["kirill"],
        min_length=15,
        summarization_threshold=30,
        high_keywords=[],
        low_keywords=[],
    )

    processor.base_url = wiremock_ai_server.get_url("")

    spy_summarize_text = mocker.spy(processor, "_summarize_text")

    test_description = """"
    Тестовый issue на github.
     Добавлена новая функциональность,
    реализованы новые методы, подробнее смотрите в репозитории
    """

    test_update = RawUpdate(
        id=1,
        url=HttpUrl("https://github.com/helleye431/asteroids"),
        description=test_description,
        author="helleye431",
        tgChatIds=[1111, 2222],
        is_error=False,
        priority="MEDIUM",
    )

    processed_update = await processor.process_update(update=test_update)
    summarization_description = processed_update.description

    # этап суммаризации после фильтра был затронут
    assert spy_summarize_text.call_count == 1

    assert summarization_description != test_description
    assert len(summarization_description) < len(test_description)


@pytest.mark.asyncio
async def test_summarization_skipped(wiremock_ai_server, mocker):
    """
    TC-3.2 Короткий текст
    Условие:
    Длина текста меньше порога суммаризации.

    Ожидаемый результат:
    Суммаризация не выполняется
    Текст передаётся без изменений
    """
    processor = AIProcessor(
        token="",
        model="",
        stop_words=["git", "pro"],
        excluded_authors=["kirill"],
        min_length=15,
        summarization_threshold=500,
        high_keywords=[],
        low_keywords=[],
    )

    processor.base_url = wiremock_ai_server.get_url("")

    spy_summarize_text = mocker.spy(processor, "_summarize_text")

    test_description = """"
    Тестовый issue на github.
    Добавлена новая функциональность,
    реализованы новые методы, подробнее смотрите в репозитории
    """

    test_update = RawUpdate(
        id=1,
        url=HttpUrl("https://github.com/helleye431/asteroids"),
        description=test_description,
        author="helleye431",
        tgChatIds=[1111, 2222],
        is_error=False,
        priority="MEDIUM",
    )

    processed_update = await processor.process_update(update=test_update)
    processed_description = processed_update.description

    # этап суммаризации после фильтра не был затронут
    assert spy_summarize_text.call_count == 0

    assert processed_description == test_description


@pytest.mark.asyncio
async def test_processing_update_with_high_keyword(wiremock_ai_server):
    """
    TC-1.1 Обновление высокой значимости
    Условие:
    Текст обновления содержит ключевое слово из high-keywords (например, "critical bug fix").

    Ожидаемый результат:
    AI Agent определяет приоритет HIGH
    Итоговое сообщение содержит "priority": "HIGH"
    """
    processor = AIProcessor(
        token="",
        model="",
        stop_words=["git", "pro"],
        excluded_authors=["kirill"],
        min_length=15,
        summarization_threshold=500,
        high_keywords=["bug"],
        low_keywords=[],
    )

    processor.base_url = wiremock_ai_server.get_url("")

    test_description = """"
        critical bug fix
        """

    test_update = RawUpdate(
        id=1,
        url=HttpUrl("https://github.com/helleye431/asteroids"),
        description=test_description,
        author="helleye431",
        tgChatIds=[1111, 2222],
        is_error=False,
        priority=None,
    )

    processed_update = await processor.process_update(update=test_update)

    assert processed_update.priority == "HIGH"


@pytest.mark.asyncio
async def test_processing_update_without_specific_keywords(wiremock_ai_server):
    """
    TC-1.2 Обновление обычной значимости
    Условие:
    Текст обновления не содержит ни high-, ни low-ключевых слов.

    Ожидаемый результат:
    Обновление получает приоритет MEDIUM
    """
    processor = AIProcessor(
        token="",
        model="",
        stop_words=["git", "pro"],
        excluded_authors=["kirill"],
        min_length=15,
        summarization_threshold=500,
        high_keywords=["bug"],
        low_keywords=["github"],
    )

    processor.base_url = wiremock_ai_server.get_url("")

    test_description = """"
        critical fix
        """

    test_update = RawUpdate(
        id=1,
        url=HttpUrl("https://github.com/helleye431/asteroids"),
        description=test_description,
        author="helleye431",
        tgChatIds=[1111, 2222],
        is_error=False,
        priority=None,
    )

    processed_update = await processor.process_update(update=test_update)

    assert processed_update.priority == "MEDIUM"


@pytest.mark.asyncio
async def test_processing_update_with_low_keyword(wiremock_ai_server):
    """
    TC-1.3 Обновление низкой значимости
    Условие:
    Текст обновления содержит ключевое слово из low-keywords (например, "fix typo in readme").

    Ожидаемый результат:
    Обновление получает приоритет LOW
    """
    processor = AIProcessor(
        token="",
        model="",
        stop_words=["git", "pro"],
        excluded_authors=["kirill"],
        min_length=15,
        summarization_threshold=500,
        high_keywords=["bug"],
        low_keywords=["github"],
    )

    processor.base_url = wiremock_ai_server.get_url("")

    test_description = """"
        critical fix on github
        """

    test_update = RawUpdate(
        id=1,
        url=HttpUrl("https://github.com/helleye431/asteroids"),
        description=test_description,
        author="helleye431",
        tgChatIds=[1111, 2222],
        is_error=False,
        priority=None,
    )

    processed_update = await processor.process_update(update=test_update)

    assert processed_update.priority == "LOW"
