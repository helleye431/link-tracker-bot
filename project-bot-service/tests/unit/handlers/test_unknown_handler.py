import pytest
from bot_service.infrastructure.adapters.telegram.handlers.command.unknown_handler import (
    UnknownHandler,
)
import copy


@pytest.fixture
def unknown_message(base_message):
    msg = copy.copy(base_message)
    msg.text = "/aaaaaaaa"
    return msg


@pytest.mark.asyncio
async def test_unknown_command(unknown_message, base_fsm_context):
    """
    Негативный сценарий:
    Если команда неизвестна,
    бот должен уведомить пользователя об ошибке.
    """
    handler = UnknownHandler()

    await handler.handle(unknown_message, base_fsm_context)
    unknown_message.answer.assert_awaited_once()

    sent_text = unknown_message.answer.call_args.args[0]
    assert sent_text == "Неизвестная команда. Воспользуйтесь /help."
