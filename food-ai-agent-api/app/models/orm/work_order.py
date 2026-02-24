from sqlalchemy import Column, String, Integer, Date, Time, Text, ForeignKey, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    menu_plan_id = Column(UUID(as_uuid=True), ForeignKey("menu_plans.id"), nullable=False)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    date = Column(Date, nullable=False)
    meal_type = Column(String(20), nullable=False)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False)
    recipe_name = Column(String(300), nullable=False)
    scaled_servings = Column(Integer, nullable=False)
    scaled_ingredients = Column(JSONB, nullable=False)
    steps = Column(JSONB, nullable=False)
    seasoning_notes = Column(Text)
    equipment_notes = Column(Text)
    deadline_time = Column(Time)
    status = Column(String(20), server_default="'pending'")  # pending, in_progress, completed
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
