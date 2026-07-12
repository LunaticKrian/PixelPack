import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, get_db
from app.models.user import User
from app.schemas.chat import (
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    SendMessageRequest,
)
from app.services import chat as chat_svc
from app.services import task_agent
from app.utils.deps import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])

# 同一会话不并发跑两个 Agent 子进程
_session_locks: dict[int, asyncio.Lock] = {}
_locks_guard = asyncio.Lock()


async def _get_lock(session_id: int) -> asyncio.Lock:
    async with _locks_guard:
        if session_id not in _session_locks:
            _session_locks[session_id] = asyncio.Lock()
        return _session_locks[session_id]


# ── 会话 CRUD ────────────────────────────────────────────────────────────

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSessionResponse:
    s = await chat_svc.create_session(db, current_user.id, body.title)
    return ChatSessionResponse(
        id=s.id, title=s.title, created_at=s.created_at, updated_at=s.updated_at,
        last_message=None, message_count=0,
    )


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await chat_svc.list_sessions(db, current_user.id)


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessageResponse]:
    if await chat_svc.get_session(db, session_id, current_user.id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    msgs = await chat_svc.list_messages(db, session_id)
    return [ChatMessageResponse.model_validate(m) for m in msgs]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    s = await chat_svc.get_session(db, session_id, current_user.id)
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    await chat_svc.delete_session(db, s)


# ── 发送消息（SSE 流式）──────────────────────────────────────────────────

def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: int,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    session = await chat_svc.get_session(db, session_id, current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # 1. 落库用户消息 + 取历史（必须在 StreamingResponse 返回前完成，避免 get_db 会话提前关闭）
    await chat_svc.add_message(db, session_id, "user", body.content)
    await db.commit()
    prompt = await chat_svc.history_prompt(db, session_id)
    sid = session_id

    lock = await _get_lock(sid)

    async def event_stream():
        # 心跳，避免代理缓冲
        yield _sse({"type": "start"})
        full_text: list[str] = []
        created_count = 0
        async with lock:
            try:
                async for ev in task_agent.run_agent(current_user.id, prompt):
                    if ev["type"] == "delta":
                        full_text.append(ev["text"])
                    elif ev["type"] == "task_created":
                        created_count += 1
                    yield _sse(ev)
            except Exception as e:  # 兜底
                yield _sse({"type": "error", "message": str(e)})

        # 2. 落库助手消息（用独立 session）
        text = "".join(full_text).strip()
        async with async_session_factory() as s2:
            await chat_svc.add_message(
                s2, sid, "assistant", text or "(无回复)",
                meta={"tasks_created": created_count},
            )
            await s2.commit()
        yield _sse({"type": "end", "tasks_created": created_count})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
