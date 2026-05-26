from datetime import datetime

from pydantic import BaseModel, Field


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#3CBBB1", max_length=20)


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, max_length=20)


class TagResponse(BaseModel):
    id: int
    user_id: int
    name: str
    color: str
    created_at: datetime

    model_config = {"from_attributes": True}
