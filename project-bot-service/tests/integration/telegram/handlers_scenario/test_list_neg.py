import copy
import pytest
from bot_service.infrastructure.adapters.telegram.handlers.command.list_handler import (
    ListHandler,
)


@pytest.fixture
def list_message(base_message):
    msg = copy.copy(base_message)
    return msg


@pytest.mark.asyncio
async def test_list_returns_no_subscriptions_message(
    list_message,
    base_fsm_context,
    tracking_service,
    fake_scrapper,
):
    """
    Пользователь отправляет запрос /list, у него нет активных подписок

    Бот присылает пользователю сообщение о том, что у него нет активных подписок

    Проверка сценария, что scrapper_service возвращает пустой список и бот пишет, что
    отслеживаемых ссылок нет
    """

    fake_scrapper.get_links.return_value = []

    handler = ListHandler(tracking_service)
    list_message.text = "/list"

    await handler.handle(list_message, base_fsm_context)
    fake_scrapper.get_links.assert_awaited_once_with(list_message.chat.id)
    list_message.answer.assert_awaited_once_with("Отслеживаемых ссылок нет")
