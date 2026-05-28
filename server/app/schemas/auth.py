from datetime import date as date_type, datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    email: EmailStr | None = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    avatar_url: str | None
    character_name: str | None
    portrait_url: str | None
    character_class: str | None
    birthday: date_type | None
    profile_completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=100)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    avatar_url: str | None = None


class ProfileUpdate(BaseModel):
    character_name: str | None = Field(default=None, min_length=1, max_length=50)
    character_class: str | None = Field(default=None, max_length=100)
    birthday: date_type | None = None


class PortraitUploadResponse(BaseModel):
    url: str
