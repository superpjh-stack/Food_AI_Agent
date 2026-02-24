from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.orm.item import Item
from app.models.orm.user import User

router = APIRouter()


class ItemCreate(BaseModel):
    name: str
    category: str
    sub_category: str | None = None
    spec: str | None = None
    unit: str
    allergens: list[str] = []
    storage_condition: str | None = None
    substitute_group: str | None = None
    nutrition_per_100g: dict | None = None
    is_active: bool = True


class ItemUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    sub_category: str | None = None
    spec: str | None = None
    unit: str | None = None
    allergens: list[str] | None = None
    storage_condition: str | None = None
    substitute_group: str | None = None
    nutrition_per_100g: dict | None = None
    is_active: bool | None = None


def _item_to_dict(item: Item) -> dict:
    return {
        "id": str(item.id),
        "name": item.name,
        "category": item.category,
        "sub_category": item.sub_category,
        "spec": item.spec,
        "unit": item.unit,
        "allergens": item.allergens or [],
        "storage_condition": item.storage_condition,
        "substitute_group": item.substitute_group,
        "nutrition_per_100g": item.nutrition_per_100g,
        "is_active": item.is_active,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


@router.get("")
async def list_items(
    category: str | None = Query(None, description="Category filter (육류, 수산, 채소, 양념, ...)"),
    search: str | None = Query(None, description="Keyword search on name"),
    is_active: bool | None = Query(True),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List food items with optional category filter and search."""
    query = select(Item)
    count_query = select(func.count(Item.id))

    if is_active is not None:
        query = query.where(Item.is_active == is_active)
        count_query = count_query.where(Item.is_active == is_active)

    if category:
        query = query.where(Item.category == category)
        count_query = count_query.where(Item.category == category)

    if search:
        pattern = f"%{search}%"
        query = query.where(Item.name.ilike(pattern))
        count_query = count_query.where(Item.name.ilike(pattern))

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Item.category, Item.name).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "success": True,
        "data": [_item_to_dict(i) for i in items],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/{item_id}")
async def get_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get item detail."""
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Item not found"}}
    return {"success": True, "data": _item_to_dict(item)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_item(
    body: ItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "ADM"),
):
    """Create a new food item. NUT or ADM only."""
    item = Item(
        name=body.name,
        category=body.category,
        sub_category=body.sub_category,
        spec=body.spec,
        unit=body.unit,
        allergens=body.allergens,
        storage_condition=body.storage_condition,
        substitute_group=body.substitute_group,
        nutrition_per_100g=body.nutrition_per_100g,
        is_active=body.is_active,
    )
    db.add(item)
    await db.flush()
    return {"success": True, "data": _item_to_dict(item)}


@router.patch("/{item_id}")
async def update_item(
    item_id: UUID,
    body: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("NUT", "ADM"),
):
    """Update food item. NUT or ADM only."""
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Item not found"}}

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.flush()
    return {"success": True, "data": _item_to_dict(item)}


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("ADM"),
):
    """Soft-delete item (is_active=False). ADM only."""
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    item.is_active = False
    await db.flush()
