import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.orm.menu_plan import MenuPlan, MenuPlanItem, MenuPlanValidation
from app.models.orm.policy import NutritionPolicy
from app.models.orm.user import User
from app.models.schemas.menu import MenuGenerateRequest, MenuPlanResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate")
async def generate_menu_plan(
    body: MenuGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "OPS", "ADM"),
):
    """AI generate menu plan."""
    plan = MenuPlan(
        site_id=body.site_id,
        title=f"Menu {body.period_start} ~ {body.period_end}",
        period_start=body.period_start,
        period_end=body.period_end,
        status="draft",
        version=1,
        target_headcount=body.target_headcount,
        budget_per_meal=body.budget_per_meal,
        created_by=current_user.id,
        ai_generation_params={
            "meal_types": body.meal_types,
            "preferences": body.preferences,
            "num_alternatives": body.num_alternatives,
        },
    )
    db.add(plan)
    await db.flush()
    return {"success": True, "data": _plan_to_dict(plan)}


@router.get("")
async def list_menu_plans(
    site_id: UUID | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "OPS", "KIT", "ADM"),
):
    """List menu plans with pagination."""
    query = select(MenuPlan)
    count_query = select(func.count(MenuPlan.id))

    if site_id:
        query = query.where(MenuPlan.site_id == site_id)
        count_query = count_query.where(MenuPlan.site_id == site_id)
    if status:
        query = query.where(MenuPlan.status == status)
        count_query = count_query.where(MenuPlan.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(MenuPlan.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    plans = result.scalars().all()

    return {
        "success": True,
        "data": [_plan_to_dict(p) for p in plans],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/{plan_id}")
async def get_menu_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "OPS", "KIT", "ADM"),
):
    """Get menu plan detail with items."""
    query = (
        select(MenuPlan)
        .options(selectinload(MenuPlan.items), selectinload(MenuPlan.validations))
        .where(MenuPlan.id == plan_id)
    )
    result = await db.execute(query)
    plan = result.scalar_one_or_none()
    if not plan:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Menu plan not found"}}

    data = _plan_to_dict(plan)
    data["items"] = [
        {
            "id": str(item.id),
            "date": str(item.date),
            "meal_type": item.meal_type,
            "course": item.course,
            "item_name": item.item_name,
            "recipe_id": str(item.recipe_id) if item.recipe_id else None,
            "nutrition": item.nutrition,
            "allergens": item.allergens or [],
            "sort_order": item.sort_order or 0,
        }
        for item in plan.items
    ]
    return {"success": True, "data": data}


@router.put("/{plan_id}")
async def update_menu_plan(
    plan_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "ADM"),
):
    """Update menu plan."""
    result = await db.execute(select(MenuPlan).where(MenuPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Menu plan not found"}}

    for field in ("title", "status", "budget_per_meal", "target_headcount"):
        if field in body:
            setattr(plan, field, body[field])

    # Handle items update
    if "items" in body:
        # Delete existing items
        await db.execute(
            select(MenuPlanItem).where(MenuPlanItem.menu_plan_id == plan_id)
        )
        for item_data in body["items"]:
            item = MenuPlanItem(
                menu_plan_id=plan_id,
                date=item_data["date"],
                meal_type=item_data["meal_type"],
                course=item_data["course"],
                item_name=item_data["item_name"],
                recipe_id=item_data.get("recipe_id"),
                nutrition=item_data.get("nutrition"),
                allergens=item_data.get("allergens", []),
                sort_order=item_data.get("sort_order", 0),
            )
            db.add(item)

    await db.flush()
    return {"success": True, "data": _plan_to_dict(plan)}


@router.post("/{plan_id}/validate")
async def validate_menu_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "OPS", "ADM"),
):
    """Run nutrition validation against site policy."""
    query = select(MenuPlan).options(selectinload(MenuPlan.items)).where(MenuPlan.id == plan_id)
    result = await db.execute(query)
    plan = result.scalar_one_or_none()
    if not plan:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Menu plan not found"}}

    # Load nutrition policy
    policy = None
    if plan.nutrition_policy_id:
        p_result = await db.execute(
            select(NutritionPolicy).where(NutritionPolicy.id == plan.nutrition_policy_id)
        )
        policy = p_result.scalar_one_or_none()

    # Default criteria
    criteria = {
        "kcal": {"min": 600, "max": 900},
        "protein": {"min": 20},
        "sodium": {"max": 2000},
    }
    if policy and policy.criteria:
        criteria = policy.criteria

    # Validate by date
    by_date: dict[str, list] = {}
    for item in plan.items:
        day = str(item.date)
        by_date.setdefault(day, []).append(item)

    daily_results = {}
    overall = "pass"

    for day, items in sorted(by_date.items()):
        totals = {"kcal": 0, "protein": 0, "sodium": 0}
        for item in items:
            if item.nutrition:
                totals["kcal"] += item.nutrition.get("kcal", 0)
                totals["protein"] += item.nutrition.get("protein", 0)
                totals["sodium"] += item.nutrition.get("sodium", 0)

        violations = []
        status = "pass"

        if criteria.get("kcal"):
            if "max" in criteria["kcal"] and totals["kcal"] > criteria["kcal"]["max"]:
                violations.append(f"Calories {totals['kcal']} > max {criteria['kcal']['max']}")
                status = "fail"
            elif "min" in criteria["kcal"] and totals["kcal"] < criteria["kcal"]["min"]:
                violations.append(f"Calories {totals['kcal']} < min {criteria['kcal']['min']}")
                status = "warning" if status == "pass" else status

        if criteria.get("protein"):
            if "min" in criteria["protein"] and totals["protein"] < criteria["protein"]["min"]:
                violations.append(f"Protein {totals['protein']}g < min {criteria['protein']['min']}g")
                status = "warning" if status == "pass" else status

        if criteria.get("sodium"):
            if "max" in criteria["sodium"] and totals["sodium"] > criteria["sodium"]["max"]:
                violations.append(f"Sodium {totals['sodium']}mg > max {criteria['sodium']['max']}mg")
                status = "fail"

        daily_results[day] = {"totals": totals, "status": status, "violations": violations}
        if status == "fail":
            overall = "fail"
        elif status == "warning" and overall == "pass":
            overall = "warning"

    # Save validation
    validation = MenuPlanValidation(
        menu_plan_id=plan_id,
        validation_type="nutrition",
        status=overall,
        details=daily_results,
    )
    db.add(validation)

    if plan.status == "draft":
        plan.status = "review"
    await db.flush()

    return {
        "success": True,
        "data": {
            "menu_plan_id": str(plan_id),
            "policy": policy.name if policy else "Default",
            "overall_status": overall,
            "daily_results": daily_results,
        },
    }


async def _auto_generate_bom(plan_id: UUID, headcount: int, user_id: UUID) -> None:
    """Background task: auto-generate BOM after menu plan confirmation."""
    from app.db.session import AsyncSessionLocal
    from app.agents.tools.purchase_tools import calculate_bom
    async with AsyncSessionLocal() as session:
        try:
            result = await calculate_bom(
                db=session,
                menu_plan_id=str(plan_id),
                headcount=headcount,
                apply_inventory=True,
                generated_by=user_id,
            )
            await session.commit()
            if "error" in result:
                logger.warning(f"BOM auto-generation failed for plan {plan_id}: {result['error']}")
            else:
                logger.info(f"BOM auto-generated for plan {plan_id}: bom_id={result.get('bom_id')}")
        except Exception as e:
            logger.error(f"BOM auto-generation exception for plan {plan_id}: {e}")
            await session.rollback()


@router.post("/{plan_id}/confirm")
async def confirm_menu_plan(
    plan_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("OPS", "ADM"),
):
    """Confirm menu plan. Triggers BOM auto-generation as background task."""
    result = await db.execute(select(MenuPlan).where(MenuPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Menu plan not found"}}

    plan.status = "confirmed"
    plan.confirmed_by = current_user.id
    await db.flush()

    # MVP 2: Trigger BOM auto-generation in background
    headcount = plan.target_headcount or 1
    background_tasks.add_task(_auto_generate_bom, plan_id, headcount, current_user.id)

    return {"success": True, "data": _plan_to_dict(plan)}


@router.post("/{plan_id}/revert")
async def revert_menu_plan(
    plan_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "OPS", "ADM"),
):
    """Revert to previous version."""
    result = await db.execute(select(MenuPlan).where(MenuPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan or not plan.parent_id:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "No parent version found"}}

    plan.status = "archived"
    await db.flush()

    return {"success": True, "data": {"reverted_to": str(plan.parent_id)}}


def _plan_to_dict(plan: MenuPlan) -> dict:
    return {
        "id": str(plan.id),
        "site_id": str(plan.site_id),
        "title": plan.title,
        "period_start": str(plan.period_start),
        "period_end": str(plan.period_end),
        "status": plan.status,
        "version": plan.version,
        "target_headcount": plan.target_headcount,
        "budget_per_meal": float(plan.budget_per_meal) if plan.budget_per_meal else None,
    }
