from sqlalchemy import Column, String, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    site_id = Column(UUID(as_uuid=True))
    action = Column(String(50), nullable=False)  # create, update, confirm, reject, delete
    entity_type = Column(String(50), nullable=False)  # menu_plan, recipe, haccp_checklist, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    changes = Column(JSONB)  # {field: {old: ..., new: ...}}
    reason = Column(Text)
    ai_context = Column(JSONB)  # AI generation params/sources if applicable
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
