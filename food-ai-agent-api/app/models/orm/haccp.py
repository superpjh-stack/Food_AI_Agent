from sqlalchemy import Column, String, Boolean, Date, Text, ForeignKey, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class HaccpChecklist(Base):
    __tablename__ = "haccp_checklists"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    date = Column(Date, nullable=False)
    checklist_type = Column(String(20), nullable=False)  # daily, weekly
    meal_type = Column(String(20))  # NULL for general daily checks
    template = Column(JSONB, nullable=False)
    status = Column(String(20), server_default="'pending'")  # pending, in_progress, completed, overdue
    completed_by = Column(UUID(as_uuid=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    records = relationship("HaccpRecord", back_populates="checklist", cascade="all, delete-orphan")


class HaccpRecord(Base):
    __tablename__ = "haccp_records"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    checklist_id = Column(UUID(as_uuid=True), ForeignKey("haccp_checklists.id"), nullable=False, index=True)
    ccp_point = Column(String(200), nullable=False)
    category = Column(String(50))  # temperature, time, cleanliness
    target_value = Column(String(100))
    actual_value = Column(String(100))
    is_compliant = Column(Boolean)
    corrective_action = Column(Text)
    photo_url = Column(Text)
    recorded_by = Column(UUID(as_uuid=True), nullable=False)
    recorded_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    checklist = relationship("HaccpChecklist", back_populates="records")


class HaccpIncident(Base):
    __tablename__ = "haccp_incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    incident_type = Column(String(50), nullable=False)  # food_safety, contamination, temperature, other
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    description = Column(Text, nullable=False)
    steps_taken = Column(JSONB, server_default="'[]'")
    status = Column(String(20), server_default="'open'")  # open, in_progress, resolved, closed
    reported_by = Column(UUID(as_uuid=True), nullable=False)
    resolved_by = Column(UUID(as_uuid=True))
    resolved_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
