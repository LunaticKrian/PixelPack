from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.intel import ArchivePageResponse, ArticleResponse, IntelStatsResponse
from app.services.intel import (
    generate_intel_now,
    get_stats,
    list_archive,
    list_today,
)
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/intel", tags=["intel"])


@router.get("/today", response_model=list[ArticleResponse])
async def get_today_intel(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ArticleResponse]:
    """今日推送（信号台）。"""
    return await list_today(db)


@router.get("/archive", response_model=ArchivePageResponse)
async def get_archive_intel(
    region: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ArchivePageResponse:
    """历史归档（航海日志），分页，可选按疆域筛选。"""
    return await list_archive(db, region=region, page=page, page_size=page_size)


@router.get("/stats", response_model=IntelStatsResponse)
async def get_intel_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IntelStatsResponse:
    """顶部统计。"""
    return await get_stats(db)


@router.post("/generate")
async def generate_intel(
    overwrite: bool = False,
    current_user: User = Depends(get_current_user),
) -> dict:
    """手动触发生成（开发联调 / 补跑）。20-60s 级，前端注意超时。

    overwrite=true 会先清空今日再重新生成。
    """
    try:
        n = await generate_intel_now(overwrite=overwrite)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成失败: {e}",
        )
    return {"status": "ok", "count": n}
