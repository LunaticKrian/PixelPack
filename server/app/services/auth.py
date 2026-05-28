import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.schemas.auth import ProfileUpdate, UserCreate, UserUpdate
from app.utils.security import get_password_hash, verify_password


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, user_data: UserCreate) -> User:
    existing = await get_user_by_username(db, user_data.username)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )

    if user_data.email is not None:
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> User | None:
    user = await get_user_by_username(db, username)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def update_user(
    db: AsyncSession,
    user: User,
    update_data: UserUpdate,
) -> User:
    if update_data.email is not None:
        result = await db.execute(
            select(User).where(User.email == update_data.email, User.id != user.id),
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )
        user.email = update_data.email

    if update_data.avatar_url is not None:
        user.avatar_url = update_data.avatar_url

    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def change_password(
    db: AsyncSession,
    user: User,
    old_password: str,
    new_password: str,
) -> bool:
    if not verify_password(old_password, user.password_hash):
        return False
    user.password_hash = get_password_hash(new_password)
    db.add(user)
    await db.flush()
    return True


async def update_profile(
    db: AsyncSession,
    user: User,
    data: ProfileUpdate,
) -> User:
    if data.character_name is not None:
        user.character_name = data.character_name
    if data.character_class is not None:
        user.character_class = data.character_class
    if data.birthday is not None:
        user.birthday = data.birthday
    user.profile_completed = True
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def upload_portrait(
    db: AsyncSession,
    user: User,
    file: UploadFile,
) -> str:
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "portrait.png")[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    url = f"/uploads/{filename}"
    user.portrait_url = url
    db.add(user)
    await db.flush()
    return url
