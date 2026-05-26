from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.stats import (
    OverviewStats, CategoryStat, DailyCostRankItem,
    MonthlyTrendPoint, WarrantyAlert, RecentItem,
)
from app.services import stats as stats_svc
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview", response_model=OverviewStats)
async def overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await stats_svc.get_overview(db, current_user.id)


@router.get("/by-category", response_model=list[CategoryStat])
async def by_category(
    start_date: str | None = None,
    end_date: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await stats_svc.get_by_category(db, current_user.id)


@router.get("/daily-cost-rank", response_model=list[DailyCostRankItem])
async def daily_cost_rank(
    limit: int = Query(10, ge=1, le=50),
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await stats_svc.get_daily_cost_rank(db, current_user.id, limit, status)


@router.get("/trends", response_model=list[MonthlyTrendPoint])
async def trends(
    period: str = "month",
    start_date: str | None = None,
    end_date: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import date as date_type
    sd = date_type.fromisoformat(start_date) if start_date else None
    ed = date_type.fromisoformat(end_date) if end_date else None
    return await stats_svc.get_trends(db, current_user.id, period, sd, ed)


@router.get("/warranty-alerts", response_model=list[WarrantyAlert])
async def warranty_alerts(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await stats_svc.get_warranty_alerts(db, current_user.id, days)


@router.get("/recent", response_model=list[RecentItem])
async def recent_items(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await stats_svc.get_recent_items(db, current_user.id, limit)
