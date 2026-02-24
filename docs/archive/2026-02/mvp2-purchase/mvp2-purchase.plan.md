# MVP 2 — 구매/발주 자동화 Plan

> **프로젝트**: Food AI Agent — MVP 2 Purchase & Inventory Automation
>
> **작성일**: 2026-02-23
>
> **PDCA 단계**: Plan
>
> **전제**: MVP 1 (식단/레시피/HACCP) 96% Match Rate 완료 기반

---

## 1. 개요 (Overview)

### 1.1 한 줄 목표

> **식단 확정 → BOM 자동 산출 → 발주 초안 생성 → 벤더/단가 비교 → 발주 확정**까지
> 구매/발주 전 과정을 AI Agent로 자동화한다.

### 1.2 MVP 2 배경

MVP 1에서 식단·레시피·HACCP AI 자동화를 완성했다. 그러나 영양사가 식단을 확정해도,
구매팀이 수작업으로 BOM을 집계하고 발주서를 작성하는 병목이 그대로 남아 있다.

MVP 2는 MVP 1의 식단 확정 이벤트를 트리거로, **BOM → 발주 → 재고/입고 검수**까지를
자동화하여 급식 운영의 공급망(Supply Chain) 루프를 닫는다.

### 1.3 신규 사용자 역할

MVP 1에서 정의된 역할 외에 MVP 2에서 추가로 활성화되는 역할:

| 역할 | 약어 | 주요 권한 (신규) |
|------|------|----------------|
| 구매/발주 | **PUR** | BOM 조회, 발주서 생성/수정/확정, 벤더 비교, 단가 등록 |

> 기존 NUT, OPS, ADM 역할도 BOM 조회 및 발주 현황 대시보드 접근 가능

---

## 2. 기능 범위 (Scope)

### 2.1 MVP 2 포함 기능

#### 그룹 A — BOM/발주 코어 (필수)

| 기능 ID | 기능명 | 설명 |
|---------|--------|------|
| FR-PUR-001 | **BOM 자동 산출** | 식단 확정 → 레시피별 소요량 집계 (현장/기간/식수 반영) |
| FR-PUR-002 | **단가/벤더 이력 조회** | 품목별 단가 추이, 벤더별 납기/품질 지표 조회 |
| FR-PUR-003 | **발주 초안 자동 생성** | 품목/규격/수량/납기/현장 포함한 발주서 초안 생성 |
| FR-PUR-004 | **단가 급등/공급 리스크 감지** | 전주 대비 +15% 초과 시 경고 + 영향 메뉴/원가 추정 |
| FR-PUR-005 | **대체품/벤더 추천** | 동일 품목의 대체 규격/식재군 추천 (알레르겐/품질 룰 반영) |
| FR-PUR-006 | **발주 승인/변경 관리** | 발주 확정 전 PUR→OPS 승인, 변경 시 BOM/원가 재계산 |

#### 그룹 B — 재고/입고/검수 (필수)

| 기능 ID | 기능명 | 설명 |
|---------|--------|------|
| FR-INV-001 | **재고 조회 및 사용 계획 반영** | 재고/유통기한/로트 기반 BOM 우선 사용 추천 |
| FR-INV-002 | **입고/검수 체크리스트** | 품질 기준(신선도/온도/포장) 점검 항목 + 기록 |
| FR-INV-003 | **로트 추적 (Traceability)** | 납품→사용 메뉴/일자/현장 역추적 (사고 대응) |

#### 그룹 C — Agent Tool 확장 (필수)

| Tool 명 | 설명 |
|---------|------|
| `calculate_bom` | 식단 ID → 소요량(BOM) 계산 |
| `generate_purchase_order` | BOM → 발주서 초안 생성 |
| `compare_vendors` | 품목별 벤더 단가/납기/품질 비교 |
| `detect_price_risk` | 단가 급등/공급 리스크 탐지 |
| `suggest_alternatives` | 대체품/대체 벤더 추천 |
| `check_inventory` | 재고 현황 + 유통기한 조회 |

#### 그룹 D — Intent 확장 (필수)

MVP 1의 11개 Intent에 다음 5개 추가:

| Intent | 트리거 예시 |
|--------|-----------|
| `purchase_bom` | "이번주 A현장 소요량 뽑아줘" |
| `purchase_order` | "발주서 만들어줘", "재발주 필요 품목" |
| `purchase_risk` | "양파 단가 오른 거 확인해줘" |
| `inventory_check` | "냉장 재고 확인해줘", "유통기한 임박 품목" |
| `inventory_receive` | "오늘 납품 검수 체크리스트 줘" |

#### 그룹 E — UI 신규 화면 (필수)

| 경로 | 화면명 | 역할 |
|------|--------|------|
| `/purchase` | **BOM & 발주** | PUR: BOM 조회, 발주서 생성/확정 |
| `/purchase/[id]` | **발주서 상세** | PUR: 발주 상세, 벤더 비교, 승인 |
| `/inventory` | **재고/입고** | PUR, KIT: 재고 현황, 입고 검수 |
| `/inventory/receive` | **입고 검수** | PUR: 검수 체크리스트 실행 |

#### 그룹 F — 대시보드 확장

기존 `/dashboard`에 구매 위젯 추가:
- 금주 발주 현황 (승인대기/완료)
- 단가 급등 경보 품목
- 재고 부족 위험 품목
- 납품 예정/지연 현황

### 2.2 MVP 2 제외 (다음 MVP)

| 항목 | 이유 | 예정 |
|------|------|------|
| 실시간 IoT 센서 연동 | 인프라 복잡도 | MVP 4+ |
| ERP/구매 시스템 연동 (외부 API) | 고객사별 커스터마이징 필요 | MVP 3 |
| 수요 예측 ML 모델 (FR-FCST) | 별도 MVP 3으로 분리 | MVP 3 |
| 결제/정산 (세금계산서) | Out of Scope | 미정 |

---

## 3. 기술 스택 (MVP 1 + 확장)

MVP 1 스택을 그대로 유지하고 다음 항목만 추가:

| 레이어 | 추가 항목 | 이유 |
|--------|----------|------|
| Backend ORM | `vendors`, `boms`, `bom_items`, `purchase_orders`, `purchase_order_items`, `inventory`, `inventory_lots` 테이블 | 구매/재고 데이터 모델 |
| Agent Tools | 6개 신규 Tool (`calculate_bom` 등) | 구매 자동화 |
| RAG Knowledge Base | 단가 이력, 벤더 계약서, 검수 기준 문서 | 벤더 비교/리스크 |
| Frontend | 4개 신규 페이지 + 3개 컴포넌트 | BOM/발주/재고 UI |
| 알림(Notification) | 단가 급등, 재고 부족, 납품 지연 → Toast/Badge | 리스크 대응 |

---

## 4. 신규 데이터 모델 (예비)

```
vendors          — 벤더(공급업체) 마스터
├─ id, name, contact, rating, active

vendor_prices    — 단가 이력
├─ vendor_id, item_id, unit_price, unit, effective_date, site_id

boms             — BOM 헤더 (식단 확정 시 자동 생성)
├─ id, menu_plan_id, site_id, period_start, period_end, headcount, status

bom_items        — BOM 상세 (품목별 소요량)
├─ bom_id, item_id, quantity, unit, unit_price, subtotal, notes

purchase_orders  — 발주서 헤더
├─ id, bom_id, site_id, vendor_id, status (draft/submitted/approved/received)
├─ order_date, delivery_date, total_amount, approved_by, approved_at

purchase_order_items — 발주서 상세
├─ po_id, item_id, quantity, unit, unit_price, subtotal

inventory        — 재고 현황 (품목별)
├─ id, site_id, item_id, quantity, unit, location, last_updated

inventory_lots   — 입고 로트 (납품 단위 추적)
├─ id, site_id, item_id, vendor_id, po_id, lot_number
├─ quantity, unit, received_at, expiry_date, status (active/used/expired)
```

---

## 5. Agent Architecture 확장

### 5.1 Intent Router 확장 (11 → 16 intents)

```python
INTENTS = {
    # MVP 1 기존 11개
    "menu_generate", "menu_validate", "recipe_search", "recipe_scale",
    "work_order", "haccp_checklist", "haccp_record", "haccp_incident",
    "dashboard", "settings", "general",

    # MVP 2 신규 5개
    "purchase_bom",     # BOM 산출/조회
    "purchase_order",   # 발주서 생성/관리
    "purchase_risk",    # 단가/공급 리스크
    "inventory_check",  # 재고 조회
    "inventory_receive" # 입고/검수
}
```

### 5.2 Tool 확장 (11 → 17 tools)

```python
MVP2_TOOLS = [
    "calculate_bom",        # 식단 ID → 소요량 집계
    "generate_purchase_order",  # BOM → 발주서 초안
    "compare_vendors",      # 품목별 벤더 비교 (단가/납기/품질)
    "detect_price_risk",    # 단가 급등 감지 (임계치 기반)
    "suggest_alternatives", # 대체품/대체 벤더 추천
    "check_inventory",      # 재고 현황 + 유통기한 조회
]
```

### 5.3 RAG 지식베이스 확장

| 문서 유형 | 설명 | 임베딩 대상 |
|----------|------|-----------|
| 단가 계약서 | 벤더별 품목/단가 계약 | 단가 비교 |
| 검수 기준 문서 | 신선도/온도/포장 기준 | 입고 검수 |
| 대체품 가이드 | 식재료 대체 규격 및 알레르겐 | 대체 추천 |

---

## 6. 사용자 시나리오 (User Stories)

### S1 — 식단 확정 → BOM 자동 생성

```
NUT: "이번주 A현장 식단 확정"
→ 시스템: menu_plans.status = 'confirmed' 이벤트
→ Agent: calculate_bom 자동 호출
→ PUR: BOM 리스트 수신 (품목/소요량/예상원가)
→ PUR: "발주서 만들어줘" 요청
→ Agent: generate_purchase_order → 벤더 자동 매핑 → 발주 초안 생성
→ PUR: 검토 후 OPS 승인 요청
→ OPS: 발주 확정
```

### S2 — 단가 급등 대응

```
상황: 양파 시세 전주 대비 +22% 급등
→ Agent: detect_price_risk 자동 감지 → 대시보드 경보
→ PUR/OPS 알림 수신
→ "영향 식단 보여줘" → Agent: 영향 메뉴/원가 추정 표시
→ "대체품 있어?" → Agent: suggest_alternatives 호출
→ NUT: 메뉴 스왑 승인 → BOM 재산출
```

### S3 — 납품 검수

```
KIT/PUR: "오늘 납품 검수 체크리스트 줘"
→ Agent: 납품 예정 로트 조회 + 검수 기준 문서 RAG
→ 검수 항목 체크리스트 생성 (신선도/온도/포장/수량)
→ 기록 저장 → inventory_lots.status = 'active'
→ 불합격 시: 반품 플로우 안내
```

### S4 — 재고 우선 사용 추천

```
NUT: "다음주 식단 계획 중, 재고 남은 거 반영해줘"
→ Agent: check_inventory 호출 → 유통기한 임박 품목 확인
→ 식단 생성 시 해당 식재료 우선 사용 제안
→ BOM 생성 시 재고 차감 반영
```

---

## 7. 성공 기준 (KPI)

| KPI | 목표 | 측정 방법 |
|-----|------|---------|
| BOM 산출 시간 단축 | 수작업 대비 80% | 식단 확정 → BOM 완성 시간 |
| 발주서 초안 생성 시간 | < 2분 (자동) | 시스템 타임스탬프 |
| 단가 급등 감지율 | ≥ 95% | 임계치 초과 건 대비 알림 건 |
| 발주 오류율 감소 | 50% 이하 | 발주 취소/수정 건수 |
| 재고 폐기율 감소 | 20% 이하 | 유통기한 만료 로트 비율 |
| 로트 추적 가능율 | 100% | 전체 납품 로트 추적 성공율 |

---

## 8. 의존성 & 리스크

### 8.1 MVP 1 의존성

| 항목 | MVP 1 결과물 | MVP 2 활용 |
|------|------------|-----------|
| `menu_plans` 테이블 | ✅ 완료 | 식단 확정 이벤트 트리거 |
| `recipes` + `recipe_documents` | ✅ 완료 | BOM 소요량 계산 기초 |
| `items` 테이블 | ✅ 완료 | 식재료 마스터 (알레르겐/영양) |
| `audit_logs` | ✅ 완료 | 발주/BOM 감사 기록 |
| RAG Pipeline | ✅ 완료 | 단가/검수 문서 검색 |
| RBAC Depends | ✅ 완료 | PUR 역할 권한 검사 |

### 8.2 리스크

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| 레시피 BOM 필드 미정의 | 중 | 높음 | 레시피 모델에 `ingredients_bom` JSONB 필드 추가 확인 |
| 벤더 마스터 데이터 없음 | 높음 | 중간 | Seed 데이터에 샘플 벤더/단가 포함 |
| 발주 승인 워크플로우 복잡도 | 중 | 중간 | 단순화: draft → submitted → approved → received |
| 재고 실시간 동기화 | 낮음 | 낮음 | MVP 2는 수동 입력 + 발주 기반 계산, IoT는 MVP 4 |

---

## 9. 개발 일정 (Phase Plan)

| Phase | 내용 | 기간 | 담당 |
|-------|------|------|------|
| Phase 1 | DB 모델 + Alembic 마이그레이션 (7개 테이블) | 1주 | Backend |
| Phase 2 | BOM 엔진 + 발주서 Core API + Agent Tools (6개) | 2주 | Backend + AI |
| Phase 3 | 재고/입고 API + 로트 추적 + 리스크 감지 | 1주 | Backend |
| Phase 4 | Frontend `/purchase` + `/inventory` UI | 2주 | Frontend |
| Phase 5 | 대시보드 확장 + 알림 시스템 + Integration QA | 1주 | Full Stack |
| **합계** | | **7주** | |

---

## 10. 참고 문서

- **요구사항**: `food_ai-agent_req.md` §5.5 (FR-PUR-001~006), §5.6 (FR-INV-001~003)
- **MVP 1 Report**: `docs/archive/2026-02/food-ai-agent/food-ai-agent.report.md`
- **MVP 1 Design**: `docs/archive/2026-02/food-ai-agent/food-ai-agent.design.md`
- **현재 DB 스키마**: `food-ai-agent-api/app/models/orm/`

---

## 11. 체크리스트 (Plan 완료 조건)

- [x] 기능 범위 (In/Out Scope) 정의
- [x] 신규 역할 (PUR) 권한 정의
- [x] 신규 DB 테이블 목록 (7개)
- [x] 신규 Agent Tool 목록 (6개)
- [x] 신규 Intent 목록 (5개)
- [x] 신규 UI 화면 목록 (4개)
- [x] 사용자 시나리오 (4개)
- [x] KPI 정의
- [x] MVP 1 의존성 확인
- [x] 리스크 식별
- [x] 개발 Phase 계획

**다음 단계**: `/pdca design mvp2-purchase`
