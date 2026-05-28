from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.quest import (
    AchievementResponse,
    DailyQuestResponse,
    QuestProgressRequest,
    QuestSummaryResponse,
)
from app.services.quest import (
    get_or_create_daily_quests,
    get_user_achievements,
    get_user_level,
    increment_quest_progress,
    check_achievements,
    get_quest_name,
    get_quest_desc,
)
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/quests", tags=["quests"])


@router.get("/daily", response_model=list[DailyQuestResponse])
async def get_daily_quests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DailyQuestResponse]:
    quests = await get_or_create_daily_quests(db, current_user.id)
    return [
        DailyQuestResponse(
            id=q.id,
            quest_key=q.quest_key,
            name=get_quest_name(q.quest_key),
            description=get_quest_desc(q.quest_key, q.target),
            target=q.target,
            progress=q.progress,
            completed=q.completed,
            exp_reward=q.exp_reward,
        )
        for q in quests
    ]


@router.post("/progress")
async def report_progress(
    body: QuestProgressRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    just_completed = await increment_quest_progress(
        db, current_user.id, body.quest_key, body.increment,
    )
    newly_unlocked = await check_achievements(db, current_user.id)
    return {
        "quest_completed": just_completed,
        "achievements_unlocked": newly_unlocked,
    }


@router.get("/achievements", response_model=list[AchievementResponse])
async def get_achievements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AchievementResponse]:
    achievements = await get_user_achievements(db, current_user.id)
    return [AchievementResponse(**a) for a in achievements]


@router.get("/summary", response_model=QuestSummaryResponse)
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuestSummaryResponse:
    quests = await get_or_create_daily_quests(db, current_user.id)
    achievements = await get_user_achievements(db, current_user.id)
    level, total_exp = await get_user_level(db, current_user.id)

    daily = [
        DailyQuestResponse(
            id=q.id,
            quest_key=q.quest_key,
            name=get_quest_name(q.quest_key),
            description=get_quest_desc(q.quest_key, q.target),
            target=q.target,
            progress=q.progress,
            completed=q.completed,
            exp_reward=q.exp_reward,
        )
        for q in quests
    ]

    completed = sum(1 for a in achievements if a["unlocked"])

    return QuestSummaryResponse(
        daily_quests=daily,
        achievements=[AchievementResponse(**a) for a in achievements],
        level=level,
        total_exp=total_exp,
        achievements_completed=completed,
        achievements_total=len(achievements),
    )
