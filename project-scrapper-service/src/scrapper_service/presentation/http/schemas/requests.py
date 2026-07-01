from pydantic import BaseModel, HttpUrl, Field


class AddLinkRequest(BaseModel):
    link: HttpUrl
    tags: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)


class RemoveLinkRequest(BaseModel):
    link: HttpUrl


class AddChatRequest(BaseModel):
    user_id: int
