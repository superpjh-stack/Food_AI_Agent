from sqlalchemy import (
    Column, String, Numeric, Date, TIMESTAMP, ForeignKey,
    Index, UniqueConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.base import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id           = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id      = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    item_id      = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    quantity     = Column(Numeric(12, 3), nullable=False, server_default="0")
    unit         = Column(String(50), nullable=False)
    location     = Column(String(100))
    min_qty      = Column(Numeric(12, 3))
    last_updated = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        UniqueConstraint("site_id", "item_id", name="uq_inventory_site_item"),
        Index("ix_inventory_site", "site_id"),
    )


class InventoryLot(Base):
    __tablename__ = "inventory_lots"

    id             = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id        = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    item_id        = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    vendor_id      = Column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    po_id          = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"))
    lot_number     = Column(String(100))
    quantity       = Column(Numeric(12, 3), nullable=False)
    unit           = Column(String(50), nullable=False)
    unit_cost      = Column(Numeric(12, 2))
    received_at    = Column(TIMESTAMP(timezone=True), nullable=False)
    expiry_date    = Column(Date)
    storage_temp   = Column(Numeric(5, 1))
    status         = Column(String(20), server_default="'active'")
    inspect_result = Column(JSONB, server_default="{}")
    used_in_menus  = Column(JSONB, server_default="'[]'")
    created_at     = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        Index("ix_lots_site_item", "site_id", "item_id"),
        Index("ix_lots_expiry", "expiry_date", "status"),
    )
