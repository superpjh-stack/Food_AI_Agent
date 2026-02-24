from uuid import UUID

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str  # NUT, KIT, QLT, OPS, ADM
    site_ids: list[UUID] = []


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role: str
    site_ids: list[UUID]
    is_active: bool

    model_config = {"from_attributes": True}
