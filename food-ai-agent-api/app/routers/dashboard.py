from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.orm.audit_log import AuditLog
from app.models.orm.haccp import HaccpChecklist, HaccpIncident
from app.models.orm.inventory import Inventory, InventoryLot
from app.models.orm.item import Item
from app.models.orm.menu_plan import MenuPlan
from app.models.orm.purchase import PurchaseOrder, VendorPrice
from app.models.orm.work_order import WorkOrder
from app.models.orm.user import User

router = APIRouter()


@router.get("/overview")
async def get_overview(
    site_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Today's operational overview."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # Menu plan status
    mp_query = select(MenuPlan)
    if site_id:
        mp_query = mp_query.where(MenuPlan.site_id == site_id)
    mp_query = mp_query.where(MenuPlan.period_start <= week_end, MenuPlan.period_end >= week_start)
    mp_result = await db.execute(mp_query)
    plans = mp_result.scalars().all()

    menu_status = {"draft": 0, "review": 0, "confirmed": 0, "archived": 0}
    for p in plans:
        menu_status[p.status] = menu_status.get(p.status, 0) + 1

    # HACCP completion
    haccp_query = select(HaccpChecklist).where(HaccpChecklist.date == today)
    if site_id:
        haccp_query = haccp_query.where(HaccpChecklist.site_id == site_id)
    haccp_result = await db.execute(haccp_query)
    checklists = haccp_result.scalars().all()

    haccp_total = len(checklists)
    haccp_completed = sum(1 for c in checklists if c.status == "completed")
    haccp_overdue = sum(1 for c in checklists if c.status in ("overdue", "pending"))

    # Work orders
    wo_query = select(WorkOrder).where(WorkOrder.date == today)
    if site_id:
        wo_query = wo_query.where(WorkOrder.site_id == site_id)
    wo_result = await db.execute(wo_query)
    work_orders = wo_result.scalars().all()

    wo_total = len(work_orders)
    wo_completed = sum(1 for w in work_orders if w.status == "completed")

    # Weekly stats
    week_mp_query = select(func.count(MenuPlan.id)).where(
        MenuPlan.period_start <= week_end,
        MenuPlan.period_end >= week_start,
        MenuPlan.status == "confirmed",
    )
    if site_id:
        week_mp_query = week_mp_query.where(MenuPlan.site_id == site_id)
    week_confirmed = (await db.execute(week_mp_query)).scalar() or 0

    week_total_mp = len(plans)

    # Recent activity
    activity_query = (
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(10)
    )
    if site_id:
        activity_query = activity_query.where(AuditLog.site_id == site_id)
    act_result = await db.execute(activity_query)
    activities = act_result.scalars().all()

    return {
        "success": True,
        "data": {
            "menu_status": menu_status,
            "haccp": {
                "total": haccp_total,
                "completed": haccp_completed,
                "overdue": haccp_overdue,
                "in_progress": haccp_total - haccp_completed - haccp_overdue,
                "completion_rate": round(haccp_completed / haccp_total * 100, 1) if haccp_total else 0,
            },
            "work_orders": {
                "total": wo_total,
                "completed": wo_completed,
                "completion_rate": round(wo_completed / wo_total * 100, 1) if wo_total else 0,
            },
            "weekly": {
                "menu_confirmed": week_confirmed,
                "menu_total": week_total_mp,
                "confirmation_rate": round(week_confirmed / week_total_mp * 100, 1) if week_total_mp else 0,
            },
            "recent_activity": [
                {
                    "id": str(a.id),
                    "action": a.action,
                    "entity_type": a.entity_type,
                    "reason": a.reason,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in activities
            ],
        },
    }


@router.get("/alerts")
async def get_alerts(
    site_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Active alerts and notifications."""
    today = date.today()
    alerts = []

    # HACCP overdue/pending
    haccp_query = select(func.count(HaccpChecklist.id)).where(
        HaccpChecklist.date == today,
        HaccpChecklist.status.in_(["pending", "overdue"]),
    )
    if site_id:
        haccp_query = haccp_query.where(HaccpChecklist.site_id == site_id)
    haccp_pending = (await db.execute(haccp_query)).scalar() or 0

    if haccp_pending > 0:
        alerts.append({
            "type": "haccp_overdue",
            "severity": "warning",
            "message": f"HACCP 미완료 점검표 {haccp_pending}건",
            "count": haccp_pending,
        })

    # Menu plans pending approval
    mp_query = select(func.count(MenuPlan.id)).where(MenuPlan.status == "review")
    if site_id:
        mp_query = mp_query.where(MenuPlan.site_id == site_id)
    mp_review = (await db.execute(mp_query)).scalar() or 0

    if mp_review > 0:
        alerts.append({
            "type": "menu_review",
            "severity": "info",
            "message": f"식단 승인 대기 {mp_review}건",
            "count": mp_review,
        })

    # Open incidents
    inc_query = select(func.count(HaccpIncident.id)).where(
        HaccpIncident.status.in_(["open", "in_progress"]),
    )
    if site_id:
        inc_query = inc_query.where(HaccpIncident.site_id == site_id)
    inc_open = (await db.execute(inc_query)).scalar() or 0

    if inc_open > 0:
        alerts.append({
            "type": "incident_open",
            "severity": "danger",
            "message": f"미해결 사고 {inc_open}건",
            "count": inc_open,
        })

    return {"success": True, "data": alerts}


@router.get("/purchase-summary")
async def get_purchase_summary(
    site_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "OPS"),
):
    """Purchase status widget — PO counts by status."""
    site_uuid = UUID(site_id) if site_id else None

    po_query = select(PurchaseOrder.status, func.count(PurchaseOrder.id)).group_by(PurchaseOrder.status)
    if site_uuid:
        po_query = po_query.where(PurchaseOrder.site_id == site_uuid)

    rows = (await db.execute(po_query)).all()
    status_counts = {row[0]: row[1] for row in rows}

    # Today's deliveries
    today = date.today()
    today_del_query = select(func.count(PurchaseOrder.id)).where(
        PurchaseOrder.delivery_date == today,
        PurchaseOrder.status == "approved",
    )
    if site_uuid:
        today_del_query = today_del_query.where(PurchaseOrder.site_id == site_uuid)
    today_deliveries = (await db.execute(today_del_query)).scalar() or 0

    return {
        "success": True,
        "data": {
            "draft": status_counts.get("draft", 0),
            "submitted": status_counts.get("submitted", 0),
            "approved": status_counts.get("approved", 0),
            "received": status_counts.get("received", 0),
            "cancelled": status_counts.get("cancelled", 0),
            "pending_approval": status_counts.get("submitted", 0),
            "today_deliveries": today_deliveries,
        },
    }


@router.get("/price-alerts")
async def get_price_alerts(
    site_id: str | None = Query(None),
    threshold_pct: float = Query(15.0),
    top_n: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "OPS"),
):
    """Price spike alert widget — items with price increase above threshold."""
    from datetime import timedelta
    cutoff = date.today() - timedelta(weeks=1)
    older_cutoff = cutoff - timedelta(weeks=1)

    current_prices = (await db.execute(
        select(VendorPrice).where(VendorPrice.is_current == True)
    )).scalars().all()

    older_prices = (await db.execute(
        select(VendorPrice).where(
            VendorPrice.effective_from >= older_cutoff,
            VendorPrice.effective_from < cutoff,
        )
    )).scalars().all()

    item_current: dict[str, float] = {}
    for vp in current_prices:
        iid = str(vp.item_id)
        price = float(vp.unit_price)
        if iid not in item_current or price < item_current[iid]:
            item_current[iid] = price

    item_older: dict[str, float] = {}
    for vp in older_prices:
        iid = str(vp.item_id)
        price = float(vp.unit_price)
        if iid not in item_older or price < item_older[iid]:
            item_older[iid] = price

    alerts = []
    for iid, cur_price in item_current.items():
        old_price = item_older.get(iid)
        if not old_price or old_price <= 0:
            continue
        change_pct = (cur_price - old_price) / old_price * 100
        if change_pct >= threshold_pct:
            alerts.append({
                "item_id": iid,
                "current_price": cur_price,
                "previous_price": old_price,
                "change_pct": round(change_pct, 1),
            })

    alerts.sort(key=lambda x: x["change_pct"], reverse=True)
    alerts = alerts[:top_n]

    if alerts:
        item_uuids = [UUID(a["item_id"]) for a in alerts]
        items = (await db.execute(select(Item).where(Item.id.in_(item_uuids)))).scalars().all()
        items_map = {str(it.id): it.name for it in items}
        for a in alerts:
            a["item_name"] = items_map.get(a["item_id"], a["item_id"])

    return {
        "success": True,
        "data": {
            "alerts": alerts,
            "total_alerts": len(alerts),
            "threshold_pct": threshold_pct,
        },
    }


@router.get("/inventory-risks")
async def get_inventory_risks(
    site_id: str | None = Query(None),
    alert_days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("PUR", "KIT", "OPS"),
):
    """Inventory risk widget — low stock + expiry alerts."""
    site_uuid = UUID(site_id) if site_id else None

    # Low stock
    low_query = select(func.count(Inventory.id)).where(
        Inventory.min_qty.isnot(None),
        Inventory.quantity < Inventory.min_qty,
    )
    if site_uuid:
        low_query = low_query.where(Inventory.site_id == site_uuid)
    low_stock_count = (await db.execute(low_query)).scalar() or 0

    # Expiry alerts
    today = date.today()
    alert_date = today + timedelta(days=alert_days)
    expiry_query = select(func.count(InventoryLot.id)).where(
        InventoryLot.expiry_date <= alert_date,
        InventoryLot.expiry_date >= today,
        InventoryLot.status.in_(["active", "partially_used"]),
    )
    if site_uuid:
        expiry_query = expiry_query.where(InventoryLot.site_id == site_uuid)
    expiry_count = (await db.execute(expiry_query)).scalar() or 0

    # Critical (D-3)
    critical_date = today + timedelta(days=3)
    critical_query = select(func.count(InventoryLot.id)).where(
        InventoryLot.expiry_date <= critical_date,
        InventoryLot.expiry_date >= today,
        InventoryLot.status.in_(["active", "partially_used"]),
    )
    if site_uuid:
        critical_query = critical_query.where(InventoryLot.site_id == site_uuid)
    critical_count = (await db.execute(critical_query)).scalar() or 0

    return {
        "success": True,
        "data": {
            "low_stock_count": low_stock_count,
            "expiry_alert_count": expiry_count,
            "critical_expiry_count": critical_count,
            "alert_days": alert_days,
            "risk_level": "high" if critical_count > 0 or low_stock_count > 5 else "medium" if expiry_count > 0 or low_stock_count > 0 else "low",
        },
    }
