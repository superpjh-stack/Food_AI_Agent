"""Test configuration and fixtures."""
import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.jwt import create_access_token
from app.auth.password import hash_password
from app.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.orm.site import Site
from app.models.orm.user import User

# Test database URL: override via TEST_DATABASE_URL env var
TEST_DB_URL = settings.database_url.replace("/food_ai_agent", "/food_ai_agent_test")

test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

# Fixed IDs for test data
SITE_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
ADMIN_ID = uuid.UUID("10000000-0000-0000-0000-000000001001")
NUT_ID = uuid.UUID("10000000-0000-0000-0000-000000001002")
KIT_ID = uuid.UUID("10000000-0000-0000-0000-000000001003")
QLT_ID = uuid.UUID("10000000-0000-0000-0000-000000001004")
OPS_ID = uuid.UUID("10000000-0000-0000-0000-000000001005")
CS_ID  = uuid.UUID("10000000-0000-0000-0000-000000001006")
PUR_ID = uuid.UUID("10000000-0000-0000-0000-000000001007")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session-scoped async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session that rolls back after each test."""
    async with test_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def seed_data(db_session: AsyncSession):
    """Insert minimal seed data for tests."""
    site = Site(
        id=SITE_ID,
        name="Test Site",
        type="office",
        capacity=100,
        address="Seoul, Test-gu",
        operating_hours={"weekday": {"start": "07:00", "end": "19:00"}},
        is_active=True,
    )
    db_session.add(site)

    users = [
        User(
            id=ADMIN_ID, email="admin@test.com", name="Test Admin",
            hashed_password=hash_password("admin1234"),
            role="ADM", site_ids=[SITE_ID], is_active=True,
        ),
        User(
            id=NUT_ID, email="nut@test.com", name="Test Nutritionist",
            hashed_password=hash_password("nut1234"),
            role="NUT", site_ids=[SITE_ID], is_active=True,
        ),
        User(
            id=KIT_ID, email="kit@test.com", name="Test Kitchen",
            hashed_password=hash_password("kit1234"),
            role="KIT", site_ids=[SITE_ID], is_active=True,
        ),
        User(
            id=QLT_ID, email="qlt@test.com", name="Test Quality",
            hashed_password=hash_password("qlt1234"),
            role="QLT", site_ids=[SITE_ID], is_active=True,
        ),
        User(
            id=OPS_ID, email="ops@test.com", name="Test Ops",
            hashed_password=hash_password("ops1234"),
            role="OPS", site_ids=[SITE_ID], is_active=True,
        ),
        User(
            id=CS_ID, email="cs@test.com", name="Test CS",
            hashed_password=hash_password("cs1234"),
            role="CS", site_ids=[SITE_ID], is_active=True,
        ),
        User(
            id=PUR_ID, email="pur@test.com", name="Test Purchase",
            hashed_password=hash_password("pur1234"),
            role="PUR", site_ids=[SITE_ID], is_active=True,
        ),
    ]
    db_session.add_all(users)
    await db_session.commit()
    return {
        "site_id": SITE_ID,
        "admin_id": ADMIN_ID,
        "nut_id": NUT_ID,
        "kit_id": KIT_ID,
        "qlt_id": QLT_ID,
        "ops_id": OPS_ID,
        "cs_id": CS_ID,
        "pur_id": PUR_ID,
    }


def _override_get_db():
    """Override the get_db dependency to use the test session factory."""
    async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    return _get_test_db


@pytest_asyncio.fixture
async def client(seed_data) -> AsyncGenerator[AsyncClient, None]:
    """Create an httpx AsyncClient for testing the FastAPI app."""
    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


def auth_header(user_id: uuid.UUID, role: str, site_ids: list[uuid.UUID] | None = None) -> dict:
    """Generate Authorization header for a user."""
    token = create_access_token(user_id, role, site_ids or [SITE_ID])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    return auth_header(ADMIN_ID, "ADM")


@pytest.fixture
def nut_headers():
    return auth_header(NUT_ID, "NUT")


@pytest.fixture
def kit_headers():
    return auth_header(KIT_ID, "KIT")


@pytest.fixture
def qlt_headers():
    return auth_header(QLT_ID, "QLT")


@pytest.fixture
def ops_headers():
    return auth_header(OPS_ID, "OPS")


@pytest.fixture
def cs_headers():
    return auth_header(CS_ID, "CS")


@pytest.fixture
def pur_headers():
    return auth_header(PUR_ID, "PUR")
