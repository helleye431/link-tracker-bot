from datetime import datetime
from pydantic import BaseModel


class LinkUpdateEvent(BaseModel):
    url: str
    event_type: str
    title: str
    author: str
    created_at: datetime
    preview: str
