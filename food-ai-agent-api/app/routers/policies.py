from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.orm.policy import NutritionPolicy, AllergenPolicy
from app.models.orm.user import User

router = APIRouter()


# ─── Pydantic schemas ────────────────────────────────────────────────────────

class NutritionPolicyCreate(BaseModel):
    site_id: UUID | None = None
    name: str
    meal_type: str | None = None  # lunch, dinner, all
    criteria: dict  # {"kcal":{"min":500,"max":800},"sodium":{"max":2000}}
    is_active: bool = True


class NutritionPolicyUpdate(BaseModel):
    name: str | None = None
    meal_type: str | None = None
    criteria: dict | None = None
    is_active: bool | None = None


class AllergenPolicyCreate(BaseModel):
    site_id: UUID | None = None
    name: str
    legal_allergens: list[str] | None = None
    custom_allergens: list[str] = []
    display_format: str = "number"  # number, text, icon
    is_active: bool = True


class AllergenPolicyUpdate(BaseModel):
    name: str | None = None
    legal_allergens: list[str] | None = None
    custom_allergens: list[str] | None = None
    display_format: str | None = None
    is_active: bool | None = None


# ─── Serializers ─────────────────────────────────────────────────────────────

def _nutrition_to_dict(p: NutritionPolicy) -> dict:
    return {
        "id": str(p.id),
        "site_id": str(p.site_id) if p.site_id else None,
        "name": p.name,
        "meal_type": p.meal_type,
        "criteria": p.criteria,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _allergen_to_dict(p: AllergenPolicy) -> dict:
    return {
        "id": str(p.id),
        "site_id": str(p.site_id) if p.site_id else None,
        "name": p.name,
        "legal_allergens": p.legal_allergens or [],
        "custom_allergens": p.custom_allergens or [],
        "display_format": p.display_format,
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


# ─── Nutrition Policy endpoints ───────────────────────────────────────────────

@router.get("/nutrition")
async def list_nutrition_policies(
    site_id: UUID | None = Query(None),
    is_active: bool | None = Query(True),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "OPS", "ADM"),
):
    """List nutrition policies. NUT, OPS, ADM roles."""
    query = select(NutritionPolicy)
    count_query = select(func.count(NutritionPolicy.id))

    if site_id:
        query = query.where(NutritionPolicy.site_id == site_id)
        count_query = count_query.where(NutritionPolicy.site_id == site_id)

    if is_active is not None:
        query = query.where(NutritionPolicy.is_active == is_active)
        count_query = count_query.where(NutritionPolicy.is_active == is_active)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(NutritionPolicy.name).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    policies = result.scalars().all()

    return {
        "success": True,
        "data": [_nutrition_to_dict(p) for p in policies],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/nutrition/{policy_id}")
async def get_nutrition_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "OPS", "ADM"),
):
    """Get nutrition policy detail."""
    result = await db.execute(select(NutritionPolicy).where(NutritionPolicy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Nutrition policy not found"}}
    return {"success": True, "data": _nutrition_to_dict(policy)}


@router.post("/nutrition", status_code=status.HTTP_201_CREATED)
async def create_nutrition_policy(
    body: NutritionPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "ADM"),
):
    """Create nutrition policy. OPS or ADM only."""
    policy = NutritionPolicy(
        site_id=body.site_id,
        name=body.name,
        meal_type=body.meal_type,
        criteria=body.criteria,
        is_active=body.is_active,
    )
    db.add(policy)
    await db.flush()
    return {"success": True, "data": _nutrition_to_dict(policy)}


@router.patch("/nutrition/{policy_id}")
async def update_nutrition_policy(
    policy_id: UUID,
    body: NutritionPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "ADM"),
):
    """Update nutrition policy. OPS or ADM only."""
    result = await db.execute(select(NutritionPolicy).where(NutritionPolicy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Nutrition policy not found"}}

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)

    await db.flush()
    return {"success": True, "data": _nutrition_to_dict(policy)}


# ─── Allergen Policy endpoints ────────────────────────────────────────────────

@router.get("/allergen")
async def list_allergen_policies(
    site_id: UUID | None = Query(None),
    is_active: bool | None = Query(True),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "OPS", "ADM"),
):
    """List allergen policies. NUT, OPS, ADM roles."""
    query = select(AllergenPolicy)
    count_query = select(func.count(AllergenPolicy.id))

    if site_id:
        query = query.where(AllergenPolicy.site_id == site_id)
        count_query = count_query.where(AllergenPolicy.site_id == site_id)

    if is_active is not None:
        query = query.where(AllergenPolicy.is_active == is_active)
        count_query = count_query.where(AllergenPolicy.is_active == is_active)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(AllergenPolicy.name).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    policies = result.scalars().all()

    return {
        "success": True,
        "data": [_allergen_to_dict(p) for p in policies],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/allergen/{policy_id}")
async def get_allergen_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "OPS", "ADM"),
):
    """Get allergen policy detail."""
    result = await db.execute(select(AllergenPolicy).where(AllergenPolicy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Allergen policy not found"}}
    return {"success": True, "data": _allergen_to_dict(policy)}


@router.post("/allergen", status_code=status.HTTP_201_CREATED)
async def create_allergen_policy(
    body: AllergenPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "ADM"),
):
    """Create allergen policy. OPS or ADM only."""
    policy = AllergenPolicy(
        site_id=body.site_id,
        name=body.name,
        custom_allergens=body.custom_allergens,
        display_format=body.display_format,
        is_active=body.is_active,
    )
    if body.legal_allergens is not None:
        policy.legal_allergens = body.legal_allergens
    db.add(policy)
    await db.flush()
    return {"success": True, "data": _allergen_to_dict(policy)}


@router.patch("/allergen/{policy_id}")
async def update_allergen_policy(
    policy_id: UUID,
    body: AllergenPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "ADM"),
):
    """Update allergen policy. OPS or ADM only."""
    result = await db.execute(select(AllergenPolicy).where(AllergenPolicy.id == policy_id))
    policy = result.scalar_one_or_none()
    if not policy:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Allergen policy not found"}}

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)

    await db.flush()
    return {"success": True, "data": _allergen_to_dict(policy)}
