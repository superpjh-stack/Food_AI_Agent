"""Dashboard domain tools - operational overview queries."""
import logging
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.haccp import HaccpChecklist, HaccpIncident
from app.models.orm.menu_plan import MenuPlan
from app.models.orm.site import Site
from app.models.orm.work_order import WorkOrder

logger = logging.getLogger(__name__)


async def query_dashboard(
    db: AsyncSession,
    site_id: str,
    date_str: str | None = None,
) -> dict:
    """Get operational dashboard data for a site."""
    site_uuid = UUID(site_id)
    target_date = date.fromisoformat(date_str) if date_str else date.today()

    site = (await db.execute(select(Site).where(Site.id == site_uuid))).scalar_one_or_none()
    if not site:
        return {"error": "Site not found"}

    # Menu plan status for today
    menu_plans = (await db.execute(
        select(MenuPlan).where(
            MenuPlan.site_id == site_uuid,
            MenuPlan.period_start <= target_date,
            MenuPlan.period_end >= target_date,
        )
    )).scalars().all()

    menu_status = {
        "total": len(menu_plans),
        "by_status": {},
    }
    for plan in menu_plans:
        menu_status["by_status"][plan.status] = menu_status["by_status"].get(plan.status, 0) + 1

    # HACCP completion
    checklists = (await db.execute(
        select(HaccpChecklist).where(
            HaccpChecklist.site_id == site_uuid,
            HaccpChecklist.date == target_date,
        )
    )).scalars().all()

    haccp_status = {
        "total": len(checklists),
        "completed": sum(1 for c in checklists if c.status == "completed"),
        "pending": sum(1 for c in checklists if c.status == "pending"),
        "overdue": sum(1 for c in checklists if c.status == "overdue"),
    }

    # Work orders for today
    work_orders = (await db.execute(
        select(WorkOrder).where(
            WorkOrder.site_id == site_uuid,
            WorkOrder.date == target_date,
        )
    )).scalars().all()

    work_order_status = {
        "total": len(work_orders),
        "completed": sum(1 for w in work_orders if w.status == "completed"),
        "in_progress": sum(1 for w in work_orders if w.status == "in_progress"),
        "pending": sum(1 for w in work_orders if w.status == "pending"),
    }

    # Open incidents
    open_incidents = (await db.execute(
        select(HaccpIncident).where(
            HaccpIncident.site_id == site_uuid,
            HaccpIncident.status.in_(["open", "in_progress"]),
        )
    )).scalars().all()

    alerts = []
    if haccp_status["overdue"] > 0:
        alerts.append({
            "type": "warning",
            "message": f"HACCP 점검표 {haccp_status['overdue']}건 미완료",
        })
    if open_incidents:
        for inc in open_incidents:
            alerts.append({
                "type": "critical" if inc.severity in ("high", "critical") else "warning",
                "message": f"사고 보고 미해결: {inc.incident_type} ({inc.severity})",
            })

    # MVP3 widgets: forecast, waste, cost, claims
    forecast_widget = {}
    waste_widget = {}
    cost_widget = {}
    claims_widget = {}
    try:
        from app.models.orm.forecast import DemandForecast, ActualHeadcount
        from sqlalchemy import desc
        latest_forecast = (await db.execute(
            select(DemandForecast).where(
                DemandForecast.site_id == site_uuid,
                DemandForecast.forecast_date == target_date,
            ).limit(1)
        )).scalar_one_or_none()
        if latest_forecast:
            forecast_widget = {
                "forecast_date": str(target_date),
                "predicted_mid": latest_forecast.predicted_mid,
                "predicted_min": latest_forecast.predicted_min,
                "predicted_max": latest_forecast.predicted_max,
                "confidence_pct": float(latest_forecast.confidence_pct) if latest_forecast.confidence_pct else None,
            }

        from datetime import timedelta
        from app.models.orm.waste import WasteRecord
        seven_days_ago = target_date - timedelta(days=7)
        recent_waste = (await db.execute(
            select(func.avg(WasteRecord.waste_pct)).where(
                WasteRecord.site_id == site_uuid,
                WasteRecord.record_date >= seven_days_ago,
                WasteRecord.waste_pct.isnot(None),
            )
        )).scalar()
        waste_widget = {
            "avg_waste_pct_7d": round(float(recent_waste), 1) if recent_waste else None,
        }

        from app.models.orm.cost import CostAnalysis
        latest_cost = (await db.execute(
            select(CostAnalysis).where(
                CostAnalysis.site_id == site_uuid,
            ).order_by(CostAnalysis.created_at.desc()).limit(1)
        )).scalar_one_or_none()
        if latest_cost:
            cost_widget = {
                "latest_variance_pct": float(latest_cost.variance_pct) if latest_cost.variance_pct else None,
                "alert_triggered": latest_cost.alert_triggered,
            }

        from app.models.orm.claim import Claim
        open_claims = (await db.execute(
            select(func.count(Claim.id)).where(
                Claim.site_id == site_uuid,
                Claim.status.in_(["open", "investigating"]),
            )
        )).scalar() or 0
        critical_claims = (await db.execute(
            select(func.count(Claim.id)).where(
                Claim.site_id == site_uuid,
                Claim.status.in_(["open", "investigating"]),
                Claim.severity == "critical",
            )
        )).scalar() or 0
        claims_widget = {
            "open_claims": open_claims,
            "critical_claims": critical_claims,
        }
        if critical_claims > 0:
            alerts.append({
                "type": "critical",
                "message": f"미처리 critical 클레임 {critical_claims}건",
            })
    except Exception as e:
        logger.debug(f"MVP3 dashboard widgets failed (non-blocking): {e}")

    return {
        "site": {"name": site.name, "type": site.type, "capacity": site.capacity},
        "date": str(target_date),
        "menu_plans": menu_status,
        "haccp": haccp_status,
        "work_orders": work_order_status,
        "open_incidents": len(open_incidents),
        "alerts": alerts,
        "forecast": forecast_widget,
        "waste": waste_widget,
        "cost": cost_widget,
        "claims": claims_widget,
    }
