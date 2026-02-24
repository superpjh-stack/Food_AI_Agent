"""Pydantic schemas for menu plan operations."""
from datetime import date
from uuid import UUID

from pydantic import BaseModel


class MenuGenerateRequest(BaseModel):
    site_id: UUID
    period_start: date
    period_end: date
    meal_types: list[str]
    target_headcount: int
    budget_per_meal: float | None = None
    preferences: dict | None = None
    num_alternatives: int = 2


class MenuPlanItemSchema(BaseModel):
    date: date
    meal_type: str
    course: str
    item_name: str
    recipe_id: UUID | None = None
    nutrition: dict | None = None
    allergens: list[str] = []
    sort_order: int = 0


class MenuPlanResponse(BaseModel):
    id: UUID
    site_id: UUID
    title: str | None
    period_start: date
    period_end: date
    status: str
    version: int
    target_headcount: int | None
    budget_per_meal: float | None

    model_config = {"from_attributes": True}


class ValidationResult(BaseModel):
    menu_plan_id: str
    policy: str
    overall_status: str
    daily_results: dict
