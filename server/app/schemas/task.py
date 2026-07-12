from datetime import date as date_type, datetime

from pydantic import BaseModel, Field, field_validator


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    description: str | None = Field(None, max_length=2000)
    category: str = Field("study", max_length=32)
    target: int = Field(1, ge=1, le=999)
    exp_reward: int | None = Field(None, ge=0, le=999)
    due_date: date_type | None = None
    recurrence: str = Field("once", max_length=16)

    @field_validator("category")
    @classmethod
    def _valid_category(cls, v: str) -> str:
        v = (v or "study").strip().lower()
        # 宽松校验：未知分类归入 other
        if v not in {"study", "work", "life", "health", "other"}:
            return "other"
        return v

    @field_validator("recurrence")
    @classmethod
    def _valid_recurrence(cls, v: str) -> str:
        v = (v or "once").strip().lower()
        return v if v in {"once", "daily", "weekly"} else "once"


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = Field(None, max_length=2000)
    category: str | None = None
    target: int | None = Field(None, ge=1, le=999)
    exp_reward: int | None = Field(None, ge=0, le=999)
    due_date: date_type | None = None
    recurrence: str | None = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None
    category: str
    source: str
    target: int
    progress: int
    completed: bool
    completed_at: datetime | None
    exp_reward: int
    due_date: date_type
    recurrence: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskProgressRequest(BaseModel):
    increment: int = Field(1, ge=-999, le=999)


class TaskCompleteResult(BaseModel):
    task: TaskResponse
    exp_gained: int
    level: int
    leveled_up: bool
    achievements_unlocked: list[str]
