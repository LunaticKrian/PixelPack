import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.models import (  # noqa: F401 – ensure tables are created
    AdditionalCost,
    Category,
    DailyQuest,
    IntelArticle,
    Item,
    ItemImage,
    Journal,
    Tag,
    User,
    UserAchievement,
    item_tags,
)
from app.routers import auth, categories, intel, items, journals, quests, stats, tags


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    # Create all database tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

# ── Static Files ───────────────────────────────────────────────────────
UPLOAD_DIR = getattr(settings, 'upload_dir', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
