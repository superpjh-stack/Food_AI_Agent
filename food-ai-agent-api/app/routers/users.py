from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.password import hash_password
from app.db.session import get_db
from app.models.orm.user import User

router = APIRouter()

VALID_ROLES = {"NUT", "KIT", "QLT", "OPS", "ADM"}


# ─── Pydantic schemas ────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str
    site_ids: list[UUID] = []
    is_active: bool = True


class UserRoleUpdate(BaseModel):
    role: str


class UserActiveUpdate(BaseModel):
    is_active: bool


class UserUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    site_ids: list[UUID] | None = None
    is_active: bool | None = None


# ─── Serializer ───────────────────────────────────────────────────────────────

def _user_to_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "site_ids": [str(s) for s in (user.site_ids or [])],
        "is_active": user.is_active,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("")
async def list_users(
    role: str | None = Query(None, description="Filter by role (NUT, KIT, QLT, OPS, ADM)"),
    site_id: UUID | None = Query(None, description="Filter users belonging to a site"),
    is_active: bool | None = Query(True),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "ADM"),
):
    """List users. OPS or ADM only."""
    query = select(User)
    count_query = select(func.count(User.id))

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)

    if site_id:
        query = query.where(User.site_ids.any(site_id))
        count_query = count_query.where(User.site_ids.any(site_id))

    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(User.name).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    users = result.scalars().all()

    return {
        "success": True,
        "data": [_user_to_dict(u) for u in users],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "ADM"),
):
    """Get user detail. OPS or ADM only."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "User not found"}}
    return {"success": True, "data": _user_to_dict(user)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("ADM"),
):
    """Create user (admin operation). ADM only."""
    if body.role not in VALID_ROLES:
        return {
            "success": False,
            "error": {"code": "INVALID_ROLE", "message": f"Role must be one of {VALID_ROLES}"},
        }

    # Check duplicate email
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        return {"success": False, "error": {"code": "EMAIL_CONFLICT", "message": "Email already in use"}}

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        name=body.name,
        role=body.role,
        site_ids=body.site_ids,
        is_active=body.is_active,
    )
    db.add(user)
    await db.flush()
    return {"success": True, "data": _user_to_dict(user)}


@router.patch("/{user_id}/role")
async def update_user_role(
    user_id: UUID,
    body: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("ADM"),
):
    """Update user role. ADM only."""
    if body.role not in VALID_ROLES:
        return {
            "success": False,
            "error": {"code": "INVALID_ROLE", "message": f"Role must be one of {VALID_ROLES}"},
        }

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "User not found"}}

    user.role = body.role
    await db.flush()
    return {"success": True, "data": _user_to_dict(user)}


@router.patch("/{user_id}/active")
async def update_user_active(
    user_id: UUID,
    body: UserActiveUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("ADM"),
):
    """Activate or deactivate user. ADM only."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "User not found"}}

    user.is_active = body.is_active
    await db.flush()
    return {"success": True, "data": _user_to_dict(user)}


@router.patch("/{user_id}")
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("ADM"),
):
    """Update user profile. ADM only."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "User not found"}}

    updates = body.model_dump(exclude_unset=True)
    if "role" in updates and updates["role"] not in VALID_ROLES:
        return {
            "success": False,
            "error": {"code": "INVALID_ROLE", "message": f"Role must be one of {VALID_ROLES}"},
        }

    for field, value in updates.items():
        setattr(user, field, value)

    await db.flush()
    return {"success": True, "data": _user_to_dict(user)}
