import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.logging_config import setup_logging
from app.database import Base, engine

# 必须在业务模块实例化 logger 之前完成配置
setup_logging()
from app.models import (  # noqa: F401 – ensure tables are created
    AdditionalCost,
    Category,
    ChatMessage,
    ChatSession,
    DailyQuest,
    IntelArticle,
    Item,
    ItemImage,
    Journal,
    Tag,
    Task,
    User,
    UserAchievement,
    item_tags,
)
from app.routers import auth, categories, chat, intel, items, journals, quests, stats, tags, tasks
from app.utils.migrate import ensure_column


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    # Create all database tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # create_all 不会 ALTER 已存在的表：给 users 补 exp 列（任务系统经验持久化）
        await ensure_column(conn, "users", "exp", "INTEGER DEFAULT 0")
        # 兜底：把误存成 datetime 字符串的 published_at 归一化为 'YYYY-MM-DD'，
        # 避免 SQLite Date 解析器在读取时抛 Invalid isoformat（历史/外部脏数据）。
        await conn.execute(text(
            "UPDATE intel_articles SET published_at = date(published_at) "
            "WHERE published_at != date(published_at)"
        ))

    # 每日 AI 资讯定时生成（APScheduler）
    scheduler = None
    if settings.INTEL_ENABLED:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        from app.services.intel import scheduled_generate_intel

        scheduler = AsyncIOScheduler(timezone=settings.INTEL_TZ)
        scheduler.add_job(
            scheduled_generate_intel,
            CronTrigger(hour=settings.INTEL_CRON_HOUR, minute=settings.INTEL_CRON_MINUTE),
            id="intel_daily",
            coalesce=True,         # 错过的多次只补跑一次
            max_instances=1,       # 绝不并发跑两个 Agent
            misfire_grace_time=3600,
        )
        scheduler.start()

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


app = FastAPI(
    title="DailyStuff API",
    description="Item management backend for DailyStuff",
    version="0.1.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

# CORS – allow all origins during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(auth.router, tags=["auth"])
app.include_router(categories.router)
app.include_router(tags.router)
app.include_router(items.router)
app.include_router(stats.router)
app.include_router(quests.router)
app.include_router(journals.router)
app.include_router(intel.router)
app.include_router(tasks.router)
app.include_router(chat.router)

# ── Static Files ───────────────────────────────────────────────────────
# 修正：原代码 getattr(settings, 'upload_dir', ...) 用了小写属性名，
# pydantic 字段是 UPLOAD_DIR，导致环境变量永远改不了静态服务目录（文件写到
# UPLOAD_DIR 但 /uploads 仍从默认 'uploads' 读 → 部署挂载卷时图片 404）。
UPLOAD_DIR = settings.UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
