from pydantic import BaseModel, HttpUrl
from typing import Literal


class LinkUpdate(BaseModel):
    id: int
    url: HttpUrl
    description: str
    tgChatIds: list[int]
    is_error: bool
    priority: Literal["HIGH", "MEDIUM", "LOW"] | None
