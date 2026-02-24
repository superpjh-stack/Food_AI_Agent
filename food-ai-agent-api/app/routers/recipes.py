from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.orm.recipe import Recipe
from app.models.orm.user import User
from app.models.schemas.recipe import RecipeSearchRequest, ScaleRecipeRequest, RecipeResponse

router = APIRouter()

# Seasoning adjustment factors for large-scale cooking
SEASONING_ADJUSTMENT = {
    "salt": 0.85,
    "soy_sauce": 0.85,
    "sugar": 0.80,
    "pepper": 0.85,
    "garlic": 0.90,
    "소금": 0.85,
    "간장": 0.85,
    "설탕": 0.80,
    "후추": 0.85,
    "마늘": 0.90,
    "고춧가루": 0.85,
    "된장": 0.85,
    "고추장": 0.85,
}

SEASONING_KEYWORDS = set(SEASONING_ADJUSTMENT.keys())


@router.get("")
async def list_recipes(
    category: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List/search recipes with pagination."""
    query = select(Recipe).where(Recipe.is_active == True)
    count_query = select(func.count(Recipe.id)).where(Recipe.is_active == True)

    if category:
        query = query.where(Recipe.category == category)
        count_query = count_query.where(Recipe.category == category)

    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(Recipe.name.ilike(pattern), Recipe.tags.any(search))
        )
        count_query = count_query.where(
            or_(Recipe.name.ilike(pattern), Recipe.tags.any(search))
        )

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Recipe.name).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    recipes = result.scalars().all()

    return {
        "success": True,
        "data": [_recipe_to_dict(r) for r in recipes],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/{recipe_id}")
async def get_recipe(
    recipe_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recipe detail."""
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Recipe not found"}}

    data = _recipe_to_dict(recipe)
    data["ingredients"] = recipe.ingredients or []
    data["steps"] = recipe.steps or []
    data["nutrition_per_serving"] = recipe.nutrition_per_serving
    return {"success": True, "data": data}


@router.post("")
async def create_recipe(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "ADM"),
):
    """Create recipe."""
    recipe = Recipe(
        name=body["name"],
        category=body.get("category"),
        sub_category=body.get("sub_category"),
        servings_base=body.get("servings_base", 1),
        prep_time_min=body.get("prep_time_min"),
        cook_time_min=body.get("cook_time_min"),
        difficulty=body.get("difficulty"),
        ingredients=body.get("ingredients", []),
        steps=body.get("steps", []),
        nutrition_per_serving=body.get("nutrition_per_serving"),
        allergens=body.get("allergens", []),
        tags=body.get("tags", []),
        created_by=current_user.id,
    )
    db.add(recipe)
    await db.flush()

    data = _recipe_to_dict(recipe)
    data["ingredients"] = recipe.ingredients
    data["steps"] = recipe.steps
    return {"success": True, "data": data}


@router.put("/{recipe_id}")
async def update_recipe(
    recipe_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "ADM"),
):
    """Update recipe."""
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Recipe not found"}}

    for field in (
        "name", "category", "sub_category", "servings_base", "prep_time_min",
        "cook_time_min", "difficulty", "ingredients", "steps",
        "nutrition_per_serving", "allergens", "tags",
    ):
        if field in body:
            setattr(recipe, field, body[field])

    await db.flush()
    data = _recipe_to_dict(recipe)
    data["ingredients"] = recipe.ingredients
    data["steps"] = recipe.steps
    return {"success": True, "data": data}


@router.post("/{recipe_id}/scale")
async def scale_recipe(
    recipe_id: UUID,
    body: ScaleRecipeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "KIT", "ADM"),
):
    """Scale recipe for target servings."""
    result = await db.execute(select(Recipe).where(Recipe.id == recipe_id))
    recipe = result.scalar_one_or_none()
    if not recipe:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Recipe not found"}}

    ratio = body.target_servings / recipe.servings_base
    large_batch = body.target_servings >= 100

    scaled_ingredients = []
    seasoning_notes_parts = []

    for ing in (recipe.ingredients or []):
        name = ing.get("name", "")
        amount = ing.get("amount", 0)
        unit = ing.get("unit", "")

        scaled_amount = amount * ratio

        # Apply seasoning adjustment for large batches
        name_lower = name.lower()
        if large_batch:
            for keyword in SEASONING_KEYWORDS:
                if keyword in name_lower:
                    factor = SEASONING_ADJUSTMENT[keyword]
                    adjusted = scaled_amount * factor
                    seasoning_notes_parts.append(
                        f"{name}: {scaled_amount:.1f}{unit} -> {adjusted:.1f}{unit} ({int(factor*100)}%)"
                    )
                    scaled_amount = adjusted
                    break

        scaled_ingredients.append({
            "name": name,
            "amount": round(scaled_amount, 1),
            "unit": unit,
        })

    seasoning_notes = ""
    if seasoning_notes_parts:
        seasoning_notes = (
            f"Large batch ({body.target_servings} servings) seasoning adjustments:\n"
            + "\n".join(seasoning_notes_parts)
        )

    return {
        "success": True,
        "data": {
            "recipe_id": str(recipe_id),
            "original_servings": recipe.servings_base,
            "target_servings": body.target_servings,
            "scaled_ingredients": scaled_ingredients,
            "seasoning_notes": seasoning_notes,
        },
    }


@router.post("/search")
async def search_recipes(
    body: RecipeSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search recipes with keyword matching."""
    query = select(Recipe).where(Recipe.is_active == True)

    if body.query:
        pattern = f"%{body.query}%"
        query = query.where(
            or_(Recipe.name.ilike(pattern), Recipe.tags.any(body.query))
        )

    if body.category:
        query = query.where(Recipe.category == body.category)

    # Allergen exclusion
    if body.allergen_exclude:
        for allergen in body.allergen_exclude:
            query = query.where(~Recipe.allergens.any(allergen))

    query = query.limit(body.max_results)
    result = await db.execute(query)
    recipes = result.scalars().all()

    return {
        "success": True,
        "data": [_recipe_to_dict(r) for r in recipes],
    }


def _recipe_to_dict(recipe: Recipe) -> dict:
    return {
        "id": str(recipe.id),
        "name": recipe.name,
        "version": recipe.version,
        "category": recipe.category,
        "sub_category": recipe.sub_category,
        "servings_base": recipe.servings_base,
        "prep_time_min": recipe.prep_time_min,
        "cook_time_min": recipe.cook_time_min,
        "difficulty": recipe.difficulty,
        "allergens": recipe.allergens or [],
        "tags": recipe.tags or [],
    }
