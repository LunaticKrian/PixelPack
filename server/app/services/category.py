from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.item import Item
from app.schemas.category import CategoryCreate, CategoryUpdate


async def create_category(
    db: AsyncSession, user_id: int, data: CategoryCreate,
) -> Category:
    category = Category(
        user_id=user_id,
        name=data.name,
        icon=data.icon,
        color=data.color,
        sort_order=data.sort_order,
        parent_id=data.parent_id,
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def get_category_by_id(
    db: AsyncSession, category_id: int, user_id: int,
) -> Category | None:
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
        ),
    )
    return result.scalar_one_or_none()


async def list_categories(db: AsyncSession, user_id: int) -> list[Category]:
    result = await db.execute(
        select(Category)
        .where(Category.user_id == user_id)
        .order_by(Category.sort_order, Category.id),
    )
    return list(result.scalars().all())


async def update_category(
    db: AsyncSession, category: Category, data: CategoryUpdate,
) -> Category:
    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(category, field, value)
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category: Category) -> None:
    # Check if any items reference this category
    result = await db.execute(
        select(Item.id).where(Item.category_id == category.id).limit(1),
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category: items still reference it",
        )
    await db.delete(category)
    await db.flush()
