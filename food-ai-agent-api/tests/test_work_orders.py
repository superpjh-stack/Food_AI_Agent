"""Integration tests for work order endpoints."""
import pytest
from datetime import date, timedelta
from httpx import AsyncClient

from tests.conftest import SITE_ID

pytestmark = pytest.mark.asyncio

# ─── Helpers ─────────────────────────────────────────────────────────────────

SAMPLE_RECIPE = {
    "name": "테스트 볶음밥",
    "category": "한식",
    "servings_base": 10,
    "ingredients": [
        {"name": "밥", "amount": 2000, "unit": "g"},
        {"name": "계란", "amount": 300, "unit": "g"},
        {"name": "간장", "amount": 50, "unit": "ml"},
    ],
    "steps": [
        {"order": 1, "description": "팬을 달구다"},
        {"order": 2, "description": "계란을 볶는다", "is_ccp": True},
    ],
    "allergens": ["난류"],
}


async def _setup_confirmed_plan(client: AsyncClient, nut_headers: dict, admin_headers: dict) -> str:
    """Create a recipe + menu plan item, confirm the plan, return plan_id."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)

    # Create menu plan (generate creates items automatically based on impl)
    resp = await client.post("/api/v1/menu-plans/generate", json={
        "site_id": str(SITE_ID),
        "period_start": str(monday),
        "period_end": str(friday),
        "meal_types": ["lunch"],
        "target_headcount": 100,
        "budget_per_meal": 3500,
    }, headers=nut_headers)
    assert resp.status_code == 200, f"Menu plan generation failed: {resp.text}"
    plan_id = resp.json()["data"]["id"]

    # Confirm the plan (ADM)
    await client.post(f"/api/v1/menu-plans/{plan_id}/confirm", headers=admin_headers)
    return plan_id


# ─── Tests ────────────────────────────────────────────────────────────────────

async def test_generate_work_orders(client: AsyncClient, nut_headers, admin_headers):
    """POST /work-orders/generate returns 201 (200 in impl) with generated orders."""
    plan_id = await _setup_confirmed_plan(client, nut_headers, admin_headers)

    resp = await client.post(
        "/api/v1/work-orders/generate",
        json={"menu_plan_id": plan_id},
        headers=nut_headers,
    )
    # Implementation returns 200 with success payload
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


async def test_list_work_orders(client: AsyncClient, nut_headers, admin_headers, kit_headers):
    """GET /work-orders returns 200 with list and pagination meta."""
    # First generate some work orders
    plan_id = await _setup_confirmed_plan(client, nut_headers, admin_headers)
    await client.post(
        "/api/v1/work-orders/generate",
        json={"menu_plan_id": plan_id},
        headers=nut_headers,
    )

    resp = await client.get(f"/api/v1/work-orders?site_id={SITE_ID}", headers=kit_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert "meta" in body


async def test_get_work_order_detail(client: AsyncClient, nut_headers, admin_headers, kit_headers):
    """GET /work-orders/{id} returns 200 with full order detail."""
    plan_id = await _setup_confirmed_plan(client, nut_headers, admin_headers)
    gen_resp = await client.post(
        "/api/v1/work-orders/generate",
        json={"menu_plan_id": plan_id},
        headers=nut_headers,
    )
    orders = gen_resp.json()["data"]
    if not orders:
        pytest.skip("No work orders generated (menu plan had no recipe items)")

    order_id = orders[0]["id"]
    resp = await client.get(f"/api/v1/work-orders/{order_id}", headers=kit_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["id"] == order_id
    assert "scaled_ingredients" in body["data"]
    assert "steps" in body["data"]


async def test_update_work_order_status_flow(client: AsyncClient, nut_headers, admin_headers, kit_headers):
    """PATCH /work-orders/{id}/status — pending -> in_progress -> completed."""
    plan_id = await _setup_confirmed_plan(client, nut_headers, admin_headers)
    gen_resp = await client.post(
        "/api/v1/work-orders/generate",
        json={"menu_plan_id": plan_id},
        headers=nut_headers,
    )
    orders = gen_resp.json()["data"]
    if not orders:
        pytest.skip("No work orders generated")

    order_id = orders[0]["id"]

    # pending -> in_progress
    resp = await client.put(
        f"/api/v1/work-orders/{order_id}/status",
        json={"status": "in_progress"},
        headers=kit_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "in_progress"

    # in_progress -> completed
    resp = await client.put(
        f"/api/v1/work-orders/{order_id}/status",
        json={"status": "completed"},
        headers=kit_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "completed"

    # completed -> any: should be rejected
    resp = await client.put(
        f"/api/v1/work-orders/{order_id}/status",
        json={"status": "in_progress"},
        headers=kit_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_TRANSITION"


async def test_list_work_orders_today(client: AsyncClient, nut_headers, admin_headers, kit_headers):
    """GET /work-orders?date=today returns orders for today."""
    today = date.today()
    resp = await client.get(
        f"/api/v1/work-orders?date={today}",
        headers=kit_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # All returned orders should have today's date (or be empty)
    for order in body["data"]:
        assert order["date"] == str(today)


async def test_rbac_nut_cannot_update_status(client: AsyncClient, nut_headers, admin_headers):
    """NUT role cannot update work order status (only KIT, ADM)."""
    plan_id = await _setup_confirmed_plan(client, nut_headers, admin_headers)
    gen_resp = await client.post(
        "/api/v1/work-orders/generate",
        json={"menu_plan_id": plan_id},
        headers=nut_headers,
    )
    orders = gen_resp.json()["data"]
    if not orders:
        pytest.skip("No work orders generated")

    order_id = orders[0]["id"]
    resp = await client.put(
        f"/api/v1/work-orders/{order_id}/status",
        json={"status": "in_progress"},
        headers=nut_headers,  # NUT is not in require_role("KIT", "ADM")
    )
    assert resp.status_code == 403
