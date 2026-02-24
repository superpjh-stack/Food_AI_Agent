from sqlalchemy import Column, String, Boolean, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    site_id = Column(UUID(as_uuid=True))
    context_type = Column(String(50))  # menu, recipe, haccp, general
    context_ref = Column(UUID(as_uuid=True))  # related entity ID
    title = Column(String(300))
    messages = Column(JSONB, nullable=False, server_default="'[]'")
    is_active = Column(Boolean, server_default="true")
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
