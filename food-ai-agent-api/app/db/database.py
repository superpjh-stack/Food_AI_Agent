from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

import os

# Cloud SQL (Cloud Run) has connection limits per tier:
# db-f1-micro: ~25 connections → pool_size=5, max_overflow=5
# db-custom-1-3840: ~100 connections → pool_size=10, max_overflow=10
# Local / Railway: no tight limit → pool_size=20, max_overflow=10
_is_cloud_run = os.getenv("K_SERVICE") is not None  # Cloud Run sets K_SERVICE automatically
_pool_size = 5 if _is_cloud_run else 20
_max_overflow = 5 if _is_cloud_run else 10

engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=_pool_size,
    max_overflow=_max_overflow,
    pool_pre_ping=True,  # Important for Cloud SQL connection health checks
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
