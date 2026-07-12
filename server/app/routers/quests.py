from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.quest import AchievementResponse, QuestSummaryResponse
from app.services.quest import get_summary, get_user_achievements
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/quests", tags=["quests"])


@router.get("/summary", response_model=QuestSummaryResponse)
async def get_quest_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestSummaryResponse:
    data = await get_summary(db, current_user.id)
    data["achievements"] = [AchievementResponse(**a) for a in data["achievements"]]
    return QuestSummaryResponse(**data)


@router.get("/achievements", response_model=list[AchievementResponse])
async def get_achievements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AchievementResponse]:
    achievements = await get_user_achievements(db, current_user.id)
    return [AchievementResponse(**a) for a in achievements]
