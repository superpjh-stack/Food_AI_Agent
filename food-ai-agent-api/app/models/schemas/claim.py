from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ClaimCreate(BaseModel):
    site_id: UUID
    incident_date: datetime
    category: str
    severity: str = "medium"
    title: str
    description: str
    menu_plan_id: UUID | None = None
    recipe_id: UUID | None = None
    lot_number: str | None = None
    reporter_name: str | None = None
    reporter_role: str | None = None


class ClaimStatusUpdate(BaseModel):
    status: str
    root_cause: str | None = None


class ClaimActionCreate(BaseModel):
    action_type: str
    description: str
    assignee_role: str
    assignee_id: UUID | None = None
    due_date: datetime | None = None


class ClaimActionResponse(BaseModel):
    id: UUID
    claim_id: UUID
    action_type: str
    description: str
    assignee_id: UUID | None
    assignee_role: str | None
    due_date: datetime | None
    status: str
    result_notes: str | None
    completed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class ClaimResponse(BaseModel):
    id: UUID
    site_id: UUID
    incident_date: datetime
    category: str
    severity: str
    status: str
    title: str
    description: str
    menu_plan_id: UUID | None
    recipe_id: UUID | None
    lot_number: str | None
    reporter_name: str | None
    reporter_role: str | None
    haccp_incident_id: UUID | None
    ai_hypotheses: list[dict]
    root_cause: str | None
    is_recurring: bool
    recurrence_count: int
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class QualityReportResponse(BaseModel):
    site_id: UUID
    year: int
    month: int
    total_claims: int
    by_category: dict[str, int]
    by_severity: dict[str, int]
    by_status: dict[str, int]
    recurring_claims: int
    avg_resolution_days: float | None
    open_critical: int
