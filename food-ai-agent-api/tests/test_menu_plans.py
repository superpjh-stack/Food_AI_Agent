"""Integration tests for menu plan endpoints."""
import pytest
from datetime import date, timedelta
from httpx import AsyncClient

from tests.conftest import SITE_ID

pytestmark = pytest.mark.asyncio


async def test_generate_menu_plan(client: AsyncClient, nut_headers):
    """NUT can generate a menu plan."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)

    resp = await client.post("/api/v1/menu-plans/generate", json={
        "site_id": str(SITE_ID),
        "period_start": str(monday),
        "period_end": str(friday),
        "meal_types": ["lunch"],
        "target_headcount": 200,
        "budget_per_meal": 3500,
    }, headers=nut_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["status"] == "draft"
    assert data["data"]["target_headcount"] == 200


async def test_generate_menu_plan_unauthorized(client: AsyncClient, kit_headers):
    """KIT cannot generate menu plans."""
    today = date.today()
    resp = await client.post("/api/v1/menu-plans/generate", json={
        "site_id": str(SITE_ID),
        "period_start": str(today),
        "period_end": str(today + timedelta(days=4)),
        "meal_types": ["lunch"],
        "target_headcount": 100,
    }, headers=kit_headers)
    assert resp.status_code == 403


async def test_list_menu_plans(client: AsyncClient, nut_headers):
    """List menu plans returns paginated results."""
    # Create a plan first
    today = date.today()
    await client.post("/api/v1/menu-plans/generate", json={
        "site_id": str(SITE_ID),
        "period_start": str(today),
        "period_end": str(today + timedelta(days=4)),
        "meal_types": ["lunch"],
        "target_headcount": 100,
    }, headers=nut_headers)

    resp = await client.get("/api/v1/menu-plans", headers=nut_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "data" in data
    assert "meta" in data
    assert data["meta"]["page"] == 1


async def test_list_menu_plans_filter_by_site(client: AsyncClient, nut_headers):
    """List menu plans can filter by site_id."""
    resp = await client.get(
        f"/api/v1/menu-plans?site_id={SITE_ID}",
        headers=nut_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


async def test_get_menu_plan_detail(client: AsyncClient, nut_headers):
    """Get menu plan by ID returns details with items."""
    today = date.today()
    create_resp = await client.post("/api/v1/menu-plans/generate", json={
        "site_id": str(SITE_ID),
        "period_start": str(today),
        "period_end": str(today + timedelta(days=4)),
        "meal_types": ["lunch"],
        "target_headcount": 100,
    }, headers=nut_headers)
    plan_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/api/v1/menu-plans/{plan_id}", headers=nut_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["id"] == plan_id


async def test_get_nonexistent_plan(client: AsyncClient, nut_headers):
    """Get non-existent plan returns NOT_FOUND."""
    fake_id = "00000000-0000-0000-0000-999999999999"
    resp = await client.get(f"/api/v1/menu-plans/{fake_id}", headers=nut_headers)
    assert resp.status_code == 200  # Returns 200 with error body
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"


async def test_validate_menu_plan(client: AsyncClient, nut_headers):
    """Validate menu plan runs nutrition checks."""
    today = date.today()
    create_resp = await client.post("/api/v1/menu-plans/generate", json={
        "site_id": str(SITE_ID),
        "period_start": str(today),
        "period_end": str(today + timedelta(days=4)),
        "meal_types": ["lunch"],
        "target_headcount": 100,
    }, headers=nut_headers)
    plan_id = create_resp.json()["data"]["id"]

    resp = await client.post(f"/api/v1/menu-plans/{plan_id}/validate", headers=nut_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "overall_status" in data["data"]
    assert data["data"]["policy"] is not None


async def test_confirm_menu_plan(client: AsyncClient, nut_headers, admin_headers):
    """ADM can confirm a menu plan."""
    today = date.today()
    create_resp = await client.post("/api/v1/menu-plans/generate", json={
        "site_id": str(SITE_ID),
        "period_start": str(today),
        "period_end": str(today + timedelta(days=4)),
        "meal_types": ["lunch"],
        "target_headcount": 100,
    }, headers=nut_headers)
    plan_id = create_resp.json()["data"]["id"]

    resp = await client.post(f"/api/v1/menu-plans/{plan_id}/confirm", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["status"] == "confirmed"


async def test_confirm_unauthorized(client: AsyncClient, nut_headers):
    """NUT cannot confirm menu plans (only OPS/ADM)."""
    today = date.today()
    create_resp = await client.post("/api/v1/menu-plans/generate", json={
        "site_id": str(SITE_ID),
        "period_start": str(today),
        "period_end": str(today + timedelta(days=4)),
        "meal_types": ["lunch"],
        "target_headcount": 100,
    }, headers=nut_headers)
    plan_id = create_resp.json()["data"]["id"]

    resp = await client.post(f"/api/v1/menu-plans/{plan_id}/confirm", headers=nut_headers)
    assert resp.status_code == 403


async def test_update_menu_plan(client: AsyncClient, nut_headers):
    """NUT can update menu plan fields."""
    today = date.today()
    create_resp = await client.post("/api/v1/menu-plans/generate", json={
        "site_id": str(SITE_ID),
        "period_start": str(today),
        "period_end": str(today + timedelta(days=4)),
        "meal_types": ["lunch"],
        "target_headcount": 100,
    }, headers=nut_headers)
    plan_id = create_resp.json()["data"]["id"]

    resp = await client.put(f"/api/v1/menu-plans/{plan_id}", json={
        "title": "Updated Title",
        "target_headcount": 250,
    }, headers=nut_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
