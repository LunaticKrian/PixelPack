from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal import Journal
from app.schemas.journal import JournalCreate, JournalUpdate


async def create_journal(db: AsyncSession, user_id: int, data: JournalCreate) -> Journal:
    entry = Journal(
        user_id=user_id,
        type="manual",
        category=data.category,
        icon=data.icon,
        title=data.title,
        content=data.content,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


async def create_system_journal(
    db: AsyncSession,
    user_id: int,
    *,
    category: str,
    icon: str,
    title: str,
    content: str | None = None,
) -> Journal:
    entry = Journal(
        user_id=user_id,
        type="system",
        category=category,
        icon=icon,
        title=title,
        content=content,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


async def list_journals(
    db: AsyncSession,
    user_id: int,
    *,
    limit: int = 20,
    category: str | None = None,
) -> list[Journal]:
    stmt = select(Journal).where(Journal.user_id == user_id)
    if category:
        stmt = stmt.where(Journal.category == category)
    stmt = stmt.order_by(Journal.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_journal_by_id(
    db: AsyncSession,
    journal_id: int,
    user_id: int,
) -> Journal | None:
    result = await db.execute(
        select(Journal).where(Journal.id == journal_id, Journal.user_id == user_id),
    )
    return result.scalar_one_or_none()


async def update_journal(
    db: AsyncSession,
    journal: Journal,
    data: JournalUpdate,
) -> Journal:
    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(journal, field, value)
    db.add(journal)
    await db.flush()
    await db.refresh(journal)
    return journal


async def delete_journal(db: AsyncSession, journal: Journal) -> None:
    await db.delete(journal)
    await db.flush()
