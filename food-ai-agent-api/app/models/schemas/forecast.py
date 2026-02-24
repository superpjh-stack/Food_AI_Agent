from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    site_id: UUID
    forecast_date: date
    meal_type: str
    model: str = "wma"


class ForecastResponse(BaseModel):
    id: UUID
    site_id: UUID
    forecast_date: date
    meal_type: str
    predicted_min: int
    predicted_mid: int
    predicted_max: int
    confidence_pct: float
    risk_factors: list[str]
    model_used: str
    generated_at: datetime

    class Config:
        from_attributes = True


class ActualHeadcountCreate(BaseModel):
    site_id: UUID
    record_date: date
    meal_type: str
    planned: int
    actual: int
    served: int | None = None
    notes: str | None = None


class ActualHeadcountResponse(BaseModel):
    id: UUID
    site_id: UUID
    record_date: date
    meal_type: str
    planned: int
    actual: int
    served: int | None
    notes: str | None
    recorded_at: datetime

    class Config:
        from_attributes = True


class SiteEventCreate(BaseModel):
    site_id: UUID
    event_date: date
    event_type: str
    event_name: str | None = None
    adjustment_factor: float = Field(default=1.0, ge=0.0, le=2.0)
    affects_meal_types: list[str] = ["lunch"]
    notes: str | None = None


class SiteEventUpdate(BaseModel):
    event_type: str | None = None
    event_name: str | None = None
    adjustment_factor: float | None = None
    affects_meal_types: list[str] | None = None
    notes: str | None = None


class SiteEventResponse(BaseModel):
    id: UUID
    site_id: UUID
    event_date: date
    event_type: str
    event_name: str | None
    adjustment_factor: float
    affects_meal_types: list[str]
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True
