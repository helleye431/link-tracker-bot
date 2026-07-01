from datetime import datetime
from pydantic import BaseModel


class OutboxEvent(BaseModel):
    id: int
    update_id: int
    url: str
    description: str
    author: str
    tg_chat_ids: list[int]
    is_error: bool
    created_at: datetime
    sent_at: datetime | None = None
