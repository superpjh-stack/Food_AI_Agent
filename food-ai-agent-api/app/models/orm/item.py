from sqlalchemy import Column, String, Boolean, Numeric, Text, ARRAY, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False, index=True)  # 육류, 수산, 채소, 양념
    sub_category = Column(String(100))
    spec = Column(String(200))  # 규격 (예: 국내산/1kg)
    unit = Column(String(50), nullable=False)  # g, kg, ml, L, ea
    allergens = Column(ARRAY(Text), server_default="{}")  # {'우유','대두','밀',...}
    storage_condition = Column(String(100))  # 냉장, 냉동, 실온
    substitute_group = Column(String(100))
    substitute_items = Column(ARRAY(UUID(as_uuid=True)), server_default="{}")  # MVP 2: 대체 가능 품목 ID 목록
    standard_yield = Column(Numeric(5, 2), server_default="100")  # MVP 2: 수율 (%) — BOM 계산 보정
    nutrition_per_100g = Column(JSONB)  # {"kcal":250,"protein":20,"sodium":500,...}
    is_active = Column(Boolean, server_default="true")
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
