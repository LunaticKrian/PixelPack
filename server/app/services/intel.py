"""AI 资讯业务层：读取（today/archive/stats）+ 写入（store/generate）。"""
import asyncio
import logging
from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intel import IntelArticle
from app.schemas.intel import (
    ArchivePageResponse,
    ArticleDraft,
    ArticleResponse,
    IntelStatsResponse,
)

logger = logging.getLogger(__name__)

# 全局并发锁：同一时刻只允许跑一个 Agent（Agent 是重资源）
_generate_lock = asyncio.Lock()

REGIONS = ("llm", "agent", "vision", "infra", "research", "tools")


def to_response(a: IntelArticle) -> ArticleResponse:
    return ArticleResponse(
        id=a.id,
        region=a.region,
        title=a.title,
        summary=a.summary,
        body=a.body,
        source=a.source,
        readTime=a.read_time,
        url=a.url,
        publishedAt=a.published_at.isoformat() if a.published_at else "",
    )


# ── 读取 ───────────────────────────────────────────────────────────────
async def list_today(db: AsyncSession) -> list[ArticleResponse]:
    today = date.today()
    rows = (await db.execute(
        select(IntelArticle)
        .where(IntelArticle.published_at == today)
        .order_by(IntelArticle.id.desc())
    )).scalars().all()
    return [to_response(a) for a in rows]


async def list_archive(
    db: AsyncSession,
    region: str | None = None,
    page: int = 1,
) -> ArchivePageResponse:
    """历史归档（航海日志）—— **一天一页**。

    page = 第几个有内容的日期（1 起，DESC）。每页返回该日期下的全部文章。
    region 过滤时只统计有匹配文章的日期，自动跳过空日期。
    """
    today = date.today()
    page = max(1, int(page))

    where_clauses = [IntelArticle.published_at < today]
    if region:
        where_clauses.append(IntelArticle.region == region)

    # 所有有内容的日期（DESC）
    date_rows = (await db.execute(
        select(IntelArticle.published_at)
        .where(*where_clauses)
        .distinct()
        .order_by(IntelArticle.published_at.desc())
    )).scalars().all()
    dates = [d.isoformat() for d in date_rows if d is not None]

    total_pages = len(dates)
    if total_pages == 0:
        return ArchivePageResponse(
            items=[], date=None, page=1, totalPages=0, total=0, dates=[],
        )

    page = min(page, total_pages)
    target = date.fromisoformat(dates[page - 1])
    rows = (await db.execute(
        select(IntelArticle)
        .where(*where_clauses, IntelArticle.published_at == target)
        .order_by(IntelArticle.id.desc())
    )).scalars().all()
    return ArchivePageResponse(
        items=[to_response(a) for a in rows],
        date=target.isoformat(),
        page=page,
        totalPages=total_pages,
        total=len(rows),
        dates=dates,
    )


async def get_stats(db: AsyncSession) -> IntelStatsResponse:
    today = date.today()
    week_ago = today - timedelta(days=7)
    today_count = (await db.scalar(
        select(func.count()).select_from(IntelArticle)
        .where(IntelArticle.published_at == today)
    )) or 0
    week_count = (await db.scalar(
        select(func.count()).select_from(IntelArticle)
        .where(IntelArticle.published_at >= week_ago)
    )) or 0
    archived_count = (await db.scalar(
        select(func.count()).select_from(IntelArticle)
    )) or 0
    return IntelStatsResponse(
        todayCount=today_count,
        weekCount=week_count,
        archivedCount=archived_count,
        unreadCount=today_count,  # 前端「今日即未读」视觉
    )


# ── 写入 ───────────────────────────────────────────────────────────────
async def store_daily_intel(
    db: AsyncSession, drafts: list[ArticleDraft], *, overwrite: bool = False,
) -> int:
    """把 Agent 产出的草稿入库。published_at = 今日。

    - overwrite=True（手动「发起侦测」刷新）：先清空今日再全部写入。
    - overwrite=False（每日定时任务，默认）：**基于数据库已有数据去重追加**——
      以 url（无 url 则退化为标题）为去重键，跳过已存在的，仅追加新条目。
    """
    today = date.today()

    if overwrite:
        await db.execute(
            delete(IntelArticle).where(IntelArticle.published_at == today)
        )
        existing_keys: set[str] = set()
    else:
        # 取库中全部 (url, title) 作为去重依据
        rows = (await db.execute(
            select(IntelArticle.url, IntelArticle.title)
        )).all()
        existing_keys = {_dedup_key(url, title) for url, title in rows if url or title}

    count = 0
    for d in drafts:
        if d.region not in REGIONS:
            logger.warning("skip draft with invalid region: %s", d.region)
            continue
        key = _dedup_key(d.url, d.title)
        if key and key in existing_keys:
            logger.info("[store] 跳过重复 | %s | %s", d.region, (d.title or "")[:60])
            continue
        logger.info(
            "[store] +%s | %s | %s",
            d.region, (d.source or "?")[:20], (d.title or "")[:60],
        )
        db.add(IntelArticle(
            region=d.region,
            title=(d.title or "")[:200],
            summary=(d.summary or "")[:500],
            body=d.body or "",
            source=(d.source or "")[:200],
            url=(d.url or None),
            read_time=(d.read_time or "5 min")[:16],
            published_at=today,
        ))
        existing_keys.add(key)
        count += 1
    await db.flush()
    return count


def _dedup_key(url: str | None, title: str | None) -> str:
    """去重键：优先 url；无 url 则用规范化标题；都空返回空串（不去重）。"""
    if url:
        return f"url:{url.strip()}"
    if title:
        return f"title:{title.strip().lower()}"
    return ""


async def generate_intel_now(*, overwrite: bool = False) -> int:
    """跑一次 Agent 生成并入库。用独立 session，带并发锁。

    供手动端点 POST /api/intel/generate 调用。
    """
    async with _generate_lock:
        # 延迟导入，避免 SDK 在模块加载时就初始化（开发期可未装）
        from app.services.intel_agent import fetch_ai_intel
        from app.database import async_session_factory

        drafts = await fetch_ai_intel()
        async with async_session_factory() as db:
            n = await store_daily_intel(db, drafts, overwrite=overwrite)
            await db.commit()
        logger.info("intel generated (overwrite=%s): %d drafts -> %d stored",
                    overwrite, len(drafts), n)
        return n


async def scheduled_generate_intel() -> None:
    """每日定时入口。失败只记日志不抛穿（调度器继续运行）。"""
    try:
        await generate_intel_now(overwrite=False)
    except Exception:  # noqa: BLE001
        logger.exception("daily intel generation failed")
