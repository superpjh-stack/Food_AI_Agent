"""Integration tests for Vendor API (MVP 2)."""
import pytest
from httpx import AsyncClient

from tests.conftest import SITE_ID

pytestmark = pytest.mark.asyncio

SAMPLE_VENDOR = {
    "name": "테스트청과",
    "business_no": "111-22-33444",
    "contact": {"phone": "02-1111-2222", "email": "test@vendor.com", "rep": "홍길동"},
    "categories": ["채소", "과일"],
    "lead_days": 1,
    "rating": "4.5",
    "notes": "테스트 벤더",
}


async def _create_vendor(client: AsyncClient, admin_headers: dict) -> str:
    resp = await client.post("/api/v1/vendors", json=SAMPLE_VENDOR, headers=admin_headers)
    assert resp.status_code == 200, f"Create vendor failed: {resp.text}"
    return resp.json()["data"]["id"]


async def test_create_vendor(client: AsyncClient, admin_headers):
    """POST /vendors creates a vendor (ADM only)."""
    resp = await client.post("/api/v1/vendors", json=SAMPLE_VENDOR, headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["name"] == SAMPLE_VENDOR["name"]
    assert body["data"]["is_active"] is True


async def test_list_vendors(client: AsyncClient, admin_headers):
    """GET /vendors returns paginated list."""
    await _create_vendor(client, admin_headers)
    resp = await client.get("/api/v1/vendors", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert "meta" in body


async def test_get_vendor(client: AsyncClient, admin_headers):
    """GET /vendors/{id} returns vendor detail."""
    vendor_id = await _create_vendor(client, admin_headers)
    resp = await client.get(f"/api/v1/vendors/{vendor_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == vendor_id


async def test_update_vendor(client: AsyncClient, admin_headers):
    """PUT /vendors/{id} updates vendor fields."""
    vendor_id = await _create_vendor(client, admin_headers)
    resp = await client.put(
        f"/api/v1/vendors/{vendor_id}",
        json={"notes": "업데이트된 메모", "lead_days": 2},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["notes"] == "업데이트된 메모"
    assert data["lead_days"] == 2


async def test_deactivate_vendor(client: AsyncClient, admin_headers):
    """DELETE /vendors/{id} deactivates vendor."""
    vendor_id = await _create_vendor(client, admin_headers)
    resp = await client.delete(f"/api/v1/vendors/{vendor_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] is False


async def test_vendor_not_found(client: AsyncClient, admin_headers):
    """GET /vendors/{nonexistent_id} returns NOT_FOUND."""
    resp = await client.get(
        "/api/v1/vendors/00000000-0000-0000-0000-000000000000",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


async def test_rbac_requires_adm_for_create(client: AsyncClient, nut_headers):
    """POST /vendors returns 403 for non-ADM roles."""
    resp = await client.post("/api/v1/vendors", json=SAMPLE_VENDOR, headers=nut_headers)
    assert resp.status_code == 403


async def test_vendor_price_upsert(client: AsyncClient, admin_headers):
    """POST /vendors/{id}/prices creates vendor price."""
    from datetime import date
    vendor_id = await _create_vendor(client, admin_headers)

    # Need an item - create one via items endpoint
    item_resp = await client.post(
        "/api/v1/items",
        json={"name": "테스트양파", "category": "채소", "unit": "kg"},
        headers=admin_headers,
    )
    if item_resp.status_code != 200:
        pytest.skip("Items endpoint not available in this test context")

    item_id = item_resp.json()["data"]["id"]
    price_data = {
        "item_id": item_id,
        "unit_price": "1200.00",
        "unit": "kg",
        "effective_from": str(date.today()),
    }
    resp = await client.post(
        f"/api/v1/vendors/{vendor_id}/prices",
        json=price_data,
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["is_current"] is True
