from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class Link(BaseModel):
    id: int | None = None
    url: HttpUrl
    tags: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    last_seen_update: datetime | None = None
