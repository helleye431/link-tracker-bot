from pydantic import BaseModel, HttpUrl
from typing import Literal


class GroupedUpdatesInfo(BaseModel):
    id: int
    url: HttpUrl | None
    description_count: int
    description: str
    have_error: bool
    priority: Literal["HIGH", "MEDIUM", "LOW"]

    @property
    def priority_weight(self):
        priority_to_weight = {
            "LOW": 0,
            "MEDIUM": 1,
            "HIGH": 2,
        }

        return priority_to_weight[self.priority]
