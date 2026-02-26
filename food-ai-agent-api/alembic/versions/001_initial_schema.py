"""Initial schema

Revision ID: 001
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Sites
    op.create_table(
        "sites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(50)),
        sa.Column("capacity", sa.Integer),
        sa.Column("address", sa.String(500)),
        sa.Column("operating_hours", JSONB),
        sa.Column("rules", JSONB),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # Users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("site_ids", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # Items
    op.create_table(
        "items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), index=True),
        sa.Column("sub_category", sa.String(100)),
        sa.Column("spec", sa.String(200)),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("allergens", ARRAY(sa.Text), server_default="{}"),
        sa.Column("storage_condition", sa.String(100)),
        sa.Column("substitute_group", sa.String(100)),
        sa.Column("nutrition_per_100g", JSONB),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # Nutrition Policies
    op.create_table(
        "nutrition_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id")),
        sa.Column("criteria", JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # Allergen Policies
    op.create_table(
        "allergen_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id")),
        sa.Column("allergens", ARRAY(sa.Text), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # Recipes
    op.create_table(
        "recipes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("category", sa.String(100), index=True),
        sa.Column("sub_category", sa.String(100)),
        sa.Column("servings_base", sa.Integer, nullable=False, server_default="1"),
        sa.Column("prep_time_min", sa.Integer),
        sa.Column("cook_time_min", sa.Integer),
        sa.Column("difficulty", sa.String(20)),
        sa.Column("ingredients", JSONB, nullable=False),
        sa.Column("steps", JSONB, nullable=False),
        sa.Column("ccp_points", JSONB, server_default=sa.text("'[]'")),
        sa.Column("nutrition_per_serving", JSONB),
        sa.Column("allergens", ARRAY(sa.Text), server_default="{}"),
        sa.Column("tags", ARRAY(sa.Text), server_default="{}"),
        sa.Column("source", sa.String(200)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # Recipe Documents (pgvector)
    op.create_table(
        "recipe_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("recipe_id", UUID(as_uuid=True)),
        sa.Column("doc_type", sa.String(50), nullable=False, index=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("chunk_index", sa.Integer, server_default="0"),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.execute("ALTER TABLE recipe_documents ADD COLUMN embedding vector(1536)")

    # Menu Plans
    op.create_table(
        "menu_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("title", sa.String(300)),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("menu_plans.id")),
        sa.Column("budget_per_meal", sa.Numeric(10, 2)),
        sa.Column("target_headcount", sa.Integer),
        sa.Column("nutrition_policy_id", UUID(as_uuid=True), sa.ForeignKey("nutrition_policies.id")),
        sa.Column("allergen_policy_id", UUID(as_uuid=True), sa.ForeignKey("allergen_policies.id")),
        sa.Column("created_by", UUID(as_uuid=True), nullable=False),
        sa.Column("confirmed_by", UUID(as_uuid=True)),
        sa.Column("confirmed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("ai_generation_params", JSONB),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # Menu Plan Items
    op.create_table(
        "menu_plan_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("menu_plan_id", UUID(as_uuid=True), sa.ForeignKey("menu_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("meal_type", sa.String(20), nullable=False),
        sa.Column("course", sa.String(50), nullable=False),
        sa.Column("item_name", sa.String(300), nullable=False),
        sa.Column("recipe_id", UUID(as_uuid=True), sa.ForeignKey("recipes.id")),
        sa.Column("nutrition", JSONB),
        sa.Column("allergens", ARRAY(sa.Text), server_default="{}"),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # Menu Plan Validations
    op.create_table(
        "menu_plan_validations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("menu_plan_id", UUID(as_uuid=True), sa.ForeignKey("menu_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("validation_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("details", JSONB, nullable=False),
        sa.Column("validated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # Work Orders
    op.create_table(
        "work_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("menu_plan_id", UUID(as_uuid=True), sa.ForeignKey("menu_plans.id"), nullable=False),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("meal_type", sa.String(20), nullable=False),
        sa.Column("recipe_id", UUID(as_uuid=True), sa.ForeignKey("recipes.id"), nullable=False),
        sa.Column("recipe_name", sa.String(300), nullable=False),
        sa.Column("scaled_servings", sa.Integer, nullable=False),
        sa.Column("scaled_ingredients", JSONB, nullable=False),
        sa.Column("steps", JSONB, nullable=False),
        sa.Column("seasoning_notes", sa.Text),
        sa.Column("equipment_notes", sa.Text),
        sa.Column("deadline_time", sa.Time),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # HACCP Checklists
    op.create_table(
        "haccp_checklists",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("checklist_type", sa.String(20), nullable=False),
        sa.Column("meal_type", sa.String(20)),
        sa.Column("template", JSONB, nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'")),
        sa.Column("completed_by", UUID(as_uuid=True)),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # HACCP Records
    op.create_table(
        "haccp_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("checklist_id", UUID(as_uuid=True), sa.ForeignKey("haccp_checklists.id"), nullable=False, index=True),
        sa.Column("ccp_point", sa.String(200), nullable=False),
        sa.Column("category", sa.String(50)),
        sa.Column("target_value", sa.String(100)),
        sa.Column("actual_value", sa.String(100)),
        sa.Column("is_compliant", sa.Boolean),
        sa.Column("corrective_action", sa.Text),
        sa.Column("photo_url", sa.Text),
        sa.Column("recorded_by", UUID(as_uuid=True), nullable=False),
        sa.Column("recorded_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # HACCP Incidents
    op.create_table(
        "haccp_incidents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("incident_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("steps_taken", JSONB, server_default=sa.text("'[]'")),
        sa.Column("status", sa.String(20), server_default=sa.text("'open'")),
        sa.Column("reported_by", UUID(as_uuid=True), nullable=False),
        sa.Column("resolved_by", UUID(as_uuid=True)),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("site_id", UUID(as_uuid=True)),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("changes", JSONB),
        sa.Column("reason", sa.Text),
        sa.Column("ai_context", JSONB),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # Conversations
    op.create_table(
        "conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("site_id", UUID(as_uuid=True)),
        sa.Column("title", sa.String(300)),
        sa.Column("messages", JSONB, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("is_archived", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("conversations")
    op.drop_table("audit_logs")
    op.drop_table("haccp_incidents")
    op.drop_table("haccp_records")
    op.drop_table("haccp_checklists")
    op.drop_table("work_orders")
    op.drop_table("menu_plan_validations")
    op.drop_table("menu_plan_items")
    op.drop_table("menu_plans")
    op.drop_table("recipe_documents")
    op.drop_table("recipes")
    op.drop_table("allergen_policies")
    op.drop_table("nutrition_policies")
    op.drop_table("items")
    op.drop_table("users")
    op.drop_table("sites")
    op.execute("DROP EXTENSION IF EXISTS vector")
