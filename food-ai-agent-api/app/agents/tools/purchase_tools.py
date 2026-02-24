"""Purchase domain tools — BOM calculation, PO generation, vendor comparison, inventory check."""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func, and_, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.item import Item
from app.models.orm.inventory import Inventory, InventoryLot
from app.models.orm.menu_plan import MenuPlan, MenuPlanItem
from app.models.orm.purchase import (
    Bom, BomItem, PurchaseOrder, PurchaseOrderItem, Vendor, VendorPrice
)
from app.models.orm.recipe import Recipe

logger = logging.getLogger(__name__)

SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def calculate_bom(
    db: AsyncSession,
    menu_plan_id: str,
    headcount: int,
    apply_inventory: bool = True,
    generated_by: UUID | None = None,
) -> dict:
    """Calculate BOM from confirmed menu plan: scale ingredients, apply inventory, snapshot prices.

    Safety: SAFE-PUR-001 — only works on confirmed menu plans.
    """
    plan_uuid = UUID(menu_plan_id)

    # Load menu plan (must be confirmed)
    plan = (await db.execute(select(MenuPlan).where(MenuPlan.id == plan_uuid))).scalar_one_or_none()
    if not plan:
        return {"error": "Menu plan not found"}
    if plan.status != "confirmed":
        return {"error": f"Menu plan must be in 'confirmed' status (current: {plan.status}). SAFE-PUR-001"}

    # Load all menu plan items
    mp_items = (await db.execute(
        select(MenuPlanItem).where(MenuPlanItem.menu_plan_id == plan_uuid)
    )).scalars().all()

    if not mp_items:
        return {"error": "No items in menu plan"}

    # Collect recipe IDs
    recipe_ids = list({item.recipe_id for item in mp_items if item.recipe_id})

    # Load recipes
    recipes_map: dict[UUID, Recipe] = {}
    if recipe_ids:
        recipes = (await db.execute(
            select(Recipe).where(Recipe.id.in_(recipe_ids))
        )).scalars().all()
        recipes_map = {r.id: r for r in recipes}

    # Aggregate ingredients across all menu plan items
    # item_id -> {name, total_qty, unit, yield_pct, source_recipes}
    aggregated: dict[str, dict] = {}

    for mp_item in mp_items:
        if not mp_item.recipe_id or mp_item.recipe_id not in recipes_map:
            continue
        recipe = recipes_map[mp_item.recipe_id]
        if not recipe.ingredients:
            continue

        servings_base = recipe.servings_base or 1
        scale_factor = headcount / servings_base

        for ing in recipe.ingredients:
            item_id = ing.get("item_id")
            if not item_id:
                continue

            amount = float(ing.get("amount", 0))
            unit = ing.get("unit", "g")
            yield_pct = float(ing.get("yield_pct", 100))

            # Scale and apply yield correction
            scaled = amount * scale_factor
            corrected = scaled / (yield_pct / 100) if yield_pct > 0 else scaled

            if item_id not in aggregated:
                aggregated[item_id] = {
                    "item_name": ing.get("name", ""),
                    "quantity": 0.0,
                    "unit": unit,
                    "source_recipes": [],
                }
            aggregated[item_id]["quantity"] += corrected
            aggregated[item_id]["source_recipes"].append({
                "recipe_id": str(mp_item.recipe_id),
                "recipe_name": recipe.name,
                "amount": corrected,
                "unit": unit,
            })

    if not aggregated:
        return {"error": "No ingredients found in recipe items"}

    # Load item master for unit confirmation
    item_ids = [UUID(iid) for iid in aggregated.keys()]
    items_list = (await db.execute(
        select(Item).where(Item.id.in_(item_ids))
    )).scalars().all()
    items_map = {str(it.id): it for it in items_list}

    # Load current inventory if apply_inventory is True
    inventory_map: dict[str, float] = {}
    if apply_inventory and plan.site_id:
        inv_rows = (await db.execute(
            select(Inventory).where(
                Inventory.site_id == plan.site_id,
                Inventory.item_id.in_(item_ids),
            )
        )).scalars().all()
        inventory_map = {str(inv.item_id): float(inv.quantity) for inv in inv_rows}

    # Load current vendor prices (is_current=True, optional site_id match)
    vp_rows = (await db.execute(
        select(VendorPrice).where(
            VendorPrice.item_id.in_(item_ids),
            VendorPrice.is_current == True,
        ).order_by(VendorPrice.unit_price)
    )).scalars().all()

    # Best (lowest) price per item
    best_price_map: dict[str, dict] = {}
    for vp in vp_rows:
        iid = str(vp.item_id)
        if iid not in best_price_map:
            best_price_map[iid] = {
                "unit_price": float(vp.unit_price),
                "unit": vp.unit,
                "vendor_id": str(vp.vendor_id),
            }

    # Create BOM record
    bom = Bom(
        menu_plan_id=plan_uuid,
        site_id=plan.site_id,
        period_start=plan.period_start,
        period_end=plan.period_end,
        headcount=headcount,
        status="draft",
        total_cost=Decimal("0"),
        generated_by=generated_by or SYSTEM_USER_ID,
    )
    db.add(bom)
    await db.flush()

    total_cost = 0.0
    order_items_count = 0
    inventory_deducted = 0.0
    bom_items_created = []

    for item_id_str, data in aggregated.items():
        item = items_map.get(item_id_str)
        item_name = item.name if item else data["item_name"]

        qty = data["quantity"]
        unit = item.unit if item else data["unit"]

        inv_avail = min(inventory_map.get(item_id_str, 0.0), qty)
        order_qty = max(0.0, qty - inv_avail)

        price_info = best_price_map.get(item_id_str, {})
        unit_price = price_info.get("unit_price")
        preferred_vendor_id = price_info.get("vendor_id")

        subtotal = None
        if unit_price is not None:
            subtotal = order_qty * unit_price
            total_cost += subtotal

        if order_qty > 0:
            order_items_count += 1
        inventory_deducted += inv_avail

        bom_item = BomItem(
            bom_id=bom.id,
            item_id=UUID(item_id_str),
            item_name=item_name,
            quantity=Decimal(str(round(qty, 3))),
            unit=unit,
            unit_price=Decimal(str(unit_price)) if unit_price else None,
            subtotal=Decimal(str(round(subtotal, 2))) if subtotal is not None else None,
            inventory_available=Decimal(str(round(inv_avail, 3))),
            order_quantity=Decimal(str(round(order_qty, 3))),
            preferred_vendor_id=UUID(preferred_vendor_id) if preferred_vendor_id else None,
            source_recipes=data["source_recipes"],
        )
        db.add(bom_item)
        bom_items_created.append(bom_item)

    bom.total_cost = Decimal(str(round(total_cost, 2)))
    if headcount > 0:
        bom.cost_per_meal = Decimal(str(round(total_cost / headcount, 2)))

    await db.flush()

    return {
        "bom_id": str(bom.id),
        "menu_plan_id": menu_plan_id,
        "headcount": headcount,
        "total_items": len(aggregated),
        "order_items_count": order_items_count,
        "total_cost": round(total_cost, 2),
        "cost_per_meal": round(total_cost / headcount, 2) if headcount > 0 else 0,
        "inventory_deducted": round(inventory_deducted, 3),
        "apply_inventory": apply_inventory,
        "status": "draft",
        "source": "[출처: 레시피 재료 마스터 + 재고 현황]",
    }


async def generate_purchase_order(
    db: AsyncSession,
    bom_id: str,
    delivery_date: str,
    vendor_strategy: str = "lowest_price",
    vendor_id: str | None = None,
) -> dict:
    """Generate PO draft(s) from BOM. Strategy: lowest_price | preferred | split.

    Safety: SAFE-PUR-001 — creates draft only; OPS approval required before submission.
    """
    bom_uuid = UUID(bom_id)
    bom = (await db.execute(
        select(Bom).where(Bom.id == bom_uuid)
    )).scalar_one_or_none()
    if not bom:
        return {"error": "BOM not found"}

    # Load BOM items with order_quantity > 0
    bom_items = (await db.execute(
        select(BomItem).where(
            BomItem.bom_id == bom_uuid,
            BomItem.order_quantity > 0,
        )
    )).scalars().all()

    if not bom_items:
        return {"error": "No items need ordering in this BOM"}

    delivery_dt = date.fromisoformat(delivery_date)
    order_dt = date.today()

    # Determine vendor assignment per item
    item_ids = [bi.item_id for bi in bom_items]

    # Load current vendor prices
    vp_rows = (await db.execute(
        select(VendorPrice).where(
            VendorPrice.item_id.in_(item_ids),
            VendorPrice.is_current == True,
        )
    )).scalars().all()

    # vendor_prices[item_id] = list of (vendor_id, unit_price)
    vp_map: dict[str, list[dict]] = {}
    for vp in vp_rows:
        iid = str(vp.item_id)
        if iid not in vp_map:
            vp_map[iid] = []
        vp_map[iid].append({"vendor_id": str(vp.vendor_id), "unit_price": float(vp.unit_price), "unit": vp.unit})

    # Sort by price for lowest_price strategy
    for iid in vp_map:
        vp_map[iid].sort(key=lambda x: x["unit_price"])

    # Group items by vendor
    vendor_items: dict[str, list[BomItem]] = {}

    for bi in bom_items:
        iid = str(bi.item_id)
        assigned_vendor = None

        if vendor_strategy == "preferred" and vendor_id:
            # Use specified vendor; if they don't supply this item, skip
            prices = vp_map.get(iid, [])
            if any(p["vendor_id"] == vendor_id for p in prices):
                assigned_vendor = vendor_id
            else:
                # No price from preferred vendor — use lowest as fallback
                assigned_vendor = prices[0]["vendor_id"] if prices else None
        elif vendor_strategy == "lowest_price":
            prices = vp_map.get(iid, [])
            assigned_vendor = prices[0]["vendor_id"] if prices else None
        elif vendor_strategy == "split":
            # Use preferred vendor per item (same as lowest_price for now)
            preferred = bi.preferred_vendor_id
            if preferred:
                assigned_vendor = str(preferred)
            else:
                prices = vp_map.get(iid, [])
                assigned_vendor = prices[0]["vendor_id"] if prices else None

        if assigned_vendor:
            if assigned_vendor not in vendor_items:
                vendor_items[assigned_vendor] = []
            vendor_items[assigned_vendor].append(bi)

    if not vendor_items:
        return {"error": "Could not assign any items to vendors (no price data)"}

    # Generate PO number prefix
    date_str = order_dt.strftime("%Y%m%d")

    # Count existing POs today to get sequence number
    today_po_count = (await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            cast(PurchaseOrder.order_date, Date) == order_dt
        )
    )).scalar() or 0

    created_pos = []
    seq = today_po_count + 1

    for vid, items_for_vendor in vendor_items.items():
        po_number = f"PO-{date_str}-{str(seq).zfill(4)}"
        seq += 1

        total_amount = Decimal("0")
        po_item_rows = []

        for bi in items_for_vendor:
            iid = str(bi.item_id)
            prices = vp_map.get(iid, [])
            unit_price = None
            for p in prices:
                if p["vendor_id"] == vid:
                    unit_price = Decimal(str(p["unit_price"]))
                    break
            if unit_price is None and prices:
                unit_price = Decimal(str(prices[0]["unit_price"]))

            if unit_price is None:
                unit_price = bi.unit_price or Decimal("0")

            qty = bi.order_quantity or Decimal("0")
            subtotal = qty * unit_price
            total_amount += subtotal

            po_item_rows.append({
                "bom_item_id": bi.id,
                "item_id": bi.item_id,
                "item_name": bi.item_name,
                "quantity": qty,
                "unit": bi.unit,
                "unit_price": unit_price,
                "subtotal": subtotal,
            })

        tax_amount = total_amount * Decimal("0.1")  # 10% VAT

        po = PurchaseOrder(
            bom_id=bom_uuid,
            site_id=bom.site_id,
            vendor_id=UUID(vid),
            po_number=po_number,
            status="draft",
            order_date=order_dt,
            delivery_date=delivery_dt,
            total_amount=total_amount,
            tax_amount=tax_amount,
        )
        db.add(po)
        await db.flush()

        for poi_data in po_item_rows:
            poi = PurchaseOrderItem(
                po_id=po.id,
                bom_item_id=poi_data["bom_item_id"],
                item_id=poi_data["item_id"],
                item_name=poi_data["item_name"],
                quantity=poi_data["quantity"],
                unit=poi_data["unit"],
                unit_price=poi_data["unit_price"],
                subtotal=poi_data["subtotal"],
            )
            db.add(poi)

        created_pos.append({
            "po_id": str(po.id),
            "po_number": po_number,
            "vendor_id": vid,
            "items_count": len(po_item_rows),
            "total_amount": float(total_amount),
            "tax_amount": float(tax_amount),
            "delivery_date": delivery_date,
        })

    bom.status = "ordered" if len(vendor_items) == len({str(bi.item_id) for bi in bom_items}) else "partial"
    await db.flush()

    return {
        "purchase_orders_created": created_pos,
        "total_pos": len(created_pos),
        "vendor_strategy": vendor_strategy,
        "bom_id": bom_id,
        "note": "발주서 초안이 생성되었습니다. OPS 승인 후 제출 가능합니다. (SAFE-PUR-001)",
        "source": "[출처: 단가 이력 최신 기준]",
    }


async def compare_vendors(
    db: AsyncSession,
    item_ids: list[str],
    site_id: str | None = None,
    compare_period: int = 4,
) -> dict:
    """Compare vendor prices, lead days, and rating for given item IDs."""
    item_uuids = [UUID(iid) for iid in item_ids]

    # Load items
    items = (await db.execute(
        select(Item).where(Item.id.in_(item_uuids))
    )).scalars().all()
    items_map = {str(it.id): it for it in items}

    # Load vendor prices (current + history)
    cutoff_date = date.today() - timedelta(weeks=compare_period)
    vp_rows = (await db.execute(
        select(VendorPrice).where(
            VendorPrice.item_id.in_(item_uuids),
            VendorPrice.effective_from >= cutoff_date,
        ).order_by(VendorPrice.item_id, VendorPrice.vendor_id, VendorPrice.effective_from)
    )).scalars().all()

    # Load vendors
    vendor_ids = list({vp.vendor_id for vp in vp_rows})
    vendors_list = (await db.execute(
        select(Vendor).where(Vendor.id.in_(vendor_ids))
    )).scalars().all()
    vendors_map = {str(v.id): v for v in vendors_list}

    # Group by item_id → vendor_id → price_history
    from collections import defaultdict
    item_vendor_prices: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for vp in vp_rows:
        item_vendor_prices[str(vp.item_id)][str(vp.vendor_id)].append({
            "price": float(vp.unit_price),
            "date": str(vp.effective_from),
            "is_current": vp.is_current,
        })

    comparisons = []
    total_savings = 0.0

    for iid in item_ids:
        item = items_map.get(iid)
        if not item:
            continue

        vendor_list = []
        prices_by_vendor = item_vendor_prices.get(iid, {})

        for vid, price_hist in prices_by_vendor.items():
            vendor = vendors_map.get(vid)
            if not vendor:
                continue

            current_price = next((p["price"] for p in price_hist if p["is_current"]), None)
            if not current_price and price_hist:
                current_price = price_hist[-1]["price"]

            # Calculate price trend
            if len(price_hist) >= 2:
                oldest = price_hist[0]["price"]
                newest = price_hist[-1]["price"]
                trend_pct = round((newest - oldest) / oldest * 100, 1) if oldest > 0 else 0
                trend_str = f"{'+' if trend_pct >= 0 else ''}{trend_pct}%"
            else:
                trend_str = "0%"
                trend_pct = 0

            vendor_list.append({
                "vendor_id": vid,
                "name": vendor.name,
                "unit_price": current_price,
                "unit": item.unit,
                "lead_days": vendor.lead_days,
                "rating": float(vendor.rating),
                "price_trend": trend_str,
                "trend_pct": trend_pct,
                "price_history": price_hist[-4:],  # last 4 weeks
                "recommended": False,
            })

        # Mark lowest price as recommended
        if vendor_list:
            vendor_list.sort(key=lambda x: (x["unit_price"] or float("inf")))
            vendor_list[0]["recommended"] = True

            # Calculate potential savings vs highest price
            if len(vendor_list) >= 2:
                lowest = vendor_list[0]["unit_price"] or 0
                highest = max(v["unit_price"] or 0 for v in vendor_list)
                total_savings += (highest - lowest)

        comparisons.append({
            "item_id": iid,
            "item_name": item.name,
            "vendors": vendor_list,
        })

    return {
        "comparisons": comparisons,
        "total_items_compared": len(comparisons),
        "total_savings_if_optimized": round(total_savings, 2),
        "compare_period_weeks": compare_period,
        "source": f"[출처: 단가 이력 최근 {compare_period}주]",
    }


async def detect_price_risk(
    db: AsyncSession,
    site_id: str,
    threshold_pct: float = 15.0,
    compare_weeks: int = 1,
    menu_plan_id: str | None = None,
) -> dict:
    """Detect price spike items above threshold.

    Safety: SAFE-PUR-002 — alerts on price spikes and suggests alternatives.
    """
    site_uuid = UUID(site_id)
    cutoff_date = date.today() - timedelta(weeks=compare_weeks)
    older_cutoff = cutoff_date - timedelta(weeks=compare_weeks)

    # Get all current prices
    current_prices = (await db.execute(
        select(VendorPrice).where(
            VendorPrice.is_current == True,
        )
    )).scalars().all()

    # Get older prices for comparison
    older_prices = (await db.execute(
        select(VendorPrice).where(
            VendorPrice.effective_from >= older_cutoff,
            VendorPrice.effective_from < cutoff_date,
        )
    )).scalars().all()

    # Map item_id → lowest current price
    item_current: dict[str, float] = {}
    item_vendor: dict[str, str] = {}
    for vp in current_prices:
        iid = str(vp.item_id)
        price = float(vp.unit_price)
        if iid not in item_current or price < item_current[iid]:
            item_current[iid] = price
            item_vendor[iid] = str(vp.vendor_id)

    # Map item_id → lowest older price
    item_older: dict[str, float] = {}
    for vp in older_prices:
        iid = str(vp.item_id)
        price = float(vp.unit_price)
        if iid not in item_older or price < item_older[iid]:
            item_older[iid] = price

    # Find risk items
    risk_items = []
    for iid, current_price in item_current.items():
        older_price = item_older.get(iid)
        if older_price is None or older_price <= 0:
            continue
        change_pct = (current_price - older_price) / older_price * 100
        if change_pct >= threshold_pct:
            risk_items.append({
                "item_id": iid,
                "current_price": current_price,
                "previous_price": older_price,
                "change_pct": round(change_pct, 1),
                "vendor_id": item_vendor.get(iid),
            })

    risk_items.sort(key=lambda x: x["change_pct"], reverse=True)

    # Load item names
    risk_item_uuids = [UUID(ri["item_id"]) for ri in risk_items]
    if risk_item_uuids:
        items_list = (await db.execute(
            select(Item).where(Item.id.in_(risk_item_uuids))
        )).scalars().all()
        items_name_map = {str(it.id): it.name for it in items_list}
        for ri in risk_items:
            ri["item_name"] = items_name_map.get(ri["item_id"], "Unknown")

    # Find affected menu plans if provided
    affected_menus = []
    estimated_cost_increase = 0.0
    if menu_plan_id and risk_items:
        plan_uuid = UUID(menu_plan_id)
        plan = (await db.execute(select(MenuPlan).where(MenuPlan.id == plan_uuid))).scalar_one_or_none()
        if plan:
            affected_menus.append({
                "menu_plan_id": menu_plan_id,
                "title": plan.title,
                "period_start": str(plan.period_start),
                "period_end": str(plan.period_end),
                "headcount": plan.target_headcount,
            })

    suggested_actions = []
    for ri in risk_items[:3]:  # Top 3 risk items
        suggested_actions.append(f"{ri.get('item_name', ri['item_id'])} 대체품 검토 또는 벤더 재협상 필요 (SAFE-PUR-002)")

    return {
        "site_id": site_id,
        "threshold_pct": threshold_pct,
        "compare_weeks": compare_weeks,
        "risk_items": risk_items,
        "risk_items_count": len(risk_items),
        "affected_menus": affected_menus,
        "estimated_cost_increase": estimated_cost_increase,
        "suggested_actions": suggested_actions,
        "source": f"[출처: 단가 이력 {compare_weeks}주 전 대비]",
    }


async def suggest_alternatives(
    db: AsyncSession,
    item_id: str,
    site_id: str,
    reason: str = "price_spike",
    allergen_policy_id: str | None = None,
) -> dict:
    """Suggest alternative items based on substitute_group and substitute_items.

    Safety: SAFE-PUR-002 — allergen check is mandatory.
    """
    item_uuid = UUID(item_id)
    item = (await db.execute(select(Item).where(Item.id == item_uuid))).scalar_one_or_none()
    if not item:
        return {"error": "Item not found"}

    alternatives = []

    # 1. Direct substitute_items (highest priority)
    if item.substitute_items:
        sub_items = (await db.execute(
            select(Item).where(
                Item.id.in_(item.substitute_items),
                Item.is_active == True,
            )
        )).scalars().all()
        for sub in sub_items:
            alternatives.append({
                "item_id": str(sub.id),
                "item_name": sub.name,
                "category": sub.category,
                "unit": sub.unit,
                "allergens": sub.allergens or [],
                "relation": "direct_substitute",
                "allergen_warning": bool(set(sub.allergens or []) & set(item.allergens or [])),
            })

    # 2. Same substitute_group
    if item.substitute_group:
        group_items = (await db.execute(
            select(Item).where(
                Item.substitute_group == item.substitute_group,
                Item.id != item_uuid,
                Item.is_active == True,
            )
        )).scalars().all()
        existing_ids = {a["item_id"] for a in alternatives}
        for gi in group_items:
            if str(gi.id) not in existing_ids:
                alternatives.append({
                    "item_id": str(gi.id),
                    "item_name": gi.name,
                    "category": gi.category,
                    "unit": gi.unit,
                    "allergens": gi.allergens or [],
                    "relation": "same_group",
                    "allergen_warning": bool(set(gi.allergens or []) & set(item.allergens or [])),
                })

    # 3. Enrich with current prices
    alt_ids = [UUID(a["item_id"]) for a in alternatives]
    if alt_ids:
        vp_rows = (await db.execute(
            select(VendorPrice).where(
                VendorPrice.item_id.in_(alt_ids),
                VendorPrice.is_current == True,
            ).order_by(VendorPrice.unit_price)
        )).scalars().all()

        best_price_map: dict[str, float] = {}
        for vp in vp_rows:
            iid = str(vp.item_id)
            if iid not in best_price_map:
                best_price_map[iid] = float(vp.unit_price)

        for alt in alternatives:
            alt["current_price"] = best_price_map.get(alt["item_id"])

    # Get original item price for comparison
    orig_vp = (await db.execute(
        select(VendorPrice).where(
            VendorPrice.item_id == item_uuid,
            VendorPrice.is_current == True,
        ).order_by(VendorPrice.unit_price).limit(1)
    )).scalar_one_or_none()
    original_price = float(orig_vp.unit_price) if orig_vp else None

    return {
        "original_item": {
            "item_id": item_id,
            "item_name": item.name,
            "category": item.category,
            "allergens": item.allergens or [],
            "current_price": original_price,
        },
        "reason": reason,
        "alternatives": alternatives,
        "alternatives_count": len(alternatives),
        "allergen_warning": "대체품 사용 전 알레르겐 정책 재확인 필수 (SAFE-PUR-002)",
        "source": "[출처: 식재료 마스터 + 단가 이력]",
    }


async def check_inventory(
    db: AsyncSession,
    site_id: str,
    item_ids: list[str] | None = None,
    alert_days: int = 7,
    include_lots: bool = False,
) -> dict:
    """Check current inventory status. Highlights expiring soon and below-minimum items."""
    site_uuid = UUID(site_id)

    query = select(Inventory).where(Inventory.site_id == site_uuid)
    if item_ids:
        query = query.where(Inventory.item_id.in_([UUID(iid) for iid in item_ids]))

    inv_rows = (await db.execute(query)).scalars().all()

    # Load item names
    inv_item_ids = [inv.item_id for inv in inv_rows]
    items_list = (await db.execute(
        select(Item).where(Item.id.in_(inv_item_ids))
    )).scalars().all() if inv_item_ids else []
    items_map = {str(it.id): it for it in items_list}

    # Expiry alert: lots expiring within alert_days
    alert_date = date.today() + timedelta(days=alert_days)
    expiring_lots = (await db.execute(
        select(InventoryLot).where(
            InventoryLot.site_id == site_uuid,
            InventoryLot.expiry_date <= alert_date,
            InventoryLot.expiry_date >= date.today(),
            InventoryLot.status.in_(["active", "partially_used"]),
        ).order_by(InventoryLot.expiry_date)
    )).scalars().all()

    result_items = []
    low_stock_count = 0
    expiry_alert_count = 0

    for inv in inv_rows:
        iid = str(inv.item_id)
        item = items_map.get(iid)

        is_low = bool(inv.min_qty and inv.quantity < inv.min_qty)
        if is_low:
            low_stock_count += 1

        row = {
            "item_id": iid,
            "item_name": item.name if item else iid,
            "category": item.category if item else None,
            "quantity": float(inv.quantity),
            "unit": inv.unit,
            "location": inv.location,
            "min_qty": float(inv.min_qty) if inv.min_qty else None,
            "is_low_stock": is_low,
            "last_updated": inv.last_updated.isoformat() if inv.last_updated else None,
        }
        result_items.append(row)

    # Sort: low stock first, then by item name
    result_items.sort(key=lambda x: (not x["is_low_stock"], x["item_name"]))

    expiry_warnings = []
    for lot in expiring_lots:
        days_left = (lot.expiry_date - date.today()).days
        iid = str(lot.item_id)
        item = items_map.get(iid)
        expiry_warnings.append({
            "lot_id": str(lot.id),
            "item_id": iid,
            "item_name": item.name if item else iid,
            "lot_number": lot.lot_number,
            "quantity": float(lot.quantity),
            "unit": lot.unit,
            "expiry_date": str(lot.expiry_date),
            "days_until_expiry": days_left,
            "severity": "critical" if days_left <= 3 else "warning",
        })
        expiry_alert_count += 1

    lots_data = []
    if include_lots:
        lot_query = select(InventoryLot).where(
            InventoryLot.site_id == site_uuid,
            InventoryLot.status.in_(["active", "partially_used"]),
        ).order_by(InventoryLot.expiry_date)
        if item_ids:
            lot_query = lot_query.where(InventoryLot.item_id.in_([UUID(iid) for iid in item_ids]))
        lots = (await db.execute(lot_query)).scalars().all()
        for lot in lots:
            iid = str(lot.item_id)
            item = items_map.get(iid)
            lots_data.append({
                "lot_id": str(lot.id),
                "item_id": iid,
                "item_name": item.name if item else iid,
                "lot_number": lot.lot_number,
                "quantity": float(lot.quantity),
                "unit": lot.unit,
                "expiry_date": str(lot.expiry_date) if lot.expiry_date else None,
                "status": lot.status,
                "received_at": lot.received_at.isoformat() if lot.received_at else None,
            })

    return {
        "site_id": site_id,
        "inventory_items": result_items,
        "total_items": len(result_items),
        "low_stock_count": low_stock_count,
        "expiry_alerts": expiry_warnings,
        "expiry_alert_count": expiry_alert_count,
        "alert_days": alert_days,
        "lots": lots_data if include_lots else [],
        "source": f"[출처: 재고 현황 {datetime.now().strftime('%Y-%m-%d %H:%M')} 기준]",
    }
