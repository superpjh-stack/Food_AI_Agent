"""BOMs API router (MVP 2 — Purchase)."""
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.tools.purchase_tools import calculate_bom
from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.orm.purchase import Bom, BomItem, VendorPrice
from app.models.orm.user import User
from app.models.schemas.purchase import BomGenerateRequest, BomUpdateRequest

router = APIRouter()


@router.post("/generate")
async def generate_bom(
    body: BomGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "OPS", "PUR"),
):
    """Generate BOM from confirmed menu plan via calculate_bom tool."""
    result = await calculate_bom(
        db=db,
        menu_plan_id=str(body.menu_plan_id),
        headcount=body.headcount,
        apply_inventory=body.apply_inventory,
        generated_by=current_user.id,
    )
    if "error" in result:
        return {"success": False, "error": {"code": "BOM_GENERATION_FAILED", "message": result["error"]}}
    return {"success": True, "data": result}


@router.get("")
async def list_boms(
    site_id: UUID | None = Query(None),
    status: str | None = Query(None),
    period_start: str | None = Query(None),
    period_end: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "OPS"),
):
    """List BOMs with optional filters."""
    query = select(Bom)
    count_query = select(func.count(Bom.id))

    if site_id:
        query = query.where(Bom.site_id == site_id)
        count_query = count_query.where(Bom.site_id == site_id)
    if status:
        query = query.where(Bom.status == status)
        count_query = count_query.where(Bom.status == status)
    if period_start:
        from datetime import date
        query = query.where(Bom.period_start >= date.fromisoformat(period_start))
        count_query = count_query.where(Bom.period_start >= date.fromisoformat(period_start))
    if period_end:
        from datetime import date
        query = query.where(Bom.period_end <= date.fromisoformat(period_end))
        count_query = count_query.where(Bom.period_end <= date.fromisoformat(period_end))

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Bom.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    boms = (await db.execute(query)).scalars().all()

    return {
        "success": True,
        "data": [_bom_to_dict(b) for b in boms],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/{bom_id}")
async def get_bom(
    bom_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "NUT", "OPS"),
):
    """Get BOM detail with all items."""
    result = await db.execute(
        select(Bom)
        .options(selectinload(Bom.items))
        .where(Bom.id == bom_id)
    )
    bom = result.scalar_one_or_none()
    if not bom:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "BOM not found"}}

    data = _bom_to_dict(bom)
    data["items"] = [_bom_item_to_dict(bi) for bi in bom.items]
    return {"success": True, "data": data}


@router.put("/{bom_id}")
async def update_bom(
    bom_id: UUID,
    body: BomUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR"),
):
    """Manually update BOM quantities."""
    bom = (await db.execute(
        select(Bom).options(selectinload(Bom.items)).where(Bom.id == bom_id)
    )).scalar_one_or_none()
    if not bom:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "BOM not found"}}
    if bom.status not in ("draft", "ready"):
        return {"success": False, "error": {"code": "INVALID_STATUS", "message": f"Cannot edit BOM in '{bom.status}' status"}}

    if body.headcount is not None:
        bom.headcount = body.headcount

    if body.items:
        bom_items_map = {str(bi.id): bi for bi in bom.items}
        from decimal import Decimal
        total_cost = 0.0
        for item_update in body.items:
            bi_id = item_update.get("id")
            if bi_id and bi_id in bom_items_map:
                bi = bom_items_map[bi_id]
                if "order_quantity" in item_update:
                    bi.order_quantity = Decimal(str(item_update["order_quantity"]))
                if "unit_price" in item_update:
                    bi.unit_price = Decimal(str(item_update["unit_price"]))
                if bi.order_quantity and bi.unit_price:
                    bi.subtotal = bi.order_quantity * bi.unit_price
                    total_cost += float(bi.subtotal)
        bom.total_cost = Decimal(str(round(total_cost, 2)))

    await db.flush()
    data = _bom_to_dict(bom)
    data["items"] = [_bom_item_to_dict(bi) for bi in bom.items]
    return {"success": True, "data": data}


@router.get("/{bom_id}/cost-analysis")
async def get_bom_cost_analysis(
    bom_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "OPS"),
):
    """Get cost analysis for BOM: per-vendor breakdown and price comparison."""
    result = await db.execute(
        select(Bom).options(selectinload(Bom.items)).where(Bom.id == bom_id)
    )
    bom = result.scalar_one_or_none()
    if not bom:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "BOM not found"}}

    # Group by preferred vendor
    vendor_breakdown: dict[str, dict] = {}
    unassigned_cost = 0.0
    total_cost = 0.0

    for bi in bom.items:
        subtotal = float(bi.subtotal) if bi.subtotal else 0.0
        total_cost += subtotal

        if bi.preferred_vendor_id:
            vid = str(bi.preferred_vendor_id)
            if vid not in vendor_breakdown:
                vendor_breakdown[vid] = {"vendor_id": vid, "items": [], "subtotal": 0.0}
            vendor_breakdown[vid]["items"].append({
                "item_id": str(bi.item_id),
                "item_name": bi.item_name,
                "order_quantity": float(bi.order_quantity) if bi.order_quantity else 0,
                "unit": bi.unit,
                "unit_price": float(bi.unit_price) if bi.unit_price else 0,
                "subtotal": subtotal,
            })
            vendor_breakdown[vid]["subtotal"] += subtotal
        else:
            unassigned_cost += subtotal

    return {
        "success": True,
        "data": {
            "bom_id": str(bom_id),
            "headcount": bom.headcount,
            "total_cost": float(bom.total_cost),
            "cost_per_meal": float(bom.cost_per_meal) if bom.cost_per_meal else None,
            "vendor_breakdown": list(vendor_breakdown.values()),
            "unassigned_cost": unassigned_cost,
            "items_count": len(bom.items),
            "order_items_count": sum(1 for bi in bom.items if bi.order_quantity and bi.order_quantity > 0),
        },
    }


@router.post("/{bom_id}/apply-inventory")
async def apply_inventory_to_bom(
    bom_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR"),
):
    """Re-calculate order quantities by applying current inventory levels."""
    from app.models.orm.inventory import Inventory
    from decimal import Decimal

    result = await db.execute(
        select(Bom).options(selectinload(Bom.items)).where(Bom.id == bom_id)
    )
    bom = result.scalar_one_or_none()
    if not bom:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "BOM not found"}}

    item_ids = [bi.item_id for bi in bom.items]
    inv_rows = (await db.execute(
        select(Inventory).where(
            Inventory.site_id == bom.site_id,
            Inventory.item_id.in_(item_ids),
        )
    )).scalars().all()
    inv_map = {str(inv.item_id): float(inv.quantity) for inv in inv_rows}

    updated_count = 0
    total_cost = 0.0
    for bi in bom.items:
        iid = str(bi.item_id)
        avail = min(inv_map.get(iid, 0.0), float(bi.quantity))
        order_qty = max(0.0, float(bi.quantity) - avail)
        bi.inventory_available = Decimal(str(round(avail, 3)))
        bi.order_quantity = Decimal(str(round(order_qty, 3)))
        if bi.unit_price:
            bi.subtotal = bi.order_quantity * bi.unit_price
            total_cost += float(bi.subtotal)
        updated_count += 1

    bom.total_cost = Decimal(str(round(total_cost, 2)))
    if bom.headcount > 0:
        bom.cost_per_meal = Decimal(str(round(total_cost / bom.headcount, 2)))
    await db.flush()

    return {
        "success": True,
        "data": {
            "bom_id": str(bom_id),
            "updated_items": updated_count,
            "total_cost": round(total_cost, 2),
            "message": "재고 차감이 반영되었습니다.",
        },
    }


def _bom_to_dict(bom: Bom) -> dict:
    return {
        "id": str(bom.id),
        "menu_plan_id": str(bom.menu_plan_id),
        "site_id": str(bom.site_id),
        "period_start": str(bom.period_start),
        "period_end": str(bom.period_end),
        "headcount": bom.headcount,
        "status": bom.status,
        "total_cost": float(bom.total_cost) if bom.total_cost else 0.0,
        "cost_per_meal": float(bom.cost_per_meal) if bom.cost_per_meal else None,
        "ai_summary": bom.ai_summary,
        "generated_by": str(bom.generated_by),
        "created_at": bom.created_at.isoformat() if bom.created_at else None,
        "updated_at": bom.updated_at.isoformat() if bom.updated_at else None,
    }


def _bom_item_to_dict(bi: BomItem) -> dict:
    return {
        "id": str(bi.id),
        "bom_id": str(bi.bom_id),
        "item_id": str(bi.item_id),
        "item_name": bi.item_name,
        "quantity": float(bi.quantity),
        "unit": bi.unit,
        "unit_price": float(bi.unit_price) if bi.unit_price else None,
        "subtotal": float(bi.subtotal) if bi.subtotal else None,
        "inventory_available": float(bi.inventory_available) if bi.inventory_available else 0.0,
        "order_quantity": float(bi.order_quantity) if bi.order_quantity else 0.0,
        "preferred_vendor_id": str(bi.preferred_vendor_id) if bi.preferred_vendor_id else None,
        "source_recipes": bi.source_recipes or [],
        "notes": bi.notes,
    }
