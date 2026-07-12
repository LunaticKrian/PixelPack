from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.task import (
    TaskCompleteResult,
    TaskCreate,
    TaskProgressRequest,
    TaskResponse,
    TaskUpdate,
)
from app.services import task as task_svc
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


async def _load_owned(db: AsyncSession, task_id: int, user_id: int):
    task = await task_svc._get_owned(db, task_id, user_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    date: date_type | None = Query(None, description="任务日期，默认今天"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskResponse]:
    tasks = await task_svc.list_tasks(db, current_user.id, due_date=date)
    return [TaskResponse.model_validate(t) for t in tasks]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await task_svc.create_task(db, current_user.id, data, source="manual")
    return TaskResponse.model_validate(task)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await _load_owned(db, task_id, current_user.id)
    task = await task_svc.update_task(db, task, data)
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    task = await _load_owned(db, task_id, current_user.id)
    await task_svc.delete_task(db, task)


@router.post("/{task_id}/complete", response_model=TaskCompleteResult)
async def complete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskCompleteResult:
    task = await _load_owned(db, task_id, current_user.id)
    result = await task_svc.complete_task(db, task)
    return TaskCompleteResult(task=TaskResponse.model_validate(task), **result)


@router.post("/{task_id}/uncomplete", response_model=TaskResponse)
async def uncomplete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await _load_owned(db, task_id, current_user.id)
    await task_svc.uncomplete_task(db, task)
    return TaskResponse.model_validate(task)


@router.post("/{task_id}/progress", response_model=TaskResponse)
async def progress_task(
    task_id: int,
    body: TaskProgressRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = await _load_owned(db, task_id, current_user.id)
    task = await task_svc.set_progress(db, task, body.increment)
    return TaskResponse.model_validate(task)
