"""Pydantic schemas for inventory domain (MVP 2)."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


# ─── Inventory ─────────────────────────────────────────────────────────────

class InventoryRead(BaseModel):
    id: UUID
    site_id: UUID
    item_id: UUID
    quantity: Decimal
    unit: str
    location: str | None
    min_qty: Decimal | None
    last_updated: datetime

    model_config = {"from_attributes": True}


class InventoryAdjustRequest(BaseModel):
    quantity: Decimal
    reason: str | None = None


# ─── InventoryLot ──────────────────────────────────────────────────────────

class InventoryLotRead(BaseModel):
    id: UUID
    site_id: UUID
    item_id: UUID
    vendor_id: UUID | None
    po_id: UUID | None
    lot_number: str | None
    quantity: Decimal
    unit: str
    unit_cost: Decimal | None
    received_at: datetime
    expiry_date: date | None
    storage_temp: Decimal | None
    status: str
    inspect_result: dict[str, Any]
    used_in_menus: list[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class InventoryReceiveItem(BaseModel):
    item_id: UUID
    item_name: str
    po_item_id: UUID | None = None
    received_qty: Decimal
    unit: str
    unit_cost: Decimal | None = None
    lot_number: str | None = None
    expiry_date: date | None = None
    storage_temp: Decimal | None = None
    inspect_passed: bool = True
    inspect_note: str | None = None


class InventoryReceiveRequest(BaseModel):
    site_id: UUID
    vendor_id: UUID | None = None
    po_id: UUID | None = None
    received_at: datetime | None = None
    items: list[InventoryReceiveItem]


class LotTraceResult(BaseModel):
    lot_id: UUID
    lot_number: str | None
    item_id: UUID
    item_name: str
    received_at: datetime
    expiry_date: date | None
    status: str
    used_in_menus: list[dict[str, Any]]
    sites: list[str]
    total_used_qty: Decimal
    remaining_qty: Decimal
