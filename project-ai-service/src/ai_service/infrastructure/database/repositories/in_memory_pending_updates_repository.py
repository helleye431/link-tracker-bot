from ai_service.application.common.models.grouped_updates_info import GroupedUpdatesInfo
from ai_service.application.ports.pendings_updates_repository_port import (
    PendingUpdatesRepositoryPort,
)
from ai_service.domain.models.processed_update import ProcessedUpdate


class InMemoryPendingUpdatesRepository(PendingUpdatesRepositoryPort):
    def __init__(self) -> None:
        self._storage: dict[int, GroupedUpdatesInfo] = {}

    @staticmethod
    def _create_numbered_paragraph(num: int, text: str) -> str:
        return f"{num}.\n{text}\n\n"

    def get_grouped_updates_info_with_keys(
        self,
    ) -> list[tuple[int, GroupedUpdatesInfo]]:
        return list(self._storage.items())

    def add_update(self, new_update: ProcessedUpdate) -> None:
        for chat_id in new_update.tgChatIds:
            updates_info = self._storage.get(chat_id)

            if updates_info is None:
                self._storage[chat_id] = self._create_grouped_info(new_update)
                continue

            if updates_info.have_error:
                if new_update.is_error:
                    # копим ошибки если их много
                    self._append_update_info(updates_info, new_update)
                    continue

                # стираем ошибку если есть нормальные обновления
                self._storage[chat_id] = self._create_grouped_info(new_update)
                continue

            if new_update.is_error:
                continue

            self._append_update_info(updates_info, new_update)

    @staticmethod
    def _create_grouped_info(new_update: ProcessedUpdate) -> GroupedUpdatesInfo:
        return GroupedUpdatesInfo(
            id=new_update.id,
            description=new_update.description,
            have_error=new_update.is_error,
            priority=new_update.priority,
            description_count=1,
            url=new_update.url,
        )

    def _append_update_info(
        self,
        updates_info: GroupedUpdatesInfo,
        new_update: ProcessedUpdate,
    ) -> None:
        if updates_info.description_count == 1:
            updates_info.description = self._create_numbered_paragraph(
                num=1,
                text=updates_info.description,
            )

        updates_info.description_count += 1
        updates_info.id = max(updates_info.id, new_update.id)

        updates_info.description += self._create_numbered_paragraph(
            num=updates_info.description_count,
            text=new_update.description,
        )

        updates_info.url = None

        if new_update.priority_weight > updates_info.priority_weight:
            updates_info.priority = new_update.priority

    def clear_storage(self) -> None:
        self._storage.clear()

    def clear_storage_by_keys(self, keys: list[int]) -> None:
        for key in keys:
            self._storage.pop(key, None)
