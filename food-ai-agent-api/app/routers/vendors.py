"""Vendors API router (MVP 2 — Purchase)."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.orm.item import Item
from app.models.orm.purchase import Vendor, VendorPrice
from app.models.orm.user import User
from app.models.schemas.purchase import (
    VendorCreate, VendorUpdate, VendorRead,
    VendorPriceCreate, VendorPriceRead,
)

router = APIRouter()


@router.get("")
async def list_vendors(
    category: str | None = Query(None),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "OPS", "ADM"),
):
    """List vendors with optional category and active filters."""
    query = select(Vendor)
    count_query = select(func.count(Vendor.id))

    if is_active is not None:
        query = query.where(Vendor.is_active == is_active)
        count_query = count_query.where(Vendor.is_active == is_active)

    # Filter by category (check if category is in the ARRAY)
    if category:
        query = query.where(Vendor.categories.contains([category]))
        count_query = count_query.where(Vendor.categories.contains([category]))

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Vendor.name).offset((page - 1) * per_page).limit(per_page)
    vendors = (await db.execute(query)).scalars().all()

    return {
        "success": True,
        "data": [_vendor_to_dict(v) for v in vendors],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.post("")
async def create_vendor(
    body: VendorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("ADM"),
):
    """Register a new vendor."""
    vendor = Vendor(
        name=body.name,
        business_no=body.business_no,
        contact=body.contact,
        categories=body.categories,
        lead_days=body.lead_days,
        rating=body.rating,
        notes=body.notes,
        is_active=True,
    )
    db.add(vendor)
    await db.flush()
    return {"success": True, "data": _vendor_to_dict(vendor)}


@router.get("/{vendor_id}")
async def get_vendor(
    vendor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "OPS", "ADM"),
):
    """Get vendor detail."""
    vendor = (await db.execute(select(Vendor).where(Vendor.id == vendor_id))).scalar_one_or_none()
    if not vendor:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Vendor not found"}}
    return {"success": True, "data": _vendor_to_dict(vendor)}


@router.put("/{vendor_id}")
async def update_vendor(
    vendor_id: UUID,
    body: VendorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("ADM"),
):
    """Update vendor information."""
    vendor = (await db.execute(select(Vendor).where(Vendor.id == vendor_id))).scalar_one_or_none()
    if not vendor:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Vendor not found"}}

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)

    await db.flush()
    return {"success": True, "data": _vendor_to_dict(vendor)}


@router.delete("/{vendor_id}")
async def deactivate_vendor(
    vendor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("ADM"),
):
    """Soft-delete (deactivate) a vendor."""
    vendor = (await db.execute(select(Vendor).where(Vendor.id == vendor_id))).scalar_one_or_none()
    if not vendor:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Vendor not found"}}

    vendor.is_active = False
    await db.flush()
    return {"success": True, "data": {"id": str(vendor_id), "is_active": False}}


@router.get("/{vendor_id}/prices")
async def get_vendor_prices(
    vendor_id: UUID,
    item_id: UUID | None = Query(None),
    is_current: bool | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "OPS"),
):
    """Get price history for a vendor."""
    query = select(VendorPrice).where(VendorPrice.vendor_id == vendor_id)
    count_query = select(func.count(VendorPrice.id)).where(VendorPrice.vendor_id == vendor_id)

    if item_id:
        query = query.where(VendorPrice.item_id == item_id)
        count_query = count_query.where(VendorPrice.item_id == item_id)
    if is_current is not None:
        query = query.where(VendorPrice.is_current == is_current)
        count_query = count_query.where(VendorPrice.is_current == is_current)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(VendorPrice.effective_from.desc()).offset((page - 1) * per_page).limit(per_page)
    prices = (await db.execute(query)).scalars().all()

    return {
        "success": True,
        "data": [_vp_to_dict(vp) for vp in prices],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.post("/{vendor_id}/prices")
async def upsert_vendor_price(
    vendor_id: UUID,
    body: VendorPriceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "ADM"),
):
    """Register or update a vendor price for an item. Marks previous price as not current."""
    # Expire existing current price for this vendor+item+site combination
    existing_query = select(VendorPrice).where(
        VendorPrice.vendor_id == vendor_id,
        VendorPrice.item_id == body.item_id,
        VendorPrice.is_current == True,
    )
    if body.site_id:
        existing_query = existing_query.where(VendorPrice.site_id == body.site_id)

    existing_prices = (await db.execute(existing_query)).scalars().all()
    for ep in existing_prices:
        ep.is_current = False
        ep.effective_to = body.effective_from

    # Create new price record
    vp = VendorPrice(
        vendor_id=vendor_id,
        item_id=body.item_id,
        site_id=body.site_id,
        unit_price=body.unit_price,
        unit=body.unit,
        currency=body.currency,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
        is_current=True,
        source=body.source,
    )
    db.add(vp)
    await db.flush()
    return {"success": True, "data": _vp_to_dict(vp)}


@router.get("/items/{item_id}/vendors")
async def get_item_vendors(
    item_id: UUID,
    site_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "NUT", "OPS"),
):
    """Get list of vendors supplying an item with current prices. Returns best price first."""
    query = select(VendorPrice).where(
        VendorPrice.item_id == item_id,
        VendorPrice.is_current == True,
    )
    if site_id:
        query = query.where(
            (VendorPrice.site_id == site_id) | (VendorPrice.site_id.is_(None))
        )
    prices = (await db.execute(query.order_by(VendorPrice.unit_price))).scalars().all()

    if not prices:
        return {"success": True, "data": [], "meta": {"item_id": str(item_id), "best_price": None}}

    vendor_ids = [vp.vendor_id for vp in prices]
    vendors = (await db.execute(
        select(Vendor).where(Vendor.id.in_(vendor_ids), Vendor.is_active == True)
    )).scalars().all()
    vendors_map = {v.id: v for v in vendors}

    result = []
    for vp in prices:
        vendor = vendors_map.get(vp.vendor_id)
        if not vendor:
            continue
        result.append({
            "vendor_id": str(vendor.id),
            "vendor_name": vendor.name,
            "unit_price": float(vp.unit_price),
            "unit": vp.unit,
            "currency": vp.currency,
            "lead_days": vendor.lead_days,
            "rating": float(vendor.rating),
            "effective_from": str(vp.effective_from),
        })

    best_price = result[0]["unit_price"] if result else None

    return {
        "success": True,
        "data": result,
        "meta": {
            "item_id": str(item_id),
            "vendor_count": len(result),
            "best_price": best_price,
        },
    }


def _vendor_to_dict(vendor: Vendor) -> dict:
    return {
        "id": str(vendor.id),
        "name": vendor.name,
        "business_no": vendor.business_no,
        "contact": vendor.contact or {},
        "categories": vendor.categories or [],
        "lead_days": vendor.lead_days,
        "rating": float(vendor.rating) if vendor.rating else 0.0,
        "is_active": vendor.is_active,
        "notes": vendor.notes,
        "created_at": vendor.created_at.isoformat() if vendor.created_at else None,
        "updated_at": vendor.updated_at.isoformat() if vendor.updated_at else None,
    }


def _vp_to_dict(vp: VendorPrice) -> dict:
    return {
        "id": str(vp.id),
        "vendor_id": str(vp.vendor_id),
        "item_id": str(vp.item_id),
        "site_id": str(vp.site_id) if vp.site_id else None,
        "unit_price": float(vp.unit_price),
        "unit": vp.unit,
        "currency": vp.currency,
        "effective_from": str(vp.effective_from),
        "effective_to": str(vp.effective_to) if vp.effective_to else None,
        "is_current": vp.is_current,
        "source": vp.source,
        "created_at": vp.created_at.isoformat() if vp.created_at else None,
    }
