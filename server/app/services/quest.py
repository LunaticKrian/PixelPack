import random
from datetime import date, datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.item import Item
from app.models.quest import DailyQuest, UserAchievement
from app.models.tag import Tag
from app.models.user import User


# ── Quest Definitions ────────────────────────────────────────────────────

QUEST_DEFS = {
    "ADD_ITEMS": {"name": "添加物品", "desc": "今日添加 {target} 件物品", "target": 3, "exp": 20},
    "VIEW_ITEMS": {"name": "查看物品", "desc": "查看物品详情 {target} 次", "target": 5, "exp": 10},
    "CHECK_WARRANTY": {"name": "保修巡查", "desc": "查看保修提醒", "target": 1, "exp": 15},
    "EDIT_ITEM": {"name": "物品维护", "desc": "编辑 {target} 件物品", "target": 2, "exp": 15},
    "REVIEW_STATS": {"name": "数据审查", "desc": "查看数据统计", "target": 1, "exp": 10},
}

DAILY_QUEST_COUNT = 3

# ── Achievement Definitions ──────────────────────────────────────────────

ACHIEVEMENT_DEFS = {
    "FIRST_ITEM": {"name": "初次获取", "desc": "创建第 1 件物品", "icon": "⚔", "exp": 10},
    "COLLECTOR_10": {"name": "小有收藏", "desc": "物品总数 ≥ 10", "icon": "📦", "exp": 30},
    "COLLECTOR_50": {"name": "收藏家", "desc": "物品总数 ≥ 50", "icon": "💎", "exp": 100},
    "COLLECTOR_100": {"name": "大收藏家", "desc": "物品总数 ≥ 100", "icon": "👑", "exp": 200},
    "CATEGORY_MASTER": {"name": "分类达人", "desc": "分类数 ≥ 5", "icon": "▦", "exp": 20},
    "TAG_MASTER": {"name": "标签达人", "desc": "标签数 ≥ 10", "icon": "◎", "exp": 20},
    "DAILY_QUEST_1": {"name": "初次任务", "desc": "完成 1 个每日任务", "icon": "★", "exp": 15},
    "DAILY_QUEST_10": {"name": "任务达人", "desc": "累计完成 10 个每日任务", "icon": "◆", "exp": 50},
    "DAILY_QUEST_30": {"name": "任务大师", "desc": "累计完成 30 个每日任务", "icon": "♛", "exp": 150},
    "WARRANTY_WATCHER": {"name": "保修哨兵", "desc": "查看保修提醒", "icon": "⚠", "exp": 10},
    "SEVEN_DAYS": {"name": "七日冒险", "desc": "注册满 7 天", "icon": "🗓", "exp": 25},
    "THRIFTY": {"name": "节俭达人", "desc": "日均成本 < ¥5", "icon": "¥", "exp": 30},
}


def get_quest_name(key: str) -> str:
    d = QUEST_DEFS.get(key, {})
    return d.get("name", key)


def get_quest_desc(key: str, target: int) -> str:
    d = QUEST_DEFS.get(key, {})
    return d.get("desc", "").format(target=target)


# ── Daily Quests ─────────────────────────────────────────────────────────

async def get_or_create_daily_quests(
    db: AsyncSession, user_id: int,
) -> list[DailyQuest]:
    today = date.today()
    stmt = select(DailyQuest).where(
        DailyQuest.user_id == user_id,
        DailyQuest.quest_date == today,
    )
    result = await db.execute(stmt)
    existing = list(result.scalars().all())

    if existing:
        return existing

    keys = random.sample(list(QUEST_DEFS.keys()), min(DAILY_QUEST_COUNT, len(QUEST_DEFS)))
    for key in keys:
        defn = QUEST_DEFS[key]
        quest = DailyQuest(
            user_id=user_id,
            quest_date=today,
            quest_key=key,
            target=defn["target"],
            exp_reward=defn["exp"],
            progress=0,
            completed=False,
        )
        db.add(quest)

    await db.flush()

    result = await db.execute(
        select(DailyQuest).where(
            DailyQuest.user_id == user_id,
            DailyQuest.quest_date == today,
        )
    )
    return list(result.scalars().all())


async def increment_quest_progress(
    db: AsyncSession, user_id: int, quest_key: str, amount: int = 1,
) -> bool:
    """Increment progress on today's quest. Returns True if quest just completed."""
    today = date.today()
    stmt = select(DailyQuest).where(
        DailyQuest.user_id == user_id,
        DailyQuest.quest_date == today,
        DailyQuest.quest_key == quest_key,
    )
    result = await db.execute(stmt)
    quest = result.scalar_one_or_none()

    if quest is None or quest.completed:
        return False

    quest.progress = min(quest.progress + amount, quest.target)
    if quest.progress >= quest.target:
        quest.completed = True
        await _add_quest_exp(db, user_id, quest.exp_reward)
        await db.flush()
        return True

    await db.flush()
    return False


async def _add_quest_exp(db: AsyncSession, user_id: int, exp: int) -> None:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user and isinstance(user.settings, dict):
        user.settings["quest_exp"] = user.settings.get("quest_exp", 0) + exp
        user.settings["daily_completed"] = user.settings.get("daily_completed", 0) + 1
    elif user:
        user.settings = {"quest_exp": exp, "daily_completed": 1}


# ── Achievements ─────────────────────────────────────────────────────────

async def get_user_achievements(
    db: AsyncSession, user_id: int,
) -> list[dict]:
    """Return all achievement definitions with unlock status."""
    stmt = select(UserAchievement.achievement_id, UserAchievement.unlocked_at).where(
        UserAchievement.user_id == user_id,
    )
    result = await db.execute(stmt)
    unlocked = {row[0]: row[1] for row in result.all()}

    achievements = []
    for aid, defn in ACHIEVEMENT_DEFS.items():
        achievements.append({
            "achievement_id": aid,
            "name": defn["name"],
            "description": defn["desc"],
            "icon": defn["icon"],
            "exp_reward": defn["exp"],
            "unlocked": aid in unlocked,
            "unlocked_at": unlocked.get(aid),
        })
    return achievements


async def unlock_achievement(
    db: AsyncSession, user_id: int, achievement_id: str,
) -> bool:
    """Unlock an achievement if not already unlocked. Returns True if newly unlocked."""
    stmt = select(UserAchievement).where(
        UserAchievement.user_id == user_id,
        UserAchievement.achievement_id == achievement_id,
    )
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        return False

    entry = UserAchievement(user_id=user_id, achievement_id=achievement_id)
    db.add(entry)

    defn = ACHIEVEMENT_DEFS.get(achievement_id, {})
    exp = defn.get("exp", 0)
    if exp:
        await _add_quest_exp(db, user_id, exp)

    await db.flush()
    return True


async def check_achievements(db: AsyncSession, user_id: int) -> list[str]:
    """Evaluate all achievement conditions and unlock newly earned ones."""
    newly_unlocked = []

    # Get current stats
    item_count = (await db.execute(
        select(func.count()).select_from(Item).where(
            Item.user_id == user_id, Item.deleted_at.is_(None)
        )
    )).scalar_one()

    cat_count = (await db.execute(
        select(func.count()).select_from(Category).where(Category.user_id == user_id)
    )).scalar_one()

    tag_count = (await db.execute(
        select(func.count()).select_from(Tag).where(Tag.user_id == user_id)
    )).scalar_one()

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    settings = user.settings if user and isinstance(user.settings, dict) else {}
    daily_completed = settings.get("daily_completed", 0)

    # Check conditions
    checks = {
        "FIRST_ITEM": item_count >= 1,
        "COLLECTOR_10": item_count >= 10,
        "COLLECTOR_50": item_count >= 50,
        "COLLECTOR_100": item_count >= 100,
        "CATEGORY_MASTER": cat_count >= 5,
        "TAG_MASTER": tag_count >= 10,
        "DAILY_QUEST_1": daily_completed >= 1,
        "DAILY_QUEST_10": daily_completed >= 10,
        "DAILY_QUEST_30": daily_completed >= 30,
    }

    # Check registration age
    if user and user.created_at:
        created = user.created_at.replace(tzinfo=timezone.utc) if user.created_at.tzinfo is None else user.created_at
        days_since = (datetime.now(timezone.utc) - created).days
        if days_since >= 7:
            checks["SEVEN_DAYS"] = True

    # Check avg daily cost (SQLite-compatible)
    item_stats = (await db.execute(
        select(func.sum(Item.purchase_price), func.count(Item.id)).where(
            Item.user_id == user_id, Item.deleted_at.is_(None)
        )
    )).one()
    if item_stats[0] and item_stats[1]:
        total_price = float(item_stats[0])
        item_count = int(item_stats[1])
        days_since = (datetime.now(timezone.utc) - created).days if user and user.created_at else 1
        days = max(days_since, 1)
        if total_price / days < 5:
            checks["THRIFTY"] = True

    for aid, condition_met in checks.items():
        if condition_met:
            if await unlock_achievement(db, user_id, aid):
                newly_unlocked.append(aid)

    return newly_unlocked


# ── Level ────────────────────────────────────────────────────────────────

async def get_user_level(db: AsyncSession, user_id: int) -> tuple[int, int]:
    """Return (level, total_exp)."""
    item_count = (await db.execute(
        select(func.count()).select_from(Item).where(
            Item.user_id == user_id, Item.deleted_at.is_(None)
        )
    )).scalar_one()

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    settings = user.settings if user and isinstance(user.settings, dict) else {}
    quest_exp = settings.get("quest_exp", 0)

    total_exp = item_count * 5 + quest_exp
    level = total_exp // 50 + 1
    return level, total_exp
