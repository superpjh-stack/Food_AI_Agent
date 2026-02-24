"""Integration tests for HACCP endpoints."""
import pytest
from datetime import date
from httpx import AsyncClient

from tests.conftest import SITE_ID

pytestmark = pytest.mark.asyncio


async def test_generate_daily_checklist(client: AsyncClient, qlt_headers):
    """QLT can generate a daily HACCP checklist."""
    resp = await client.post("/api/v1/haccp/checklists/generate", json={
        "site_id": str(SITE_ID),
        "date": str(date.today()),
        "checklist_type": "daily",
        "meal_type": "lunch",
    }, headers=qlt_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["checklist_type"] == "daily"
    assert data["data"]["status"] == "pending"
    assert len(data["data"]["template"]) == 10  # DAILY_TEMPLATE has 10 items


async def test_generate_weekly_checklist(client: AsyncClient, qlt_headers):
    """Generate weekly checklist has 7 items."""
    resp = await client.post("/api/v1/haccp/checklists/generate", json={
        "site_id": str(SITE_ID),
        "date": str(date.today()),
        "checklist_type": "weekly",
    }, headers=qlt_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["checklist_type"] == "weekly"
    assert len(data["data"]["template"]) == 7  # WEEKLY_TEMPLATE has 7 items


async def test_generate_checklist_unauthorized(client: AsyncClient, kit_headers):
    """KIT cannot generate checklists (only QLT/OPS/ADM)."""
    resp = await client.post("/api/v1/haccp/checklists/generate", json={
        "site_id": str(SITE_ID),
        "date": str(date.today()),
        "checklist_type": "daily",
    }, headers=kit_headers)
    assert resp.status_code == 403


async def test_list_checklists(client: AsyncClient, qlt_headers):
    """List checklists with pagination."""
    # Create one first
    await client.post("/api/v1/haccp/checklists/generate", json={
        "site_id": str(SITE_ID),
        "date": str(date.today()),
        "checklist_type": "daily",
        "meal_type": "lunch",
    }, headers=qlt_headers)

    resp = await client.get("/api/v1/haccp/checklists", headers=qlt_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "data" in data
    assert "meta" in data


async def test_list_checklists_filter_by_site(client: AsyncClient, qlt_headers):
    """Filter checklists by site_id."""
    resp = await client.get(
        f"/api/v1/haccp/checklists?site_id={SITE_ID}",
        headers=qlt_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_get_checklist_detail(client: AsyncClient, qlt_headers):
    """Get checklist by ID returns detail with records."""
    create_resp = await client.post("/api/v1/haccp/checklists/generate", json={
        "site_id": str(SITE_ID),
        "date": str(date.today()),
        "checklist_type": "daily",
        "meal_type": "lunch",
    }, headers=qlt_headers)
    checklist_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/api/v1/haccp/checklists/{checklist_id}", headers=qlt_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["id"] == checklist_id
    assert "records" in data["data"]


async def test_submit_ccp_record(client: AsyncClient, qlt_headers):
    """QLT can submit a CCP record."""
    # Create checklist
    create_resp = await client.post("/api/v1/haccp/checklists/generate", json={
        "site_id": str(SITE_ID),
        "date": str(date.today()),
        "checklist_type": "daily",
        "meal_type": "lunch",
    }, headers=qlt_headers)
    checklist_id = create_resp.json()["data"]["id"]

    # Submit CCP record
    resp = await client.post("/api/v1/haccp/records", json={
        "checklist_id": checklist_id,
        "ccp_point": "냉장고 온도 확인",
        "category": "temperature",
        "target_value": "0~5°C",
        "actual_value": "3°C",
        "is_compliant": True,
    }, headers=qlt_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["is_compliant"] is True


async def test_submit_noncompliant_ccp_record(client: AsyncClient, qlt_headers):
    """Submit non-compliant CCP record with corrective action."""
    create_resp = await client.post("/api/v1/haccp/checklists/generate", json={
        "site_id": str(SITE_ID),
        "date": str(date.today()),
        "checklist_type": "daily",
    }, headers=qlt_headers)
    checklist_id = create_resp.json()["data"]["id"]

    resp = await client.post("/api/v1/haccp/records", json={
        "checklist_id": checklist_id,
        "ccp_point": "냉장고 온도 확인",
        "category": "temperature",
        "target_value": "0~5°C",
        "actual_value": "8°C",
        "is_compliant": False,
        "corrective_action": "냉장고 온도 재설정 및 식재료 이동",
    }, headers=qlt_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["is_compliant"] is False


async def test_submit_checklist(client: AsyncClient, qlt_headers):
    """Mark checklist as completed."""
    create_resp = await client.post("/api/v1/haccp/checklists/generate", json={
        "site_id": str(SITE_ID),
        "date": str(date.today()),
        "checklist_type": "daily",
    }, headers=qlt_headers)
    checklist_id = create_resp.json()["data"]["id"]

    resp = await client.post(
        f"/api/v1/haccp/checklists/{checklist_id}/submit",
        headers=qlt_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["status"] == "completed"


async def test_report_incident(client: AsyncClient, qlt_headers):
    """QLT can report an incident."""
    resp = await client.post("/api/v1/haccp/incidents", json={
        "site_id": str(SITE_ID),
        "incident_type": "temperature",
        "severity": "high",
        "description": "냉장고 온도 10°C 초과 확인",
    }, headers=qlt_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["severity"] == "high"
    assert data["data"]["status"] == "open"
    assert len(data["data"]["steps_taken"]) >= 5  # high severity has 7+ steps


async def test_report_incident_low_severity(client: AsyncClient, qlt_headers):
    """Low severity incident has fewer response steps."""
    resp = await client.post("/api/v1/haccp/incidents", json={
        "site_id": str(SITE_ID),
        "incident_type": "other",
        "severity": "low",
        "description": "Minor label issue",
    }, headers=qlt_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]["steps_taken"]) == 5  # low severity = 5 steps


async def test_list_incidents(client: AsyncClient, qlt_headers):
    """List incidents with pagination."""
    # Create one
    await client.post("/api/v1/haccp/incidents", json={
        "site_id": str(SITE_ID),
        "incident_type": "contamination",
        "severity": "medium",
        "description": "Test incident",
    }, headers=qlt_headers)

    resp = await client.get("/api/v1/haccp/incidents", headers=qlt_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["data"]) >= 1


async def test_update_incident_resolve(client: AsyncClient, qlt_headers):
    """Resolve an incident."""
    create_resp = await client.post("/api/v1/haccp/incidents", json={
        "site_id": str(SITE_ID),
        "incident_type": "temperature",
        "severity": "medium",
        "description": "Temperature deviation",
    }, headers=qlt_headers)
    incident_id = create_resp.json()["data"]["id"]

    resp = await client.put(f"/api/v1/haccp/incidents/{incident_id}", json={
        "status": "resolved",
    }, headers=qlt_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["status"] == "resolved"


async def test_completion_status(client: AsyncClient, qlt_headers):
    """Check daily HACCP completion status."""
    resp = await client.get(
        f"/api/v1/haccp/completion-status?site_id={SITE_ID}&date={date.today()}",
        headers=qlt_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "completion_rate" in data["data"]


async def test_audit_report(client: AsyncClient, qlt_headers):
    """Generate audit report for a period."""
    today = date.today()
    resp = await client.post("/api/v1/haccp/reports/audit", json={
        "site_id": str(SITE_ID),
        "start_date": str(today),
        "end_date": str(today),
    }, headers=qlt_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    report = data["data"]
    assert "checklists" in report
    assert "ccp_records" in report
    assert "incidents" in report
