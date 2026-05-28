from datetime import datetime

from pydantic import BaseModel


class DailyQuestResponse(BaseModel):
    id: int
    quest_key: str
    name: str
    description: str
    target: int
    progress: int
    completed: bool
    exp_reward: int

    model_config = {"from_attributes": True}


class AchievementResponse(BaseModel):
    achievement_id: str
    name: str
    description: str
    icon: str
    exp_reward: int
    unlocked: bool
    unlocked_at: datetime | None = None


class QuestProgressRequest(BaseModel):
    quest_key: str
    increment: int = 1


class QuestSummaryResponse(BaseModel):
    daily_quests: list[DailyQuestResponse]
    achievements: list[AchievementResponse]
    level: int
    total_exp: int
    achievements_completed: int
    achievements_total: int
