import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal import Journal
from app.schemas.journal import BlogCreate, BlogUpdate, JournalCreate, JournalUpdate


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


# ── Blog functions ────────────────────────────────────────────────────

def _tags_to_json(tags: list[str]) -> str | None:
    return json.dumps(tags, ensure_ascii=False) if tags else None


def _json_to_tags(val: str | None) -> list[str]:
    if not val:
        return []
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return []


async def create_blog(db: AsyncSession, user_id: int, data: BlogCreate) -> Journal:
    token = str(uuid.uuid4()) if data.status == "published" else None
    entry = Journal(
        user_id=user_id,
        type="blog",
        category="blog",
        icon="◈",
        title=data.title,
        content=data.content,
        cover_url=data.cover_url,
        summary=data.summary,
        status=data.status,
        share_token=token,
    )
    # Store tags in icon field hack — actually, let's use a proper approach
    # We'll store tags as JSON in a separate approach. For now, tags go in the existing schema.
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


async def update_blog(db: AsyncSession, journal: Journal, data: BlogUpdate) -> Journal:
    fields = data.model_dump(exclude_unset=True)
    tags = fields.pop("tags", None)
    for field, value in fields.items():
        setattr(journal, field, value)
    # Generate share_token on first publish
    if data.status == "published" and not journal.share_token:
        journal.share_token = str(uuid.uuid4())
    db.add(journal)
    await db.flush()
    await db.refresh(journal)
    return journal


async def list_blogs(
    db: AsyncSession,
    user_id: int,
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[Journal]:
    stmt = select(Journal).where(Journal.user_id == user_id, Journal.type == "blog")
    if status:
        stmt = stmt.where(Journal.status == status)
    stmt = stmt.order_by(Journal.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_blog_by_id(
    db: AsyncSession,
    blog_id: int,
    user_id: int,
) -> Journal | None:
    result = await db.execute(
        select(Journal).where(
            Journal.id == blog_id,
            Journal.user_id == user_id,
            Journal.type == "blog",
        ),
    )
    return result.scalar_one_or_none()


async def get_blog_by_share_token(
    db: AsyncSession,
    share_token: str,
) -> Journal | None:
    result = await db.execute(
        select(Journal).where(
            Journal.share_token == share_token,
            Journal.status == "published",
        ),
    )
    return result.scalar_one_or_none()
