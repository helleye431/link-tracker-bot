import copy
import pytest
from pydantic import HttpUrl
from bot_service.infrastructure.adapters.telegram.handlers.command.track_handler import (
    TrackHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers.fsm.track_scenario.track_link_handler import (
    TrackLinkHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers.fsm.track_scenario.track_tags_handler import (
    TrackTagsHandler,
)
from bot_service.infrastructure.adapters.telegram.handlers.fsm.track_scenario.track_filters_handler import (
    TrackFiltersHandler,
)
from bot_service.infrastructure.adapters.telegram.states.track_states import TrackStates
from bot_service.domain.models.link import Link


@pytest.fixture
def track_message(base_message):
    msg = copy.copy(base_message)
    return msg


@pytest.mark.asyncio
async def test_track_correct_link_and_data_are_saved(
    track_message,
    base_fsm_context,
    tracking_service,
    fake_scrapper,
):
    """
    Пользователь отправляет /track и
    корректную ссылку (например, https://github.com/user/repo), а затем теги и фильтры
    Данные сохранены в локальное хранилище

    Тестирую полный сценарий fsm,
    что бот в конце отправит 'Ссылка успешно добавлена', а это значит, что scrapper_service
    отправил запрос без ошибки -> ссылка добавилась бы в бд

    """
    url = "https://github.com/user/repo"
    validated_url = HttpUrl(url)

    track_handler = TrackHandler()
    link_handler = TrackLinkHandler(tracking_service)
    tags_handler = TrackTagsHandler()
    filters_handler = TrackFiltersHandler(tracking_service)

    track_message.text = "/track"
    await track_handler.handle(track_message, base_fsm_context)
    assert base_fsm_context.current_state == TrackStates.waiting_for_link

    link_message = copy.copy(track_message)
    link_message.text = url
    await link_handler.handle(link_message, base_fsm_context)
    assert base_fsm_context.data["link"] == validated_url
    assert base_fsm_context.current_state == TrackStates.waiting_for_tags

    tags_message = copy.copy(track_message)
    tags_message.text = "backend, github"
    await tags_handler.handle(tags_message, base_fsm_context)
    assert base_fsm_context.data["tags"] == ["backend", "github"]
    assert base_fsm_context.current_state == TrackStates.waiting_for_filters

    filters_message = copy.copy(track_message)
    filters_message.text = "kirill, homework"
    await filters_handler.handle(filters_message, base_fsm_context)
    created_link = Link(
        url=validated_url, tags=["backend", "github"], filters=["kirill", "homework"]
    )

    fake_scrapper.add_link.assert_awaited_with(filters_message.chat.id, created_link)
    filters_message.answer.assert_awaited_with("Ссылка успешно добавлена")
    assert base_fsm_context.data == {}
    assert base_fsm_context.current_state is None
