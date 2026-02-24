from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.orm.site import Site
from app.models.orm.user import User

router = APIRouter()


class SiteCreate(BaseModel):
    name: str
    type: str
    capacity: int = 0
    address: str | None = None
    operating_hours: dict | None = None
    rules: dict | None = None
    is_active: bool = True


class SiteUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    capacity: int | None = None
    address: str | None = None
    operating_hours: dict | None = None
    rules: dict | None = None
    is_active: bool | None = None


def _site_to_dict(site: Site) -> dict:
    return {
        "id": str(site.id),
        "name": site.name,
        "type": site.type,
        "capacity": site.capacity,
        "address": site.address,
        "operating_hours": site.operating_hours,
        "rules": site.rules,
        "is_active": site.is_active,
        "created_at": site.created_at.isoformat() if site.created_at else None,
        "updated_at": site.updated_at.isoformat() if site.updated_at else None,
    }


@router.get("")
async def list_sites(
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all sites. All authenticated users can read."""
    query = select(Site)
    count_query = select(func.count(Site.id))

    if is_active is not None:
        query = query.where(Site.is_active == is_active)
        count_query = count_query.where(Site.is_active == is_active)

    # Non-ADM/OPS users only see their assigned sites
    if current_user.role not in ("ADM", "OPS") and current_user.site_ids:
        query = query.where(Site.id.in_(current_user.site_ids))
        count_query = count_query.where(Site.id.in_(current_user.site_ids))

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Site.name).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    sites = result.scalars().all()

    return {
        "success": True,
        "data": [_site_to_dict(s) for s in sites],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/{site_id}")
async def get_site(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get site detail."""
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Site not found"}}

    # Access control: non-ADM/OPS users can only view their own sites
    if current_user.role not in ("ADM", "OPS"):
        if current_user.site_ids and site_id not in current_user.site_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this site")

    return {"success": True, "data": _site_to_dict(site)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_site(
    body: SiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("ADM"),
):
    """Create a new site. ADM only."""
    site = Site(
        name=body.name,
        type=body.type,
        capacity=body.capacity,
        address=body.address,
        operating_hours=body.operating_hours or {},
        rules=body.rules or {},
        is_active=body.is_active,
    )
    db.add(site)
    await db.flush()
    return {"success": True, "data": _site_to_dict(site)}


@router.patch("/{site_id}")
async def update_site(
    site_id: UUID,
    body: SiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("ADM"),
):
    """Update site. ADM only."""
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Site not found"}}

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(site, field, value)

    await db.flush()
    return {"success": True, "data": _site_to_dict(site)}


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("ADM"),
):
    """Soft-delete site (is_active=False). ADM only."""
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    site.is_active = False
    await db.flush()
