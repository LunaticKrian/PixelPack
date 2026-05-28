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
    Item,
    ItemImage,
    Tag,
    User,
    UserAchievement,
    item_tags,
)
from app.routers import auth, categories, items, quests, stats, tags


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    # Create all database tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


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

# ── Static Files ───────────────────────────────────────────────────────
UPLOAD_DIR = getattr(settings, 'upload_dir', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
