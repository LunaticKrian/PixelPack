from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.models import (  # noqa: F401 – ensure tables are created
    AdditionalCost,
    Category,
    Item,
    ItemImage,
    Tag,
    User,
    item_tags,
)
from app.routers import auth, categories, items, tags


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
