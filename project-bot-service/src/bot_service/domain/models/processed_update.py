from typing import Literal

from pydantic import BaseModel, HttpUrl


class ProcessedUpdate(BaseModel):
    id: int
    url: HttpUrl | None
    description: str
    tgChatIds: list[int]
    is_error: bool
    priority: Literal["LOW", "MEDIUM", "HIGH"]
