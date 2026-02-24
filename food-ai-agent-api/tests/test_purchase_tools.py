"""Unit tests for purchase agent tools (MVP 2)."""
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


class MockItem:
    def __init__(self, item_id, name, category, unit, allergens=None, substitute_items=None, substitute_group=None):
        self.id = uuid.UUID(item_id) if isinstance(item_id, str) else item_id
        self.name = name
        self.category = category
        self.unit = unit
        self.allergens = allergens or []
        self.substitute_items = substitute_items or []
        self.substitute_group = substitute_group
        self.is_active = True


async def test_calculate_bom_menu_not_found():
    """calculate_bom returns error when menu plan not found."""
    from app.agents.tools.purchase_tools import calculate_bom

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

    result = await calculate_bom(db, "00000000-0000-0000-0000-000000000000", 100)
    assert "error" in result
    assert "not found" in result["error"].lower()


async def test_calculate_bom_non_confirmed_plan():
    """calculate_bom returns SAFE-PUR-001 error if plan is not confirmed."""
    from app.agents.tools.purchase_tools import calculate_bom

    mock_plan = MagicMock()
    mock_plan.status = "draft"

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: mock_plan))

    result = await calculate_bom(db, "00000000-0000-0000-0000-000000000000", 100)
    assert "error" in result
    assert "confirmed" in result["error"]


async def test_check_inventory_site_required():
    """check_inventory returns site_id in response."""
    from app.agents.tools.purchase_tools import check_inventory

    db = AsyncMock(spec=AsyncSession)
    # Return empty lists for all queries
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=empty_result)

    result = await check_inventory(db, "00000000-0000-0000-0000-000000000001")
    assert result["site_id"] == "00000000-0000-0000-0000-000000000001"
    assert "inventory_items" in result
    assert "expiry_alerts" in result


async def test_check_inventory_empty_site():
    """check_inventory returns empty lists for site with no inventory."""
    from app.agents.tools.purchase_tools import check_inventory

    db = AsyncMock(spec=AsyncSession)
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=empty_result)

    result = await check_inventory(db, "00000000-0000-0000-0000-000000000001", alert_days=7)
    assert result["total_items"] == 0
    assert result["low_stock_count"] == 0
    assert result["expiry_alert_count"] == 0


async def test_suggest_alternatives_item_not_found():
    """suggest_alternatives returns error when item not found."""
    from app.agents.tools.purchase_tools import suggest_alternatives

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

    result = await suggest_alternatives(db, "00000000-0000-0000-0000-000000000000", "site123")
    assert "error" in result
    assert "not found" in result["error"].lower()


async def test_suggest_alternatives_returns_structure():
    """suggest_alternatives returns expected structure with original_item."""
    from app.agents.tools.purchase_tools import suggest_alternatives

    mock_item = MockItem("00000000-0000-0000-0000-000000000001", "양파", "채소", "kg")

    db = AsyncMock(spec=AsyncSession)
    # First call returns the item, subsequent calls return empty
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []

    item_result = MagicMock()
    item_result.scalar_one_or_none = lambda: mock_item

    db.execute = AsyncMock(side_effect=[item_result, empty_result, empty_result, empty_result])

    result = await suggest_alternatives(db, "00000000-0000-0000-0000-000000000001", "site123")
    assert "original_item" in result
    assert result["original_item"]["item_name"] == "양파"
    assert "alternatives" in result
    assert "allergen_warning" in result


async def test_detect_price_risk_returns_structure():
    """detect_price_risk returns expected structure."""
    from app.agents.tools.purchase_tools import detect_price_risk

    db = AsyncMock(spec=AsyncSession)
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=empty_result)

    result = await detect_price_risk(db, "00000000-0000-0000-0000-000000000001")
    assert "risk_items" in result
    assert "site_id" in result
    assert "threshold_pct" in result


async def test_compare_vendors_returns_structure():
    """compare_vendors returns expected structure."""
    from app.agents.tools.purchase_tools import compare_vendors

    db = AsyncMock(spec=AsyncSession)
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=empty_result)

    result = await compare_vendors(db, ["00000000-0000-0000-0000-000000000001"])
    assert "comparisons" in result
    assert "total_savings_if_optimized" in result


async def test_generate_purchase_order_bom_not_found():
    """generate_purchase_order returns error when BOM not found."""
    from app.agents.tools.purchase_tools import generate_purchase_order

    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))

    result = await generate_purchase_order(
        db, "00000000-0000-0000-0000-000000000000", "2026-03-05"
    )
    assert "error" in result
    assert "not found" in result["error"].lower()


async def test_check_inventory_source_citation():
    """check_inventory result includes source citation."""
    from app.agents.tools.purchase_tools import check_inventory

    db = AsyncMock(spec=AsyncSession)
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=empty_result)

    result = await check_inventory(db, "00000000-0000-0000-0000-000000000001")
    assert "source" in result
    assert "[출처:" in result["source"]
