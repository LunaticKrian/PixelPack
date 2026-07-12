"""对话会话 / 消息持久化。"""
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession


async def create_session(db: AsyncSession, user_id: int, title: str | None = None) -> ChatSession:
    session = ChatSession(user_id=user_id, title=(title or "新对话")[:120])
    db.add(session)
    await db.flush()
    return session


async def list_sessions(db: AsyncSession, user_id: int) -> list[dict]:
    """会话列表，带最后一条消息预览与消息数。"""
    sessions = list((await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(desc(ChatSession.updated_at))
    )).scalars().all())
    if not sessions:
        return []
    ids = [s.id for s in sessions]

    # 最后一条消息预览
    last_rows = (await db.execute(
        select(ChatMessage.session_id, ChatMessage.content)
        .where(ChatMessage.session_id.in_(ids))
        .order_by(ChatMessage.session_id, desc(ChatMessage.id))
    )).all()
    last_by_session: dict[int, str] = {}
    for sid, content in last_rows:
        if sid not in last_by_session and content:
            last_by_session[sid] = content

    count_rows = (await db.execute(
        select(ChatMessage.session_id, func.count())
        .where(ChatMessage.session_id.in_(ids))
        .group_by(ChatMessage.session_id)
    )).all()
    count_by_session = {sid: c for sid, c in count_rows}

    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
            "last_message": (last_by_session.get(s.id) or "")[:80],
            "message_count": count_by_session.get(s.id, 0),
        }
        for s in sessions
    ]


async def get_session(db: AsyncSession, session_id: int, user_id: int) -> ChatSession | None:
    return (await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )).scalar_one_or_none()


async def delete_session(db: AsyncSession, session: ChatSession) -> None:
    # 先删消息（无外键级联）
    await db.execute(
        ChatMessage.__table__.delete().where(ChatMessage.session_id == session.id)
    )
    await db.delete(session)
    await db.flush()


async def add_message(
    db: AsyncSession,
    session_id: int,
    role: str,
    content: str,
    meta: dict | None = None,
) -> ChatMessage:
    msg = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        meta=meta,
    )
    db.add(msg)
    # 更新会话时间戳 & 首条消息生成标题
    session = (await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )).scalar_one_or_none()
    if session is not None:
        if session.title == "新对话" and role == "user" and content.strip():
            session.title = content.strip()[:30]
    await db.flush()
    return msg


async def list_messages(db: AsyncSession, session_id: int) -> list[ChatMessage]:
    return list((await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.asc())
    )).scalars().all())


async def history_prompt(db: AsyncSession, session_id: int) -> str:
    """把会话历史拼成字符串 prompt（GLM 走字符串 prompt 已验证可用）。"""
    msgs = await list_messages(db, session_id)
    lines = []
    for m in msgs:
        speaker = "用户" if m.role == "user" else "NEXA"
        lines.append(f"{speaker}: {m.content}")
    return "\n".join(lines)
