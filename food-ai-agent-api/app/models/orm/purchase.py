from sqlalchemy import (
    Column, String, Boolean, Integer, Text, Numeric, Date, ARRAY,
    TIMESTAMP, ForeignKey, Index, UniqueConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id          = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name        = Column(String(200), nullable=False)
    business_no = Column(String(20), unique=True)
    contact     = Column(JSONB, server_default="{}")
    categories  = Column(ARRAY(Text), server_default="{}")
    lead_days   = Column(Integer, server_default="2")
    rating      = Column(Numeric(3, 2), server_default="0")
    is_active   = Column(Boolean, server_default="true")
    notes       = Column(Text)
    created_at  = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at  = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))


class VendorPrice(Base):
    __tablename__ = "vendor_prices"

    id             = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    vendor_id      = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    item_id        = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    site_id        = Column(UUID(as_uuid=True), ForeignKey("sites.id"))
    unit_price     = Column(Numeric(12, 2), nullable=False)
    unit           = Column(String(50), nullable=False)
    currency       = Column(String(10), server_default="'KRW'")
    effective_from = Column(Date, nullable=False)
    effective_to   = Column(Date)
    is_current     = Column(Boolean, server_default="true")
    source         = Column(String(50), server_default="'manual'")
    created_at     = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        Index("ix_vendor_prices_item_vendor", "item_id", "vendor_id"),
        Index("ix_vendor_prices_item_current", "item_id", "is_current"),
    )


class Bom(Base):
    __tablename__ = "boms"

    id             = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    menu_plan_id   = Column(UUID(as_uuid=True), ForeignKey("menu_plans.id"), nullable=False, unique=True)
    site_id        = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    period_start   = Column(Date, nullable=False)
    period_end     = Column(Date, nullable=False)
    headcount      = Column(Integer, nullable=False)
    status         = Column(String(20), nullable=False, server_default="'draft'")
    total_cost     = Column(Numeric(14, 2), server_default="0")
    cost_per_meal  = Column(Numeric(10, 2))
    ai_summary     = Column(Text)
    generated_by   = Column(UUID(as_uuid=True), nullable=False)
    created_at     = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at     = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    items = relationship("BomItem", back_populates="bom", cascade="all, delete-orphan")


class BomItem(Base):
    __tablename__ = "bom_items"

    id                  = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    bom_id              = Column(UUID(as_uuid=True), ForeignKey("boms.id", ondelete="CASCADE"), nullable=False)
    item_id             = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    item_name           = Column(String(200), nullable=False)
    quantity            = Column(Numeric(12, 3), nullable=False)
    unit                = Column(String(50), nullable=False)
    unit_price          = Column(Numeric(12, 2))
    subtotal            = Column(Numeric(14, 2))
    inventory_available = Column(Numeric(12, 3), server_default="0")
    order_quantity      = Column(Numeric(12, 3))
    preferred_vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    source_recipes      = Column(JSONB, server_default="'[]'")
    notes               = Column(Text)
    created_at          = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    bom = relationship("Bom", back_populates="items")

    __table_args__ = (Index("ix_bom_items_bom", "bom_id"),)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id            = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    bom_id        = Column(UUID(as_uuid=True), ForeignKey("boms.id"))
    site_id       = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    vendor_id     = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    po_number     = Column(String(50), unique=True)
    status        = Column(String(20), nullable=False, server_default="'draft'")
    order_date    = Column(Date, nullable=False)
    delivery_date = Column(Date, nullable=False)
    total_amount  = Column(Numeric(14, 2), server_default="0")
    tax_amount    = Column(Numeric(12, 2), server_default="0")
    note          = Column(Text)
    submitted_by  = Column(UUID(as_uuid=True))
    submitted_at  = Column(TIMESTAMP(timezone=True))
    approved_by   = Column(UUID(as_uuid=True))
    approved_at   = Column(TIMESTAMP(timezone=True))
    received_at   = Column(TIMESTAMP(timezone=True))
    cancelled_at  = Column(TIMESTAMP(timezone=True))
    cancel_reason = Column(Text)
    created_at    = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at    = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    items = relationship("PurchaseOrderItem", back_populates="po", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_po_site_status", "site_id", "status"),)


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id            = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    po_id         = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    bom_item_id   = Column(UUID(as_uuid=True), ForeignKey("bom_items.id"))
    item_id       = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    item_name     = Column(String(200), nullable=False)
    spec          = Column(String(200))
    quantity      = Column(Numeric(12, 3), nullable=False)
    unit          = Column(String(50), nullable=False)
    unit_price    = Column(Numeric(12, 2), nullable=False)
    subtotal      = Column(Numeric(14, 2), nullable=False)
    received_qty  = Column(Numeric(12, 3), server_default="0")
    received_at   = Column(TIMESTAMP(timezone=True))
    reject_reason = Column(Text)

    po = relationship("PurchaseOrder", back_populates="items")

    __table_args__ = (Index("ix_po_items_po", "po_id"),)
