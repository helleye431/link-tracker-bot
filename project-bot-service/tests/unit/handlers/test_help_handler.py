import pytest
from bot_service.infrastructure.adapters.telegram.handlers.command.help_handler import (
    HelpHandler,
)
from unittest.mock import Mock
import copy


@pytest.fixture
def help_message(base_message):
    msg = copy.copy(base_message)
    msg.text = "/help"
    return msg


@pytest.fixture
def fake_handlers():

    fake_handler_start = Mock()
    fake_handler_start.name = "start"
    fake_handler_start.description = "начать работу"

    fake_handler_new = Mock()
    fake_handler_new.name = "new"
    fake_handler_new.description = "что-то делает"

    return [fake_handler_start, fake_handler_new]


@pytest.mark.asyncio
async def test_help_command(help_message, fake_handlers, base_fsm_context):
    """
    Позитивный сценарий:
    При получении команды /help
    бот должен вернуть список доступных команд.
    """
    handler = HelpHandler()
    handler.set_handlers(fake_handlers)
    await handler.handle(help_message, base_fsm_context)
    help_message.answer.assert_awaited_once()

    sent_text = help_message.answer.call_args.args[0]
    assert (
        sent_text == "Доступные команды\n/start - начать работу\n/new - что-то делает"
    )
