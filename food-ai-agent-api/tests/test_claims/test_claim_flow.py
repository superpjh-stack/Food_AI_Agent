"""Integration tests for claim E2E flow."""
import pytest
from httpx import AsyncClient

from tests.conftest import SITE_ID

pytestmark = pytest.mark.asyncio

SAMPLE_CLAIM = {
    "site_id": str(SITE_ID),
    "incident_date": "2026-02-24T10:30:00",
    "category": "맛/품질",
    "severity": "medium",
    "title": "오늘 점심 김치찌개 맛이 이상함",
    "description": "김치찌개에서 신맛이 과도하게 납니다.",
    "reporter_name": "홍길동",
    "reporter_role": "CS",
}


async def _create_claim(client: AsyncClient, ops_headers: dict, overrides: dict | None = None) -> str:
    """Helper: create a claim and return claim_id."""
    payload = {**SAMPLE_CLAIM, **(overrides or {})}
    resp = await client.post("/api/v1/claims", json=payload, headers=ops_headers)
    assert resp.status_code == 200, f"Create claim failed: {resp.text}"
    return resp.json()["data"]["claim_id"]


async def test_register_claim(client: AsyncClient, ops_headers: dict):
    """POST /claims creates claim with status=open."""
    claim_id = await _create_claim(client, ops_headers)
    assert claim_id

    # Verify
    resp = await client.get(f"/api/v1/claims/{claim_id}", headers=ops_headers)
    assert resp.status_code == 200
    claim = resp.json()["data"]
    assert claim["status"] == "open"
    assert claim["category"] == "맛/품질"


async def test_claim_recurrence(client: AsyncClient, ops_headers: dict):
    """Same category within 30 days → is_recurring=True."""
    # Create first claim
    await _create_claim(client, ops_headers, {"category": "이물"})
    # Create second claim with same category
    resp = await client.post(
        "/api/v1/claims",
        json={**SAMPLE_CLAIM, "category": "이물", "title": "이물 재발 클레임"},
        headers=ops_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["is_recurring"] is True
    assert data["recurrence_count"] >= 1


async def test_add_action(client: AsyncClient, ops_headers: dict):
    """POST /claims/{id}/actions → claim status becomes action_taken."""
    claim_id = await _create_claim(client, ops_headers, {"category": "온도"})

    resp = await client.post(
        f"/api/v1/claims/{claim_id}/actions",
        json={
            "action_type": "staff_training",
            "description": "배식 온도 관리 교육 실시",
            "assignee_role": "KIT",
        },
        headers=ops_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["claim_status"] == "action_taken"


async def test_close_claim(client: AsyncClient, ops_headers: dict):
    """PUT /claims/{id}/status → closed."""
    claim_id = await _create_claim(client, ops_headers, {"category": "서비스"})

    resp = await client.put(
        f"/api/v1/claims/{claim_id}/status",
        json={"status": "closed", "root_cause": "직원 실수로 인한 서비스 불량"},
        headers=ops_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "closed"
