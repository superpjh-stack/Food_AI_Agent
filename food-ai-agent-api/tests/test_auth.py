"""Integration tests for auth endpoints."""
import pytest
from httpx import AsyncClient

from tests.conftest import ADMIN_ID, SITE_ID

pytestmark = pytest.mark.asyncio


async def test_login_success(client: AsyncClient):
    """Login with valid credentials returns tokens."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "admin1234",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_invalid_password(client: AsyncClient):
    """Login with wrong password returns 401."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


async def test_login_nonexistent_user(client: AsyncClient):
    """Login with unknown email returns 401."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nobody@test.com",
        "password": "whatever",
    })
    assert resp.status_code == 401


async def test_get_me(client: AsyncClient, admin_headers):
    """GET /me returns current user info."""
    resp = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "admin@test.com"
    assert data["role"] == "ADM"
    assert data["is_active"] is True


async def test_get_me_no_token(client: AsyncClient):
    """GET /me without token returns 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_register_by_admin(client: AsyncClient, admin_headers):
    """ADM can register a new user."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "newuser@test.com",
        "password": "newpass123",
        "name": "New User",
        "role": "KIT",
        "site_ids": [str(SITE_ID)],
    }, headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "newuser@test.com"
    assert data["role"] == "KIT"


async def test_register_by_non_admin(client: AsyncClient, nut_headers):
    """Non-ADM cannot register users."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "another@test.com",
        "password": "pass123",
        "name": "Another",
        "role": "KIT",
    }, headers=nut_headers)
    assert resp.status_code == 403


async def test_register_duplicate_email(client: AsyncClient, admin_headers):
    """Cannot register with existing email."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "admin@test.com",
        "password": "pass123",
        "name": "Dup",
        "role": "KIT",
    }, headers=admin_headers)
    assert resp.status_code == 409


async def test_refresh_token(client: AsyncClient):
    """Refresh token returns new access and refresh tokens."""
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "admin1234",
    })
    refresh = login_resp.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_refresh_invalid_token(client: AsyncClient):
    """Invalid refresh token returns 401."""
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": "invalid.token.here",
    })
    assert resp.status_code == 401
