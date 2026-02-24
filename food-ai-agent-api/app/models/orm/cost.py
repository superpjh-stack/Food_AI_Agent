from sqlalchemy import Column, String, Integer, Numeric, Text, TIMESTAMP, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class CostAnalysis(Base):
    """원가 분석 결과 (식단 확정/실발주 원가 추적)"""
    __tablename__ = "cost_analyses"

    id             = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id        = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    menu_plan_id   = Column(UUID(as_uuid=True), ForeignKey("menu_plans.id"))
    analysis_type  = Column(String(30), nullable=False)
    target_cost    = Column(Numeric(12, 2))
    estimated_cost = Column(Numeric(12, 2))
    actual_cost    = Column(Numeric(12, 2))
    headcount      = Column(Integer)
    cost_breakdown = Column(JSONB, server_default="{}")
    variance_pct   = Column(Numeric(7, 2))
    alert_triggered = Column(String(10))
    suggestions    = Column(JSONB, server_default="[]")
    created_at     = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    created_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index("ix_cost_analyses_site", "site_id"),
        Index("ix_cost_analyses_menu_plan", "menu_plan_id"),
    )
