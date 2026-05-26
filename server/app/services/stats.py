from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.models.category import Category
from app.models.cost import AdditionalCost


async def get_overview(db: AsyncSession, user_id: int) -> dict:
    active_items = await db.scalar(
        select(func.count()).select_from(Item)
        .where(Item.user_id == user_id, Item.deleted_at.is_(None), Item.status == "ACTIVE")
    ) or 0
    total_items = await db.scalar(
        select(func.count()).select_from(Item)
        .where(Item.user_id == user_id, Item.deleted_at.is_(None))
    ) or 0
    total_value = await db.scalar(
        select(func.coalesce(func.sum(Item.purchase_price), 0))
        .where(Item.user_id == user_id, Item.deleted_at.is_(None), Item.status.in_(["ACTIVE", "IDLE"]))
    ) or Decimal(0)

    items = (await db.execute(
        select(Item).where(Item.user_id == user_id, Item.deleted_at.is_(None), Item.status.in_(["ACTIVE", "IDLE"]))
    )).scalars().all()

    total_daily = Decimal(0)
    for item in items:
        end = item.retired_at.date() if item.retired_at else date.today()
        days = max(1, (end - item.purchase_date).days)
        costs_sum = await db.scalar(
            select(func.coalesce(func.sum(AdditionalCost.amount), 0))
            .where(AdditionalCost.item_id == item.id)
        ) or Decimal(0)
        total_daily += (item.purchase_price + costs_sum) / days

    total_costs = await db.scalar(
        select(func.coalesce(func.sum(AdditionalCost.amount), 0))
        .where(AdditionalCost.item_id.in_(
            select(Item.id).where(Item.user_id == user_id, Item.deleted_at.is_(None))
        ))
    ) or Decimal(0)

    return {
        "total_items": total_items,
        "active_items": active_items,
        "total_assets_value": float(total_value),
        "avg_daily_cost": float(total_daily) if total_daily else 0.0,
        "total_additional_costs": float(total_costs),
    }


async def get_by_category(db: AsyncSession, user_id: int) -> list[dict]:
    cats = (await db.execute(
        select(Category).where(Category.user_id == user_id)
    )).scalars().all()

    cat_map = {c.id: c for c in cats}
    results = []

    for cat in cats:
        count = await db.scalar(
            select(func.count()).select_from(Item)
            .where(Item.user_id == user_id, Item.deleted_at.is_(None), Item.category_id == cat.id)
        ) or 0
        total = await db.scalar(
            select(func.coalesce(func.sum(Item.purchase_price), 0))
            .where(Item.user_id == user_id, Item.deleted_at.is_(None), Item.category_id == cat.id)
        ) or Decimal(0)

        items = (await db.execute(
            select(Item).where(Item.user_id == user_id, Item.deleted_at.is_(None),
                               Item.category_id == cat.id, Item.status.in_(["ACTIVE", "IDLE"]))
        )).scalars().all()

        daily_sum = Decimal(0)
        for item in items:
            end = item.retired_at.date() if item.retired_at else date.today()
            days = max(1, (end - item.purchase_date).days)
            daily_sum += item.purchase_price / days

        if count > 0:
            results.append({
                "category_id": cat.id,
                "category_name": cat.name,
                "item_count": count,
                "total_value": float(total),
                "avg_daily_cost": float(daily_sum) if daily_sum else 0.0,
                "color": cat.color,
            })

    uncategorized_count = await db.scalar(
        select(func.count()).select_from(Item)
        .where(Item.user_id == user_id, Item.deleted_at.is_(None), Item.category_id.is_(None))
    ) or 0
    if uncategorized_count > 0:
        unc_total = await db.scalar(
            select(func.coalesce(func.sum(Item.purchase_price), 0))
            .where(Item.user_id == user_id, Item.deleted_at.is_(None), Item.category_id.is_(None))
        ) or Decimal(0)
        results.append({
            "category_id": None,
            "category_name": "未分类",
            "item_count": uncategorized_count,
            "total_value": float(unc_total),
            "avg_daily_cost": 0.0,
            "color": "#566c86",
        })

    return results


async def get_daily_cost_rank(db: AsyncSession, user_id: int, limit: int = 10, status: str | None = None) -> list[dict]:
    q = select(Item).where(Item.user_id == user_id, Item.deleted_at.is_(None))
    if status:
        q = q.where(Item.status == status)
    items = (await db.execute(q)).scalars().all()

    ranked = []
    for item in items:
        end = item.retired_at.date() if item.retired_at else date.today()
        days = max(1, (end - item.purchase_date).days)
        costs_sum = await db.scalar(
            select(func.coalesce(func.sum(AdditionalCost.amount), 0))
            .where(AdditionalCost.item_id == item.id)
        ) or Decimal(0)
        daily = float((item.purchase_price + costs_sum) / days)
        ranked.append({
            "id": item.id,
            "name": item.name,
            "daily_cost": daily,
            "purchase_price": float(item.purchase_price),
            "usage_days": days,
            "status": item.status,
        })

    ranked.sort(key=lambda x: x["daily_cost"], reverse=True)
    return ranked[:limit]


async def get_trends(db: AsyncSession, user_id: int, period: str = "month",
                     start_date: date | None = None, end_date: date | None = None) -> list[dict]:
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=180)

    items = (await db.execute(
        select(Item).where(
            Item.user_id == user_id, Item.deleted_at.is_(None),
            Item.purchase_date >= start_date, Item.purchase_date <= end_date,
        )
    )).scalars().all()

    monthly: dict[str, dict] = {}
    for item in items:
        key = item.purchase_date.strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = {"spending": Decimal(0), "count": 0}
        monthly[key]["spending"] += item.purchase_price
        monthly[key]["count"] += 1

    return [
        {"month": k, "spending": float(v["spending"]), "item_count": v["count"]}
        for k, v in sorted(monthly.items())
    ]


async def get_warranty_alerts(db: AsyncSession, user_id: int, days: int = 30) -> list[dict]:
    threshold = date.today() + timedelta(days=days)
    items = (await db.execute(
        select(Item).where(
            Item.user_id == user_id, Item.deleted_at.is_(None),
            Item.warranty_expiry.isnot(None),
            Item.warranty_expiry <= threshold,
            Item.warranty_expiry >= date.today(),
        )
    )).scalars().all()

    return [
        {
            "id": item.id,
            "name": item.name,
            "warranty_expiry": item.warranty_expiry,
            "days_remaining": (item.warranty_expiry - date.today()).days,
            "purchase_price": float(item.purchase_price),
        }
        for item in sorted(items, key=lambda x: x.warranty_expiry)
    ]


async def get_recent_items(db: AsyncSession, user_id: int, limit: int = 5) -> list[dict]:
    items = (await db.execute(
        select(Item).where(Item.user_id == user_id, Item.deleted_at.is_(None))
        .order_by(Item.created_at.desc()).limit(limit)
    )).scalars().all()

    results = []
    for item in items:
        end = item.retired_at.date() if item.retired_at else date.today()
        days = max(1, (end - item.purchase_date).days)
        results.append({
            "id": item.id,
            "name": item.name,
            "status": item.status,
            "purchase_price": float(item.purchase_price),
            "daily_cost": float(item.purchase_price / days),
            "created_at": item.created_at.isoformat() if item.created_at else "",
        })
    return results
