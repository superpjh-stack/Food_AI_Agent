"""Work order agent tool — generate a single-recipe work order via AI chat."""
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.recipe import Recipe

# Seasoning adjustment factors (same as work_orders router)
SEASONING_ADJUSTMENT = {
    "소금": 0.85, "간장": 0.85, "설탕": 0.80, "후추": 0.85,
    "마늘": 0.90, "고춧가루": 0.85, "된장": 0.85, "고추장": 0.85,
    "salt": 0.85, "soy_sauce": 0.85, "sugar": 0.80, "pepper": 0.85,
}
SEASONING_KEYWORDS = set(SEASONING_ADJUSTMENT.keys())


async def generate_work_order(
    db: AsyncSession,
    recipe_id: str,
    planned_servings: int,
    planned_date: str,
    site_id: str | None = None,
) -> dict:
    """Generate a work order for a specific recipe and serving count.

    Called by AgentOrchestrator when Claude invokes the generate_work_order tool.
    Returns a structured work order dict suitable for SSE tool_result.
    """
    # Validate date
    try:
        cook_date = date.fromisoformat(planned_date)
    except ValueError:
        return {"error": f"Invalid date format: {planned_date}. Expected YYYY-MM-DD."}

    # Load recipe
    try:
        recipe_uuid = UUID(recipe_id)
    except ValueError:
        return {"error": f"Invalid recipe_id UUID: {recipe_id}"}

    result = await db.execute(select(Recipe).where(Recipe.id == recipe_uuid, Recipe.is_active == True))
    recipe = result.scalar_one_or_none()
    if not recipe:
        return {"error": f"Recipe {recipe_id} not found or inactive"}

    # Scale ingredients
    ratio = planned_servings / max(recipe.servings_base, 1)
    large_batch = planned_servings >= 100
    scaled_ingredients = []
    seasoning_notes_parts = []

    for ing in (recipe.ingredients or []):
        name = ing.get("name", "")
        amount = ing.get("amount", 0)
        unit = ing.get("unit", "")
        scaled_amount = amount * ratio

        if large_batch:
            name_lower = name.lower()
            for keyword in SEASONING_KEYWORDS:
                if keyword in name_lower:
                    factor = SEASONING_ADJUSTMENT[keyword]
                    adjusted = scaled_amount * factor
                    seasoning_notes_parts.append(
                        f"{name}: {scaled_amount:.1f}{unit} → {adjusted:.1f}{unit} ({int(factor * 100)}%)"
                    )
                    scaled_amount = adjusted
                    break

        scaled_ingredients.append({
            "name": name,
            "amount": round(scaled_amount, 1),
            "unit": unit,
        })

    # Identify CCP steps from recipe steps
    ccp_checkpoints = [
        step for step in (recipe.steps or [])
        if step.get("is_ccp") or "ccp" in str(step.get("type", "")).lower()
    ]

    seasoning_notes = ""
    if seasoning_notes_parts:
        seasoning_notes = (
            f"대용량 조리 ({planned_servings}인분) 양념 조정:\n"
            + "\n".join(seasoning_notes_parts)
        )

    return {
        "recipe_id": recipe_id,
        "recipe_name": recipe.name,
        "planned_date": str(cook_date),
        "planned_servings": planned_servings,
        "site_id": site_id,
        "scaled_ingredients": scaled_ingredients,
        "steps": recipe.steps or [],
        "ccp_checkpoints": ccp_checkpoints,
        "seasoning_notes": seasoning_notes or None,
        "allergens": recipe.allergens or [],
        "prep_time_min": recipe.prep_time_min,
        "cook_time_min": recipe.cook_time_min,
        "status": "generated",
    }
