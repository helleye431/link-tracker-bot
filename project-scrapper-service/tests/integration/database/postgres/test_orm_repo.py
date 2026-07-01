import pytest
from datetime import datetime


@pytest.mark.asyncio
async def test_orm_add_link(orm_repository):
    chat_id = 11
    url = "https://stackoverflow.com/questions/123456/test"
    tags = ["qa", "stack"]
    filters: list[str] = []
    last_seen_update = datetime(2021, 1, 1)

    await orm_repository.register_chat(chat_id)

    created_link = await orm_repository.add_link(
        chat_id=chat_id,
        url=url,
        tags=tags,
        filters=filters,
        last_seen_update=last_seen_update,
    )

    links = await orm_repository.get_links(chat_id)
    actual_link = links[0]

    assert created_link.id is not None
    assert len(links) == 1
    assert str(actual_link.url) == url
    assert sorted(actual_link.tags) == sorted(tags)
    assert actual_link.filters == filters


@pytest.mark.asyncio
async def test_orm_remove_link(orm_repository):
    chat_id = 12
    url = "https://github.com/test/orm-remove"
    tags = ["tag1"]
    filters = ["f1"]
    last_seen_update = None

    await orm_repository.register_chat(chat_id)

    await orm_repository.add_link(
        chat_id=chat_id,
        url=url,
        tags=tags,
        filters=filters,
        last_seen_update=last_seen_update,
    )

    removed_link = await orm_repository.remove_link(chat_id, url)
    remaining_links = await orm_repository.get_links(chat_id)

    assert str(removed_link.url) == url
    assert sorted(removed_link.tags) == sorted(tags)
    assert sorted(removed_link.filters) == sorted(filters)
    assert remaining_links == []


@pytest.mark.asyncio
async def test_orm_same_link_different_chats(orm_repository):
    first_chat_id = 14
    second_chat_id = 15
    url = "https://github.com/test/orm-shared"
    first_tags = ["x"]
    second_tags = ["y"]
    filters: list[str] = []
    last_seen_update = None

    await orm_repository.register_chat(first_chat_id)
    await orm_repository.register_chat(second_chat_id)

    await orm_repository.add_link(
        chat_id=first_chat_id,
        url=url,
        tags=first_tags,
        filters=filters,
        last_seen_update=last_seen_update,
    )

    await orm_repository.add_link(
        chat_id=second_chat_id,
        url=url,
        tags=second_tags,
        filters=filters,
        last_seen_update=last_seen_update,
    )

    first_chat_links = await orm_repository.get_links(first_chat_id)
    second_chat_links = await orm_repository.get_links(second_chat_id)
    actual_chat_ids = await orm_repository.get_chat_ids_by_url(url)

    assert len(first_chat_links) == 1
    assert len(second_chat_links) == 1
    assert str(first_chat_links[0].url) == url
    assert str(second_chat_links[0].url) == url
    assert sorted(first_chat_links[0].tags) == sorted(first_tags)
    assert sorted(second_chat_links[0].tags) == sorted(second_tags)
    assert actual_chat_ids == [first_chat_id, second_chat_id]
