"""Pydantic schemas for HACCP operations."""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class ChecklistGenerateRequest(BaseModel):
    site_id: UUID
    date: date
    checklist_type: str  # daily, weekly
    meal_type: str | None = None


class CcpRecordRequest(BaseModel):
    checklist_id: UUID
    ccp_point: str
    category: str | None = None
    target_value: str | None = None
    actual_value: str | None = None
    is_compliant: bool | None = None
    corrective_action: str | None = None


class IncidentRequest(BaseModel):
    site_id: UUID
    incident_type: str  # food_safety, contamination, temperature, other
    severity: str  # low, medium, high, critical
    description: str


class AuditReportRequest(BaseModel):
    site_id: UUID
    start_date: date
    end_date: date
    include_sections: list[str] | None = None


# Response schemas

class ChecklistItemResponse(BaseModel):
    item: str
    category: str
    is_ccp: bool
    target: str | None = None


class ChecklistResponse(BaseModel):
    id: UUID
    site_id: UUID
    date: date
    checklist_type: str
    meal_type: str | None
    template: list[dict]
    status: str
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class CCPRecordResponse(BaseModel):
    id: UUID
    checklist_id: UUID
    ccp_point: str
    category: str | None
    target_value: str | None
    actual_value: str | None
    is_compliant: bool | None
    corrective_action: str | None
    recorded_by: UUID
    recorded_at: datetime | None

    model_config = {"from_attributes": True}


class IncidentResponse(BaseModel):
    id: UUID
    site_id: UUID
    incident_type: str
    severity: str
    description: str
    steps_taken: list[dict]
    status: str
    reported_by: UUID
    created_at: datetime | None
    resolved_at: datetime | None

    model_config = {"from_attributes": True}
