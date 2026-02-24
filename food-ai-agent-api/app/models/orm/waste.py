from sqlalchemy import Column, String, Integer, Numeric, Date, Text, TIMESTAMP, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class WasteRecord(Base):
    """잔반 기록 (날짜·메뉴별)"""
    __tablename__ = "waste_records"

    id                = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id           = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    record_date       = Column(Date, nullable=False)
    meal_type         = Column(String(20), nullable=False)
    menu_plan_item_id = Column(UUID(as_uuid=True), ForeignKey("menu_plan_items.id"))
    recipe_id         = Column(UUID(as_uuid=True), ForeignKey("recipes.id"))
    item_name         = Column(String(200), nullable=False)
    waste_kg          = Column(Numeric(8, 3))
    waste_pct         = Column(Numeric(5, 2))
    served_count      = Column(Integer)
    notes             = Column(Text)
    recorded_at       = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    recorded_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index("ix_waste_records_site_date", "site_id", "record_date"),
    )


class MenuPreference(Base):
    """메뉴 선호도 누적 (잔반 피드백 → 식단 생성 가중치)"""
    __tablename__ = "menu_preferences"

    id               = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id          = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    recipe_id        = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False)
    preference_score = Column(Numeric(4, 3), server_default="0.0")
    waste_avg_pct    = Column(Numeric(5, 2), server_default="0.0")
    serve_count      = Column(Integer, server_default="0")
    last_served      = Column(Date)
    updated_at       = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        Index("ix_menu_preferences_site_recipe", "site_id", "recipe_id", unique=True),
    )
