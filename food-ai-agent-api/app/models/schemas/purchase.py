"""Pydantic schemas for purchase/vendor/BOM/PO domain (MVP 2)."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Vendor ────────────────────────────────────────────────────────────────

class VendorCreate(BaseModel):
    name: str
    business_no: str | None = None
    contact: dict[str, Any] = {}
    categories: list[str] = []
    lead_days: int = 2
    rating: Decimal = Decimal("0")
    notes: str | None = None


class VendorUpdate(BaseModel):
    name: str | None = None
    business_no: str | None = None
    contact: dict[str, Any] | None = None
    categories: list[str] | None = None
    lead_days: int | None = None
    rating: Decimal | None = None
    notes: str | None = None
    is_active: bool | None = None


class VendorRead(BaseModel):
    id: UUID
    name: str
    business_no: str | None
    contact: dict[str, Any]
    categories: list[str]
    lead_days: int
    rating: Decimal
    is_active: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── VendorPrice ───────────────────────────────────────────────────────────

class VendorPriceCreate(BaseModel):
    item_id: UUID
    site_id: UUID | None = None
    unit_price: Decimal
    unit: str
    currency: str = "KRW"
    effective_from: date
    effective_to: date | None = None
    source: str = "manual"


class VendorPriceRead(BaseModel):
    id: UUID
    vendor_id: UUID
    item_id: UUID
    site_id: UUID | None
    unit_price: Decimal
    unit: str
    currency: str
    effective_from: date
    effective_to: date | None
    is_current: bool
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── BOM ───────────────────────────────────────────────────────────────────

class BomItemRead(BaseModel):
    id: UUID
    bom_id: UUID
    item_id: UUID
    item_name: str
    quantity: Decimal
    unit: str
    unit_price: Decimal | None
    subtotal: Decimal | None
    inventory_available: Decimal
    order_quantity: Decimal | None
    preferred_vendor_id: UUID | None
    source_recipes: list[dict[str, Any]]
    notes: str | None

    model_config = {"from_attributes": True}


class BomRead(BaseModel):
    id: UUID
    menu_plan_id: UUID
    site_id: UUID
    period_start: date
    period_end: date
    headcount: int
    status: str
    total_cost: Decimal
    cost_per_meal: Decimal | None
    ai_summary: str | None
    generated_by: UUID
    created_at: datetime
    updated_at: datetime
    items: list[BomItemRead] = []

    model_config = {"from_attributes": True}


class BomGenerateRequest(BaseModel):
    menu_plan_id: UUID
    headcount: int = Field(..., gt=0)
    apply_inventory: bool = True


class BomUpdateRequest(BaseModel):
    headcount: int | None = None
    items: list[dict[str, Any]] | None = None


# ─── PurchaseOrder ─────────────────────────────────────────────────────────

class PurchaseOrderItemRead(BaseModel):
    id: UUID
    po_id: UUID
    bom_item_id: UUID | None
    item_id: UUID
    item_name: str
    spec: str | None
    quantity: Decimal
    unit: str
    unit_price: Decimal
    subtotal: Decimal
    received_qty: Decimal
    received_at: datetime | None
    reject_reason: str | None

    model_config = {"from_attributes": True}


class PurchaseOrderItemCreate(BaseModel):
    bom_item_id: UUID | None = None
    item_id: UUID
    item_name: str
    spec: str | None = None
    quantity: Decimal
    unit: str
    unit_price: Decimal


class PurchaseOrderCreate(BaseModel):
    bom_id: UUID | None = None
    site_id: UUID
    vendor_id: UUID
    order_date: date
    delivery_date: date
    note: str | None = None
    items: list[PurchaseOrderItemCreate] = []


class PurchaseOrderUpdate(BaseModel):
    delivery_date: date | None = None
    note: str | None = None
    items: list[PurchaseOrderItemCreate] | None = None


class PurchaseOrderRead(BaseModel):
    id: UUID
    bom_id: UUID | None
    site_id: UUID
    vendor_id: UUID
    po_number: str | None
    status: str
    order_date: date
    delivery_date: date
    total_amount: Decimal
    tax_amount: Decimal
    note: str | None
    submitted_by: UUID | None
    submitted_at: datetime | None
    approved_by: UUID | None
    approved_at: datetime | None
    received_at: datetime | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    updated_at: datetime
    items: list[PurchaseOrderItemRead] = []

    model_config = {"from_attributes": True}


class POSubmitRequest(BaseModel):
    note: str | None = None


class POApproveRequest(BaseModel):
    note: str | None = None


class POCancelRequest(BaseModel):
    cancel_reason: str


class POReceiveItemInput(BaseModel):
    po_item_id: UUID
    received_qty: Decimal
    reject_reason: str | None = None


class POReceiveRequest(BaseModel):
    items: list[POReceiveItemInput]
    lot_number: str | None = None
    expiry_date: date | None = None
    storage_temp: Decimal | None = None
    inspect_note: str | None = None


# ─── BOM Generate from PO ──────────────────────────────────────────────────

class GeneratePOFromBomRequest(BaseModel):
    bom_id: UUID
    delivery_date: date
    vendor_strategy: str = Field("lowest_price", pattern="^(lowest_price|preferred|split)$")
    vendor_id: UUID | None = None
    note: str | None = None
