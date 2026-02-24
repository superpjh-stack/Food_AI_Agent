"""Cost optimization API router."""
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.db.session import get_db
from app.models.orm.cost import CostAnalysis
from app.models.orm.user import User
from app.models.schemas.cost import CostSimulateRequest
from app.agents.tools.demand_tools import simulate_cost as _simulate_cost

router = APIRouter()


@router.post("/simulate")
async def simulate_cost(
    body: CostSimulateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "NUT", "PUR"),
):
    """Simulate meal plan cost against target and get AI suggestions."""
    result = await _simulate_cost(
        db=db,
        site_id=str(body.site_id),
        menu_plan_id=str(body.menu_plan_id),
        target_cost_per_meal=body.target_cost_per_meal,
        headcount=body.headcount,
        suggest_alternatives_flag=body.suggest_alternatives,
        created_by=current_user.id,
    )
    if "error" in result:
        return {"success": False, "error": {"code": "SIMULATION_ERROR", "message": result["error"]}}
    return {"success": True, "data": result}


@router.get("/analyses")
async def list_analyses(
    site_id: UUID | None = Query(None),
    menu_plan_id: UUID | None = Query(None),
    analysis_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "NUT", "PUR"),
):
    """List cost analyses."""
    query = select(CostAnalysis)
    count_q = select(func.count(CostAnalysis.id))

    if site_id:
        query = query.where(CostAnalysis.site_id == site_id)
        count_q = count_q.where(CostAnalysis.site_id == site_id)
    if menu_plan_id:
        query = query.where(CostAnalysis.menu_plan_id == menu_plan_id)
        count_q = count_q.where(CostAnalysis.menu_plan_id == menu_plan_id)
    if analysis_type:
        query = query.where(CostAnalysis.analysis_type == analysis_type)
        count_q = count_q.where(CostAnalysis.analysis_type == analysis_type)

    total = (await db.execute(count_q)).scalar() or 0
    rows = (await db.execute(
        query.order_by(CostAnalysis.created_at.desc())
             .offset((page - 1) * per_page)
             .limit(per_page)
    )).scalars().all()

    return {
        "success": True,
        "data": [_analysis_to_dict(r) for r in rows],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/analyses/{analysis_id}")
async def get_analysis(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "NUT", "PUR"),
):
    """Get cost analysis detail."""
    row = (await db.execute(
        select(CostAnalysis).where(CostAnalysis.id == analysis_id)
    )).scalar_one_or_none()
    if not row:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Cost analysis not found"}}
    return {"success": True, "data": _analysis_to_dict(row)}


@router.get("/trend")
async def cost_trend(
    site_id: UUID = Query(...),
    period_days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS"),
):
    """Get cost trend over a period."""
    cutoff = datetime.utcnow() - timedelta(days=period_days)
    rows = (await db.execute(
        select(CostAnalysis).where(
            CostAnalysis.site_id == site_id,
            CostAnalysis.created_at >= cutoff,
        ).order_by(CostAnalysis.created_at)
    )).scalars().all()

    trend = [
        {
            "date": r.created_at.strftime("%Y-%m-%d") if r.created_at else None,
            "analysis_id": str(r.id),
            "estimated_cost": float(r.estimated_cost) if r.estimated_cost else None,
            "actual_cost": float(r.actual_cost) if r.actual_cost else None,
            "variance_pct": float(r.variance_pct) if r.variance_pct else None,
            "alert_triggered": r.alert_triggered,
        }
        for r in rows
    ]

    variance_values = [t["variance_pct"] for t in trend if t["variance_pct"] is not None]
    avg_variance = round(sum(variance_values) / len(variance_values), 2) if variance_values else None

    return {
        "success": True,
        "data": {
            "site_id": str(site_id),
            "period_days": period_days,
            "trend": trend,
            "avg_variance_pct": avg_variance,
        },
    }


def _analysis_to_dict(r: CostAnalysis) -> dict:
    return {
        "id": str(r.id),
        "site_id": str(r.site_id),
        "menu_plan_id": str(r.menu_plan_id) if r.menu_plan_id else None,
        "analysis_type": r.analysis_type,
        "target_cost": float(r.target_cost) if r.target_cost else None,
        "estimated_cost": float(r.estimated_cost) if r.estimated_cost else None,
        "actual_cost": float(r.actual_cost) if r.actual_cost else None,
        "headcount": r.headcount,
        "variance_pct": float(r.variance_pct) if r.variance_pct else None,
        "alert_triggered": r.alert_triggered,
        "cost_breakdown": r.cost_breakdown or {},
        "suggestions": r.suggestions or [],
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
