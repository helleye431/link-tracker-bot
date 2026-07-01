import pytest


from bot_service.infrastructure.adapters.telegram.handlers.command.start_handler import (
    StartHandler,
)
import copy


@pytest.fixture
def start_message(base_message):
    msg = copy.copy(base_message)
    msg.text = "/start"
    return msg


@pytest.mark.asyncio
async def test_start_command(start_message, tracking_service, base_fsm_context):
    """
    Позитивный сценарий:
    При получении команды /start
    бот должен отправить приветственное сообщение.
    """
    handler = StartHandler(tracking_service=tracking_service)

    await handler.handle(start_message, base_fsm_context)
    start_message.answer.assert_awaited_once()

    sent_text = start_message.answer.call_args.args[0]
    assert sent_text == "Добро пожаловать!\nИспользуйте /help."
