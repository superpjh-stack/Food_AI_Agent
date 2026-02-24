"""Waste management API router."""
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.orm.waste import MenuPreference, WasteRecord
from app.models.orm.user import User
from app.models.schemas.waste import WasteRecordCreate, MenuPreferenceUpdate
from app.agents.tools.demand_tools import record_waste as _record_waste

router = APIRouter()


@router.post("/records")
async def create_waste_record(
    body: WasteRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("KIT", "NUT"),
):
    """Create waste records and update menu preferences."""
    waste_items = [item.model_dump() for item in body.items]
    # Convert UUIDs to strings for the tool
    for item in waste_items:
        if item.get("recipe_id"):
            item["recipe_id"] = str(item["recipe_id"])
        if item.get("menu_plan_item_id"):
            item["menu_plan_item_id"] = str(item["menu_plan_item_id"])

    result = await _record_waste(
        db=db,
        site_id=str(body.site_id),
        record_date=str(body.record_date),
        meal_type=body.meal_type,
        waste_items=waste_items,
        recorded_by=current_user.id,
    )
    return {"success": True, "data": result}


@router.get("/records")
async def list_waste_records(
    site_id: UUID | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    meal_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "NUT", "KIT"),
):
    """List waste records with filters."""
    query = select(WasteRecord)
    count_q = select(func.count(WasteRecord.id))

    if site_id:
        query = query.where(WasteRecord.site_id == site_id)
        count_q = count_q.where(WasteRecord.site_id == site_id)
    if date_from:
        query = query.where(WasteRecord.record_date >= date.fromisoformat(date_from))
        count_q = count_q.where(WasteRecord.record_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.where(WasteRecord.record_date <= date.fromisoformat(date_to))
        count_q = count_q.where(WasteRecord.record_date <= date.fromisoformat(date_to))
    if meal_type:
        query = query.where(WasteRecord.meal_type == meal_type)
        count_q = count_q.where(WasteRecord.meal_type == meal_type)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(
        query.order_by(WasteRecord.record_date.desc())
             .offset((page - 1) * per_page)
             .limit(per_page)
    )).scalars().all()

    return {
        "success": True,
        "data": [_waste_to_dict(r) for r in rows],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/summary")
async def waste_summary(
    site_id: UUID = Query(...),
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "NUT"),
):
    """Waste summary by menu item, sorted by waste_pct descending."""
    cutoff = date.today() - timedelta(days=period_days)

    rows = (await db.execute(
        select(WasteRecord).where(
            WasteRecord.site_id == site_id,
            WasteRecord.record_date >= cutoff,
        )
    )).scalars().all()

    # Aggregate by item_name
    agg: dict[str, dict] = {}
    for r in rows:
        key = r.item_name
        if key not in agg:
            agg[key] = {
                "item_name": key,
                "recipe_id": str(r.recipe_id) if r.recipe_id else None,
                "waste_pct_sum": 0.0,
                "count": 0,
            }
        if r.waste_pct:
            agg[key]["waste_pct_sum"] += float(r.waste_pct)
            agg[key]["count"] += 1

    summary_items = []
    for key, data in agg.items():
        avg = data["waste_pct_sum"] / data["count"] if data["count"] > 0 else 0
        summary_items.append({
            "item_name": data["item_name"],
            "recipe_id": data["recipe_id"],
            "avg_waste_pct": round(avg, 2),
            "total_records": data["count"],
        })

    summary_items.sort(key=lambda x: x["avg_waste_pct"], reverse=True)

    return {
        "success": True,
        "data": {
            "site_id": str(site_id),
            "period_days": period_days,
            "items": summary_items,
            "total_records": len(rows),
        },
    }


@router.get("/preferences/{site_id}")
async def get_preferences(
    site_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "OPS"),
):
    """Get menu preferences for a site."""
    query = select(MenuPreference).where(
        MenuPreference.site_id == site_id
    ).order_by(MenuPreference.preference_score)

    count_q = select(func.count(MenuPreference.id)).where(MenuPreference.site_id == site_id)
    total = (await db.execute(count_q)).scalar() or 0

    rows = (await db.execute(
        query.offset((page - 1) * per_page).limit(per_page)
    )).scalars().all()

    return {
        "success": True,
        "data": [_pref_to_dict(r) for r in rows],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.put("/preferences/{site_id}")
async def update_preferences(
    site_id: UUID,
    body: list[MenuPreferenceUpdate],
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT"),
):
    """Manually update menu preference scores."""
    updated = []
    for item in body:
        pref = (await db.execute(
            select(MenuPreference).where(
                MenuPreference.site_id == site_id,
                MenuPreference.recipe_id == item.recipe_id,
            )
        )).scalar_one_or_none()

        if pref:
            pref.preference_score = Decimal(str(max(-1.0, min(1.0, item.preference_score))))
            if item.waste_pct is not None:
                pref.waste_avg_pct = Decimal(str(item.waste_pct))
        else:
            pref = MenuPreference(
                site_id=site_id,
                recipe_id=item.recipe_id,
                preference_score=Decimal(str(max(-1.0, min(1.0, item.preference_score)))),
                waste_avg_pct=Decimal(str(item.waste_pct)) if item.waste_pct else Decimal("0"),
            )
            db.add(pref)

        await db.flush()
        updated.append(_pref_to_dict(pref))

    return {"success": True, "data": updated}


def _waste_to_dict(r: WasteRecord) -> dict:
    return {
        "id": str(r.id),
        "site_id": str(r.site_id),
        "record_date": str(r.record_date),
        "meal_type": r.meal_type,
        "item_name": r.item_name,
        "recipe_id": str(r.recipe_id) if r.recipe_id else None,
        "waste_kg": float(r.waste_kg) if r.waste_kg else None,
        "waste_pct": float(r.waste_pct) if r.waste_pct else None,
        "served_count": r.served_count,
        "notes": r.notes,
        "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
    }


def _pref_to_dict(p: MenuPreference) -> dict:
    return {
        "id": str(p.id),
        "site_id": str(p.site_id),
        "recipe_id": str(p.recipe_id),
        "preference_score": float(p.preference_score) if p.preference_score else 0.0,
        "waste_avg_pct": float(p.waste_avg_pct) if p.waste_avg_pct else 0.0,
        "serve_count": p.serve_count or 0,
        "last_served": str(p.last_served) if p.last_served else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
