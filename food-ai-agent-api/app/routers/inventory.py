"""Inventory API router (MVP 2)."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.orm.inventory import Inventory, InventoryLot
from app.models.orm.item import Item
from app.models.orm.user import User
from app.models.schemas.inventory import InventoryAdjustRequest, InventoryReceiveRequest

router = APIRouter()


@router.get("")
async def list_inventory(
    site_id: UUID | None = Query(None),
    category: str | None = Query(None),
    low_stock_only: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "KIT", "OPS"),
):
    """List current inventory levels for a site."""
    query = select(Inventory)
    count_query = select(func.count(Inventory.id))

    if site_id:
        query = query.where(Inventory.site_id == site_id)
        count_query = count_query.where(Inventory.site_id == site_id)
    if low_stock_only:
        query = query.where(Inventory.quantity < Inventory.min_qty)
        count_query = count_query.where(Inventory.quantity < Inventory.min_qty)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Inventory.last_updated.desc()).offset((page - 1) * per_page).limit(per_page)
    inv_rows = (await db.execute(query)).scalars().all()

    # Load item details
    item_ids = [inv.item_id for inv in inv_rows]
    items_list = (await db.execute(
        select(Item).where(Item.id.in_(item_ids))
    )).scalars().all() if item_ids else []
    items_map = {str(it.id): it for it in items_list}

    # Filter by category if needed (post-fetch filter)
    result = []
    for inv in inv_rows:
        item = items_map.get(str(inv.item_id))
        if category and (not item or item.category != category):
            continue
        result.append(_inv_to_dict(inv, item))

    return {
        "success": True,
        "data": result,
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.put("/{item_id}")
async def adjust_inventory(
    item_id: UUID,
    site_id: UUID = Query(...),
    body: InventoryAdjustRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "KIT"),
):
    """Manual inventory adjustment (재고실사). Updates current quantity."""
    inv = (await db.execute(
        select(Inventory).where(
            Inventory.site_id == site_id,
            Inventory.item_id == item_id,
        )
    )).scalar_one_or_none()

    if inv:
        old_qty = float(inv.quantity)
        inv.quantity = body.quantity
        inv.last_updated = datetime.utcnow()
    else:
        # Get item unit
        item = (await db.execute(select(Item).where(Item.id == item_id))).scalar_one_or_none()
        if not item:
            return {"success": False, "error": {"code": "NOT_FOUND", "message": "Item not found"}}
        old_qty = 0.0
        inv = Inventory(
            site_id=site_id,
            item_id=item_id,
            quantity=body.quantity,
            unit=item.unit,
            last_updated=datetime.utcnow(),
        )
        db.add(inv)

    await db.flush()

    return {
        "success": True,
        "data": {
            "site_id": str(site_id),
            "item_id": str(item_id),
            "old_quantity": old_qty,
            "new_quantity": float(body.quantity),
            "reason": body.reason,
        },
    }


@router.get("/lots")
async def list_lots(
    site_id: UUID | None = Query(None),
    item_id: UUID | None = Query(None),
    status: str | None = Query(None),
    expiry_before: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "KIT", "QLT"),
):
    """List inventory lots ordered by expiry date (soonest first)."""
    query = select(InventoryLot)
    count_query = select(func.count(InventoryLot.id))

    if site_id:
        query = query.where(InventoryLot.site_id == site_id)
        count_query = count_query.where(InventoryLot.site_id == site_id)
    if item_id:
        query = query.where(InventoryLot.item_id == item_id)
        count_query = count_query.where(InventoryLot.item_id == item_id)
    if status:
        query = query.where(InventoryLot.status == status)
        count_query = count_query.where(InventoryLot.status == status)
    if expiry_before:
        query = query.where(InventoryLot.expiry_date <= date.fromisoformat(expiry_before))
        count_query = count_query.where(InventoryLot.expiry_date <= date.fromisoformat(expiry_before))

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(InventoryLot.expiry_date.asc().nulls_last()).offset((page - 1) * per_page).limit(per_page)
    lots = (await db.execute(query)).scalars().all()

    # Enrich with item names
    item_ids = list({lot.item_id for lot in lots})
    items_map = {}
    if item_ids:
        items_list = (await db.execute(select(Item).where(Item.id.in_(item_ids)))).scalars().all()
        items_map = {str(it.id): it.name for it in items_list}

    return {
        "success": True,
        "data": [_lot_to_dict(lot, items_map.get(str(lot.item_id))) for lot in lots],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/lots/{lot_id}")
async def get_lot(
    lot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "KIT", "QLT"),
):
    """Get lot detail with full usage history."""
    lot = (await db.execute(select(InventoryLot).where(InventoryLot.id == lot_id))).scalar_one_or_none()
    if not lot:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Lot not found"}}

    item = (await db.execute(select(Item).where(Item.id == lot.item_id))).scalar_one_or_none()

    return {"success": True, "data": _lot_to_dict(lot, item.name if item else None)}


@router.post("/receive")
async def receive_inventory(
    body: InventoryReceiveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "KIT"),
):
    """Process incoming delivery — creates lots and updates inventory. SAFE-PUR-004."""
    received_at = body.received_at or datetime.utcnow()
    lots_created = []

    for receive_item in body.items:
        # Create lot record
        lot = InventoryLot(
            site_id=body.site_id,
            item_id=receive_item.item_id,
            vendor_id=body.vendor_id,
            po_id=body.po_id,
            lot_number=receive_item.lot_number,
            quantity=receive_item.received_qty,
            unit=receive_item.unit,
            unit_cost=receive_item.unit_cost,
            received_at=received_at,
            expiry_date=receive_item.expiry_date,
            storage_temp=receive_item.storage_temp,
            status="active",
            inspect_result={
                "passed": receive_item.inspect_passed,
                "note": receive_item.inspect_note or "",
                "inspector": str(current_user.id),
            },
        )
        db.add(lot)
        await db.flush()
        lots_created.append(str(lot.id))

        # Update inventory quantity
        inv = (await db.execute(
            select(Inventory).where(
                Inventory.site_id == body.site_id,
                Inventory.item_id == receive_item.item_id,
            )
        )).scalar_one_or_none()

        if inv:
            inv.quantity = inv.quantity + receive_item.received_qty
            inv.last_updated = received_at
        else:
            inv = Inventory(
                site_id=body.site_id,
                item_id=receive_item.item_id,
                quantity=receive_item.received_qty,
                unit=receive_item.unit,
                last_updated=received_at,
            )
            db.add(inv)

    await db.flush()

    return {
        "success": True,
        "data": {
            "site_id": str(body.site_id),
            "items_received": len(body.items),
            "lots_created": lots_created,
            "received_at": received_at.isoformat(),
            "message": "입고 기록 완료. 로트 추적 가능합니다. (SAFE-PUR-004)",
        },
    }


@router.get("/expiry-alert")
async def get_expiry_alerts(
    site_id: UUID | None = Query(None),
    alert_days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "KIT", "OPS"),
):
    """Get items expiring within alert_days (D-3 and D-7 categories)."""
    today = date.today()
    alert_date = today + timedelta(days=alert_days)

    query = select(InventoryLot).where(
        InventoryLot.expiry_date <= alert_date,
        InventoryLot.expiry_date >= today,
        InventoryLot.status.in_(["active", "partially_used"]),
    ).order_by(InventoryLot.expiry_date)

    if site_id:
        query = query.where(InventoryLot.site_id == site_id)

    lots = (await db.execute(query)).scalars().all()

    item_ids = list({lot.item_id for lot in lots})
    items_map = {}
    if item_ids:
        items_list = (await db.execute(select(Item).where(Item.id.in_(item_ids)))).scalars().all()
        items_map = {str(it.id): it for it in items_list}

    critical = []  # D-3
    warning = []   # D-4 to D-7

    for lot in lots:
        days_left = (lot.expiry_date - today).days
        item = items_map.get(str(lot.item_id))
        entry = {
            "lot_id": str(lot.id),
            "item_id": str(lot.item_id),
            "item_name": item.name if item else str(lot.item_id),
            "item_category": item.category if item else None,
            "lot_number": lot.lot_number,
            "quantity": float(lot.quantity),
            "unit": lot.unit,
            "expiry_date": str(lot.expiry_date),
            "days_until_expiry": days_left,
            "storage_condition": item.storage_condition if item else None,
        }
        if days_left <= 3:
            critical.append(entry)
        else:
            warning.append(entry)

    return {
        "success": True,
        "data": {
            "critical": critical,   # D-3 이하
            "warning": warning,     # D-4 ~ D-7
            "total_alerts": len(lots),
            "critical_count": len(critical),
            "warning_count": len(warning),
            "alert_days": alert_days,
        },
    }


@router.post("/lots/{lot_id}/trace")
async def trace_lot(
    lot_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "QLT"),
):
    """Trace a lot — find which menus/sites this lot was used in. SAFE-PUR-004."""
    lot = (await db.execute(select(InventoryLot).where(InventoryLot.id == lot_id))).scalar_one_or_none()
    if not lot:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Lot not found"}}

    item = (await db.execute(select(Item).where(Item.id == lot.item_id))).scalar_one_or_none()

    used_qty = sum(float(u.get("used_qty", 0)) for u in (lot.used_in_menus or []))
    remaining = float(lot.quantity) - used_qty

    return {
        "success": True,
        "data": {
            "lot_id": str(lot.id),
            "lot_number": lot.lot_number,
            "item_id": str(lot.item_id),
            "item_name": item.name if item else str(lot.item_id),
            "received_at": lot.received_at.isoformat() if lot.received_at else None,
            "expiry_date": str(lot.expiry_date) if lot.expiry_date else None,
            "status": lot.status,
            "total_quantity": float(lot.quantity),
            "remaining_qty": remaining,
            "total_used_qty": used_qty,
            "used_in_menus": lot.used_in_menus or [],
            "vendor_id": str(lot.vendor_id) if lot.vendor_id else None,
            "po_id": str(lot.po_id) if lot.po_id else None,
            "inspect_result": lot.inspect_result or {},
            "trace_note": "로트 추적 결과 기록됨. (SAFE-PUR-004)",
        },
    }


def _inv_to_dict(inv: Inventory, item: Item | None) -> dict:
    return {
        "id": str(inv.id),
        "site_id": str(inv.site_id),
        "item_id": str(inv.item_id),
        "item_name": item.name if item else str(inv.item_id),
        "item_category": item.category if item else None,
        "quantity": float(inv.quantity),
        "unit": inv.unit,
        "location": inv.location,
        "min_qty": float(inv.min_qty) if inv.min_qty else None,
        "is_low_stock": bool(inv.min_qty and inv.quantity < inv.min_qty),
        "last_updated": inv.last_updated.isoformat() if inv.last_updated else None,
    }


def _lot_to_dict(lot: InventoryLot, item_name: str | None) -> dict:
    return {
        "id": str(lot.id),
        "site_id": str(lot.site_id),
        "item_id": str(lot.item_id),
        "item_name": item_name or str(lot.item_id),
        "vendor_id": str(lot.vendor_id) if lot.vendor_id else None,
        "po_id": str(lot.po_id) if lot.po_id else None,
        "lot_number": lot.lot_number,
        "quantity": float(lot.quantity),
        "unit": lot.unit,
        "unit_cost": float(lot.unit_cost) if lot.unit_cost else None,
        "received_at": lot.received_at.isoformat() if lot.received_at else None,
        "expiry_date": str(lot.expiry_date) if lot.expiry_date else None,
        "days_until_expiry": (lot.expiry_date - date.today()).days if lot.expiry_date else None,
        "storage_temp": float(lot.storage_temp) if lot.storage_temp else None,
        "status": lot.status,
        "inspect_result": lot.inspect_result or {},
        "used_in_menus": lot.used_in_menus or [],
        "created_at": lot.created_at.isoformat() if lot.created_at else None,
    }
