from sqlalchemy import Column, String, Boolean, Integer, Text, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class Site(Base):
    __tablename__ = "sites"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False)  # school, corporate, hospital, etc.
    capacity = Column(Integer, nullable=False, server_default="0")
    address = Column(Text)
    operating_hours = Column(JSONB)  # {"mon": {"start": "06:00", "end": "20:00"}, ...}
    rules = Column(JSONB, server_default="{}")
    is_active = Column(Boolean, server_default="true")
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
