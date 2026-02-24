"""Purchase Orders API router (MVP 2)."""
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.orm.purchase import PurchaseOrder, PurchaseOrderItem
from app.models.orm.user import User
from app.models.schemas.purchase import (
    PurchaseOrderCreate, PurchaseOrderUpdate,
    POSubmitRequest, POApproveRequest, POCancelRequest, POReceiveRequest,
)

router = APIRouter()


def _generate_po_number(today: date, seq: int) -> str:
    return f"PO-{today.strftime('%Y%m%d')}-{str(seq).zfill(4)}"


@router.post("")
async def create_purchase_order(
    body: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR"),
):
    """Create purchase order (draft). SAFE-PUR-001: draft only; OPS approval required."""
    today = date.today()
    today_count = (await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            cast(PurchaseOrder.order_date, Date) == today
        )
    )).scalar() or 0
    po_number = _generate_po_number(today, today_count + 1)

    po = PurchaseOrder(
        bom_id=body.bom_id,
        site_id=body.site_id,
        vendor_id=body.vendor_id,
        po_number=po_number,
        status="draft",
        order_date=body.order_date,
        delivery_date=body.delivery_date,
        note=body.note,
        total_amount=Decimal("0"),
        tax_amount=Decimal("0"),
    )
    db.add(po)
    await db.flush()

    total = Decimal("0")
    for item_data in body.items:
        subtotal = item_data.quantity * item_data.unit_price
        total += subtotal
        poi = PurchaseOrderItem(
            po_id=po.id,
            bom_item_id=item_data.bom_item_id,
            item_id=item_data.item_id,
            item_name=item_data.item_name,
            spec=item_data.spec,
            quantity=item_data.quantity,
            unit=item_data.unit,
            unit_price=item_data.unit_price,
            subtotal=subtotal,
        )
        db.add(poi)

    po.total_amount = total
    po.tax_amount = total * Decimal("0.1")
    await db.flush()

    return {"success": True, "data": _po_to_dict(po)}


@router.get("")
async def list_purchase_orders(
    site_id: UUID | None = Query(None),
    status: str | None = Query(None),
    vendor_id: UUID | None = Query(None),
    order_date_from: str | None = Query(None),
    order_date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "OPS"),
):
    """List purchase orders with filters."""
    query = select(PurchaseOrder)
    count_query = select(func.count(PurchaseOrder.id))

    if site_id:
        query = query.where(PurchaseOrder.site_id == site_id)
        count_query = count_query.where(PurchaseOrder.site_id == site_id)
    if status:
        query = query.where(PurchaseOrder.status == status)
        count_query = count_query.where(PurchaseOrder.status == status)
    if vendor_id:
        query = query.where(PurchaseOrder.vendor_id == vendor_id)
        count_query = count_query.where(PurchaseOrder.vendor_id == vendor_id)
    if order_date_from:
        query = query.where(PurchaseOrder.order_date >= date.fromisoformat(order_date_from))
        count_query = count_query.where(PurchaseOrder.order_date >= date.fromisoformat(order_date_from))
    if order_date_to:
        query = query.where(PurchaseOrder.order_date <= date.fromisoformat(order_date_to))
        count_query = count_query.where(PurchaseOrder.order_date <= date.fromisoformat(order_date_to))

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(PurchaseOrder.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    pos = (await db.execute(query)).scalars().all()

    return {
        "success": True,
        "data": [_po_to_dict(po) for po in pos],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/{po_id}")
async def get_purchase_order(
    po_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "OPS"),
):
    """Get purchase order detail with items."""
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Purchase order not found"}}

    data = _po_to_dict(po)
    data["items"] = [_poi_to_dict(item) for item in po.items]
    return {"success": True, "data": data}


@router.put("/{po_id}")
async def update_purchase_order(
    po_id: UUID,
    body: PurchaseOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR"),
):
    """Update purchase order. Only allowed in draft status."""
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Purchase order not found"}}
    if po.status != "draft":
        return {"success": False, "error": {"code": "INVALID_STATUS", "message": "Can only edit draft purchase orders"}}

    if body.delivery_date is not None:
        po.delivery_date = body.delivery_date
    if body.note is not None:
        po.note = body.note

    if body.items is not None:
        # Remove existing items and recreate
        for existing_item in po.items:
            await db.delete(existing_item)
        await db.flush()

        total = Decimal("0")
        for item_data in body.items:
            subtotal = item_data.quantity * item_data.unit_price
            total += subtotal
            poi = PurchaseOrderItem(
                po_id=po.id,
                bom_item_id=item_data.bom_item_id,
                item_id=item_data.item_id,
                item_name=item_data.item_name,
                spec=item_data.spec,
                quantity=item_data.quantity,
                unit=item_data.unit,
                unit_price=item_data.unit_price,
                subtotal=subtotal,
            )
            db.add(poi)
        po.total_amount = total
        po.tax_amount = total * Decimal("0.1")

    await db.flush()
    return {"success": True, "data": _po_to_dict(po)}


@router.delete("/{po_id}")
async def delete_purchase_order(
    po_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR"),
):
    """Delete purchase order. Only allowed in draft status."""
    po = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))).scalar_one_or_none()
    if not po:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Purchase order not found"}}
    if po.status != "draft":
        return {"success": False, "error": {"code": "INVALID_STATUS", "message": "Can only delete draft purchase orders"}}

    await db.delete(po)
    await db.flush()
    return {"success": True, "data": {"id": str(po_id), "deleted": True}}


@router.post("/{po_id}/submit")
async def submit_purchase_order(
    po_id: UUID,
    body: POSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR"),
):
    """Submit purchase order for OPS approval. SAFE-PUR-001."""
    po = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))).scalar_one_or_none()
    if not po:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Purchase order not found"}}
    if po.status != "draft":
        return {"success": False, "error": {"code": "INVALID_STATUS", "message": f"Cannot submit PO in '{po.status}' status"}}

    po.status = "submitted"
    po.submitted_by = current_user.id
    po.submitted_at = datetime.utcnow()
    if body.note:
        po.note = f"{po.note}\n[제출 메모] {body.note}" if po.note else f"[제출 메모] {body.note}"
    await db.flush()

    return {"success": True, "data": _po_to_dict(po)}


@router.post("/{po_id}/approve")
async def approve_purchase_order(
    po_id: UUID,
    body: POApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS"),
):
    """Approve purchase order. SAFE-PUR-001: OPS role required."""
    po = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))).scalar_one_or_none()
    if not po:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Purchase order not found"}}
    if po.status != "submitted":
        return {"success": False, "error": {"code": "INVALID_STATUS", "message": f"Cannot approve PO in '{po.status}' status"}}

    po.status = "approved"
    po.approved_by = current_user.id
    po.approved_at = datetime.utcnow()
    await db.flush()

    return {"success": True, "data": _po_to_dict(po)}


@router.post("/{po_id}/cancel")
async def cancel_purchase_order(
    po_id: UUID,
    body: POCancelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "OPS"),
):
    """Cancel purchase order. Reason is required. SAFE-PUR-003."""
    po = (await db.execute(select(PurchaseOrder).where(PurchaseOrder.id == po_id))).scalar_one_or_none()
    if not po:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Purchase order not found"}}
    if po.status in ("received", "cancelled"):
        return {"success": False, "error": {"code": "INVALID_STATUS", "message": f"Cannot cancel PO in '{po.status}' status"}}

    po.status = "cancelled"
    po.cancel_reason = body.cancel_reason
    po.cancelled_at = datetime.utcnow()
    await db.flush()

    return {"success": True, "data": _po_to_dict(po)}


@router.post("/{po_id}/receive")
async def receive_purchase_order(
    po_id: UUID,
    body: POReceiveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "KIT"),
):
    """Process delivery receipt. Creates inventory lots and updates inventory.

    Safety: SAFE-PUR-004 — lot tracking is mandatory.
    """
    from app.models.orm.inventory import Inventory, InventoryLot

    result = await db.execute(
        select(PurchaseOrder).options(selectinload(PurchaseOrder.items)).where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Purchase order not found"}}
    if po.status != "approved":
        return {"success": False, "error": {"code": "INVALID_STATUS", "message": "PO must be approved before receiving"}}

    poi_map = {str(item.id): item for item in po.items}
    received_at = datetime.utcnow()
    lots_created = []

    for receive_item in body.items:
        poi = poi_map.get(str(receive_item.po_item_id))
        if not poi:
            continue

        poi.received_qty = receive_item.received_qty
        poi.received_at = received_at
        if receive_item.reject_reason:
            poi.reject_reason = receive_item.reject_reason

        # Create inventory lot (SAFE-PUR-004)
        lot = InventoryLot(
            site_id=po.site_id,
            item_id=poi.item_id,
            vendor_id=po.vendor_id,
            po_id=po.id,
            lot_number=body.lot_number,
            quantity=receive_item.received_qty,
            unit=poi.unit,
            unit_cost=poi.unit_price,
            received_at=received_at,
            expiry_date=body.expiry_date,
            storage_temp=body.storage_temp,
            status="active",
            inspect_result={
                "passed": True,
                "note": body.inspect_note or "",
                "inspector": str(current_user.id),
            },
        )
        db.add(lot)
        await db.flush()
        lots_created.append(str(lot.id))

        # Update or create inventory record
        inv = (await db.execute(
            select(Inventory).where(
                Inventory.site_id == po.site_id,
                Inventory.item_id == poi.item_id,
            )
        )).scalar_one_or_none()

        if inv:
            inv.quantity = inv.quantity + receive_item.received_qty
            inv.last_updated = received_at
        else:
            new_inv = Inventory(
                site_id=po.site_id,
                item_id=poi.item_id,
                quantity=receive_item.received_qty,
                unit=poi.unit,
                last_updated=received_at,
            )
            db.add(new_inv)

    # Check if all items received
    await db.flush()
    all_received = all(poi.received_qty and poi.received_qty >= poi.quantity for poi in po.items)
    po.status = "received" if all_received else "approved"
    po.received_at = received_at if all_received else None
    await db.flush()

    return {
        "success": True,
        "data": {
            "po_id": str(po_id),
            "po_number": po.po_number,
            "status": po.status,
            "lots_created": lots_created,
            "all_received": all_received,
            "message": "입고 검수 완료. 로트 추적 가능합니다. (SAFE-PUR-004)",
        },
    }


@router.get("/{po_id}/export")
async def export_purchase_order(
    po_id: UUID,
    format: str = Query("json", pattern="^(json|csv)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "OPS"),
):
    """Export purchase order data (JSON or CSV format)."""
    result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.id == po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Purchase order not found"}}

    data = _po_to_dict(po)
    data["items"] = [_poi_to_dict(item) for item in po.items]

    if format == "csv":
        lines = ["품목명,규격,수량,단위,단가,소계"]
        for item in data["items"]:
            lines.append(f"{item['item_name']},{item['spec'] or ''},{item['quantity']},{item['unit']},{item['unit_price']},{item['subtotal']}")
        return {"success": True, "data": {"format": "csv", "content": "\n".join(lines)}}

    return {"success": True, "data": data}


def _po_to_dict(po: PurchaseOrder) -> dict:
    return {
        "id": str(po.id),
        "bom_id": str(po.bom_id) if po.bom_id else None,
        "site_id": str(po.site_id),
        "vendor_id": str(po.vendor_id),
        "po_number": po.po_number,
        "status": po.status,
        "order_date": str(po.order_date),
        "delivery_date": str(po.delivery_date),
        "total_amount": float(po.total_amount) if po.total_amount else 0.0,
        "tax_amount": float(po.tax_amount) if po.tax_amount else 0.0,
        "note": po.note,
        "submitted_by": str(po.submitted_by) if po.submitted_by else None,
        "submitted_at": po.submitted_at.isoformat() if po.submitted_at else None,
        "approved_by": str(po.approved_by) if po.approved_by else None,
        "approved_at": po.approved_at.isoformat() if po.approved_at else None,
        "received_at": po.received_at.isoformat() if po.received_at else None,
        "cancelled_at": po.cancelled_at.isoformat() if po.cancelled_at else None,
        "cancel_reason": po.cancel_reason,
        "created_at": po.created_at.isoformat() if po.created_at else None,
        "updated_at": po.updated_at.isoformat() if po.updated_at else None,
    }


def _poi_to_dict(poi: PurchaseOrderItem) -> dict:
    return {
        "id": str(poi.id),
        "po_id": str(poi.po_id),
        "bom_item_id": str(poi.bom_item_id) if poi.bom_item_id else None,
        "item_id": str(poi.item_id),
        "item_name": poi.item_name,
        "spec": poi.spec,
        "quantity": float(poi.quantity),
        "unit": poi.unit,
        "unit_price": float(poi.unit_price),
        "subtotal": float(poi.subtotal),
        "received_qty": float(poi.received_qty) if poi.received_qty else 0.0,
        "received_at": poi.received_at.isoformat() if poi.received_at else None,
        "reject_reason": poi.reject_reason,
    }
