from datetime import datetime

from pydantic import BaseModel, Field


class JournalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str | None = None
    category: str = Field(default="general", max_length=50)
    icon: str = Field(default="*", max_length=10)


class JournalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = None
    category: str | None = Field(default=None, max_length=50)
    icon: str | None = Field(default=None, max_length=10)


class JournalResponse(BaseModel):
    id: int
    user_id: int
    type: str
    category: str
    icon: str
    title: str
    content: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
