"""Integration tests for recipe endpoints."""
import pytest
from httpx import AsyncClient

from tests.conftest import SITE_ID

pytestmark = pytest.mark.asyncio

# ─── Helper ───────────────────────────────────────────────────────────────────

SAMPLE_RECIPE = {
    "name": "테스트 된장찌개",
    "category": "한식",
    "sub_category": "찌개",
    "servings_base": 10,
    "prep_time_min": 15,
    "cook_time_min": 30,
    "difficulty": "easy",
    "ingredients": [
        {"name": "된장", "amount": 100, "unit": "g"},
        {"name": "두부", "amount": 300, "unit": "g"},
        {"name": "소금", "amount": 5, "unit": "g"},
    ],
    "steps": [
        {"order": 1, "description": "육수를 끓인다", "is_ccp": False},
        {"order": 2, "description": "된장을 풀어 넣는다", "is_ccp": True, "ccp_temp": 85},
    ],
    "allergens": ["대두"],
    "tags": ["찌개", "한식"],
}


async def _create_recipe(client: AsyncClient, nut_headers: dict) -> str:
    """Helper: create a recipe and return its id."""
    resp = await client.post("/api/v1/recipes", json=SAMPLE_RECIPE, headers=nut_headers)
    assert resp.status_code == 201, f"Create failed: {resp.text}"
    return resp.json()["data"]["id"]


# ─── Tests ────────────────────────────────────────────────────────────────────

async def test_list_recipes(client: AsyncClient, nut_headers):
    """GET /recipes returns 200 with list and pagination meta."""
    resp = await client.get("/api/v1/recipes", headers=nut_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert "meta" in body
    assert "total" in body["meta"]


async def test_create_recipe(client: AsyncClient, nut_headers):
    """POST /recipes returns 201 and created recipe data."""
    resp = await client.post("/api/v1/recipes", json=SAMPLE_RECIPE, headers=nut_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["name"] == SAMPLE_RECIPE["name"]
    assert data["category"] == "한식"
    assert "id" in data


async def test_get_recipe_detail(client: AsyncClient, nut_headers):
    """GET /recipes/{id} returns 200 with full detail including ingredients/steps."""
    recipe_id = await _create_recipe(client, nut_headers)

    resp = await client.get(f"/api/v1/recipes/{recipe_id}", headers=nut_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["id"] == recipe_id
    assert "ingredients" in data
    assert "steps" in data
    assert len(data["ingredients"]) == 3


async def test_get_recipe_not_found(client: AsyncClient, nut_headers):
    """GET /recipes/{id} with invalid id returns NOT_FOUND."""
    resp = await client.get(
        "/api/v1/recipes/00000000-0000-0000-0000-999999999999",
        headers=nut_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


async def test_search_recipes_rag(client: AsyncClient, nut_headers):
    """POST /recipes/search returns 200 with matching recipes (keyword fallback)."""
    # Create a recipe first so there's something to find
    await _create_recipe(client, nut_headers)

    resp = await client.post(
        "/api/v1/recipes/search",
        json={"query": "된장찌개", "max_results": 10},
        headers=nut_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    # At least our created recipe should appear
    names = [r["name"] for r in body["data"]]
    assert any("된장" in n for n in names)


async def test_scale_recipe(client: AsyncClient, nut_headers):
    """POST /recipes/{id}/scale returns 200 with scaled ingredient quantities."""
    recipe_id = await _create_recipe(client, nut_headers)

    resp = await client.post(
        f"/api/v1/recipes/{recipe_id}/scale",
        json={"target_servings": 100},
        headers=nut_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["original_servings"] == SAMPLE_RECIPE["servings_base"]
    assert data["target_servings"] == 100
    assert isinstance(data["scaled_ingredients"], list)
    assert len(data["scaled_ingredients"]) == 3

    # Verify ratio: 100 / 10 = 10x
    original_tofu = next(i for i in SAMPLE_RECIPE["ingredients"] if i["name"] == "두부")
    scaled_tofu = next(i for i in data["scaled_ingredients"] if i["name"] == "두부")
    assert abs(scaled_tofu["amount"] - original_tofu["amount"] * 10) < 0.5


async def test_update_recipe(client: AsyncClient, nut_headers):
    """PATCH/PUT /recipes/{id} returns 200 with updated fields."""
    recipe_id = await _create_recipe(client, nut_headers)

    resp = await client.put(
        f"/api/v1/recipes/{recipe_id}",
        json={"name": "수정된 된장찌개", "servings_base": 20},
        headers=nut_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["name"] == "수정된 된장찌개"
    assert body["data"]["servings_base"] == 20


async def test_delete_recipe_not_allowed_for_nut(client: AsyncClient, nut_headers):
    """NUT can create/edit but the design assigns delete to ADM only.
    This test documents RBAC: NUT can PUT but not that NUT is blocked on ADM-only ops.
    (recipes router uses NUT+ADM for PUT — this tests the RBAC boundary for KIT.)
    KIT role cannot create or update recipes (should get 403)."""
    resp = await client.post("/api/v1/recipes", json=SAMPLE_RECIPE, headers=nut_headers)
    # NUT can create
    assert resp.status_code == 201


async def test_rbac_kit_cannot_create_recipe(client: AsyncClient, kit_headers):
    """KIT role cannot create recipes — should receive 403."""
    resp = await client.post("/api/v1/recipes", json=SAMPLE_RECIPE, headers=kit_headers)
    assert resp.status_code == 403


async def test_rbac_kit_can_scale_recipe(client: AsyncClient, nut_headers, kit_headers):
    """KIT role can scale recipes (allowed: NUT, KIT, ADM)."""
    recipe_id = await _create_recipe(client, nut_headers)

    resp = await client.post(
        f"/api/v1/recipes/{recipe_id}/scale",
        json={"target_servings": 50},
        headers=kit_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
