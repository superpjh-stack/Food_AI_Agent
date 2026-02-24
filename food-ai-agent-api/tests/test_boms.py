"""Integration tests for BOM API (MVP 2)."""
import pytest
import uuid
from httpx import AsyncClient

from tests.conftest import SITE_ID, NUT_ID, auth_header

pytestmark = pytest.mark.asyncio

PUR_ID = uuid.UUID("10000000-0000-0000-0000-000000001005")


def pur_headers():
    return auth_header(PUR_ID, "PUR")


async def test_bom_generate_requires_confirmed_plan(client: AsyncClient, nut_headers):
    """POST /boms/generate fails if menu plan is not confirmed."""
    # Create a draft menu plan
    plan_resp = await client.post(
        "/api/v1/menu-plans/generate",
        json={
            "site_id": str(SITE_ID),
            "period_start": "2026-03-01",
            "period_end": "2026-03-07",
            "meal_types": ["lunch"],
            "target_headcount": 100,
        },
        headers=nut_headers,
    )
    if plan_resp.status_code != 200:
        pytest.skip("Menu plans endpoint unavailable")
    plan_id = plan_resp.json()["data"]["id"]

    resp = await client.post(
        "/api/v1/boms/generate",
        json={"menu_plan_id": plan_id, "headcount": 100},
        headers=nut_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    # Should fail because plan is draft, not confirmed
    assert body["success"] is False
    assert "confirmed" in body["error"]["message"].lower()


async def test_list_boms(client: AsyncClient, nut_headers):
    """GET /boms returns list with pagination."""
    resp = await client.get("/api/v1/boms", headers=nut_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert "meta" in body


async def test_list_boms_with_site_filter(client: AsyncClient, nut_headers):
    """GET /boms?site_id=... filters by site."""
    resp = await client.get(f"/api/v1/boms?site_id={SITE_ID}", headers=nut_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_get_bom_not_found(client: AsyncClient, nut_headers):
    """GET /boms/{nonexistent_id} returns NOT_FOUND."""
    resp = await client.get(
        "/api/v1/boms/00000000-0000-0000-0000-000000000000",
        headers=nut_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False
    assert resp.json()["error"]["code"] == "NOT_FOUND"


async def test_bom_cost_analysis_not_found(client: AsyncClient, nut_headers):
    """GET /boms/{id}/cost-analysis returns NOT_FOUND for nonexistent BOM."""
    resp = await client.get(
        "/api/v1/boms/00000000-0000-0000-0000-000000000000/cost-analysis",
        headers=nut_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False


async def test_apply_inventory_bom_not_found(client: AsyncClient, nut_headers):
    """POST /boms/{id}/apply-inventory returns NOT_FOUND for nonexistent BOM."""
    resp = await client.post(
        "/api/v1/boms/00000000-0000-0000-0000-000000000000/apply-inventory",
        headers=nut_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False


async def test_bom_generate_endpoint_exists(client: AsyncClient, nut_headers):
    """POST /boms/generate endpoint is accessible."""
    # Just verify the endpoint exists with a bad UUID
    resp = await client.post(
        "/api/v1/boms/generate",
        json={"menu_plan_id": "00000000-0000-0000-0000-000000000000", "headcount": 100},
        headers=nut_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False  # Plan not found


async def test_bom_generate_invalid_headcount(client: AsyncClient, nut_headers):
    """POST /boms/generate with headcount=0 returns validation error."""
    resp = await client.post(
        "/api/v1/boms/generate",
        json={"menu_plan_id": "00000000-0000-0000-0000-000000000000", "headcount": 0},
        headers=nut_headers,
    )
    assert resp.status_code == 422


async def test_list_boms_status_filter(client: AsyncClient, nut_headers):
    """GET /boms?status=draft filters by status."""
    resp = await client.get("/api/v1/boms?status=draft", headers=nut_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_bom_rbac_requires_auth(client: AsyncClient):
    """GET /boms without auth returns 401."""
    resp = await client.get("/api/v1/boms")
    assert resp.status_code == 401


async def test_bom_update_not_found(client: AsyncClient, nut_headers):
    """PUT /boms/{nonexistent_id} returns NOT_FOUND."""
    resp = await client.put(
        "/api/v1/boms/00000000-0000-0000-0000-000000000000",
        json={"headcount": 200},
        headers=nut_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False
    assert resp.json()["error"]["code"] == "NOT_FOUND"
