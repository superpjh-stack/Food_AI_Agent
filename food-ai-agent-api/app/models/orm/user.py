from sqlalchemy import Column, String, Boolean, ARRAY, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email = Column(String(300), unique=True, nullable=False, index=True)
    hashed_password = Column(String(500), nullable=False)
    name = Column(String(200), nullable=False)
    role = Column(String(10), nullable=False)  # NUT, KIT, QLT, OPS, ADM
    site_ids = Column(ARRAY(UUID(as_uuid=True)), server_default="{}")
    preferences = Column(JSONB, server_default="{}")
    is_active = Column(Boolean, server_default="true")
    last_login_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
