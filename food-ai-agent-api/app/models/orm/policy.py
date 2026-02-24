from sqlalchemy import Column, String, Boolean, Text, ARRAY, ForeignKey, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class NutritionPolicy(Base):
    __tablename__ = "nutrition_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"))  # NULL = global default
    name = Column(String(200), nullable=False)
    meal_type = Column(String(50))  # lunch, dinner, all
    criteria = Column(JSONB, nullable=False)  # {"kcal":{"min":500,"max":800},"sodium":{"max":2000}}
    is_active = Column(Boolean, server_default="true")
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))


class AllergenPolicy(Base):
    __tablename__ = "allergen_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"))
    name = Column(String(200), nullable=False)
    legal_allergens = Column(
        ARRAY(Text),
        server_default=text(
            "ARRAY['난류','우유','메밀','땅콩','대두','밀','고등어','게',"
            "'새우','돼지고기','복숭아','토마토','아황산류','호두',"
            "'닭고기','쇠고기','오징어','조개류','잣','쑥','홍합','전복']"
        ),
    )
    custom_allergens = Column(ARRAY(Text), server_default="{}")
    display_format = Column(String(50), server_default="'number'")  # number, text, icon
    is_active = Column(Boolean, server_default="true")
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
