from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    title: str | None = Field(None, max_length=120)


class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    last_message: str | None = None
    message_count: int = 0

    model_config = {"from_attributes": True}


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    meta: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
