"""MVP 2: purchase & inventory schema

Revision ID: 002
Revises: 001
Create Date: 2026-02-23

Migration order (FK dependency):
1. vendors (standalone)
2. vendor_prices (vendors, items, sites FK)
3. boms (menu_plans, sites FK)
4. bom_items (boms, items, vendors FK)
5. purchase_orders (boms, sites, vendors FK)
6. purchase_order_items (purchase_orders, items, bom_items FK)
7. inventory (sites, items FK)
8. inventory_lots (sites, items, vendors, purchase_orders FK)
9. items column additions (substitute_items, standard_yield)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. vendors
    op.create_table(
        "vendors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("business_no", sa.String(20), unique=True),
        sa.Column("contact", JSONB, server_default="{}"),
        sa.Column("categories", ARRAY(sa.Text), server_default="{}"),
        sa.Column("lead_days", sa.Integer, server_default="2"),
        sa.Column("rating", sa.Numeric(3, 2), server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # 2. vendor_prices
    op.create_table(
        "vendor_prices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("vendor_id", UUID(as_uuid=True), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id")),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("currency", sa.String(10), server_default=sa.text("'KRW'")),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date),
        sa.Column("is_current", sa.Boolean, server_default="true"),
        sa.Column("source", sa.String(50), server_default=sa.text("'manual'")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_vendor_prices_item_vendor", "vendor_prices", ["item_id", "vendor_id"])
    op.create_index("ix_vendor_prices_item_current", "vendor_prices", ["item_id", "is_current"])

    # 3. boms
    op.create_table(
        "boms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("menu_plan_id", UUID(as_uuid=True), sa.ForeignKey("menu_plans.id"), nullable=False, unique=True),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("headcount", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("total_cost", sa.Numeric(14, 2), server_default="0"),
        sa.Column("cost_per_meal", sa.Numeric(10, 2)),
        sa.Column("ai_summary", sa.Text),
        sa.Column("generated_by", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )

    # 4. bom_items
    op.create_table(
        "bom_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bom_id", UUID(as_uuid=True), sa.ForeignKey("boms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2)),
        sa.Column("subtotal", sa.Numeric(14, 2)),
        sa.Column("inventory_available", sa.Numeric(12, 3), server_default="0"),
        sa.Column("order_quantity", sa.Numeric(12, 3)),
        sa.Column("preferred_vendor_id", UUID(as_uuid=True), sa.ForeignKey("vendors.id")),
        sa.Column("source_recipes", JSONB, server_default=sa.text("'[]'")),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_bom_items_bom", "bom_items", ["bom_id"])

    # 5. purchase_orders
    op.create_table(
        "purchase_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("bom_id", UUID(as_uuid=True), sa.ForeignKey("boms.id")),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("vendor_id", UUID(as_uuid=True), sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("po_number", sa.String(50), unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("order_date", sa.Date, nullable=False),
        sa.Column("delivery_date", sa.Date, nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), server_default="0"),
        sa.Column("tax_amount", sa.Numeric(12, 2), server_default="0"),
        sa.Column("note", sa.Text),
        sa.Column("submitted_by", UUID(as_uuid=True)),
        sa.Column("submitted_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("approved_by", UUID(as_uuid=True)),
        sa.Column("approved_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("received_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("cancelled_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("cancel_reason", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_po_site_status", "purchase_orders", ["site_id", "status"])

    # 6. purchase_order_items
    op.create_table(
        "purchase_order_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("po_id", UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bom_item_id", UUID(as_uuid=True), sa.ForeignKey("bom_items.id")),
        sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("item_name", sa.String(200), nullable=False),
        sa.Column("spec", sa.String(200)),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False),
        sa.Column("received_qty", sa.Numeric(12, 3), server_default="0"),
        sa.Column("received_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("reject_reason", sa.Text),
    )
    op.create_index("ix_po_items_po", "purchase_order_items", ["po_id"])

    # 7. inventory
    op.create_table(
        "inventory",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("location", sa.String(100)),
        sa.Column("min_qty", sa.Numeric(12, 3)),
        sa.Column("last_updated", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("site_id", "item_id", name="uq_inventory_site_item"),
    )
    op.create_index("ix_inventory_site", "inventory", ["site_id"])

    # 8. inventory_lots
    op.create_table(
        "inventory_lots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("site_id", UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False),
        sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("vendor_id", UUID(as_uuid=True), sa.ForeignKey("vendors.id")),
        sa.Column("po_id", UUID(as_uuid=True), sa.ForeignKey("purchase_orders.id")),
        sa.Column("lot_number", sa.String(100)),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("unit_cost", sa.Numeric(12, 2)),
        sa.Column("received_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("expiry_date", sa.Date),
        sa.Column("storage_temp", sa.Numeric(5, 1)),
        sa.Column("status", sa.String(20), server_default=sa.text("'active'")),
        sa.Column("inspect_result", JSONB, server_default="{}"),
        sa.Column("used_in_menus", JSONB, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_lots_site_item", "inventory_lots", ["site_id", "item_id"])
    op.create_index("ix_lots_expiry", "inventory_lots", ["expiry_date", "status"])

    # 9. items column additions
    op.add_column("items", sa.Column("substitute_items", ARRAY(UUID(as_uuid=True)), server_default="{}"))
    op.add_column("items", sa.Column("standard_yield", sa.Numeric(5, 2), server_default="100"))


def downgrade() -> None:
    op.drop_column("items", "standard_yield")
    op.drop_column("items", "substitute_items")

    op.drop_index("ix_lots_expiry", table_name="inventory_lots")
    op.drop_index("ix_lots_site_item", table_name="inventory_lots")
    op.drop_table("inventory_lots")

    op.drop_index("ix_inventory_site", table_name="inventory")
    op.drop_table("inventory")

    op.drop_index("ix_po_items_po", table_name="purchase_order_items")
    op.drop_table("purchase_order_items")

    op.drop_index("ix_po_site_status", table_name="purchase_orders")
    op.drop_table("purchase_orders")

    op.drop_index("ix_bom_items_bom", table_name="bom_items")
    op.drop_table("bom_items")

    op.drop_table("boms")

    op.drop_index("ix_vendor_prices_item_current", table_name="vendor_prices")
    op.drop_index("ix_vendor_prices_item_vendor", table_name="vendor_prices")
    op.drop_table("vendor_prices")

    op.drop_table("vendors")
