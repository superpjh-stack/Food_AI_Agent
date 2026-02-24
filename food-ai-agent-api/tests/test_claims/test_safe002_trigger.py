"""Tests for SAFE-002: hygiene/allergen high/critical claim → HACCP incident auto-creation."""
import pytest
from httpx import AsyncClient

from tests.conftest import SITE_ID

pytestmark = pytest.mark.asyncio


async def test_haccp_incident_created_on_high_severity_hygiene_claim(
    client: AsyncClient, ops_headers: dict
):
    """SAFE-002: 위생/HACCP high severity claim → HACCP incident auto-created."""
    payload = {
        "site_id": str(SITE_ID),
        "incident_date": "2026-02-24T14:00:00",
        "category": "위생/HACCP",
        "severity": "high",
        "title": "냉장고 온도 이상으로 식재료 변질 의심",
        "description": "냉장고 온도가 10도 이상으로 올라가 식재료 변질이 우려됩니다.",
        "reporter_name": "김품질",
        "reporter_role": "QLT",
    }
    resp = await client.post("/api/v1/claims", json=payload, headers=ops_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["haccp_incident_created"] is True
    assert data["haccp_incident_id"] is not None
    assert data["status"] == "open"


async def test_haccp_incident_created_on_critical_allergen_claim(
    client: AsyncClient, ops_headers: dict
):
    """SAFE-002: 알레르겐 critical severity claim → HACCP incident auto-created."""
    payload = {
        "site_id": str(SITE_ID),
        "incident_date": "2026-02-24T12:00:00",
        "category": "알레르겐",
        "severity": "critical",
        "title": "땅콩 알레르기 반응 보고",
        "description": "학생이 급식 후 알레르기 반응을 보였습니다. 땅콩 성분 의심.",
        "reporter_name": "이선생",
        "reporter_role": "CS",
    }
    resp = await client.post("/api/v1/claims", json=payload, headers=ops_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["haccp_incident_created"] is True
    assert data["haccp_incident_id"] is not None


async def test_no_incident_for_low_severity_taste_claim(
    client: AsyncClient, ops_headers: dict
):
    """SAFE-002 NOT triggered for low severity taste/quality claim."""
    payload = {
        "site_id": str(SITE_ID),
        "incident_date": "2026-02-24T13:00:00",
        "category": "맛/품질",
        "severity": "low",
        "title": "밥이 약간 딱딱함",
        "description": "오늘 점심 밥이 조금 딱딱하다는 의견이 있었습니다.",
    }
    resp = await client.post("/api/v1/claims", json=payload, headers=ops_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["haccp_incident_created"] is False
    assert data["haccp_incident_id"] is None


async def test_no_incident_for_medium_hygiene_claim(
    client: AsyncClient, ops_headers: dict
):
    """SAFE-002 NOT triggered for medium severity hygiene claim (only high/critical)."""
    payload = {
        "site_id": str(SITE_ID),
        "incident_date": "2026-02-24T11:00:00",
        "category": "위생/HACCP",
        "severity": "medium",
        "title": "조리도구 세척 미흡",
        "description": "일부 조리도구의 세척 상태가 불량합니다.",
    }
    resp = await client.post("/api/v1/claims", json=payload, headers=ops_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["haccp_incident_created"] is False
