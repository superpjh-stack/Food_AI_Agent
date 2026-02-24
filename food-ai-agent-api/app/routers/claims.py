"""Claims management API router (MVP 3)."""
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.orm.claim import Claim, ClaimAction
from app.models.orm.user import User
from app.models.schemas.claim import (
    ClaimCreate, ClaimStatusUpdate, ClaimActionCreate,
)
from app.agents.tools.demand_tools import (
    register_claim as _register_claim,
    analyze_claim as _analyze_claim,
    track_claim_action as _track_claim_action,
)

router = APIRouter()


@router.get("")
async def list_claims(
    site_id: UUID | None = Query(None),
    status: str | None = Query(None),
    category: str | None = Query(None),
    severity: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("CS", "OPS"),
):
    """List claims with filters."""
    query = select(Claim)
    count_q = select(func.count(Claim.id))

    if site_id:
        query = query.where(Claim.site_id == site_id)
        count_q = count_q.where(Claim.site_id == site_id)
    if status:
        query = query.where(Claim.status == status)
        count_q = count_q.where(Claim.status == status)
    if category:
        query = query.where(Claim.category == category)
        count_q = count_q.where(Claim.category == category)
    if severity:
        query = query.where(Claim.severity == severity)
        count_q = count_q.where(Claim.severity == severity)
    if date_from:
        query = query.where(Claim.incident_date >= datetime.fromisoformat(date_from))
        count_q = count_q.where(Claim.incident_date >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.where(Claim.incident_date <= datetime.fromisoformat(date_to))
        count_q = count_q.where(Claim.incident_date <= datetime.fromisoformat(date_to))

    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(
        query.order_by(Claim.incident_date.desc())
             .offset((page - 1) * per_page)
             .limit(per_page)
    )).scalars().all()

    return {
        "success": True,
        "data": [_claim_to_dict(r) for r in rows],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.post("")
async def create_claim(
    body: ClaimCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("CS", "OPS", "KIT"),
):
    """Register a new claim with SAFE-002 auto-trigger."""
    result = await _register_claim(
        db=db,
        site_id=str(body.site_id),
        incident_date=body.incident_date.isoformat(),
        category=body.category,
        severity=body.severity,
        title=body.title,
        description=body.description,
        menu_plan_id=str(body.menu_plan_id) if body.menu_plan_id else None,
        recipe_id=str(body.recipe_id) if body.recipe_id else None,
        lot_number=body.lot_number,
        reporter_name=body.reporter_name,
        reporter_role=body.reporter_role,
        created_by=current_user.id,
    )
    return {"success": True, "data": result}


@router.get("/reports/quality")
async def quality_report(
    site_id: UUID = Query(...),
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020, le=2030),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS"),
):
    """Generate monthly quality report."""
    start_dt = datetime(year, month, 1)
    if month == 12:
        end_dt = datetime(year + 1, 1, 1)
    else:
        end_dt = datetime(year, month + 1, 1)

    rows = (await db.execute(
        select(Claim).where(
            Claim.site_id == site_id,
            Claim.incident_date >= start_dt,
            Claim.incident_date < end_dt,
        )
    )).scalars().all()

    by_category: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    by_status: dict[str, int] = {}
    recurring = 0
    resolution_days = []
    open_critical = 0

    for r in rows:
        by_category[r.category] = by_category.get(r.category, 0) + 1
        by_severity[r.severity] = by_severity.get(r.severity, 0) + 1
        by_status[r.status] = by_status.get(r.status, 0) + 1
        if r.is_recurring:
            recurring += 1
        if r.resolved_at and r.created_at:
            delta = (r.resolved_at - r.created_at).days
            resolution_days.append(delta)
        if r.severity == "critical" and r.status not in ("closed",):
            open_critical += 1

    avg_resolution = round(sum(resolution_days) / len(resolution_days), 1) if resolution_days else None

    return {
        "success": True,
        "data": {
            "site_id": str(site_id),
            "year": year,
            "month": month,
            "total_claims": len(rows),
            "by_category": by_category,
            "by_severity": by_severity,
            "by_status": by_status,
            "recurring_claims": recurring,
            "avg_resolution_days": avg_resolution,
            "open_critical": open_critical,
        },
    }


@router.get("/{claim_id}")
async def get_claim(
    claim_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("CS", "OPS"),
):
    """Get claim detail."""
    claim = (await db.execute(
        select(Claim).where(Claim.id == claim_id)
    )).scalar_one_or_none()
    if not claim:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Claim not found"}}
    return {"success": True, "data": _claim_to_dict(claim)}


@router.put("/{claim_id}/status")
async def update_claim_status(
    claim_id: UUID,
    body: ClaimStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("CS", "OPS"),
):
    """Update claim status."""
    claim = (await db.execute(
        select(Claim).where(Claim.id == claim_id)
    )).scalar_one_or_none()
    if not claim:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Claim not found"}}

    claim.status = body.status
    if body.root_cause:
        claim.root_cause = body.root_cause
    if body.status == "closed":
        claim.resolved_at = datetime.utcnow()

    await db.flush()
    return {"success": True, "data": _claim_to_dict(claim)}


@router.post("/{claim_id}/actions")
async def add_claim_action(
    claim_id: UUID,
    body: ClaimActionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("CS", "OPS"),
):
    """Add action to claim."""
    result = await _track_claim_action(
        db=db,
        claim_id=str(claim_id),
        action_type=body.action_type,
        description=body.description,
        assignee_role=body.assignee_role,
        assignee_id=str(body.assignee_id) if body.assignee_id else None,
        due_date=body.due_date.isoformat() if body.due_date else None,
        created_by=current_user.id,
    )
    if "error" in result:
        return {"success": False, "error": {"code": "ACTION_ERROR", "message": result["error"]}}
    return {"success": True, "data": result}


@router.get("/{claim_id}/actions")
async def list_claim_actions(
    claim_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("CS", "OPS"),
):
    """List claim actions."""
    actions = (await db.execute(
        select(ClaimAction).where(ClaimAction.claim_id == claim_id)
                          .order_by(ClaimAction.created_at)
    )).scalars().all()
    return {"success": True, "data": [_action_to_dict(a) for a in actions]}


@router.post("/{claim_id}/analyze")
async def analyze_claim(
    claim_id: UUID,
    use_rag: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("CS", "OPS"),
):
    """Run AI root-cause analysis on a claim."""
    result = await _analyze_claim(db=db, claim_id=str(claim_id), use_rag=use_rag)
    if "error" in result:
        return {"success": False, "error": {"code": "ANALYSIS_ERROR", "message": result["error"]}}
    return {"success": True, "data": result}


def _claim_to_dict(c: Claim) -> dict:
    return {
        "id": str(c.id),
        "site_id": str(c.site_id),
        "incident_date": c.incident_date.isoformat() if c.incident_date else None,
        "category": c.category,
        "severity": c.severity,
        "status": c.status,
        "title": c.title,
        "description": c.description,
        "menu_plan_id": str(c.menu_plan_id) if c.menu_plan_id else None,
        "recipe_id": str(c.recipe_id) if c.recipe_id else None,
        "lot_number": c.lot_number,
        "reporter_name": c.reporter_name,
        "reporter_role": c.reporter_role,
        "haccp_incident_id": str(c.haccp_incident_id) if c.haccp_incident_id else None,
        "ai_hypotheses": c.ai_hypotheses or [],
        "root_cause": c.root_cause,
        "is_recurring": c.is_recurring,
        "recurrence_count": c.recurrence_count,
        "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _action_to_dict(a: ClaimAction) -> dict:
    return {
        "id": str(a.id),
        "claim_id": str(a.claim_id),
        "action_type": a.action_type,
        "description": a.description,
        "assignee_id": str(a.assignee_id) if a.assignee_id else None,
        "assignee_role": a.assignee_role,
        "due_date": a.due_date.isoformat() if a.due_date else None,
        "status": a.status,
        "result_notes": a.result_notes,
        "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
