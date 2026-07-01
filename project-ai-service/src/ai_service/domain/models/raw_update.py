from pydantic import BaseModel, HttpUrl
from typing import Literal


class RawUpdate(BaseModel):
    id: int
    url: HttpUrl
    description: str
    author: str
    tgChatIds: list[int]
    is_error: bool
    priority: Literal["HIGH", "MEDIUM", "LOW"] | None
