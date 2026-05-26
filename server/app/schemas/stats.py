from datetime import date as date_type
from pydantic import BaseModel


class OverviewStats(BaseModel):
    total_items: int
    active_items: int
    total_assets_value: float
    avg_daily_cost: float
    total_additional_costs: float


class CategoryStat(BaseModel):
    category_id: int | None
    category_name: str
    item_count: int
    total_value: float
    avg_daily_cost: float
    color: str | None


class DailyCostRankItem(BaseModel):
    id: int
    name: str
    daily_cost: float
    purchase_price: float
    usage_days: int
    status: str


class MonthlyTrendPoint(BaseModel):
    month: str
    spending: float
    item_count: int


class WarrantyAlert(BaseModel):
    id: int
    name: str
    warranty_expiry: date_type
    days_remaining: int
    purchase_price: float


class RecentItem(BaseModel):
    id: int
    name: str
    status: str
    purchase_price: float
    daily_cost: float
    created_at: str
