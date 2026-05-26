from datetime import datetime

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: str | None = None
    color: str | None = None
    sort_order: int = 0
    parent_id: int | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    icon: str | None = None
    color: str | None = None
    sort_order: int | None = None
    parent_id: int | None = None


class CategoryResponse(BaseModel):
    id: int
    user_id: int
    name: str
    icon: str | None
    color: str | None
    sort_order: int
    parent_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
