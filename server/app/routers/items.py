import math
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.item import (
    CostCreate,
    CostResponse,
    CostUpdate,
    ItemCreate,
    ItemListResponse,
    ItemResponse,
    ItemUpdate,
    StatusChange,
)
from app.services.item import (
    calc_item_stats,
    change_status,
    create_cost,
    create_image,
    delete_cost,
    delete_image,
    get_cost_by_id,
    get_image_by_id,
    get_item_by_id,
    list_items,
    soft_delete_item,
    update_cost,
    update_item,
    create_item,
)
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/items", tags=["items"])


def _item_to_response(item) -> ItemResponse:
    stats = calc_item_stats(item)
    return ItemResponse(
        id=item.id,
        user_id=item.user_id,
        name=item.name,
        description=item.description,
        category_id=item.category_id,
        status=item.status,
        purchase_date=item.purchase_date,
        purchase_price=item.purchase_price,
        currency=item.currency,
        purchase_channel=item.purchase_channel,
        current_value=item.current_value,
        warranty_expiry=item.warranty_expiry,
        expected_lifespan=item.expected_lifespan,
        usage_count=item.usage_count,
        retired_at=item.retired_at,
        retired_reason=item.retired_reason,
        deleted_at=item.deleted_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        daily_cost=stats["daily_cost"],
        per_use_cost=stats["per_use_cost"],
        total_cost=stats["total_cost"],
        usage_days=stats["usage_days"],
        images=item.images or [],
        tags=item.tags or [],
        additional_costs=item.additional_costs or [],
    )


# ── Items CRUD ─────────────────────────────────────────────────────────
@router.get("/", response_model=ItemListResponse)
async def get_items(
    keyword: str | None = None,
    category_id: int | None = None,
    status: str | None = None,
    tag_id: int | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemListResponse:
    items, total = await list_items(
        db,
        current_user.id,
        keyword=keyword,
        category_id=category_id,
        status_filter=status,
        tag_id=tag_id,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
    )
    pages = math.ceil(total / page_size) if page_size > 0 else 0
    return ItemListResponse(
        items=[_item_to_response(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_new_item(
    data: ItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemResponse:
    # Refresh with relationships loaded
    item = await create_item(db, current_user.id, data)
    item = await get_item_by_id(db, item.id, current_user.id)
    return _item_to_response(item)


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item_detail(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemResponse:
    item = await get_item_by_id(db, item_id, current_user.id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return _item_to_response(item)


@router.put("/{item_id}", response_model=ItemResponse)
async def update_existing_item(
    item_id: int,
    data: ItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemResponse:
    item = await get_item_by_id(db, item_id, current_user.id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await update_item(db, item, data)
    # Reload with relationships
    item = await get_item_by_id(db, item_id, current_user.id)
    return _item_to_response(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    item = await get_item_by_id(db, item_id, current_user.id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await soft_delete_item(db, item)


@router.patch("/{item_id}/status", response_model=ItemResponse)
async def change_item_status(
    item_id: int,
    data: StatusChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ItemResponse:
    item = await get_item_by_id(db, item_id, current_user.id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await change_status(db, item, data.status.value, data.reason)
    item = await get_item_by_id(db, item_id, current_user.id)
    return _item_to_response(item)


# ── Additional Costs ───────────────────────────────────────────────────
@router.post("/{item_id}/costs", response_model=CostResponse, status_code=status.HTTP_201_CREATED)
async def add_cost(
    item_id: int,
    data: CostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CostResponse:
    item = await get_item_by_id(db, item_id, current_user.id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    cost = await create_cost(db, item_id, data)
    return cost


@router.put("/costs/{cost_id}", response_model=CostResponse)
async def update_existing_cost(
    cost_id: int,
    data: CostUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CostResponse:
    cost = await get_cost_by_id(db, cost_id, current_user.id)
    if cost is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost not found")
    cost = await update_cost(db, cost, data)
    return cost


@router.delete("/costs/{cost_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_cost(
    cost_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    cost = await get_cost_by_id(db, cost_id, current_user.id)
    if cost is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cost not found")
    await delete_cost(db, cost)


# ── Images ─────────────────────────────────────────────────────────────
@router.post("/{item_id}/images", response_model=CostResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    item_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.schemas.item import ItemImageResponse

    item = await get_item_by_id(db, item_id, current_user.id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    # Ensure upload directory exists
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename
    ext = os.path.splitext(file.filename or "image.jpg")[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)

    # Save file
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    url = f"/uploads/{filename}"

    # Determine sort order
    sort_order = len(item.images) if item.images else 0

    image = await create_image(db, item_id, url, sort_order)
    return ItemImageResponse.model_validate(image).model_dump()


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_image(
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    image = await get_image_by_id(db, image_id, current_user.id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    # Try to delete file from disk
    try:
        if image.url.startswith("/uploads/"):
            filepath = image.url.lstrip("/")
            if os.path.exists(filepath):
                os.remove(filepath)
    except OSError:
        pass  # File deletion is best-effort

    await delete_image(db, image)
