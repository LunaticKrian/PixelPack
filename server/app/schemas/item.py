import enum
from datetime import date as date_type, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ItemStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    IDLE = "IDLE"
    RETIRED = "RETIRED"
    SOLD = "SOLD"
    DISCARDED = "DISCARDED"


# ── Image ──────────────────────────────────────────────────────────────
class ItemImageResponse(BaseModel):
    id: int
    item_id: int
    url: str
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Cost ───────────────────────────────────────────────────────────────
class CostCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(gt=0)
    date: date_type
    description: str | None = None


class CostUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    amount: Decimal | None = Field(default=None, gt=0)
    date: date_type | None = None
    description: str | None = None


class CostResponse(BaseModel):
    id: int
    item_id: int
    name: str
    amount: Decimal
    date: date_type
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Item ───────────────────────────────────────────────────────────────
class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category_id: int | None = None
    purchase_date: date_type
    purchase_price: Decimal = Field(gt=0)
    currency: str = Field(default="CNY", max_length=3)
    purchase_channel: str | None = Field(default=None, max_length=200)
    current_value: Decimal | None = None
    warranty_expiry: date_type | None = None
    expected_lifespan: int | None = Field(default=None, ge=0)
    usage_count: int | None = Field(default=None, ge=0)
    tag_ids: list[int] | None = None


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category_id: int | None = None
    purchase_date: date_type | None = None
    purchase_price: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, max_length=3)
    purchase_channel: str | None = Field(default=None, max_length=200)
    current_value: Decimal | None = None
    warranty_expiry: date_type | None = None
    expected_lifespan: int | None = Field(default=None, ge=0)
    usage_count: int | None = Field(default=None, ge=0)
    tag_ids: list[int] | None = None


class StatusChange(BaseModel):
    status: ItemStatus
    reason: str | None = Field(default=None, max_length=500)


class ItemResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None
    category_id: int | None
    status: str
    purchase_date: date_type
    purchase_price: Decimal
    currency: str
    purchase_channel: str | None
    current_value: Decimal | None
    warranty_expiry: date_type | None
    expected_lifespan: int | None
    usage_count: int | None
    retired_at: datetime | None
    retired_reason: str | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    # Computed fields
    daily_cost: float = 0.0
    per_use_cost: float | None = None
    total_cost: float = 0.0
    usage_days: int = 0

    # Nested
    images: list[ItemImageResponse] = []
    tags: list["TagResponse"] = []
    additional_costs: list[CostResponse] = []

    model_config = {"from_attributes": True}


# Forward reference resolve (TagResponse from schemas.tag)
from app.schemas.tag import TagResponse  # noqa: E402

ItemResponse.model_rebuild()


class ItemListResponse(BaseModel):
    items: list[ItemResponse]
    total: int
    page: int
    page_size: int
    pages: int
