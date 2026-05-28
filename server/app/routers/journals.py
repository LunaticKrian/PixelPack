import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.journal import (
    BlogCreate,
    BlogResponse,
    BlogUpdate,
    JournalCreate,
    JournalResponse,
    JournalUpdate,
)
from app.services.journal import (
    create_blog,
    create_journal,
    delete_journal,
    get_blog_by_id,
    get_blog_by_share_token,
    get_journal_by_id,
    list_blogs,
    list_journals,
    update_blog,
    update_journal,
)
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/journals", tags=["journals"])


# ── Regular journal endpoints ─────────────────────────────────────────

@router.get("", response_model=list[JournalResponse])
async def get_journals(
    limit: int = 20,
    category: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[JournalResponse]:
    entries = await list_journals(db, current_user.id, limit=limit, category=category)
    return entries


@router.post("", response_model=JournalResponse, status_code=status.HTTP_201_CREATED)
async def create_new_journal(
    data: JournalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JournalResponse:
    entry = await create_journal(db, current_user.id, data)
    return entry


@router.put("/{journal_id}", response_model=JournalResponse)
async def update_existing_journal(
    journal_id: int,
    data: JournalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JournalResponse:
    entry = await get_journal_by_id(db, journal_id, current_user.id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    if entry.type == "system":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot edit system journal entries")
    entry = await update_journal(db, entry, data)
    return entry


@router.delete("/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_journal(
    journal_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    entry = await get_journal_by_id(db, journal_id, current_user.id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
    if entry.type == "system":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete system journal entries")
    await delete_journal(db, entry)


# ── Blog endpoints ────────────────────────────────────────────────────

@router.get("/blog", response_model=list[BlogResponse])
async def get_blogs(
    status_filter: str | None = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BlogResponse]:
    blogs = await list_blogs(db, current_user.id, status=status_filter, limit=limit)
    return blogs


@router.post("/blog", response_model=BlogResponse, status_code=status.HTTP_201_CREATED)
async def create_new_blog(
    data: BlogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BlogResponse:
    entry = await create_blog(db, current_user.id, data)
    return entry


@router.put("/blog/{blog_id}", response_model=BlogResponse)
async def update_existing_blog(
    blog_id: int,
    data: BlogUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BlogResponse:
    entry = await get_blog_by_id(db, blog_id, current_user.id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog not found")
    entry = await update_blog(db, entry, data)
    return entry


@router.delete("/blog/{blog_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_blog(
    blog_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    entry = await get_blog_by_id(db, blog_id, current_user.id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog not found")
    await delete_journal(db, entry)


@router.get("/blog/share/{token}", response_model=BlogResponse)
async def get_shared_blog(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> BlogResponse:
    """Public endpoint — no auth required."""
    entry = await get_blog_by_share_token(db, token)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog not found")
    return entry


@router.post("/blog/upload")
async def upload_blog_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "image.png")[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    return {"url": f"/uploads/{filename}"}
