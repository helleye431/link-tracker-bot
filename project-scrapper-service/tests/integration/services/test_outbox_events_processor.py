from unittest.mock import AsyncMock

import pytest
from scrapper_service.application.services.outbox_events_processor import (
    OutboxEventsProcessor,
)
from scrapper_service.application.services.notification_service import (
    NotificationService,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", ["success", "error"])
async def test_outbox_events_processor_positive_and_negative_scenarios(
    scenario, raw_sql_repository, mock_bot_client
):
    """
    1: success
     Transactional Outbox: успешная отправка сообщения

    Дата отправки в outbox-таблице заполняется только после успешной отправки сообщения

    2: error
    Transactional Outbox: ошибка отправки сообщения

    При ошибке отправки дата отправки в outbox-таблице остаётся NULL
    """
    repo = raw_sql_repository
    test_update_id = 1
    test_url = "https://github.com/helleye431/asteroids"
    test_description = "new issue"
    test_author = "test_author"
    test_tg_chat_ids = [1, 2]
    test_is_error = False

    if scenario == "error":
        mock_bot_client.send_update = AsyncMock(side_effect=ValueError)

    notification_service = NotificationService([mock_bot_client])
    outbox_processor = OutboxEventsProcessor(
        repository=repo, notification_service=notification_service
    )

    await repo.create_outbox_event(
        update_id=test_update_id,
        url=test_url,
        description=test_description,
        author=test_author,
        tg_chat_ids=test_tg_chat_ids,
        is_error=test_is_error,
    )

    first_attempt_events = await repo.get_all_events()
    first_attempt_event = first_attempt_events[0]

    assert first_attempt_event.sent_at is None

    await outbox_processor.process_current_events()

    assert mock_bot_client.send_update.await_count == 1

    second_attempt_events = await repo.get_all_events()
    second_attempt_event = second_attempt_events[0]

    if scenario == "success":
        assert second_attempt_event.sent_at is not None
    elif scenario == "error":
        assert second_attempt_event.sent_at is None
