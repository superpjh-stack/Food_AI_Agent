from sqlalchemy import Column, String, Integer, Boolean, Text, TIMESTAMP, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


CLAIM_CATEGORIES = ["맛/품질", "이물", "양/분량", "온도", "알레르겐", "위생/HACCP", "서비스", "기타"]
CLAIM_SEVERITIES = ["low", "medium", "high", "critical"]
CLAIM_STATUSES   = ["open", "investigating", "action_taken", "closed", "recurred"]


class Claim(Base):
    """클레임 원장"""
    __tablename__ = "claims"

    id               = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id          = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    incident_date    = Column(TIMESTAMP(timezone=True), nullable=False)
    category         = Column(String(30), nullable=False)
    severity         = Column(String(20), nullable=False, server_default="'medium'")
    status           = Column(String(30), nullable=False, server_default="'open'")
    title            = Column(String(300), nullable=False)
    description      = Column(Text, nullable=False)
    menu_plan_id     = Column(UUID(as_uuid=True), ForeignKey("menu_plans.id"))
    recipe_id        = Column(UUID(as_uuid=True), ForeignKey("recipes.id"))
    lot_number       = Column(String(100))
    reporter_name    = Column(String(100))
    reporter_role    = Column(String(20))
    haccp_incident_id = Column(UUID(as_uuid=True), ForeignKey("haccp_incidents.id"))
    ai_hypotheses    = Column(JSONB, server_default="[]")
    root_cause       = Column(Text)
    is_recurring     = Column(Boolean, server_default="false")
    recurrence_count = Column(Integer, server_default="0")
    resolved_at      = Column(TIMESTAMP(timezone=True))
    created_at       = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    created_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_at       = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        Index("ix_claims_site_date", "site_id", "incident_date"),
        Index("ix_claims_category_severity", "category", "severity"),
        Index("ix_claims_status", "status"),
    )


class ClaimAction(Base):
    """클레임 조치 이력"""
    __tablename__ = "claim_actions"

    id            = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    claim_id      = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    action_type   = Column(String(50), nullable=False)
    description   = Column(Text, nullable=False)
    assignee_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    assignee_role = Column(String(20))
    due_date      = Column(TIMESTAMP(timezone=True))
    status        = Column(String(20), server_default="'pending'")
    result_notes  = Column(Text)
    completed_at  = Column(TIMESTAMP(timezone=True))
    created_at    = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    created_by    = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index("ix_claim_actions_claim_id", "claim_id"),
    )
