"""Pydantic schemas for recipe operations."""
from uuid import UUID

from pydantic import BaseModel


class RecipeSearchRequest(BaseModel):
    query: str
    category: str | None = None
    allergen_exclude: list[str] | None = None
    max_results: int = 10


class ScaleRecipeRequest(BaseModel):
    target_servings: int


class IngredientSchema(BaseModel):
    item_id: str | None = None
    name: str
    amount: float
    unit: str


class RecipeResponse(BaseModel):
    id: UUID
    name: str
    version: int
    category: str | None
    sub_category: str | None
    servings_base: int
    prep_time_min: int | None
    cook_time_min: int | None
    difficulty: str | None
    allergens: list[str]
    tags: list[str]

    model_config = {"from_attributes": True}
