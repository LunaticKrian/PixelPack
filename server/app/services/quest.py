"""任务系统：等级 / 经验 / 成就（围绕「任务完成」重新设计）。

经验仅来自：完成任务 + 解锁成就。等级 = exp // PER_LEVEL + 1。
经验持久化在 User.exp 独立列（修复了旧版存 settings JSON 不持久化的 bug）。
"""
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.quest import UserAchievement
from app.models.task import Task
from app.models.user import User

PER_LEVEL = settings.TASK_EXP_PER_LEVEL

# ── 成就定义（任务核心）──────────────────────────────────────────────────
ACHIEVEMENT_DEFS = {
    "FIRST_TASK":       {"name": "初试身手", "desc": "完成第 1 个任务",            "icon": "⚔", "exp": 20},
    "TASKS_10":         {"name": "坚持十连", "desc": "累计完成 10 个任务",         "icon": "✦", "exp": 40},
    "TASKS_50":         {"name": "半百里程", "desc": "累计完成 50 个任务",         "icon": "◆", "exp": 100},
    "TASKS_100":        {"name": "百炼成钢", "desc": "累计完成 100 个任务",        "icon": "✷", "exp": 200},
    "STREAK_3":         {"name": "三日不辍", "desc": "连续打卡 3 天",              "icon": "❋", "exp": 40},
    "STREAK_7":         {"name": "一周不缺", "desc": "连续打卡 7 天",              "icon": "☰", "exp": 80},
    "STREAK_30":        {"name": "月度勤勉", "desc": "连续打卡 30 天",             "icon": "☾", "exp": 240},
    "PERFECT_DAY":      {"name": "完美一天", "desc": "单日清单全部完成",           "icon": "★", "exp": 60},
    "CATEGORY_SCHOLAR": {"name": "学者",     "desc": "学习类累计完成 30 个",       "icon": "✎", "exp": 120},
    "AI_EXPLORER":      {"name": "智者辅佐", "desc": "AI 生成并完成 10 个任务",    "icon": "⚛", "exp": 80},
    "SELF_MADE":        {"name": "自律工匠", "desc": "手动添加并完成 10 个任务",   "icon": "⚒", "exp": 80},
    "CENTURY":          {"name": "百日征途", "desc": "累计打卡 100 天",            "icon": "⌛", "exp": 500},
}


# ── 等级 / 经验 ──────────────────────────────────────────────────────────

def level_from_exp(exp: int) -> int:
    return exp // PER_LEVEL + 1


def exp_to_next(exp: int) -> int:
    """距离下一级还差多少经验。"""
    return PER_LEVEL - (exp % PER_LEVEL)


async def _get_user(db: AsyncSession, user_id: int) -> User | None:
    return (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()


# ── 成就 ─────────────────────────────────────────────────────────────────

async def get_user_achievements(db: AsyncSession, user_id: int) -> list[dict]:
    stmt = select(UserAchievement.achievement_id, UserAchievement.unlocked_at).where(
        UserAchievement.user_id == user_id,
    )
    result = await db.execute(stmt)
    unlocked = {row[0]: row[1] for row in result.all()}

    out = []
    for aid, defn in ACHIEVEMENT_DEFS.items():
        out.append({
            "achievement_id": aid,
            "name": defn["name"],
            "description": defn["desc"],
            "icon": defn["icon"],
            "exp_reward": defn["exp"],
            "unlocked": aid in unlocked,
            "unlocked_at": unlocked.get(aid),
        })
    return out


async def unlock_achievement(db: AsyncSession, user_id: int, achievement_id: str) -> bool:
    """解锁成就（若未解锁）。返回是否为新解锁。"""
    stmt = select(UserAchievement).where(
        UserAchievement.user_id == user_id,
        UserAchievement.achievement_id == achievement_id,
    )
    if (await db.execute(stmt)).scalar_one_or_none() is not None:
        return False

    db.add(UserAchievement(user_id=user_id, achievement_id=achievement_id))
    defn = ACHIEVEMENT_DEFS.get(achievement_id, {})
    exp = defn.get("exp", 0)

    user = await _get_user(db, user_id)
    if user and exp:
        user.exp += exp

    await db.flush()
    from app.services.journal import create_system_journal as _log
    await _log(
        db, user_id,
        category="achievement_event",
        icon=defn.get("icon", "?"),
        title=f"成就解锁: {defn.get('name', achievement_id)}",
        content=defn.get("desc"),
    )
    return True


async def _task_stats(db: AsyncSession, user_id: int) -> dict:
    """聚合任务完成统计，供成就判定。"""
    base = select(Task).where(Task.user_id == user_id, Task.completed.is_(True))

    total = (await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id, Task.completed.is_(True)
        )
    )).scalar_one()

    ai_done = (await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id, Task.completed.is_(True), Task.source == "ai"
        )
    )).scalar_one()

    manual_done = (await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id, Task.completed.is_(True), Task.source == "manual"
        )
    )).scalar_one()

    study_done = (await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id, Task.completed.is_(True), Task.category == "study"
        )
    )).scalar_one()

    days_active = (await db.execute(
        select(func.count(func.distinct(Task.due_date))).where(
            Task.user_id == user_id, Task.completed.is_(True)
        )
    )).scalar_one()

    return {
        "total": total,
        "ai": ai_done,
        "manual": manual_done,
        "study": study_done,
        "days_active": days_active,
    }


async def compute_streak(db: AsyncSession, user_id: int) -> int:
    """连续打卡天数：从今天（或昨天）往前回溯，每天至少完成 1 个任务即算。"""
    res = await db.execute(
        select(Task.due_date).where(
            Task.user_id == user_id, Task.completed.is_(True),
        ).distinct().order_by(Task.due_date.desc())
    )
    dates = {row[0] for row in res.fetchall()}
    today = date.today()
    cursor = today if today in dates else today.fromordinal(today.toordinal() - 1)
    streak = 0
    while cursor in dates:
        streak += 1
        cursor = cursor.fromordinal(cursor.toordinal() - 1)
    return streak


async def _perfect_day(db: AsyncSession, user_id: int) -> bool:
    """今日清单是否全部完成（且至少有 1 个任务）。"""
    today = date.today()
    total = (await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id, Task.due_date == today
        )
    )).scalar_one()
    if total == 0:
        return False
    done = (await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id, Task.due_date == today, Task.completed.is_(True)
        )
    )).scalar_one()
    return done == total


async def check_achievements(db: AsyncSession, user_id: int) -> list[str]:
    """评估所有成就条件并解锁新达成的。返回新解锁的 achievement_id 列表。"""
    stats = await _task_stats(db, user_id)
    streak = await compute_streak(db, user_id)
    perfect = await _perfect_day(db, user_id)

    checks = {
        "FIRST_TASK":       stats["total"] >= 1,
        "TASKS_10":         stats["total"] >= 10,
        "TASKS_50":         stats["total"] >= 50,
        "TASKS_100":        stats["total"] >= 100,
        "STREAK_3":         streak >= 3,
        "STREAK_7":         streak >= 7,
        "STREAK_30":        streak >= 30,
        "PERFECT_DAY":      perfect,
        "CATEGORY_SCHOLAR": stats["study"] >= 30,
        "AI_EXPLORER":      stats["ai"] >= 10,
        "SELF_MADE":        stats["manual"] >= 10,
        "CENTURY":          stats["days_active"] >= 100,
    }

    newly = []
    for aid, ok in checks.items():
        if ok and await unlock_achievement(db, user_id, aid):
            newly.append(aid)
    return newly


# ── 汇总 ─────────────────────────────────────────────────────────────────

async def get_summary(db: AsyncSession, user_id: int) -> dict:
    user = await _get_user(db, user_id)
    exp = user.exp if user else 0
    level = level_from_exp(exp)
    achievements = await get_user_achievements(db, user_id)
    unlocked = sum(1 for a in achievements if a["unlocked"])
    streak = await compute_streak(db, user_id)

    today = date.today()
    today_total = (await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id, Task.due_date == today
        )
    )).scalar_one()
    today_done = (await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id, Task.due_date == today, Task.completed.is_(True)
        )
    )).scalar_one()
    tasks_total = (await db.execute(
        select(func.count()).select_from(Task).where(
            Task.user_id == user_id, Task.completed.is_(True)
        )
    )).scalar_one()

    return {
        "level": level,
        "exp": exp,
        "exp_to_next": exp_to_next(exp),
        "streak": streak,
        "today_total": today_total,
        "today_completed": today_done,
        "tasks_completed_total": tasks_total,
        "achievements_completed": unlocked,
        "achievements_total": len(achievements),
        "achievements": achievements,
    }
