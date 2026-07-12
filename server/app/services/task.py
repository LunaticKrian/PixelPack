"""任务 CRUD + 完成联动（加经验 / 写日志 / 判成就）。"""
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.quest import check_achievements, level_from_exp


async def _get_owned(db: AsyncSession, task_id: int, user_id: int) -> Task | None:
    return (await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )).scalar_one_or_none()


async def list_tasks(db: AsyncSession, user_id: int, due_date: date | None = None) -> list[Task]:
    target = due_date or date.today()
    stmt = (
        select(Task)
        .where(Task.user_id == user_id, Task.due_date == target)
        .order_by(Task.completed.asc(), Task.sort_order.asc(), Task.created_at.asc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_task(
    db: AsyncSession, user_id: int, data: TaskCreate, source: str = "manual",
) -> Task:
    task = Task(
        user_id=user_id,
        title=data.title.strip(),
        description=data.description,
        category=data.category,
        source=source,
        target=data.target,
        progress=0,
        completed=False,
        exp_reward=data.exp_reward if data.exp_reward is not None else settings.TASK_DEFAULT_EXP,
        due_date=data.due_date or date.today(),
        recurrence=data.recurrence,
    )
    db.add(task)
    await db.flush()
    return task


async def update_task(db: AsyncSession, task: Task, data: TaskUpdate) -> Task:
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "title" and value is not None:
            value = value.strip()
        if field == "category" and value is not None:
            value = value.lower()
            if value not in {"study", "work", "life", "health", "other"}:
                value = "other"
        if field == "recurrence" and value is not None:
            value = value.lower() if value in {"once", "daily", "weekly"} else "once"
        setattr(task, field, value)
    # 目标值变化后，保证进度不越界；若已完成则保持完成
    if task.progress > task.target:
        task.progress = task.target
    await db.flush()
    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    await db.delete(task)
    await db.flush()


async def set_progress(db: AsyncSession, task: Task, increment: int) -> Task:
    """推进多步任务进度；满额自动完成。"""
    if task.completed and increment > 0:
        return task
    task.progress = max(0, min(task.progress + increment, task.target))
    if task.progress >= task.target and not task.completed:
        await _complete(db, task)
    else:
        await db.flush()
    return task


async def _complete(db: AsyncSession, task: Task) -> int:
    """标记完成、加经验、写日志。返回获得的经验。"""
    task.completed = True
    task.progress = task.target
    task.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

    user = (await db.execute(select(User).where(User.id == task.user_id))).scalar_one_or_none()
    if user:
        user.exp += task.exp_reward

    await db.flush()
    from app.services.journal import create_system_journal as _log
    await _log(
        db, task.user_id,
        category="task_event", icon="▣",
        title=f"完成任务: {task.title}",
        content=f"+{task.exp_reward} EXP",
    )
    return task.exp_reward


async def complete_task(db: AsyncSession, task: Task) -> dict:
    """完成任务 → 加经验 → 判成就。返回 {exp_gained, level, leveled_up, achievements}。"""
    if task.completed:
        user = (await db.execute(select(User).where(User.id == task.user_id))).scalar_one_or_none()
        exp_now = user.exp if user else 0
        return {
            "exp_gained": 0,
            "level": level_from_exp(exp_now),
            "leveled_up": False,
            "achievements_unlocked": [],
        }

    before_level = level_from_exp(
        (await db.execute(select(User).where(User.id == task.user_id))).scalar_one().exp
    )
    gained = await _complete(db, task)
    unlocked = await check_achievements(db, task.user_id)
    after_exp = (await db.execute(select(User).where(User.id == task.user_id))).scalar_one().exp
    after_level = level_from_exp(after_exp)

    if after_level > before_level:
        from app.services.journal import create_system_journal as _log
        await _log(
            db, task.user_id,
            category="level_up", icon="★",
            title=f"等级提升 → Lv.{after_level}",
        )

    return {
        "exp_gained": gained,
        "level": after_level,
        "leveled_up": after_level > before_level,
        "achievements_unlocked": unlocked,
    }


async def uncomplete_task(db: AsyncSession, task: Task) -> None:
    """撤销完成：扣回经验（不回收成就）。"""
    if not task.completed:
        return
    task.completed = False
    task.completed_at = None
    if task.target > 1:
        task.progress = min(task.progress, task.target - 1)
    else:
        task.progress = 0

    user = (await db.execute(select(User).where(User.id == task.user_id))).scalar_one_or_none()
    if user:
        user.exp = max(0, user.exp - task.exp_reward)
    await db.flush()
