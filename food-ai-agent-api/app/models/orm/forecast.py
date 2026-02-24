from sqlalchemy import Column, String, Integer, Numeric, Date, Text, TIMESTAMP, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class DemandForecast(Base):
    """식수 예측 결과 (site별 날짜+식사별)"""
    __tablename__ = "demand_forecasts"

    id             = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id        = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    forecast_date  = Column(Date, nullable=False)
    meal_type      = Column(String(20), nullable=False)
    predicted_min  = Column(Integer, nullable=False)
    predicted_mid  = Column(Integer, nullable=False)
    predicted_max  = Column(Integer, nullable=False)
    confidence_pct = Column(Numeric(5, 2), server_default="70.0")
    model_used     = Column(String(50), server_default="'wma'")
    input_factors  = Column(JSONB, server_default="{}")
    risk_factors   = Column(JSONB, server_default="[]")
    generated_at   = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    created_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index("ix_demand_forecasts_site_date", "site_id", "forecast_date"),
    )


class ActualHeadcount(Base):
    """실제 식수/배식 실적 (잔반 계산 기준)"""
    __tablename__ = "actual_headcounts"

    id           = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id      = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    record_date  = Column(Date, nullable=False)
    meal_type    = Column(String(20), nullable=False)
    planned      = Column(Integer, nullable=False)
    actual       = Column(Integer, nullable=False)
    served       = Column(Integer)
    notes        = Column(Text)
    recorded_at  = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    recorded_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index("ix_actual_headcounts_site_date", "site_id", "record_date"),
    )


class SiteEvent(Base):
    """현장 이벤트 캘린더 (식수 예측 보정용)"""
    __tablename__ = "site_events"

    id                 = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id            = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    event_date         = Column(Date, nullable=False)
    event_type         = Column(String(50), nullable=False)
    event_name         = Column(String(200))
    adjustment_factor  = Column(Numeric(4, 2), server_default="1.0")
    affects_meal_types = Column(JSONB, server_default='["lunch"]')
    notes              = Column(Text)
    created_at         = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    created_by         = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index("ix_site_events_site_date", "site_id", "event_date"),
    )
