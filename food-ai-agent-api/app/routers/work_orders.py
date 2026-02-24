from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import require_role
from app.db.session import get_db
from app.models.orm.menu_plan import MenuPlan, MenuPlanItem
from app.models.orm.recipe import Recipe
from app.models.orm.work_order import WorkOrder
from app.models.orm.user import User

router = APIRouter()

# Seasoning adjustment factors for large-scale cooking
SEASONING_ADJUSTMENT = {
    "소금": 0.85, "간장": 0.85, "설탕": 0.80, "후추": 0.85,
    "마늘": 0.90, "고춧가루": 0.85, "된장": 0.85, "고추장": 0.85,
    "salt": 0.85, "soy_sauce": 0.85, "sugar": 0.80,
}
SEASONING_KEYWORDS = set(SEASONING_ADJUSTMENT.keys())


class GenerateRequest(BaseModel):
    menu_plan_id: UUID


class StatusUpdateRequest(BaseModel):
    status: str


@router.post("/generate")
async def generate_work_orders(
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "OPS", "ADM"),
):
    """Generate work orders from a confirmed menu plan."""
    query = (
        select(MenuPlan)
        .options(selectinload(MenuPlan.items))
        .where(MenuPlan.id == body.menu_plan_id)
    )
    result = await db.execute(query)
    plan = result.scalar_one_or_none()
    if not plan:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Menu plan not found"}}

    orders = []
    for item in plan.items:
        if not item.recipe_id:
            continue

        # Load recipe
        r_result = await db.execute(select(Recipe).where(Recipe.id == item.recipe_id))
        recipe = r_result.scalar_one_or_none()
        if not recipe:
            continue

        target_servings = plan.target_headcount or 1
        ratio = target_servings / recipe.servings_base
        large_batch = target_servings >= 100

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
                f"Large batch ({target_servings}) seasoning adjustments:\n"
                + "\n".join(seasoning_notes_parts)
            )

        order = WorkOrder(
            menu_plan_id=plan.id,
            site_id=plan.site_id,
            date=item.date,
            meal_type=item.meal_type,
            recipe_id=recipe.id,
            recipe_name=recipe.name,
            scaled_servings=target_servings,
            scaled_ingredients=scaled_ingredients,
            steps=recipe.steps or [],
            seasoning_notes=seasoning_notes or None,
            status="pending",
        )
        db.add(order)
        orders.append(order)

    await db.flush()

    return {
        "success": True,
        "data": [_order_to_dict(o) for o in orders],
    }


@router.get("")
async def list_work_orders(
    site_id: UUID | None = Query(None),
    date: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("KIT", "NUT", "OPS", "ADM"),
):
    """List work orders with filtering."""
    query = select(WorkOrder)
    count_query = select(func.count(WorkOrder.id))

    if site_id:
        query = query.where(WorkOrder.site_id == site_id)
        count_query = count_query.where(WorkOrder.site_id == site_id)
    if date:
        query = query.where(WorkOrder.date == date)
        count_query = count_query.where(WorkOrder.date == date)
    if status:
        query = query.where(WorkOrder.status == status)
        count_query = count_query.where(WorkOrder.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(WorkOrder.date, WorkOrder.meal_type).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    orders = result.scalars().all()

    return {
        "success": True,
        "data": [_order_to_dict(o) for o in orders],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/{order_id}")
async def get_work_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("KIT", "NUT", "OPS", "ADM"),
):
    """Get work order detail."""
    result = await db.execute(select(WorkOrder).where(WorkOrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Work order not found"}}

    return {"success": True, "data": _order_to_dict(order)}


@router.put("/{order_id}/status")
async def update_work_order_status(
    order_id: UUID,
    body: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("KIT", "ADM"),
):
    """Update work order status."""
    result = await db.execute(select(WorkOrder).where(WorkOrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Work order not found"}}

    valid_transitions = {
        "pending": ["in_progress"],
        "in_progress": ["completed"],
        "completed": [],
    }
    if body.status not in valid_transitions.get(order.status, []):
        return {
            "success": False,
            "error": {
                "code": "INVALID_TRANSITION",
                "message": f"Cannot transition from {order.status} to {body.status}",
            },
        }

    order.status = body.status
    await db.flush()

    return {"success": True, "data": _order_to_dict(order)}


def _order_to_dict(order: WorkOrder) -> dict:
    return {
        "id": str(order.id),
        "menu_plan_id": str(order.menu_plan_id),
        "site_id": str(order.site_id),
        "date": str(order.date),
        "meal_type": order.meal_type,
        "recipe_id": str(order.recipe_id),
        "recipe_name": order.recipe_name,
        "scaled_servings": order.scaled_servings,
        "scaled_ingredients": order.scaled_ingredients or [],
        "steps": order.steps or [],
        "seasoning_notes": order.seasoning_notes,
        "status": order.status,
    }
