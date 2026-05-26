from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagUpdate


async def create_tag(db: AsyncSession, user_id: int, data: TagCreate) -> Tag:
    tag = Tag(
        user_id=user_id,
        name=data.name,
        color=data.color,
    )
    db.add(tag)
    await db.flush()
    await db.refresh(tag)
    return tag


async def get_tag_by_id(
    db: AsyncSession, tag_id: int, user_id: int,
) -> Tag | None:
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id),
    )
    return result.scalar_one_or_none()


async def list_tags(db: AsyncSession, user_id: int) -> list[Tag]:
    result = await db.execute(
        select(Tag).where(Tag.user_id == user_id).order_by(Tag.id),
    )
    return list(result.scalars().all())


async def update_tag(db: AsyncSession, tag: Tag, data: TagUpdate) -> Tag:
    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(tag, field, value)
    db.add(tag)
    await db.flush()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, tag: Tag) -> None:
    await db.delete(tag)
    await db.flush()
