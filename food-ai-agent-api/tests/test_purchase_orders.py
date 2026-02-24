"""Integration tests for Purchase Orders API (MVP 2)."""
import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import SITE_ID, ADMIN_ID, auth_header

pytestmark = pytest.mark.asyncio

PUR_ID = uuid.UUID("10000000-0000-0000-0000-000000001005")
OPS_ID = uuid.UUID("10000000-0000-0000-0000-000000001006")
VENDOR_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
ITEM_ID = uuid.UUID("30000000-0000-0000-0000-000000000001")


def pur_headers():
    return auth_header(PUR_ID, "PUR")


def ops_headers():
    return auth_header(OPS_ID, "OPS")


def _sample_po(vendor_id: str | None = None):
    today = date.today()
    delivery = today + timedelta(days=2)
    return {
        "site_id": str(SITE_ID),
        "vendor_id": vendor_id or str(VENDOR_ID),
        "order_date": str(today),
        "delivery_date": str(delivery),
        "note": "테스트 발주",
        "items": [],
    }


async def test_list_purchase_orders(client: AsyncClient):
    """GET /purchase-orders returns list."""
    resp = await client.get("/api/v1/purchase-orders", headers=pur_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


async def test_list_purchase_orders_site_filter(client: AsyncClient):
    """GET /purchase-orders?site_id=... filters by site."""
    resp = await client.get(
        f"/api/v1/purchase-orders?site_id={SITE_ID}",
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_list_purchase_orders_status_filter(client: AsyncClient):
    """GET /purchase-orders?status=draft filters by status."""
    resp = await client.get(
        "/api/v1/purchase-orders?status=draft",
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_get_purchase_order_not_found(client: AsyncClient):
    """GET /purchase-orders/{nonexistent_id} returns NOT_FOUND."""
    resp = await client.get(
        "/api/v1/purchase-orders/00000000-0000-0000-0000-000000000000",
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False
    assert resp.json()["error"]["code"] == "NOT_FOUND"


async def test_update_po_not_found(client: AsyncClient):
    """PUT /purchase-orders/{nonexistent_id} returns NOT_FOUND."""
    resp = await client.put(
        "/api/v1/purchase-orders/00000000-0000-0000-0000-000000000000",
        json={"note": "updated"},
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False


async def test_delete_po_not_found(client: AsyncClient):
    """DELETE /purchase-orders/{nonexistent_id} returns NOT_FOUND."""
    resp = await client.delete(
        "/api/v1/purchase-orders/00000000-0000-0000-0000-000000000000",
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False


async def test_submit_po_not_found(client: AsyncClient):
    """POST /purchase-orders/{id}/submit with nonexistent PO returns error."""
    resp = await client.post(
        "/api/v1/purchase-orders/00000000-0000-0000-0000-000000000000/submit",
        json={},
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False


async def test_approve_po_requires_ops_role(client: AsyncClient, nut_headers):
    """POST /purchase-orders/{id}/approve requires OPS role."""
    resp = await client.post(
        "/api/v1/purchase-orders/00000000-0000-0000-0000-000000000000/approve",
        json={},
        headers=nut_headers,
    )
    assert resp.status_code == 403


async def test_cancel_po_not_found(client: AsyncClient):
    """POST /purchase-orders/{id}/cancel with nonexistent PO returns error."""
    resp = await client.post(
        "/api/v1/purchase-orders/00000000-0000-0000-0000-000000000000/cancel",
        json={"cancel_reason": "테스트 취소"},
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False


async def test_receive_po_not_found(client: AsyncClient):
    """POST /purchase-orders/{id}/receive with nonexistent PO returns error."""
    resp = await client.post(
        "/api/v1/purchase-orders/00000000-0000-0000-0000-000000000000/receive",
        json={"items": []},
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False


async def test_export_po_not_found(client: AsyncClient):
    """GET /purchase-orders/{id}/export with nonexistent PO returns error."""
    resp = await client.get(
        "/api/v1/purchase-orders/00000000-0000-0000-0000-000000000000/export",
        headers=pur_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False


async def test_po_rbac_requires_pur_role(client: AsyncClient, kit_headers):
    """GET /purchase-orders returns 403 for KIT role."""
    resp = await client.get("/api/v1/purchase-orders", headers=kit_headers)
    assert resp.status_code == 403
