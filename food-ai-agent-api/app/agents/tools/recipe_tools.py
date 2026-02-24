"""Recipe domain tools - search and scale recipes."""
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.recipe import Recipe
from app.rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

# 대량조리 조미료 보정 비율
SEASONING_ADJUSTMENT = {
    "소금": 0.80,
    "간장": 0.85,
    "고추장": 0.80,
    "된장": 0.85,
    "설탕": 0.80,
    "식초": 0.85,
    "참기름": 0.85,
    "들기름": 0.85,
    "고춧가루": 0.80,
    "후추": 0.75,
    "맛술": 0.85,
    "굴소스": 0.85,
}

LARGE_BATCH_THRESHOLD = 100  # 100식 이상이면 대량조리 보정 적용


async def search_recipes(
    db: AsyncSession,
    query: str,
    category: str | None = None,
    allergen_exclude: list[str] | None = None,
    max_results: int = 10,
) -> dict:
    """Search recipes using hybrid RAG search + DB filter."""
    # 1. RAG hybrid search
    rag = RAGPipeline(db)
    rag_context = await rag.retrieve(query, doc_types=["recipe", "sop"], top_k=max_results)

    # 2. Also search recipes table directly
    stmt = select(Recipe).where(Recipe.is_active == True)
    if category:
        stmt = stmt.where(Recipe.category == category)
    stmt = stmt.limit(max_results)

    db_recipes = (await db.execute(stmt)).scalars().all()

    # 3. Filter by allergen exclusion
    results = []
    for recipe in db_recipes:
        recipe_allergens = set(recipe.allergens or [])
        if allergen_exclude and recipe_allergens.intersection(allergen_exclude):
            continue
        results.append({
            "id": str(recipe.id),
            "name": recipe.name,
            "category": recipe.category,
            "sub_category": recipe.sub_category,
            "servings_base": recipe.servings_base,
            "prep_time_min": recipe.prep_time_min,
            "cook_time_min": recipe.cook_time_min,
            "difficulty": recipe.difficulty,
            "allergens": recipe.allergens or [],
            "tags": recipe.tags or [],
        })

    # 4. Include RAG document results as additional context
    rag_results = []
    for chunk in rag_context.chunks:
        rag_results.append({
            "title": chunk.metadata.get("title", ""),
            "content_preview": chunk.content[:200],
            "score": chunk.score,
            "source": chunk.metadata.get("source_file", ""),
        })

    return {
        "query": query,
        "db_results": results,
        "rag_results": rag_results,
        "total_db": len(results),
        "total_rag": len(rag_results),
    }


async def scale_recipe(
    db: AsyncSession,
    recipe_id: str,
    target_servings: int,
) -> dict:
    """Scale recipe ingredients with large-batch seasoning adjustments."""
    recipe = (await db.execute(
        select(Recipe).where(Recipe.id == UUID(recipe_id))
    )).scalar_one_or_none()

    if not recipe:
        return {"error": "Recipe not found"}

    base = recipe.servings_base or 1
    ratio = target_servings / base
    is_large_batch = target_servings >= LARGE_BATCH_THRESHOLD

    scaled_ingredients = []
    seasoning_notes = []

    for ing in (recipe.ingredients or []):
        name = ing.get("name", "")
        amount = ing.get("amount", 0)
        unit = ing.get("unit", "g")

        # Apply seasoning adjustment for large batches
        adjustment_ratio = 1.0
        if is_large_batch:
            for keyword, adj in SEASONING_ADJUSTMENT.items():
                if keyword in name:
                    adjustment_ratio = adj
                    seasoning_notes.append(
                        f"{name}: {ratio:.1f}배 x {adj*100:.0f}% = {ratio * adj:.1f}배 적용"
                    )
                    break

        scaled_amount = round(amount * ratio * adjustment_ratio, 1)

        # Unit conversion for large amounts
        display_amount = scaled_amount
        display_unit = unit
        if unit == "g" and scaled_amount >= 1000:
            display_amount = round(scaled_amount / 1000, 2)
            display_unit = "kg"
        elif unit == "ml" and scaled_amount >= 1000:
            display_amount = round(scaled_amount / 1000, 2)
            display_unit = "L"

        scaled_ingredients.append({
            "name": name,
            "original_amount": amount,
            "original_unit": unit,
            "scaled_amount": display_amount,
            "scaled_unit": display_unit,
            "adjustment": f"{adjustment_ratio*100:.0f}%" if adjustment_ratio < 1.0 else None,
            "item_id": ing.get("item_id"),
        })

    # Scale nutrition
    scaled_nutrition = None
    if recipe.nutrition_per_serving:
        scaled_nutrition = {
            k: round(v * target_servings, 1) if isinstance(v, (int, float)) else v
            for k, v in recipe.nutrition_per_serving.items()
        }

    return {
        "recipe_id": recipe_id,
        "recipe_name": recipe.name,
        "base_servings": base,
        "target_servings": target_servings,
        "ratio": round(ratio, 2),
        "is_large_batch": is_large_batch,
        "scaled_ingredients": scaled_ingredients,
        "seasoning_notes": seasoning_notes if seasoning_notes else None,
        "steps": recipe.steps or [],
        "ccp_points": recipe.ccp_points or [],
        "allergens": recipe.allergens or [],
        "total_nutrition": scaled_nutrition,
        "warning": (
            f"대량조리({target_servings}식) 양념류는 단순 비례가 아닌 80-85% 보정 적용. "
            "실제 맛보기 후 조절하세요."
        ) if is_large_batch else None,
    }
