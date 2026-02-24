"""Forecast API router — headcount prediction, actual recording, site events."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.orm.forecast import ActualHeadcount, DemandForecast, SiteEvent
from app.models.orm.user import User
from app.models.schemas.forecast import (
    ActualHeadcountCreate, ActualHeadcountResponse,
    ForecastRequest, ForecastResponse,
    SiteEventCreate, SiteEventResponse, SiteEventUpdate,
)
from app.agents.tools.demand_tools import forecast_headcount as _forecast_headcount

router = APIRouter()


# ── Forecast Headcount ────────────────────────────────────────────────────────

@router.get("/headcount")
async def list_forecasts(
    site_id: UUID | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    meal_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "NUT", "KIT"),
):
    """List demand forecasts with filters."""
    query = select(DemandForecast)
    count_q = select(func.count(DemandForecast.id))

    if site_id:
        query = query.where(DemandForecast.site_id == site_id)
        count_q = count_q.where(DemandForecast.site_id == site_id)
    if date_from:
        query = query.where(DemandForecast.forecast_date >= date.fromisoformat(date_from))
        count_q = count_q.where(DemandForecast.forecast_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(DemandForecast.forecast_date <= date.fromisoformat(date_to))
        count_q = count_q.where(DemandForecast.forecast_date <= date.fromisoformat(date_to))
    if meal_type:
        query = query.where(DemandForecast.meal_type == meal_type)
        count_q = count_q.where(DemandForecast.meal_type == meal_type)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(
        query.order_by(DemandForecast.forecast_date.desc())
             .offset((page - 1) * per_page)
             .limit(per_page)
    )).scalars().all()

    return {
        "success": True,
        "data": [_forecast_to_dict(r) for r in rows],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.post("/headcount")
async def create_forecast(
    req: ForecastRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "NUT"),
):
    """Create demand forecast using WMA algorithm."""
    result = await _forecast_headcount(
        db=db,
        site_id=str(req.site_id),
        forecast_date=str(req.forecast_date),
        meal_type=req.meal_type,
        model=req.model,
        created_by=current_user.id,
    )
    if "error" in result:
        return {"success": False, "error": {"code": "FORECAST_ERROR", "message": result["error"]}}
    return {"success": True, "data": result}


# ── Actual Headcount ─────────────────────────────────────────────────────────

@router.post("/actual")
async def record_actual(
    body: ActualHeadcountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("KIT", "NUT"),
):
    """Record actual headcount for a date/meal."""
    from decimal import Decimal
    record = ActualHeadcount(
        site_id=body.site_id,
        record_date=body.record_date,
        meal_type=body.meal_type,
        planned=body.planned,
        actual=body.actual,
        served=body.served,
        notes=body.notes,
        recorded_by=current_user.id,
    )
    db.add(record)
    await db.flush()
    return {"success": True, "data": _actual_to_dict(record)}


@router.get("/actual")
async def list_actuals(
    site_id: UUID | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    meal_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "NUT"),
):
    """List actual headcount records."""
    query = select(ActualHeadcount)
    count_q = select(func.count(ActualHeadcount.id))

    if site_id:
        query = query.where(ActualHeadcount.site_id == site_id)
        count_q = count_q.where(ActualHeadcount.site_id == site_id)
    if date_from:
        query = query.where(ActualHeadcount.record_date >= date.fromisoformat(date_from))
        count_q = count_q.where(ActualHeadcount.record_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(ActualHeadcount.record_date <= date.fromisoformat(date_to))
        count_q = count_q.where(ActualHeadcount.record_date <= date.fromisoformat(date_to))
    if meal_type:
        query = query.where(ActualHeadcount.meal_type == meal_type)
        count_q = count_q.where(ActualHeadcount.meal_type == meal_type)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(
        query.order_by(ActualHeadcount.record_date.desc())
             .offset((page - 1) * per_page)
             .limit(per_page)
    )).scalars().all()

    return {
        "success": True,
        "data": [_actual_to_dict(r) for r in rows],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


# ── Site Events ───────────────────────────────────────────────────────────────

@router.get("/site-events")
async def list_site_events(
    site_id: UUID | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List site events."""
    query = select(SiteEvent)
    if site_id:
        query = query.where(SiteEvent.site_id == site_id)
    if date_from:
        query = query.where(SiteEvent.event_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(SiteEvent.event_date <= date.fromisoformat(date_to))

    rows = (await db.execute(query.order_by(SiteEvent.event_date))).scalars().all()
    return {"success": True, "data": [_event_to_dict(r) for r in rows]}


@router.post("/site-events")
async def create_site_event(
    body: SiteEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "NUT"),
):
    """Create a site event."""
    event = SiteEvent(
        site_id=body.site_id,
        event_date=body.event_date,
        event_type=body.event_type,
        event_name=body.event_name,
        adjustment_factor=body.adjustment_factor,
        affects_meal_types=body.affects_meal_types,
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(event)
    await db.flush()
    return {"success": True, "data": _event_to_dict(event)}


@router.put("/site-events/{event_id}")
async def update_site_event(
    event_id: UUID,
    body: SiteEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "NUT"),
):
    """Update a site event."""
    event = (await db.execute(
        select(SiteEvent).where(SiteEvent.id == event_id)
    )).scalar_one_or_none()
    if not event:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Site event not found"}}

    if body.event_type is not None:
        event.event_type = body.event_type
    if body.event_name is not None:
        event.event_name = body.event_name
    if body.adjustment_factor is not None:
        event.adjustment_factor = body.adjustment_factor
    if body.affects_meal_types is not None:
        event.affects_meal_types = body.affects_meal_types
    if body.notes is not None:
        event.notes = body.notes

    await db.flush()
    return {"success": True, "data": _event_to_dict(event)}


@router.delete("/site-events/{event_id}")
async def delete_site_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS"),
):
    """Delete a site event."""
    event = (await db.execute(
        select(SiteEvent).where(SiteEvent.id == event_id)
    )).scalar_one_or_none()
    if not event:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Site event not found"}}

    await db.delete(event)
    await db.flush()
    return {"success": True, "data": {"id": str(event_id), "deleted": True}}


# ── Helper serializers ────────────────────────────────────────────────────────

def _forecast_to_dict(f: DemandForecast) -> dict:
    return {
        "id": str(f.id),
        "site_id": str(f.site_id),
        "forecast_date": str(f.forecast_date),
        "meal_type": f.meal_type,
        "predicted_min": f.predicted_min,
        "predicted_mid": f.predicted_mid,
        "predicted_max": f.predicted_max,
        "confidence_pct": float(f.confidence_pct) if f.confidence_pct else None,
        "model_used": f.model_used,
        "risk_factors": f.risk_factors or [],
        "input_factors": f.input_factors or {},
        "generated_at": f.generated_at.isoformat() if f.generated_at else None,
    }


def _actual_to_dict(a: ActualHeadcount) -> dict:
    return {
        "id": str(a.id),
        "site_id": str(a.site_id),
        "record_date": str(a.record_date),
        "meal_type": a.meal_type,
        "planned": a.planned,
        "actual": a.actual,
        "served": a.served,
        "notes": a.notes,
        "recorded_at": a.recorded_at.isoformat() if a.recorded_at else None,
    }


def _event_to_dict(e: SiteEvent) -> dict:
    return {
        "id": str(e.id),
        "site_id": str(e.site_id),
        "event_date": str(e.event_date),
        "event_type": e.event_type,
        "event_name": e.event_name,
        "adjustment_factor": float(e.adjustment_factor) if e.adjustment_factor else 1.0,
        "affects_meal_types": e.affects_meal_types or ["lunch"],
        "notes": e.notes,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
