from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CostSimulateRequest(BaseModel):
    site_id: UUID
    menu_plan_id: UUID
    target_cost_per_meal: float
    headcount: int
    suggest_alternatives: bool = True


class CostSimulateResponse(BaseModel):
    analysis_id: UUID
    menu_plan_id: UUID
    headcount: int
    target_cost_per_meal: float
    estimated_cost_per_meal: float
    estimated_cost: float
    target_cost: float
    variance_pct: float
    alert_triggered: str
    cost_breakdown: list[dict]
    suggestions: list[dict]


class CostAnalysisResponse(BaseModel):
    id: UUID
    site_id: UUID
    menu_plan_id: UUID | None
    analysis_type: str
    target_cost: float | None
    estimated_cost: float | None
    actual_cost: float | None
    headcount: int | None
    variance_pct: float | None
    alert_triggered: str | None
    suggestions: list[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class CostTrendPoint(BaseModel):
    date: str
    estimated_cost: float | None
    actual_cost: float | None
    variance_pct: float | None
    alert_triggered: str | None


class CostTrendResponse(BaseModel):
    site_id: UUID
    period_days: int
    trend: list[CostTrendPoint]
    avg_variance_pct: float | None
