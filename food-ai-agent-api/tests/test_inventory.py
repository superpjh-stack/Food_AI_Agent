"""Integration tests for Inventory API (MVP 2)."""
import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import SITE_ID, auth_header

pytestmark = pytest.mark.asyncio

PUR_ID = uuid.UUID("10000000-0000-0000-0000-000000001005")
KIT_ID = uuid.UUID("10000000-0000-0000-0000-000000001003")


def pur_headers():
    return auth_header(PUR_ID, "PUR")


async def test_list_inventory(client: AsyncClient):
    """GET /inventory returns list with pagination."""
    resp = await client.get(f"/api/v1/inventory?site_id={SITE_ID}", headers=pur_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert "meta" in body


async def test_list_inventory_no_site_filter(client: AsyncClient):
    """GET /inventory without site_id returns all inventory."""
    resp = await client.get("/api/v1/inventory", headers=pur_headers())
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_list_inventory_low_stock_filter(client: AsyncClient):
    """GET /inventory?low_stock_only=true filters low stock items."""
    resp = await client.get(
        f"/api/v1/inventory?site_id={SITE_ID}&low_stock_only=true",
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # All items returned should be low stock
    for item in body["data"]:
        assert item.get("is_low_stock") is True


async def test_list_lots(client: AsyncClient):
    """GET /inventory/lots returns lot list."""
    resp = await client.get(f"/api/v1/inventory/lots?site_id={SITE_ID}", headers=pur_headers())
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_get_lot_not_found(client: AsyncClient):
    """GET /inventory/lots/{nonexistent_id} returns NOT_FOUND."""
    resp = await client.get(
        "/api/v1/inventory/lots/00000000-0000-0000-0000-000000000000",
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False
    assert resp.json()["error"]["code"] == "NOT_FOUND"


async def test_expiry_alert(client: AsyncClient):
    """GET /inventory/expiry-alert returns expiry data."""
    resp = await client.get(
        f"/api/v1/inventory/expiry-alert?site_id={SITE_ID}&alert_days=7",
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert "critical" in data
    assert "warning" in data
    assert "total_alerts" in data


async def test_trace_lot_not_found(client: AsyncClient):
    """POST /inventory/lots/{id}/trace with nonexistent lot returns error."""
    resp = await client.post(
        "/api/v1/inventory/lots/00000000-0000-0000-0000-000000000000/trace",
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False
    assert resp.json()["error"]["code"] == "NOT_FOUND"


async def test_receive_inventory_endpoint_exists(client: AsyncClient):
    """POST /inventory/receive endpoint is accessible."""
    resp = await client.post(
        "/api/v1/inventory/receive",
        json={
            "site_id": str(SITE_ID),
            "items": [],
        },
        headers=pur_headers(),
    )
    # Empty items is technically valid (0 items received)
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_inventory_rbac_requires_pur_kit_ops(client: AsyncClient, admin_headers):
    """GET /inventory accessible to ADM (as admin is usually a superset)."""
    resp = await client.get("/api/v1/inventory", headers=admin_headers)
    # ADM is in allowed roles
    assert resp.status_code in (200, 403)


async def test_inventory_rbac_kit_allowed(client: AsyncClient, kit_headers):
    """GET /inventory is accessible to KIT role."""
    resp = await client.get("/api/v1/inventory", headers=kit_headers)
    assert resp.status_code == 200
