# MVP 2 — 구매/발주 자동화 Design

> **프로젝트**: Food AI Agent — MVP 2 Purchase & Inventory Automation
>
> **작성일**: 2026-02-23
>
> **PDCA 단계**: Design
>
> **참조 Plan**: `docs/01-plan/features/mvp2-purchase.plan.md`
>
> **MVP 1 기반**: SQLAlchemy 2.0 async + FastAPI + Next.js 14 App Router

---

## 1. 데이터 모델 (DB Schema)

### 1.1 신규 테이블 (8개)

MVP 1 패턴 그대로 적용: UUID PK, `server_default=text("gen_random_uuid()")`, TIMESTAMP with timezone, JSONB

---

#### 1.1.1 `vendors` — 벤더(공급업체) 마스터

```python
class Vendor(Base):
    __tablename__ = "vendors"

    id          = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name        = Column(String(200), nullable=False)
    business_no = Column(String(20), unique=True)           # 사업자등록번호
    contact     = Column(JSONB, server_default="{}")        # {"phone":"010-...","email":"...","rep":"홍길동"}
    categories  = Column(ARRAY(Text), server_default="{}")  # ["채소","육류","수산"]
    lead_days   = Column(Integer, server_default="2")       # 납기 소요일수 (기본 2일)
    rating      = Column(Numeric(3, 2), server_default="0") # 0.00 ~ 5.00 (벤더 품질 평점)
    is_active   = Column(Boolean, server_default="true")
    notes       = Column(Text)
    created_at  = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at  = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
```

---

#### 1.1.2 `vendor_prices` — 품목별 단가 이력

```python
class VendorPrice(Base):
    __tablename__ = "vendor_prices"

    id             = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    vendor_id      = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    item_id        = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    site_id        = Column(UUID(as_uuid=True), ForeignKey("sites.id"))  # NULL = 전체 공통
    unit_price     = Column(Numeric(12, 2), nullable=False)
    unit           = Column(String(50), nullable=False)                  # kg, ea, box
    currency       = Column(String(10), server_default="'KRW'")
    effective_from = Column(Date, nullable=False)
    effective_to   = Column(Date)                                        # NULL = 현재 유효
    is_current     = Column(Boolean, server_default="true")              # 현재 유효 단가 플래그
    source         = Column(String(50), server_default="'manual'")      # manual, import, api
    created_at     = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    # Index: (item_id, vendor_id, effective_from) — 단가 추이 조회 최적화
    __table_args__ = (
        Index("ix_vendor_prices_item_vendor", "item_id", "vendor_id"),
        Index("ix_vendor_prices_item_current", "item_id", "is_current"),
    )
```

---

#### 1.1.3 `boms` — BOM 헤더 (식단 확정 시 자동 생성)

```python
class Bom(Base):
    __tablename__ = "boms"

    id             = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    menu_plan_id   = Column(UUID(as_uuid=True), ForeignKey("menu_plans.id"), nullable=False, unique=True)
    site_id        = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    period_start   = Column(Date, nullable=False)
    period_end     = Column(Date, nullable=False)
    headcount      = Column(Integer, nullable=False)
    status         = Column(String(20), nullable=False, server_default="'draft'")
                   # draft | ready | ordered | partial | complete
    total_cost     = Column(Numeric(14, 2), server_default="0")   # 예상 총 원가
    cost_per_meal  = Column(Numeric(10, 2))                        # 식당 원가
    ai_summary     = Column(Text)                                  # AI 요약 (리스크, 절감 제안)
    generated_by   = Column(UUID(as_uuid=True), nullable=False)   # 생성한 사용자 or 시스템
    created_at     = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at     = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    items = relationship("BomItem", back_populates="bom", cascade="all, delete-orphan")
```

---

#### 1.1.4 `bom_items` — BOM 상세 (품목별 소요량)

```python
class BomItem(Base):
    __tablename__ = "bom_items"

    id           = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    bom_id       = Column(UUID(as_uuid=True), ForeignKey("boms.id", ondelete="CASCADE"), nullable=False)
    item_id      = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    item_name    = Column(String(200), nullable=False)   # 조회 편의 denormalize
    quantity     = Column(Numeric(12, 3), nullable=False)
    unit         = Column(String(50), nullable=False)
    unit_price   = Column(Numeric(12, 2))                # 적용 단가 (snapshot)
    subtotal     = Column(Numeric(14, 2))                # quantity * unit_price
    inventory_available = Column(Numeric(12, 3), server_default="0")  # 재고 차감 가능량
    order_quantity      = Column(Numeric(12, 3))         # 발주 필요량 = quantity - inventory_available
    preferred_vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    source_recipes = Column(JSONB, server_default="'[]'")
                   # [{"recipe_id":"...", "recipe_name":"제육볶음", "amount":150, "unit":"g"}]
    notes        = Column(Text)
    created_at   = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    bom = relationship("Bom", back_populates="items")
    __table_args__ = (Index("ix_bom_items_bom", "bom_id"),)
```

---

#### 1.1.5 `purchase_orders` — 발주서 헤더

```python
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id            = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    bom_id        = Column(UUID(as_uuid=True), ForeignKey("boms.id"))
    site_id       = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    vendor_id     = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=False)
    po_number     = Column(String(50), unique=True)   # 자동 채번: PO-YYYYMMDD-0001
    status        = Column(String(20), nullable=False, server_default="'draft'")
                  # draft | submitted | approved | received | cancelled
    order_date    = Column(Date, nullable=False)
    delivery_date = Column(Date, nullable=False)
    total_amount  = Column(Numeric(14, 2), server_default="0")
    tax_amount    = Column(Numeric(12, 2), server_default="0")  # 부가세
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
```

---

#### 1.1.6 `purchase_order_items` — 발주서 상세

```python
class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id          = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    po_id       = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    bom_item_id = Column(UUID(as_uuid=True), ForeignKey("bom_items.id"))  # 연결된 BOM 항목
    item_id     = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    item_name   = Column(String(200), nullable=False)
    spec        = Column(String(200))                    # 규격 (예: 국내산/1kg)
    quantity    = Column(Numeric(12, 3), nullable=False)
    unit        = Column(String(50), nullable=False)
    unit_price  = Column(Numeric(12, 2), nullable=False)
    subtotal    = Column(Numeric(14, 2), nullable=False)
    received_qty  = Column(Numeric(12, 3), server_default="0")    # 실제 수령량
    received_at   = Column(TIMESTAMP(timezone=True))
    reject_reason = Column(Text)                                   # 반품 사유

    po = relationship("PurchaseOrder", back_populates="items")
    __table_args__ = (Index("ix_po_items_po", "po_id"),)
```

---

#### 1.1.7 `inventory` — 재고 현황 (사이트별 품목 현재고)

```python
class Inventory(Base):
    __tablename__ = "inventory"

    id          = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id     = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    item_id     = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    quantity    = Column(Numeric(12, 3), nullable=False, server_default="0")
    unit        = Column(String(50), nullable=False)
    location    = Column(String(100))           # 냉장/냉동/실온/창고위치
    min_qty     = Column(Numeric(12, 3))        # 최소 재고 경보 기준
    last_updated = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        UniqueConstraint("site_id", "item_id", name="uq_inventory_site_item"),
        Index("ix_inventory_site", "site_id"),
    )
```

---

#### 1.1.8 `inventory_lots` — 입고 로트 (납품 단위 추적)

```python
class InventoryLot(Base):
    __tablename__ = "inventory_lots"

    id           = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id      = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    item_id      = Column(UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    vendor_id    = Column(UUID(as_uuid=True), ForeignKey("vendors.id"))
    po_id        = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"))
    lot_number   = Column(String(100))                    # 벤더 로트번호 또는 내부 채번
    quantity     = Column(Numeric(12, 3), nullable=False)
    unit         = Column(String(50), nullable=False)
    unit_cost    = Column(Numeric(12, 2))
    received_at  = Column(TIMESTAMP(timezone=True), nullable=False)
    expiry_date  = Column(Date)                           # 유통기한
    storage_temp = Column(Numeric(5, 1))                  # 수령 시 온도(℃)
    status       = Column(String(20), server_default="'active'")
                 # active | partially_used | fully_used | expired | rejected
    inspect_result = Column(JSONB, server_default="{}")
                   # {"passed": true, "note": "신선도 양호", "inspector": "홍길동"}
    used_in_menus = Column(JSONB, server_default="'[]'")
                  # [{"menu_plan_id":"...", "date":"2026-03-01", "used_qty":2.5}]
    created_at   = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        Index("ix_lots_site_item", "site_id", "item_id"),
        Index("ix_lots_expiry", "expiry_date", "status"),
    )
```

---

### 1.2 기존 테이블 수정

#### `items` 테이블에 컬럼 추가 (Alembic 마이그레이션)

```python
# 기존 items 테이블에 추가
substitute_items = Column(ARRAY(UUID(as_uuid=True)), server_default="{}")  # 대체 가능 품목 ID 목록
standard_yield   = Column(Numeric(5, 2), server_default="100")             # 수율 (%) — BOM 계산 보정
```

#### `recipes` 테이블 — `ingredients` JSONB 구조 표준화

기존: `[{"item_id":"...","name":"양파","amount":200,"unit":"g"}]`

MVP 2 표준 (하위 호환 유지):
```json
[
  {
    "item_id": "uuid",
    "name": "양파",
    "amount": 200,
    "unit": "g",
    "yield_pct": 85,
    "note": "껍질 제거 후"
  }
]
```

`yield_pct` 필드 추가 (없으면 100% 가정) — Alembic 마이그레이션 불필요 (JSONB 확장)

---

## 2. API 엔드포인트 설계 (28개 신규)

### 2.1 Vendors API (`/api/v1/vendors`)

| Method | Path | 권한 | 설명 |
|--------|------|------|------|
| GET | `/vendors` | PUR, OPS, ADM | 벤더 목록 (필터: category, is_active) |
| POST | `/vendors` | ADM | 벤더 등록 |
| GET | `/vendors/{vendor_id}` | PUR, OPS, ADM | 벤더 상세 |
| PUT | `/vendors/{vendor_id}` | ADM | 벤더 수정 |
| DELETE | `/vendors/{vendor_id}` | ADM | 벤더 비활성화 |
| GET | `/vendors/{vendor_id}/prices` | PUR, OPS | 벤더 단가 이력 |
| POST | `/vendors/{vendor_id}/prices` | PUR, ADM | 단가 등록/수정 |
| GET | `/items/{item_id}/vendors` | PUR, NUT, OPS | 품목 취급 벤더 목록 + 최저가 |

### 2.2 BOM API (`/api/v1/boms`)

| Method | Path | 권한 | 설명 |
|--------|------|------|------|
| POST | `/boms/generate` | NUT, OPS, PUR | 식단 ID → BOM 자동 산출 (AI Tool 연동) |
| GET | `/boms` | PUR, OPS | BOM 목록 (site_id, status, period 필터) |
| GET | `/boms/{bom_id}` | PUR, NUT, OPS | BOM 상세 (items 포함) |
| PUT | `/boms/{bom_id}` | PUR | BOM 수동 수정 (수량 조정) |
| GET | `/boms/{bom_id}/cost-analysis` | PUR, OPS | 원가 분석 (벤더별 가격 비교) |
| POST | `/boms/{bom_id}/apply-inventory` | PUR | 재고 차감 반영 → 발주 수량 재계산 |

### 2.3 Purchase Orders API (`/api/v1/purchase-orders`)

| Method | Path | 권한 | 설명 |
|--------|------|------|------|
| POST | `/purchase-orders` | PUR | 발주서 생성 (BOM ID or 수동) |
| GET | `/purchase-orders` | PUR, OPS | 발주서 목록 (site_id, status, period 필터) |
| GET | `/purchase-orders/{po_id}` | PUR, OPS | 발주서 상세 (items 포함) |
| PUT | `/purchase-orders/{po_id}` | PUR | 발주서 수정 (draft 상태만) |
| DELETE | `/purchase-orders/{po_id}` | PUR | 발주서 삭제 (draft 상태만) |
| POST | `/purchase-orders/{po_id}/submit` | PUR | 발주서 제출 (→ submitted) |
| POST | `/purchase-orders/{po_id}/approve` | OPS | 발주 승인 (→ approved) |
| POST | `/purchase-orders/{po_id}/cancel` | PUR, OPS | 발주 취소 (사유 필수) |
| POST | `/purchase-orders/{po_id}/receive` | PUR, KIT | 납품 수령 처리 |
| GET | `/purchase-orders/{po_id}/export` | PUR, OPS | 발주서 PDF/엑셀 출력 |

### 2.4 Inventory API (`/api/v1/inventory`)

| Method | Path | 권한 | 설명 |
|--------|------|------|------|
| GET | `/inventory` | PUR, KIT, OPS | 재고 현황 (site_id, category, 부족/임박 필터) |
| PUT | `/inventory/{item_id}` | PUR, KIT | 재고 수동 조정 (재고실사) |
| GET | `/inventory/lots` | PUR, KIT, QLT | 로트 목록 (expiry_date 임박순) |
| GET | `/inventory/lots/{lot_id}` | PUR, KIT, QLT | 로트 상세 + 사용 이력 |
| POST | `/inventory/receive` | PUR, KIT | 입고 검수 기록 (납품 체크리스트) |
| GET | `/inventory/expiry-alert` | PUR, KIT, OPS | 유통기한 임박 품목 (D-3, D-7) |
| POST | `/inventory/lots/{lot_id}/trace` | PUR, QLT | 로트 추적 (어느 식단/현장에 사용됐는지) |

### 2.5 Dashboard API 확장 (`/api/v1/dashboard`)

| Method | Path | 권한 | 설명 |
|--------|------|------|------|
| GET | `/dashboard/purchase-summary` | PUR, OPS | 발주 현황 위젯 (승인대기/발주중/수령완료) |
| GET | `/dashboard/price-alerts` | PUR, OPS | 단가 급등 경보 품목 |
| GET | `/dashboard/inventory-risks` | PUR, KIT, OPS | 재고 부족/임박 위험 품목 |

---

## 3. Agent 설계 확장

### 3.1 Intent Router 확장 (11 → 16)

```python
INTENTS = {
    # ── MVP 1 기존 11개 (변경 없음) ──
    "menu_generate", "menu_validate", "recipe_search", "recipe_scale",
    "work_order", "haccp_checklist", "haccp_record", "haccp_incident",
    "dashboard", "settings", "general",

    # ── MVP 2 신규 5개 ──
    "purchase_bom":     ["BOM", "소요량", "발주 수량", "식재료 필요"],
    "purchase_order":   ["발주서", "주문", "발주", "재발주", "벤더"],
    "purchase_risk":    ["단가", "급등", "공급 위기", "납품 지연", "대체품"],
    "inventory_check":  ["재고", "냉장", "유통기한", "남은 것"],
    "inventory_receive":["납품", "검수", "입고", "배달"],
}
```

**분류 프롬프트 예시** (Intent Router 시스템 프롬프트에 추가):
```
purchase_bom: 식단 소요량 집계, BOM 산출 요청
purchase_order: 발주서 생성/조회/수정/승인 요청
purchase_risk: 단가 급등 경보, 공급 리스크, 대체품 추천
inventory_check: 재고 현황 조회, 유통기한 조회, 부족 품목
inventory_receive: 납품 검수 체크리스트, 입고 기록
```

### 3.2 Tool 정의 (6개 신규)

#### Tool 1: `calculate_bom`

```python
{
    "name": "calculate_bom",
    "description": "확정된 식단의 레시피별 원재료 소요량을 집계하여 BOM을 생성합니다. 인분 스케일링과 수율을 반영합니다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "menu_plan_id": {"type": "string", "description": "식단 ID (confirmed 상태여야 함)"},
            "headcount":    {"type": "integer", "description": "예정 식수 (명)"},
            "apply_inventory": {"type": "boolean", "description": "재고 우선 차감 반영 여부", "default": true}
        },
        "required": ["menu_plan_id", "headcount"]
    }
}
```

**구현 로직** (`agents/tools/purchase_tools.py`):
1. `menu_plan_items` 조회 → `recipe_id` 수집
2. 각 레시피의 `ingredients` JSONB 파싱
3. 인분 스케일링: `amount * headcount / recipe.servings_base`
4. 수율 보정: `scaled_amount / (yield_pct / 100)`
5. 동일 `item_id` 합산 (날짜/식사별 그룹화)
6. `inventory.quantity` 조회 → `order_quantity` = `total_qty - inventory_available`
7. 최신 `vendor_prices` 조회 → `unit_price` 스냅샷
8. `boms` + `bom_items` INSERT
9. 반환: `{bom_id, total_items, total_cost, order_items_count, inventory_deducted}`

---

#### Tool 2: `generate_purchase_order`

```python
{
    "name": "generate_purchase_order",
    "description": "BOM을 기반으로 벤더별 발주서 초안을 생성합니다. 최저가 벤더를 자동 선택하거나 지정 벤더로 생성합니다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "bom_id":          {"type": "string", "description": "BOM ID"},
            "vendor_strategy": {"type": "string", "enum": ["lowest_price", "preferred", "split"],
                                "description": "벤더 선택 전략: 최저가/선호벤더/분할발주"},
            "delivery_date":   {"type": "string", "description": "납품 희망일 (YYYY-MM-DD)"},
            "vendor_id":       {"type": "string", "description": "지정 벤더 ID (preferred 전략 시)"}
        },
        "required": ["bom_id", "delivery_date"]
    }
}
```

**벤더 선택 전략**:
- `lowest_price`: 품목별 최저가 벤더 자동 매핑
- `preferred`: 지정 벤더 1개로 전체 발주 (취급 품목만)
- `split`: 카테고리별 선호 벤더로 분할 발주 (multiple PO 생성)

---

#### Tool 3: `compare_vendors`

```python
{
    "name": "compare_vendors",
    "description": "특정 품목 또는 품목 목록에 대해 벤더별 단가, 납기, 품질 점수를 비교합니다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "item_ids":   {"type": "array", "items": {"type": "string"}, "description": "품목 ID 목록"},
            "site_id":    {"type": "string", "description": "현장 ID (단가 계약 확인용)"},
            "compare_period": {"type": "integer", "description": "단가 추이 비교 기간 (주)", "default": 4}
        },
        "required": ["item_ids"]
    }
}
```

**반환 예시**:
```json
{
  "comparisons": [
    {
      "item_id": "...",
      "item_name": "양파",
      "vendors": [
        {"vendor_id": "...", "name": "한국청과", "unit_price": 1200, "unit": "kg",
         "lead_days": 1, "rating": 4.5, "price_trend": "-5%", "recommended": true},
        {"vendor_id": "...", "name": "서울청과", "unit_price": 1350, "unit": "kg",
         "lead_days": 2, "rating": 4.2, "price_trend": "+3%", "recommended": false}
      ]
    }
  ],
  "total_savings_if_optimized": 45000
}
```

---

#### Tool 4: `detect_price_risk`

```python
{
    "name": "detect_price_risk",
    "description": "최근 단가 변동을 분석하여 급등/공급 리스크 품목을 탐지하고 영향 메뉴를 추정합니다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "site_id":          {"type": "string"},
            "threshold_pct":    {"type": "number", "description": "급등 임계치 (%)", "default": 15},
            "compare_weeks":    {"type": "integer", "description": "비교 기간 (주 전)", "default": 1},
            "menu_plan_id":     {"type": "string", "description": "영향 식단 ID (선택)"}
        },
        "required": ["site_id"]
    }
}
```

**탐지 로직**:
1. 최근 N주 `vendor_prices` 비교 → 상승률 계산
2. `threshold_pct` 초과 품목 필터
3. 해당 품목이 포함된 `menu_plan_items` 조회
4. 원가 상승 추정: `quantity * (new_price - old_price) * headcount`
5. 반환: `{risk_items, affected_menus, estimated_cost_increase, suggested_actions}`

---

#### Tool 5: `suggest_alternatives`

```python
{
    "name": "suggest_alternatives",
    "description": "특정 품목의 대체품 또는 대체 벤더를 추천합니다. 알레르겐 규정과 영양 정책을 반영합니다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "item_id":         {"type": "string", "description": "대체할 품목 ID"},
            "site_id":         {"type": "string"},
            "reason":          {"type": "string", "enum": ["price_spike", "out_of_stock", "quality"],
                                "description": "대체 이유"},
            "allergen_policy_id": {"type": "string", "description": "알레르겐 정책 ID"}
        },
        "required": ["item_id", "site_id"]
    }
}
```

**추천 로직**:
1. `items.substitute_group` 기반 동일 그룹 품목 조회
2. `items.substitute_items` 직접 연결 대체품 우선
3. RAG 검색: `{품목명} 대체 식재료` 쿼리 → 표준레시피/SOP 문서에서 추천
4. 알레르겐 필터: 동일 알레르겐 있으면 경고 표시
5. 가격 비교: 대체품의 현재 최저가 표시

---

#### Tool 6: `check_inventory`

```python
{
    "name": "check_inventory",
    "description": "현장의 재고 현황을 조회합니다. 유통기한 임박, 부족 품목을 우선 표시합니다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "site_id":    {"type": "string", "description": "현장 ID"},
            "item_ids":   {"type": "array", "items": {"type": "string"}, "description": "특정 품목 필터 (선택)"},
            "alert_days": {"type": "integer", "description": "유통기한 임박 기준 (일)", "default": 7},
            "include_lots": {"type": "boolean", "description": "로트 상세 포함 여부", "default": false}
        },
        "required": ["site_id"]
    }
}
```

---

### 3.3 Orchestrator 수정사항

`app/agents/orchestrator.py`에서:

```python
# 기존 TOOL_REGISTRY에 추가
from app.agents.tools.purchase_tools import (
    calculate_bom,
    generate_purchase_order,
    compare_vendors,
    detect_price_risk,
    suggest_alternatives,
    check_inventory,
)

TOOL_REGISTRY = {
    # ... MVP 1 기존 11개 ...
    "calculate_bom": calculate_bom,
    "generate_purchase_order": generate_purchase_order,
    "compare_vendors": compare_vendors,
    "detect_price_risk": detect_price_risk,
    "suggest_alternatives": suggest_alternatives,
    "check_inventory": check_inventory,
}
```

---

## 4. Frontend 설계

### 4.1 신규 페이지 라우트

```
app/(main)/
├── purchase/
│   ├── page.tsx          # BOM & 발주 목록 대시보드
│   ├── new/page.tsx      # 발주서 직접 생성
│   └── [id]/page.tsx     # 발주서 상세 (벤더 비교, 승인)
├── inventory/
│   ├── page.tsx          # 재고 현황 목록
│   └── receive/page.tsx  # 입고 검수 체크리스트
```

### 4.2 신규 컴포넌트 목록 (14개)

#### Purchase 컴포넌트 (`components/purchase/`)

| 컴포넌트 | 설명 |
|---------|------|
| `bom-summary-card.tsx` | BOM 요약 카드 (총 품목수, 예상 원가, 발주 필요량) |
| `bom-items-table.tsx` | BOM 상세 테이블 (품목/소요량/재고/발주량/단가) |
| `purchase-order-form.tsx` | 발주서 생성/수정 폼 (vendor 선택, delivery_date) |
| `purchase-order-table.tsx` | 발주서 목록 테이블 (status 배지, 금액, 납기) |
| `vendor-compare-panel.tsx` | 벤더 비교 패널 (품목별 가격/납기/평점 비교) |
| `price-risk-alert.tsx` | 단가 급등 경보 배너 (아이템별 상승률, 영향 메뉴) |
| `po-status-badge.tsx` | 발주 상태 배지 (draft/submitted/approved/received) |
| `bom-cost-chart.tsx` | 원가 구성 차트 (카테고리별 비중, 전주 비교) |

#### Inventory 컴포넌트 (`components/inventory/`)

| 컴포넌트 | 설명 |
|---------|------|
| `inventory-grid.tsx` | 재고 현황 그리드 (품목/수량/유통기한/위치) |
| `expiry-alert-list.tsx` | 유통기한 임박 목록 (D-3, D-7 구분 컬러) |
| `receive-checklist.tsx` | 납품 검수 체크리스트 (신선도/온도/포장/수량) |
| `lot-trace-modal.tsx` | 로트 추적 모달 (어느 식단/일자/현장에 사용됐는지) |
| `inventory-adjust-form.tsx` | 재고 실사 조정 폼 |
| `lot-badge.tsx` | 로트 상태 배지 (active/partially_used/expired) |

### 4.3 신규 Hooks (`lib/hooks/`)

| Hook | 설명 |
|------|------|
| `use-boms.ts` | BOM 목록/상세, BOM 생성, 재고 반영 |
| `use-purchase-orders.ts` | PO 목록/상세, 제출/승인/수령 액션 |
| `use-vendors.ts` | 벤더 목록, 단가 이력, 벤더 비교 |
| `use-inventory.ts` | 재고 현황, 로트 목록, 유통기한 알림 |

### 4.4 Dashboard 위젯 확장

기존 `app/(main)/dashboard/page.tsx`에 구매 위젯 추가:

```tsx
// 추가될 위젯 (components/dashboard/ 신규)
<PurchaseStatusWidget />   // 발주 현황 (승인대기 N건, 납품예정 M건)
<PriceAlertWidget />       // 단가 급등 경보 (상위 3 품목)
<InventoryRiskWidget />    // 재고 위험 (부족 N개, 임박 M개)
```

---

## 5. 데이터 흐름 (Data Flow)

### 5.1 BOM 자동 생성 흐름

```
[NUT] 식단 확정 클릭
    ↓
PUT /menu-plans/{id}/confirm
    ↓ (menu_plans.status = 'confirmed' 이벤트)
[System] calculate_bom Tool 자동 호출
    ├─ menu_plan_items → recipe_id 수집
    ├─ recipes.ingredients JSONB 파싱
    ├─ 인분 스케일링 (× headcount / servings_base)
    ├─ 수율 보정 (/ yield_pct × 100)
    ├─ item_id별 합산 (소요량 집계)
    ├─ inventory.quantity 조회 (재고 차감)
    ├─ vendor_prices 최신 단가 스냅샷
    └─ boms + bom_items INSERT
    ↓
[PUR] /purchase 화면에서 BOM 확인
    ↓
[PUR] "발주서 만들어줘" 채팅 or 버튼
    ↓
generate_purchase_order Tool
    ├─ vendor_strategy 선택 (lowest_price 기본)
    ├─ 품목별 최저가 벤더 매핑
    ├─ purchase_orders + purchase_order_items INSERT
    └─ po_number 자동 채번 (PO-20260301-0001)
    ↓
[PUR] 발주서 검토 → Submit
    ↓
[OPS] 승인 → Approved
    ↓
[Vendor] 납품
    ↓
[PUR/KIT] 입고 검수 → inventory_lots INSERT → inventory 업데이트
```

### 5.2 단가 급등 대응 흐름

```
[System] detect_price_risk (일 1회 배치 or 실시간 트리거)
    ├─ vendor_prices 최근 1주 비교
    ├─ 15% 초과 품목 탐지
    └─ dashboard.price_alerts 업데이트
    ↓
[PUR/OPS] 대시보드 경보 알림
    ↓
[PUR] "양파 대체품 있어?" 채팅
    ↓
suggest_alternatives Tool
    ├─ items.substitute_group 조회
    ├─ RAG: "양파 대체 식재료" 문서 검색
    └─ 대체품 + 가격 + 알레르겐 체크 반환
    ↓
[NUT] 메뉴 스왑 승인 → BOM 재산출 (calculate_bom 재호출)
```

### 5.3 입고 검수 흐름

```
[PUR/KIT] /inventory/receive 접속
    ├─ 오늘 납품 예정 PO 조회
    └─ receive_checklist 체크리스트 표시
    ↓
각 품목별 체크: 수량/신선도/온도/포장
    ↓
POST /inventory/receive
    ├─ inventory_lots INSERT (lot_number, expiry_date, storage_temp)
    ├─ inventory.quantity UPDATE (현재고 + received_qty)
    ├─ purchase_order_items.received_qty UPDATE
    └─ (전체 수령 완료 시) purchase_orders.status = 'received'
    ↓
[QLT] 로트 추적 가능 (incident 발생 시 /inventory/lots/{id}/trace)
```

---

## 6. Alembic 마이그레이션 계획

```python
# 마이그레이션 순서 (의존성 기준)
# 1. vendors (독립)
# 2. vendor_prices (vendors, items, sites FK)
# 3. boms (menu_plans, sites FK)
# 4. bom_items (boms, items, vendors FK)
# 5. purchase_orders (boms, sites, vendors FK)
# 6. purchase_order_items (purchase_orders, items, bom_items FK)
# 7. inventory (sites, items FK)
# 8. inventory_lots (sites, items, vendors, purchase_orders FK)
# 9. items 컬럼 추가 (substitute_items, standard_yield)
```

마이그레이션 파일: `alembic/versions/002_mvp2_purchase_schema.py`

---

## 7. 시스템 프롬프트 확장

`app/agents/prompts/system.py`에 구매 도메인 섹션 추가:

```python
PURCHASE_DOMAIN_PROMPT = """
## 구매/발주 업무 가이드라인

당신은 구매팀(PUR)의 AI 어시스턴트입니다.

### 발주 워크플로우 안전 규칙
1. 발주 확정(submitted)은 반드시 OPS 승인 후 진행 (SAFE-PUR-001)
2. 단가 급등 감지 시 항상 대체품/메뉴 스왑 옵션 제시 (SAFE-PUR-002)
3. 재발주(긴급발주) 요청 시 원인과 재발 방지 조치 포함 (SAFE-PUR-003)
4. 로트 추적 결과는 항상 audit_logs에 기록 (SAFE-PUR-004)

### 출처 표시 원칙
- 단가 정보: [출처: 단가 이력 {effective_date}]
- 대체품 추천: [출처: 표준레시피 SOP or 내부 식재료 마스터]
- 재고 정보: [출처: 재고 현황 {last_updated}]
"""
```

---

## 8. Seed 데이터 (개발/테스트용)

`food-ai-agent-api/db/seed_mvp2.py`:

```python
SAMPLE_VENDORS = [
    {"name": "한국청과", "categories": ["채소", "과일"], "lead_days": 1, "rating": 4.5},
    {"name": "서울수산", "categories": ["수산", "해산물"], "lead_days": 2, "rating": 4.3},
    {"name": "우리축산", "categories": ["육류", "가공육"], "lead_days": 1, "rating": 4.7},
    {"name": "한라양념", "categories": ["양념", "소스", "조미료"], "lead_days": 3, "rating": 4.1},
    {"name": "대한유가공", "categories": ["유제품", "냉동"], "lead_days": 2, "rating": 4.4},
]

# 각 벤더별 items 단가 데이터 (50개 × 5개 벤더 중복)
# 초기 재고 데이터 (3개 현장 × 30개 품목)
```

---

## 9. 테스트 설계 (55개 예상)

| 영역 | 수량 | 주요 케이스 |
|------|------|-----------|
| Vendors API | 8개 | CRUD, 단가 등록, 품목별 벤더 조회 |
| BOM 생성 | 10개 | 자동 산출, 인분 스케일링, 재고 차감, 원가 계산 |
| Purchase Orders | 12개 | 생성, 제출, 승인, 수령, 취소, 권한 검사 |
| Inventory | 10개 | 재고 조회, 입고 검수, 로트 추적, 임박 알림 |
| Agent Tools | 10개 | calculate_bom, compare_vendors, detect_price_risk, suggest_alternatives |
| Dashboard 위젯 | 5개 | 발주 현황, 단가 경보, 재고 위험 |

---

## 10. 설계 완료 체크리스트

- [x] 신규 DB 테이블 8개 (컬럼/타입/인덱스/관계)
- [x] 기존 테이블 수정 사항 (items, recipes)
- [x] Alembic 마이그레이션 순서
- [x] API 엔드포인트 28개 (Method/Path/권한/설명)
- [x] Agent Tool 6개 (파라미터/반환/로직)
- [x] Intent Router 확장 (11 → 16)
- [x] 시스템 프롬프트 확장 (구매 도메인)
- [x] Frontend 페이지 4개 + 컴포넌트 14개 + Hook 4개
- [x] 대시보드 위젯 3개
- [x] 데이터 흐름 3가지 (BOM/급등대응/입고검수)
- [x] Seed 데이터 설계
- [x] 테스트 케이스 55개 설계

**다음 단계**: `/pdca do mvp2-purchase`
