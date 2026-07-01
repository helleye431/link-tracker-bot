import copy
import pytest
from pydantic import HttpUrl
from bot_service.domain.models.link import Link
from bot_service.infrastructure.adapters.telegram.handlers.command.list_handler import (
    ListHandler,
)


@pytest.fixture
def list_message(base_message):
    msg = copy.copy(base_message)
    return msg


@pytest.mark.asyncio
async def test_list_returns_active_subscriptions(
    list_message,
    base_fsm_context,
    tracking_service,
    fake_scrapper,
):
    """
    Пользователь отправляет запрос /list, у него есть активные подписки
    Бот присылает пользователю список активных подписок


    Проверка сценария, что scrapper_service возвращает список ссылок, и бот
    корректно распаршивает их и отправляет пользователю
    """

    fake_scrapper.get_links.return_value = [
        Link(
            id=1,
            url=HttpUrl("https://github.com/user/repo1"),
            tags=["backend", "github"],
            filters=["kirill"],
            last_seen_update=None,
        ),
        Link(
            id=2,
            url=HttpUrl("https://stackoverflow.com/questions/1"),
            tags=["python"],
            filters=["homework"],
            last_seen_update=None,
        ),
    ]

    handler = ListHandler(tracking_service)
    list_message.text = "/list"

    await handler.handle(list_message, base_fsm_context)

    fake_scrapper.get_links.assert_awaited_once_with(list_message.chat.id)
    list_message.answer.assert_awaited_once()

    sent_text = list_message.answer.call_args.args[0]
    assert "Список отслеживаемых ссылок:" in sent_text
    assert "https://github.com/user/repo1" in sent_text
    assert "https://stackoverflow.com/questions/1" in sent_text


@pytest.mark.asyncio
async def test_list_by_tag_returns_filtered_subscriptions(
    list_message,
    base_fsm_context,
    tracking_service,
    fake_scrapper,
):
    """Пользователь отправляет запрос /list <tag>, у него есть активные подписки

    Бот присылает пользователю список активных подписок, имеющих тег <tag>


    Проверка сценария, что scrapper_service возвращает список ссылок, и бот
    корректно распаршивает их и отправляет пользователю, отфильтровав по тэгу
    """

    fake_scrapper.get_links.return_value = [
        Link(
            id=1,
            url=HttpUrl("https://github.com/user/repo1"),
            tags=["backend", "github"],
            filters=["kirill"],
            last_seen_update=None,
        )
    ]

    handler = ListHandler(tracking_service)
    list_message.text = "/list backend"

    await handler.handle(list_message, base_fsm_context)

    fake_scrapper.get_links.assert_awaited_once_with(list_message.chat.id)
    list_message.answer.assert_awaited_once()

    sent_text = list_message.answer.call_args.args[0]
    assert "Список отслеживаемых ссылок:" in sent_text
    assert "https://github.com/user/repo1" in sent_text
    assert "backend, github" in sent_text
