from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class WasteItemCreate(BaseModel):
    item_name: str
    waste_kg: float | None = None
    waste_pct: float | None = None
    recipe_id: UUID | None = None
    menu_plan_item_id: UUID | None = None
    served_count: int | None = None
    notes: str | None = None


class WasteRecordCreate(BaseModel):
    site_id: UUID
    record_date: date
    meal_type: str
    items: list[WasteItemCreate]


class WasteRecordResponse(BaseModel):
    id: UUID
    site_id: UUID
    record_date: date
    meal_type: str
    item_name: str
    waste_kg: float | None
    waste_pct: float | None
    served_count: int | None
    notes: str | None
    recorded_at: datetime

    class Config:
        from_attributes = True


class MenuPreferenceUpdate(BaseModel):
    recipe_id: UUID
    preference_score: float
    waste_pct: float | None = None


class MenuPreferenceResponse(BaseModel):
    id: UUID
    site_id: UUID
    recipe_id: UUID
    preference_score: float
    waste_avg_pct: float
    serve_count: int
    last_served: date | None
    updated_at: datetime

    class Config:
        from_attributes = True


class WasteSummaryItem(BaseModel):
    recipe_id: UUID | None
    item_name: str
    avg_waste_pct: float
    total_records: int
    preference_score: float | None


class WasteSummaryResponse(BaseModel):
    site_id: UUID
    period_days: int
    items: list[WasteSummaryItem]
    total_records: int
