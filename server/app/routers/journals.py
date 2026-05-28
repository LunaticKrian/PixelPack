from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.journal import JournalCreate, JournalResponse, JournalUpdate
from app.services.journal import (
    create_journal,
    delete_journal,
    get_journal_by_id,
    list_journals,
    update_journal,
)
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/journals", tags=["journals"])


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
