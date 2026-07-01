from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime


class LinkResponse(BaseModel):
    id: int
    url: HttpUrl
    tags: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    last_seen_update: datetime | None


class ApiErrorResponse(BaseModel):
    description: str
    code: str
    exceptionName: str
    exceptionMessage: str
    stacktrace: list[str]


class ListLinksResponse(BaseModel):
    links: list[LinkResponse] = Field(default_factory=list)
    size: int
