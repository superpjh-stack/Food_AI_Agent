from sqlalchemy import Column, String, Boolean, Integer, Text, ARRAY, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

from app.db.base import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String(300), nullable=False)
    version = Column(Integer, nullable=False, server_default="1")
    category = Column(String(100), index=True)  # 한식, 중식, 양식, 일식
    sub_category = Column(String(100))  # 구이, 볶음, 조림, 탕
    servings_base = Column(Integer, nullable=False, server_default="1")
    prep_time_min = Column(Integer)
    cook_time_min = Column(Integer)
    difficulty = Column(String(20))  # easy, medium, hard
    ingredients = Column(JSONB, nullable=False)  # [{"item_id":"...","name":"양파","amount":200,"unit":"g"}]
    steps = Column(JSONB, nullable=False)  # [{"order":1,"description":"...","duration_min":10,"ccp":null}]
    ccp_points = Column(JSONB, server_default="'[]'")
    nutrition_per_serving = Column(JSONB)
    allergens = Column(ARRAY(Text), server_default="{}")
    tags = Column(ARRAY(Text), server_default="{}")
    source = Column(String(200))
    is_active = Column(Boolean, server_default="true")
    created_by = Column(UUID(as_uuid=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))


class RecipeDocument(Base):
    __tablename__ = "recipe_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    recipe_id = Column(UUID(as_uuid=True))  # NULL for standalone SOP docs
    doc_type = Column(String(50), nullable=False, index=True)  # recipe, sop, haccp_guide, policy
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, server_default="0")
    metadata_ = Column("metadata", JSONB, server_default="{}")
    embedding = Column(Vector(1536))  # pgvector
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
