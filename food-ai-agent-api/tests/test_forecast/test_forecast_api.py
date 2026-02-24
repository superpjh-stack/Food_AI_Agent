"""Integration tests for forecast API endpoints."""
import pytest
from httpx import AsyncClient

from tests.conftest import SITE_ID

pytestmark = pytest.mark.asyncio


async def test_create_forecast(client: AsyncClient, ops_headers: dict):
    """POST /forecast/headcount creates a forecast."""
    payload = {
        "site_id": str(SITE_ID),
        "forecast_date": "2026-03-01",
        "meal_type": "lunch",
        "model": "wma",
    }
    resp = await client.post("/api/v1/forecast/headcount", json=payload, headers=ops_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "predicted_mid" in data["data"]
    assert data["data"]["forecast_date"] == "2026-03-01"


async def test_record_actual(client: AsyncClient, kit_headers: dict):
    """POST /forecast/actual records actual headcount."""
    payload = {
        "site_id": str(SITE_ID),
        "record_date": "2026-02-24",
        "meal_type": "lunch",
        "planned": 300,
        "actual": 285,
        "served": 280,
        "notes": "테스트 기록",
    }
    resp = await client.post("/api/v1/forecast/actual", json=payload, headers=kit_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["actual"] == 285


async def test_list_forecasts(client: AsyncClient, ops_headers: dict):
    """GET /forecast/headcount returns list."""
    resp = await client.get(
        f"/api/v1/forecast/headcount?site_id={SITE_ID}&date_from=2026-01-01",
        headers=ops_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "data" in data
    assert isinstance(data["data"], list)


async def test_site_event_crud(client: AsyncClient, ops_headers: dict):
    """Create, update, delete site event."""
    # Create
    payload = {
        "site_id": str(SITE_ID),
        "event_date": "2026-03-15",
        "event_type": "holiday",
        "event_name": "봄 축제",
        "adjustment_factor": 1.2,
    }
    create_resp = await client.post("/api/v1/forecast/site-events", json=payload, headers=ops_headers)
    assert create_resp.status_code == 200
    event_id = create_resp.json()["data"]["id"]

    # Update
    update_resp = await client.put(
        f"/api/v1/forecast/site-events/{event_id}",
        json={"adjustment_factor": 0.8, "notes": "인원 감소 예상"},
        headers=ops_headers,
    )
    assert update_resp.status_code == 200
    assert float(update_resp.json()["data"]["adjustment_factor"]) == pytest.approx(0.8)

    # Delete
    del_resp = await client.delete(
        f"/api/v1/forecast/site-events/{event_id}",
        headers=ops_headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True
