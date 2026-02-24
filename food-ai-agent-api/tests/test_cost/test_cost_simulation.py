"""Integration tests for cost simulation."""
import pytest
from httpx import AsyncClient

from tests.conftest import SITE_ID

pytestmark = pytest.mark.asyncio


async def _get_confirmed_menu_plan_id(client: AsyncClient, ops_headers: dict) -> str | None:
    """Helper: find a confirmed menu plan for cost simulation."""
    resp = await client.get(
        f"/api/v1/menu-plans?site_id={SITE_ID}&status=confirmed&per_page=1",
        headers=ops_headers,
    )
    if resp.status_code != 200:
        return None
    data = resp.json().get("data", [])
    return data[0]["id"] if data else None


async def test_simulate_within_budget(client: AsyncClient, ops_headers: dict):
    """simulate_cost with target far above estimated → alert=none."""
    plan_id = await _get_confirmed_menu_plan_id(client, ops_headers)
    if not plan_id:
        pytest.skip("No confirmed menu plan available")

    resp = await client.post(
        "/api/v1/cost/simulate",
        json={
            "site_id": str(SITE_ID),
            "menu_plan_id": plan_id,
            "target_cost_per_meal": 99999,  # Very high target → should be within budget
            "headcount": 300,
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    result = data["data"]
    assert result["alert_triggered"] == "none"
    assert result["variance_pct"] < 0  # Under budget


async def test_simulate_over_budget_warning(client: AsyncClient, ops_headers: dict):
    """simulate_cost with target 15% below estimated → alert=warning."""
    plan_id = await _get_confirmed_menu_plan_id(client, ops_headers)
    if not plan_id:
        pytest.skip("No confirmed menu plan available")

    # First simulate to get actual estimated cost
    resp1 = await client.post(
        "/api/v1/cost/simulate",
        json={
            "site_id": str(SITE_ID),
            "menu_plan_id": plan_id,
            "target_cost_per_meal": 99999,
            "headcount": 300,
        },
        headers=ops_headers,
    )
    if resp1.status_code != 200 or not resp1.json().get("success"):
        pytest.skip("Could not get cost estimate")

    estimated = resp1.json()["data"]["estimated_cost_per_meal"]
    if estimated <= 0:
        pytest.skip("No cost data available")

    # Now set target 15% below estimated
    target = estimated * 0.85
    resp2 = await client.post(
        "/api/v1/cost/simulate",
        json={
            "site_id": str(SITE_ID),
            "menu_plan_id": plan_id,
            "target_cost_per_meal": target,
            "headcount": 300,
        },
        headers=ops_headers,
    )
    assert resp2.status_code == 200
    result = resp2.json()["data"]
    assert result["alert_triggered"] in ("warning", "critical")


async def test_simulate_over_budget_critical(client: AsyncClient, ops_headers: dict):
    """simulate_cost with very low target → alert=critical."""
    plan_id = await _get_confirmed_menu_plan_id(client, ops_headers)
    if not plan_id:
        pytest.skip("No confirmed menu plan available")

    resp = await client.post(
        "/api/v1/cost/simulate",
        json={
            "site_id": str(SITE_ID),
            "menu_plan_id": plan_id,
            "target_cost_per_meal": 1,  # Impossibly low target
            "headcount": 300,
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # May fail if no ingredients → success=False
    if not data["success"]:
        pytest.skip("No ingredient data for cost simulation")

    result = data["data"]
    if result["estimated_cost_per_meal"] > 0:
        assert result["alert_triggered"] == "critical"
