import math
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cost import AdditionalCost
from app.models.image import ItemImage
from app.models.item import Item, item_tags
from app.models.tag import Tag
from app.schemas.item import CostCreate, CostUpdate, ItemCreate, ItemUpdate


async def create_item(db: AsyncSession, user_id: int, data: ItemCreate) -> Item:
    item = Item(
        user_id=user_id,
        name=data.name,
        description=data.description,
        category_id=data.category_id,
        purchase_date=data.purchase_date,
        purchase_price=data.purchase_price,
        currency=data.currency,
        purchase_channel=data.purchase_channel,
        current_value=data.current_value,
        warranty_expiry=data.warranty_expiry,
        expected_lifespan=data.expected_lifespan,
        usage_count=data.usage_count,
    )
    db.add(item)
    await db.flush()

    # Attach tags if provided
    if data.tag_ids:
        await _sync_tags(db, item, data.tag_ids)

    await db.refresh(item)
    return item


async def get_item_by_id(
    db: AsyncSession, item_id: int, user_id: int,
) -> Item | None:
    stmt = (
        select(Item)
        .options(
            selectinload(Item.tags),
            selectinload(Item.images),
            selectinload(Item.additional_costs),
        )
        .where(Item.id == item_id, Item.user_id == user_id, Item.deleted_at.is_(None))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_items(
    db: AsyncSession,
    user_id: int,
    *,
    keyword: str | None = None,
    category_id: int | None = None,
    status_filter: str | None = None,
    tag_id: int | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Item], int]:
    # Base conditions
    conditions = [Item.user_id == user_id, Item.deleted_at.is_(None)]

    if keyword:
        conditions.append(Item.name.ilike(f"%{keyword}%"))
    if category_id is not None:
        conditions.append(Item.category_id == category_id)
    if status_filter:
        conditions.append(Item.status == status_filter)
    if tag_id is not None:
        conditions.append(Item.tags.any(Tag.id == tag_id))

    where = and_(*conditions)

    # Count
    count_stmt = select(func.count()).select_from(Item).where(where)
    total = (await db.execute(count_stmt)).scalar_one()

    # Sorting
    sort_col = _resolve_sort_column(sort_by)
    sort_expr = sort_col.desc() if order == "desc" else sort_col.asc()

    # Query
    stmt: Select = (
        select(Item)
        .options(
            selectinload(Item.tags),
            selectinload(Item.images),
            selectinload(Item.additional_costs),
        )
        .where(where)
        .order_by(sort_expr)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return items, total


async def update_item(db: AsyncSession, item: Item, data: ItemUpdate) -> Item:
    update_fields = data.model_dump(exclude_unset=True)
    tag_ids = update_fields.pop("tag_ids", None)

    for field, value in update_fields.items():
        setattr(item, field, value)

    if tag_ids is not None:
        await _sync_tags(db, item, tag_ids)

    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def soft_delete_item(db: AsyncSession, item: Item) -> Item:
    item.deleted_at = datetime.now(timezone.utc)
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def change_status(
    db: AsyncSession,
    item: Item,
    new_status: str,
    reason: str | None = None,
) -> Item:
    item.status = new_status
    if new_status in ("RETIRED", "SOLD", "DISCARDED"):
        item.retired_at = datetime.now(timezone.utc)
        item.retired_reason = reason
    else:
        item.retired_at = None
        item.retired_reason = None
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


def calc_item_stats(item: Item) -> dict:
    """Compute daily_cost, per_use_cost, total_cost, usage_days."""
    purchase_date = item.purchase_date
    retired_at = item.retired_at
    usage_count = item.usage_count
    purchase_price = float(item.purchase_price or 0)

    # Total additional costs
    extra = sum(float(c.amount) for c in item.additional_costs) if item.additional_costs else 0.0
    total_cost = purchase_price + extra

    # Usage days
    today = date.today()
    end_date = retired_at.date() if retired_at else today
    usage_days = max(1, (end_date - purchase_date).days)

    daily_cost = total_cost / usage_days

    per_use_cost = None
    if usage_count and usage_count > 0:
        per_use_cost = total_cost / usage_count

    return {
        "daily_cost": round(daily_cost, 2),
        "per_use_cost": round(per_use_cost, 2) if per_use_cost is not None else None,
        "total_cost": round(total_cost, 2),
        "usage_days": usage_days,
    }


# ── Additional Costs ───────────────────────────────────────────────────
async def create_cost(
    db: AsyncSession, item_id: int, data: CostCreate,
) -> AdditionalCost:
    cost = AdditionalCost(
        item_id=item_id,
        name=data.name,
        amount=data.amount,
        date=data.date,
        description=data.description,
    )
    db.add(cost)
    await db.flush()
    await db.refresh(cost)
    return cost


async def update_cost(
    db: AsyncSession, cost: AdditionalCost, data: CostUpdate,
) -> AdditionalCost:
    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(cost, field, value)
    db.add(cost)
    await db.flush()
    await db.refresh(cost)
    return cost


async def delete_cost(db: AsyncSession, cost: AdditionalCost) -> None:
    await db.delete(cost)
    await db.flush()


async def get_cost_by_id(
    db: AsyncSession, cost_id: int, user_id: int,
) -> AdditionalCost | None:
    stmt = (
        select(AdditionalCost)
        .join(Item, AdditionalCost.item_id == Item.id)
        .where(AdditionalCost.id == cost_id, Item.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ── Images ─────────────────────────────────────────────────────────────
async def create_image(
    db: AsyncSession, item_id: int, url: str, sort_order: int = 0,
) -> ItemImage:
    image = ItemImage(item_id=item_id, url=url, sort_order=sort_order)
    db.add(image)
    await db.flush()
    await db.refresh(image)
    return image


async def delete_image(db: AsyncSession, image: ItemImage) -> None:
    await db.delete(image)
    await db.flush()


async def get_image_by_id(
    db: AsyncSession, image_id: int, user_id: int,
) -> ItemImage | None:
    stmt = (
        select(ItemImage)
        .join(Item, ItemImage.item_id == Item.id)
        .where(ItemImage.id == image_id, Item.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ── Helpers ────────────────────────────────────────────────────────────
def _resolve_sort_column(sort_by: str):
    mapping = {
        "created_at": Item.created_at,
        "updated_at": Item.updated_at,
        "name": Item.name,
        "purchase_date": Item.purchase_date,
        "purchase_price": Item.purchase_price,
        "usage_count": Item.usage_count,
    }
    return mapping.get(sort_by, Item.created_at)


async def _sync_tags(db: AsyncSession, item: Item, tag_ids: list[int]) -> None:
    """Replace item's tags with the given tag_ids list."""
    # Clear existing associations
    await db.execute(
        item_tags.delete().where(item_tags.c.item_id == item.id),
    )
    # Insert new associations
    if tag_ids:
        # Verify tags belong to user
        result = await db.execute(
            select(Tag.id).where(Tag.id.in_(tag_ids), Tag.user_id == item.user_id),
        )
        valid_ids = {row[0] for row in result.all()}
        for tid in tag_ids:
            if tid in valid_ids:
                await db.execute(
                    item_tags.insert().values(item_id=item.id, tag_id=tid),
                )
