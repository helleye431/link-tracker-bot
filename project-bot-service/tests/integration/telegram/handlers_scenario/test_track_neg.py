import copy

import pytest
from pydantic import HttpUrl

from bot_service.infrastructure.adapters.telegram.handlers.command.track_handler import (
    TrackHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers.fsm.track_scenario.track_link_handler import (
    TrackLinkHandler,
)
from bot_service.infrastructure.adapters.telegram.states.track_states import TrackStates
from bot_service.domain.models.link import Link


@pytest.fixture
def track_message(base_message):
    msg = copy.copy(base_message)
    return msg


@pytest.mark.asyncio
async def test_track_invalid_link_shows_error(
    track_message,
    base_fsm_context,
    tracking_service,
    fake_scrapper,
):
    """
    Пользователь отправляет /track и некорректную ссылку
    (например, tbank://github.com/user/repo).

    Бот уведомляет пользователя, что ссылка некорректна

    Проверка сценария обработки ссылки в tracking_service.validate_new_link, в случае
    провала бот отправляет сообщение 'Ссылка некорректна...'
    """

    track_handler = TrackHandler()
    link_handler = TrackLinkHandler(tracking_service)

    track_message.text = "/track"
    await track_handler.handle(track_message, base_fsm_context)
    assert base_fsm_context.current_state == TrackStates.waiting_for_link

    link_message = copy.copy(track_message)
    link_message.text = "tbank://github.com/user/repo"
    await link_handler.handle(link_message, base_fsm_context)
    link_message.answer.assert_awaited_with(
        "Ссылка некорректна.\n"
        "Проверьте её и отправьте заново.\n\n"
        "Для отмены используйте /cancel"
    )
    assert base_fsm_context.data == {}
    assert base_fsm_context.current_state == TrackStates.waiting_for_link


@pytest.mark.asyncio
async def test_track_existing_link_shows_error(
    track_message,
    base_fsm_context,
    tracking_service,
    fake_scrapper,
):
    """
    Пользователь в рамках запроса /track отправляет ссылку, на которую уже подписан

    Бот уведомляет пользователя, что он уже подписан на эту ссылку

    Проверка сценария обработки ссылки в tracking_service.validate_new_link, в случае
    провала бот отправляет сообщение 'Эта ссылка уже отслеживается...'
    """
    url = "https://github.com/user/repo"
    fake_scrapper.get_links.return_value = [
        Link(
            id=1,
            url=HttpUrl(url),
            tags=["backend"],
            filters=[],
            last_seen_update=None,
        )
    ]

    track_handler = TrackHandler()
    link_handler = TrackLinkHandler(tracking_service)

    track_message.text = "/track"
    await track_handler.handle(track_message, base_fsm_context)
    assert base_fsm_context.current_state == TrackStates.waiting_for_link

    link_message = copy.copy(track_message)
    link_message.text = url
    await link_handler.handle(link_message, base_fsm_context)
    link_message.answer.assert_awaited_with(
        "Эта ссылка уже отслеживается.\n"
        "Попробуйте другую ссылку.\n\n"
        "Для отмены используйте /cancel"
    )
    assert base_fsm_context.data == {}
    assert base_fsm_context.current_state == TrackStates.waiting_for_link
