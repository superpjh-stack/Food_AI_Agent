"""MVP3: demand_forecasts, actual_headcounts, site_events, waste_records,
         menu_preferences, cost_analyses, claims, claim_actions

Revision ID: 003
Revises: 002
Create Date: 2026-02-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # demand_forecasts
    op.create_table(
        "demand_forecasts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("forecast_date", sa.Date, nullable=False),
        sa.Column("meal_type", sa.String(20), nullable=False),
        sa.Column("predicted_min", sa.Integer, nullable=False),
        sa.Column("predicted_mid", sa.Integer, nullable=False),
        sa.Column("predicted_max", sa.Integer, nullable=False),
        sa.Column("confidence_pct", sa.Numeric(5, 2), server_default="70.0"),
        sa.Column("model_used", sa.String(50), server_default=sa.text("'wma'")),
        sa.Column("input_factors", JSONB, server_default="{}"),
        sa.Column("risk_factors", JSONB, server_default="[]"),
        sa.Column("generated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_demand_forecasts_site_date", "demand_forecasts", ["site_id", "forecast_date"])

    # actual_headcounts
    op.create_table(
        "actual_headcounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("record_date", sa.Date, nullable=False),
        sa.Column("meal_type", sa.String(20), nullable=False),
        sa.Column("planned", sa.Integer, nullable=False),
        sa.Column("actual", sa.Integer, nullable=False),
        sa.Column("served", sa.Integer),
        sa.Column("notes", sa.Text),
        sa.Column("recorded_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("recorded_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_actual_headcounts_site_date", "actual_headcounts", ["site_id", "record_date"])

    # site_events
    op.create_table(
        "site_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("event_date", sa.Date, nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_name", sa.String(200)),
        sa.Column("adjustment_factor", sa.Numeric(4, 2), server_default="1.0"),
        sa.Column("affects_meal_types", JSONB, server_default='["lunch"]'),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_site_events_site_date", "site_events", ["site_id", "event_date"])

    # waste_records
    op.create_table(
        "waste_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("record_date", sa.Date, nullable=False),
        sa.Column("meal_type", sa.String(20), nullable=False),
        sa.Column("menu_plan_item_id", UUID(as_uuid=True), sa.ForeignKey("menu_plan_items.id")),
        sa.Column("recipe_id", UUID(as_uuid=True), sa.ForeignKey("recipes.id")),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("waste_kg", sa.Numeric(8, 3)),
        sa.Column("waste_pct", sa.Numeric(5, 2)),
        sa.Column("served_count", sa.Integer),
        sa.Column("notes", sa.Text),
        sa.Column("recorded_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("recorded_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_waste_records_site_date", "waste_records", ["site_id", "record_date"])

    # menu_preferences
    op.create_table(
        "menu_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("recipe_id", UUID(as_uuid=True), sa.ForeignKey("recipes.id"), nullable=False),
        sa.Column("preference_score", sa.Numeric(4, 3), server_default="0.0"),
        sa.Column("waste_avg_pct", sa.Numeric(5, 2), server_default="0.0"),
        sa.Column("serve_count", sa.Integer, server_default="0"),
        sa.Column("last_served", sa.Date),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_menu_preferences_site_recipe", "menu_preferences", ["site_id", "recipe_id"], unique=True)

    # cost_analyses
    op.create_table(
        "cost_analyses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("menu_plan_id", UUID(as_uuid=True), sa.ForeignKey("menu_plans.id")),
        sa.Column("analysis_type", sa.String(30), nullable=False),
        sa.Column("target_cost", sa.Numeric(12, 2)),
        sa.Column("estimated_cost", sa.Numeric(12, 2)),
        sa.Column("actual_cost", sa.Numeric(12, 2)),
        sa.Column("headcount", sa.Integer),
        sa.Column("cost_breakdown", JSONB, server_default="{}"),
        sa.Column("variance_pct", sa.Numeric(7, 2)),
        sa.Column("alert_triggered", sa.String(10)),
        sa.Column("suggestions", JSONB, server_default="[]"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_cost_analyses_site", "cost_analyses", ["site_id"])
    op.create_index("ix_cost_analyses_menu_plan", "cost_analyses", ["menu_plan_id"])

    # claims
    op.create_table(
        "claims",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("incident_date", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default=sa.text("'medium'")),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'open'")),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("menu_plan_id", UUID(as_uuid=True), sa.ForeignKey("menu_plans.id")),
        sa.Column("recipe_id", UUID(as_uuid=True), sa.ForeignKey("recipes.id")),
        sa.Column("lot_number", sa.String(100)),
        sa.Column("reporter_name", sa.String(100)),
        sa.Column("reporter_role", sa.String(20)),
        sa.Column("haccp_incident_id", UUID(as_uuid=True), sa.ForeignKey("haccp_incidents.id")),
        sa.Column("ai_hypotheses", JSONB, server_default="[]"),
        sa.Column("root_cause", sa.Text),
        sa.Column("is_recurring", sa.Boolean, server_default="false"),
        sa.Column("recurrence_count", sa.Integer, server_default="0"),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_claims_site_date", "claims", ["site_id", "incident_date"])
    op.create_index("ix_claims_category_severity", "claims", ["category", "severity"])
    op.create_index("ix_claims_status", "claims", ["status"])

    # claim_actions
    op.create_table(
        "claim_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("assignee_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("assignee_role", sa.String(20)),
        sa.Column("due_date", sa.TIMESTAMP(timezone=True)),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'")),
        sa.Column("result_notes", sa.Text),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
    )
    op.create_index("ix_claim_actions_claim_id", "claim_actions", ["claim_id"])


def downgrade() -> None:
    for table in [
        "claim_actions",
        "claims",
        "cost_analyses",
        "menu_preferences",
        "waste_records",
        "site_events",
        "actual_headcounts",
        "demand_forecasts",
    ]:
        op.drop_table(table)
