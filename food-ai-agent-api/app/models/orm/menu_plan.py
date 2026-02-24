from sqlalchemy import Column, String, Boolean, Integer, Date, Text, ARRAY, Numeric, ForeignKey, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class MenuPlan(Base):
    __tablename__ = "menu_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    title = Column(String(300))
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, server_default="'draft'")  # draft, review, confirmed, archived
    version = Column(Integer, nullable=False, server_default="1")
    parent_id = Column(UUID(as_uuid=True), ForeignKey("menu_plans.id"))
    budget_per_meal = Column(Numeric(10, 2))
    target_headcount = Column(Integer)
    nutrition_policy_id = Column(UUID(as_uuid=True), ForeignKey("nutrition_policies.id"))
    allergen_policy_id = Column(UUID(as_uuid=True), ForeignKey("allergen_policies.id"))
    created_by = Column(UUID(as_uuid=True), nullable=False)
    confirmed_by = Column(UUID(as_uuid=True))
    confirmed_at = Column(TIMESTAMP(timezone=True))
    ai_generation_params = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    items = relationship("MenuPlanItem", back_populates="menu_plan", cascade="all, delete-orphan")
    validations = relationship("MenuPlanValidation", back_populates="menu_plan", cascade="all, delete-orphan")


class MenuPlanItem(Base):
    __tablename__ = "menu_plan_items"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    menu_plan_id = Column(UUID(as_uuid=True), ForeignKey("menu_plans.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    meal_type = Column(String(20), nullable=False)  # breakfast, lunch, dinner, snack
    course = Column(String(50), nullable=False)  # main, soup, side1, side2, side3, dessert, rice
    item_name = Column(String(300), nullable=False)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.id"))
    nutrition = Column(JSONB)  # {"kcal":350,"protein":15,"sodium":800,...}
    allergens = Column(ARRAY(Text), server_default="{}")
    sort_order = Column(Integer, server_default="0")
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    menu_plan = relationship("MenuPlan", back_populates="items")


class MenuPlanValidation(Base):
    __tablename__ = "menu_plan_validations"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    menu_plan_id = Column(UUID(as_uuid=True), ForeignKey("menu_plans.id", ondelete="CASCADE"), nullable=False)
    validation_type = Column(String(50), nullable=False)  # nutrition, allergen, diversity
    status = Column(String(20), nullable=False)  # pass, warning, fail
    details = Column(JSONB, nullable=False)
    validated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    menu_plan = relationship("MenuPlan", back_populates="validations")
