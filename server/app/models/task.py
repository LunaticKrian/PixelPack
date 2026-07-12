from datetime import date as date_type, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Task(Base):
    """用户任务（替代旧的随机抽样 DailyQuest）。

    每日清单 = due_date == today。来源 source=ai（对话生成）| manual（手动添加）。
    """

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="study")
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")  # ai | manual
    target: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    exp_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    due_date: Mapped[date_type] = mapped_column(Date, index=True, nullable=False)
    recurrence: Mapped[str] = mapped_column(String(16), nullable=False, default="once")  # once|daily|weekly
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False,
    )
