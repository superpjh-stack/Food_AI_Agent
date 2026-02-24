"""Integration tests for MVP 2 dashboard endpoints."""
import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import SITE_ID, auth_header

pytestmark = pytest.mark.asyncio

PUR_ID = uuid.UUID("10000000-0000-0000-0000-000000001005")
OPS_ID = uuid.UUID("10000000-0000-0000-0000-000000001006")


def pur_headers():
    return auth_header(PUR_ID, "PUR")


def ops_headers():
    return auth_header(OPS_ID, "OPS")


async def test_purchase_summary_widget(client: AsyncClient):
    """GET /dashboard/purchase-summary returns PO status counts."""
    resp = await client.get(
        f"/api/v1/dashboard/purchase-summary?site_id={SITE_ID}",
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert "draft" in data
    assert "submitted" in data
    assert "approved" in data
    assert "received" in data
    assert "pending_approval" in data
    assert "today_deliveries" in data


async def test_price_alerts_widget(client: AsyncClient):
    """GET /dashboard/price-alerts returns price spike data."""
    resp = await client.get(
        f"/api/v1/dashboard/price-alerts?site_id={SITE_ID}",
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert "alerts" in data
    assert "total_alerts" in data
    assert "threshold_pct" in data


async def test_inventory_risks_widget(client: AsyncClient):
    """GET /dashboard/inventory-risks returns risk counts."""
    resp = await client.get(
        f"/api/v1/dashboard/inventory-risks?site_id={SITE_ID}",
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert "low_stock_count" in data
    assert "expiry_alert_count" in data
    assert "critical_expiry_count" in data
    assert "risk_level" in data


async def test_purchase_summary_ops_access(client: AsyncClient):
    """GET /dashboard/purchase-summary accessible to OPS role."""
    resp = await client.get(
        "/api/v1/dashboard/purchase-summary",
        headers=ops_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_inventory_risks_kit_access(client: AsyncClient, kit_headers):
    """GET /dashboard/inventory-risks accessible to KIT role."""
    resp = await client.get(
        "/api/v1/dashboard/inventory-risks",
        headers=kit_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
