from datetime import datetime

from pydantic import BaseModel


class AchievementResponse(BaseModel):
    achievement_id: str
    name: str
    description: str
    icon: str
    exp_reward: int
    unlocked: bool
    unlocked_at: datetime | None = None


class QuestSummaryResponse(BaseModel):
    level: int
    exp: int
    exp_to_next: int
    streak: int
    today_total: int
    today_completed: int
    tasks_completed_total: int
    achievements_completed: int
    achievements_total: int
    achievements: list[AchievementResponse]
