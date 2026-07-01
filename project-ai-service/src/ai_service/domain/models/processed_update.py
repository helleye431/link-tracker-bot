from pydantic import BaseModel, HttpUrl
from typing import Literal


class ProcessedUpdate(BaseModel):
    id: int
    url: HttpUrl | None
    description: str
    tgChatIds: list[int]
    is_error: bool
    priority: Literal["HIGH", "MEDIUM", "LOW"]

    @property
    def priority_weight(self):
        priority_to_weight = {
            "LOW": 0,
            "MEDIUM": 1,
            "HIGH": 2,
        }

        return priority_to_weight[self.priority]
