"""Menu domain tools - generate/validate/tag/diversity."""
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.item import Item
from app.models.orm.menu_plan import MenuPlan, MenuPlanItem, MenuPlanValidation
from app.models.orm.policy import AllergenPolicy, NutritionPolicy
from app.models.orm.recipe import Recipe
from app.models.orm.site import Site
from app.rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

# 법정 알레르겐 22종
LEGAL_ALLERGENS = [
    "난류", "우유", "메밀", "땅콩", "대두", "밀", "고등어", "게",
    "새우", "돼지고기", "복숭아", "토마토", "아황산류", "호두",
    "닭고기", "쇠고기", "오징어", "조개류", "잣", "쑥", "홍합", "전복",
]


async def generate_menu_plan(
    db: AsyncSession,
    site_id: str,
    period_start: str,
    period_end: str,
    meal_types: list[str],
    target_headcount: int,
    budget_per_meal: float | None = None,
    preferences: dict | None = None,
    num_alternatives: int = 2,
    created_by: UUID | None = None,
) -> dict:
    """Generate meal plan alternatives using RAG recipe search + Claude generation."""
    site_uuid = UUID(site_id)

    # 1. Load site info
    site = (await db.execute(select(Site).where(Site.id == site_uuid))).scalar_one_or_none()
    if not site:
        return {"error": "Site not found"}

    # 2. Load nutrition policy
    policy = (await db.execute(
        select(NutritionPolicy)
        .where(NutritionPolicy.site_id == site_uuid, NutritionPolicy.is_active == True)
        .limit(1)
    )).scalar_one_or_none()

    # 3. Load allergen policy
    allergen_policy = (await db.execute(
        select(AllergenPolicy)
        .where(AllergenPolicy.site_id == site_uuid, AllergenPolicy.is_active == True)
        .limit(1)
    )).scalar_one_or_none()

    # 4. Search recipes via RAG
    rag = RAGPipeline(db)
    query = f"{site.type} 급식 {' '.join(meal_types)} 레시피"
    if preferences:
        query += f" {json.dumps(preferences, ensure_ascii=False)}"
    rag_context = await rag.retrieve(query, doc_types=["recipe", "sop"])

    # 5. Search available recipes from DB
    recipe_query = select(Recipe).where(Recipe.is_active == True).limit(50)
    recipes = (await db.execute(recipe_query)).scalars().all()

    recipe_list = [
        {"id": str(r.id), "name": r.name, "category": r.category, "allergens": r.allergens or []}
        for r in recipes
    ]

    # 5b. Load low-preference recipes (MVP3 waste feedback integration)
    low_preference_context = ""
    try:
        from app.models.orm.waste import MenuPreference
        low_pref_rows = (await db.execute(
            select(MenuPreference).where(
                MenuPreference.site_id == site_uuid,
                MenuPreference.preference_score < -0.3,
            ).order_by(MenuPreference.preference_score).limit(10)
        )).scalars().all()
        if low_pref_rows:
            low_pref_ids = [str(r.recipe_id) for r in low_pref_rows]
            low_pref_recipes = (await db.execute(
                select(Recipe).where(Recipe.id.in_([r.recipe_id for r in low_pref_rows]))
            )).scalars().all()
            low_pref_names = [r.name for r in low_pref_recipes]
            low_preference_context = f"\n[잔반 피드백] 선호도 낮은 레시피 (가급적 제외): {', '.join(low_pref_names)}"
    except Exception as e:
        logger.debug(f"MenuPreference query skipped: {e}")

    # 6. Create menu plan records
    plans_created = []
    for alt_num in range(1, num_alternatives + 1):
        plan = MenuPlan(
            site_id=site_uuid,
            title=f"{site.name} {period_start}~{period_end} 식단 (안{alt_num})",
            period_start=date.fromisoformat(period_start),
            period_end=date.fromisoformat(period_end),
            status="draft",
            budget_per_meal=Decimal(str(budget_per_meal)) if budget_per_meal else None,
            target_headcount=target_headcount,
            nutrition_policy_id=policy.id if policy else None,
            allergen_policy_id=allergen_policy.id if allergen_policy else None,
            created_by=created_by or UUID("00000000-0000-0000-0000-000000000000"),
            ai_generation_params={
                "meal_types": meal_types,
                "preferences": preferences,
                "rag_chunks_used": len(rag_context.chunks),
                "recipes_available": len(recipe_list),
                "low_preference_context": low_preference_context,
            },
        )
        db.add(plan)
        await db.flush()
        plans_created.append({
            "plan_id": str(plan.id),
            "title": plan.title,
            "alternative": alt_num,
        })

    return {
        "plans_created": plans_created,
        "site": {"name": site.name, "type": site.type, "capacity": site.capacity},
        "policy": {"name": policy.name, "criteria": policy.criteria} if policy else None,
        "recipes_available": len(recipe_list),
        "rag_context_chunks": len(rag_context.chunks),
        "note": "식단 상세 항목은 Claude가 생성한 내용으로 MenuPlanItem에 저장됩니다.",
    }


async def validate_nutrition(
    db: AsyncSession,
    menu_plan_id: str,
    policy_id: str | None = None,
) -> dict:
    """Validate menu plan against nutrition policy."""
    plan_uuid = UUID(menu_plan_id)

    plan = (await db.execute(select(MenuPlan).where(MenuPlan.id == plan_uuid))).scalar_one_or_none()
    if not plan:
        return {"error": "Menu plan not found"}

    # Load policy
    pol_uuid = UUID(policy_id) if policy_id else plan.nutrition_policy_id
    policy = None
    if pol_uuid:
        policy = (await db.execute(select(NutritionPolicy).where(NutritionPolicy.id == pol_uuid))).scalar_one_or_none()

    if not policy:
        return {"error": "No nutrition policy found for this plan"}

    # Load items
    items = (await db.execute(
        select(MenuPlanItem).where(MenuPlanItem.menu_plan_id == plan_uuid)
    )).scalars().all()

    criteria = policy.criteria or {}
    daily_results = {}

    # Group items by date
    from collections import defaultdict
    by_date = defaultdict(list)
    for item in items:
        by_date[str(item.date)].append(item)

    for day, day_items in by_date.items():
        totals = {"kcal": 0, "protein": 0, "sodium": 0, "fat": 0, "carbs": 0}
        for item in day_items:
            if item.nutrition:
                for key in totals:
                    totals[key] += item.nutrition.get(key, 0)

        status = "pass"
        violations = []
        for nutrient, bounds in criteria.items():
            value = totals.get(nutrient, 0)
            if isinstance(bounds, dict):
                if "max" in bounds and value > bounds["max"]:
                    violations.append(f"{nutrient}: {value} > {bounds['max']} (초과)")
                    status = "fail"
                elif "min" in bounds and value < bounds["min"]:
                    violations.append(f"{nutrient}: {value} < {bounds['min']} (미달)")
                    if status != "fail":
                        status = "warning"

        daily_results[day] = {
            "totals": totals,
            "status": status,
            "violations": violations,
        }

    # Save validation record
    overall_status = "pass"
    if any(d["status"] == "fail" for d in daily_results.values()):
        overall_status = "fail"
    elif any(d["status"] == "warning" for d in daily_results.values()):
        overall_status = "warning"

    validation = MenuPlanValidation(
        menu_plan_id=plan_uuid,
        validation_type="nutrition",
        status=overall_status,
        details={"criteria": criteria, "daily_results": daily_results},
    )
    db.add(validation)
    await db.flush()

    return {
        "menu_plan_id": menu_plan_id,
        "policy": policy.name,
        "overall_status": overall_status,
        "daily_results": daily_results,
    }


async def tag_allergens(
    db: AsyncSession,
    target_type: str,
    target_id: str,
) -> dict:
    """Auto-tag allergens for menu plan or recipe."""
    target_uuid = UUID(target_id)

    if target_type == "recipe":
        recipe = (await db.execute(select(Recipe).where(Recipe.id == target_uuid))).scalar_one_or_none()
        if not recipe:
            return {"error": "Recipe not found"}

        detected = set()
        needs_verification = []
        ingredients = recipe.ingredients or []

        for ing in ingredients:
            item_name = ing.get("name", "")
            item_id = ing.get("item_id")

            # Check item master for known allergens
            if item_id:
                item = (await db.execute(select(Item).where(Item.id == UUID(item_id)))).scalar_one_or_none()
                if item and item.allergens:
                    detected.update(item.allergens)
                    continue

            # Keyword-based detection
            for allergen in LEGAL_ALLERGENS:
                if allergen in item_name:
                    detected.add(allergen)

            # Common ingredient → allergen mapping
            allergen_keywords = {
                "간장": ["대두", "밀"], "고추장": ["대두", "밀"], "된장": ["대두"],
                "두부": ["대두"], "우유": ["우유"], "계란": ["난류"], "달걀": ["난류"],
                "밀가루": ["밀"], "빵": ["밀", "난류", "우유"], "참기름": ["참깨"],
                "굴소스": ["조개류"], "새우젓": ["새우"],
            }
            for keyword, allergens in allergen_keywords.items():
                if keyword in item_name:
                    detected.update(allergens)

            # If no allergen found, mark for verification
            if not any(a in item_name for a in LEGAL_ALLERGENS) and item_name not in allergen_keywords:
                needs_verification.append(item_name)

        # Update recipe allergens
        recipe.allergens = list(detected)
        await db.flush()

        return {
            "target_type": "recipe",
            "target_id": target_id,
            "detected_allergens": sorted(detected),
            "needs_verification": needs_verification,
            "total_ingredients": len(ingredients),
        }

    elif target_type == "menu_plan":
        items = (await db.execute(
            select(MenuPlanItem).where(MenuPlanItem.menu_plan_id == target_uuid)
        )).scalars().all()

        all_allergens = set()
        needs_verification = []
        for item in items:
            if item.allergens:
                all_allergens.update(item.allergens)
            else:
                needs_verification.append(item.item_name)

        return {
            "target_type": "menu_plan",
            "target_id": target_id,
            "detected_allergens": sorted(all_allergens),
            "needs_verification": needs_verification,
            "total_items": len(items),
        }

    return {"error": f"Unknown target_type: {target_type}"}


async def check_diversity(
    db: AsyncSession,
    menu_plan_id: str,
) -> dict:
    """Check menu diversity - cooking method bias, ingredient repetition."""
    plan_uuid = UUID(menu_plan_id)

    items = (await db.execute(
        select(MenuPlanItem).where(MenuPlanItem.menu_plan_id == plan_uuid)
    )).scalars().all()

    if not items:
        return {"error": "No items found in menu plan"}

    from collections import Counter

    # Analyze names for cooking method patterns
    method_keywords = {
        "볶음": 0, "구이": 0, "조림": 0, "튀김": 0, "찜": 0,
        "무침": 0, "국/탕": 0, "전": 0, "샐러드": 0,
    }
    item_names = [item.item_name for item in items]
    name_counter = Counter(item_names)

    for name in item_names:
        for method in method_keywords:
            methods = method.split("/")
            if any(m in name for m in methods):
                method_keywords[method] += 1

    # Detect repetition
    repeated = {name: count for name, count in name_counter.items() if count > 1}

    # Calculate diversity score
    total = len(items)
    unique_names = len(set(item_names))
    diversity_score = (unique_names / total * 100) if total > 0 else 0

    warnings = []
    for method, count in method_keywords.items():
        if count > total * 0.3:
            warnings.append(f"{method} 빈도 과다: {count}/{total}건 ({count/total*100:.0f}%)")

    if repeated:
        for name, count in repeated.items():
            warnings.append(f"동일 메뉴 반복: '{name}' {count}회")

    return {
        "menu_plan_id": menu_plan_id,
        "total_items": total,
        "unique_items": unique_names,
        "diversity_score": round(diversity_score, 1),
        "method_distribution": {k: v for k, v in method_keywords.items() if v > 0},
        "repeated_items": repeated,
        "warnings": warnings,
        "status": "pass" if not warnings else "warning",
    }
