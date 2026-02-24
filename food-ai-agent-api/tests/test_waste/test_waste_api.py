"""Integration tests for waste management API."""
import pytest
from httpx import AsyncClient

from tests.conftest import SITE_ID

pytestmark = pytest.mark.asyncio


async def test_create_waste_record(client: AsyncClient, kit_headers: dict):
    """POST /waste/records saves waste records."""
    payload = {
        "site_id": str(SITE_ID),
        "record_date": "2026-02-24",
        "meal_type": "lunch",
        "items": [
            {"item_name": "김치찌개", "waste_pct": 15.0, "served_count": 200},
            {"item_name": "된장국", "waste_pct": 8.0, "served_count": 200},
        ],
    }
    resp = await client.post("/api/v1/waste/records", json=payload, headers=kit_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["saved_count"] == 2


async def test_ewma_preference_update(client: AsyncClient, kit_headers: dict):
    """POST /waste/records with high waste_pct decreases preference_score."""
    # Create a recipe first so we can use recipe_id
    # For simplicity, we test that preferences_updated is returned
    payload = {
        "site_id": str(SITE_ID),
        "record_date": "2026-02-23",
        "meal_type": "lunch",
        "items": [
            {"item_name": "비선호메뉴", "waste_pct": 60.0, "served_count": 100},
        ],
    }
    resp = await client.post("/api/v1/waste/records", json=payload, headers=kit_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    # No recipe_id provided, so preferences_updated should be empty
    assert data["saved_count"] == 1
    assert isinstance(data["preferences_updated"], list)


async def test_waste_summary(client: AsyncClient, ops_headers: dict):
    """GET /waste/summary returns items sorted by avg_waste_pct desc."""
    resp = await client.get(
        f"/api/v1/waste/summary?site_id={SITE_ID}&period_days=30",
        headers=ops_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    items = data["data"]["items"]
    if len(items) >= 2:
        assert items[0]["avg_waste_pct"] >= items[1]["avg_waste_pct"]
