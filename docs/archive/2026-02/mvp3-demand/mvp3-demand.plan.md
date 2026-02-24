# MVP 3 Plan: 수요예측/원가최적화/클레임 관리

- **문서 버전**: 1.0.0
- **작성일**: 2026-02-24
- **PDCA 단계**: Plan
- **기반 요구사항**: `food_ai-agent_req.md` §5.4, §5.8, §11 MVP 3~4, §5.9

---

## 1. 개요

### 1.1 목적

MVP 1(식단·레시피·HACCP), MVP 2(구매·발주·BOM) 위에 **수요예측 + 원가최적화 + 클레임 관리**를 추가하여, 급식 운영의 전 사이클을 AI로 완성한다.

- **식수 예측**: 과거 실적·요일·이벤트·날씨 기반 → 잔반 감소 & 발주 정확도 향상
- **잔반/선호 피드백 루프**: 실적 데이터 → 다음 식단 추천 품질 향상
- **원가 시뮬레이션**: 메뉴 조합별 원가 분석 → 예산 내 최적 식단 제안
- **클레임 자동 분류 + 원인분석 + 재발방지**: CS 업무 자동화 및 품질 개선 루프

### 1.2 범위 (In Scope)

| 기능 그룹 | 주요 내용 | 요구사항 참조 |
|-----------|----------|--------------|
| **수요예측** | 식수 예측(기본/이벤트 보정), 신뢰도 표시 | FR-FCST-001~003 |
| **잔반 피드백** | 잔반률/선호도 입력 → 식단 추천 반영 | FR-FCST-002 |
| **원가 최적화** | 원가 시뮬레이션, 대체 메뉴 제안, 예산 대비 분석 | FR-MENU-002, OPS KPI |
| **클레임 관리** | 접수/분류/원인분석/조치추적/재발방지 | FR-CLM-001~004 |
| **통합 대시보드** | 수요예측·잔반·원가·클레임 KPI 통합 | FR-OPS-001~003 |

### 1.3 제외 (Out of Scope)

- 실시간 IoT 센서 연동 (온도계/저울)
- 외부 날씨 API 연동 (1차 구현은 수동 입력, 이후 확장)
- 고객 설문/평점 앱 연동 (클레임은 내부 접수 채널 기준)

---

## 2. 신규 사용자 역할

| 약어 | 역할 | MVP 3 추가 권한 |
|------|------|-----------------|
| OPS | 운영/관리 | 수요예측 조회, 원가 시뮬레이션, KPI 대시보드 |
| CS | CS/영업 | 클레임 접수/분류/조치, 리포트 생성 |
| NUT | 영양사/메뉴팀 | 잔반 데이터 입력, 선호 피드백 반영 식단 생성 |
| KIT | 조리/생산 | 예측 식수 기반 조리량 확인, 잔반 입력 |

---

## 3. 기능 상세

### 3.1 수요예측 (Demand Forecast)

#### FR-FCST-001: 식수 예측 기본 모델

**입력 변수**:
- 과거 실적 식수 (최소 4주 이상)
- 요일 패턴 (월~금, 토, 공휴일)
- 계획 식수 (NUT가 설정한 기준 인원)
- 현장(site_id) 특성 (학교/기업/병원)

**예측 출력**:
- 예측 식수 (범위: min~max)
- 신뢰도 (%) + 리스크 요인 표시
- 전주/전년 동기 대비 변화율

**알고리즘 (초기)**: 가중 이동평균 (Weighted Moving Average) + 요일 계수 보정
- 추후 확장: Prophet (Facebook) 또는 LightGBM 시계열 모델

#### FR-FCST-002: 잔반/선호 피드백 루프

**잔반 데이터 입력**:
- KIT/NUT: 날짜·메뉴별 잔반량(kg 또는 %) 입력
- 메뉴별 인기도 (매우 좋음/좋음/보통/나쁨) 선택 입력

**피드백 적용**:
- 잔반률 높은 메뉴 → 식단 생성 시 빈도 감소 권고
- 선호도 높은 메뉴 → 대안 제시 우선순위 상향
- `generate_menu_plan` Tool에 선호도 벡터 컨텍스트로 주입

#### FR-FCST-003: 이벤트/휴무/행사 보정

**이벤트 유형**: 공휴일, 학사 행사(수학여행/체험학습), 기업 이벤트, 기타 임시 휴무

**보정 방식**:
- 이벤트 캘린더 입력 → 예측 식수 자동 조정 (출석률 × 보정 계수)
- Agent가 "이번 주 수요일 현장 행사로 식수 70% 예상" 자동 경고

---

### 3.2 원가 최적화 (Cost Optimization)

#### 원가 시뮬레이션

**시나리오 분석**:
- 현재 식단 원가 계산 (BOM × 단가)
- 예산 목표 입력 시 → 원가 초과 메뉴 자동 식별
- 대체 메뉴/식재료 제안으로 목표 원가 달성 경로 제시

**원가 트래킹**:
- 일간/주간/월간 현장별 원가율 추이
- 식단 확정 원가 vs 실제 발주 원가 차이 분석
- 원가율 임계값 초과 시 Alert

#### 대체 메뉴 추천

- 단가 급등 식재료 포함 메뉴 → 유사 영양 프로파일 대체 메뉴 자동 제안
- MVP 2 `suggest_alternatives` Tool 확장 (메뉴 단위 대체까지 커버)

---

### 3.3 클레임 관리 (Claim Management)

#### FR-CLM-001: 클레임 접수 및 자동 분류

**접수 채널**: 내부 시스템 직접 입력 (CS/OPS)

**자동 분류 카테고리**:
| 카테고리 | 예시 |
|----------|------|
| 맛/품질 | 짜다, 싱겁다, 냄새, 식감 |
| 이물 | 이물질, 벌레, 금속 |
| 양/분량 | 양 부족, 과잉 제공 |
| 온도 | 차갑다, 너무 뜨겁다 |
| 알레르겐 | 알레르기 유발 의심 |
| 위생/HACCP | 식중독 의심, 복통 |
| 서비스 | 배식 시간, 직원 태도 |

**심각도 자동 판정**: 위생/알레르겐 클레임 → 즉시 SAFE-002 트리거 (기존 HACCP incident flow 연동)

#### FR-CLM-002: 원인 분석 지원

**Claude Agent 가설 생성**:
- 클레임 유형 + 날짜 + 현장 입력 시 → 가능 원인 목록 제시
- 관련 데이터 자동 조회: 해당 날짜 식단, 레시피 버전, 로트 번호, 공급업체, HACCP 기록
- "짜다" 클레임 3건 연속 → "레시피 염도 표준 대비 편차" 가설 자동 생성

#### FR-CLM-003: 조치/재발방지 액션 관리

**액션 유형**:
- 레시피 수정 → NUT 검토 요청 (승인 워크플로우)
- 공급업체 품질 경고 → PUR 전달
- 직원 교육 필요 → KIT 공지
- HACCP 절차 보완 → QLT 업데이트

**진행 상태 추적**: 접수 → 원인분석 → 조치 → 완료/재발확인

#### FR-CLM-004: 클레임 리포팅

- 기간별/현장별/카테고리별 클레임 집계
- 재발률, 해결 소요 시간 KPI
- OPS 월간 품질 리포트 자동 생성 (AI 요약)

---

### 3.4 통합 대시보드 확장

MVP 1·2의 `query_dashboard` Tool 및 대시보드 페이지에 신규 위젯 추가:

| 위젯 | 내용 | 사용자 |
|------|------|--------|
| 수요예측 현황 | 이번 주 예측 식수 vs 실제 | OPS, KIT |
| 잔반률 추이 | 현장별 주간 잔반률 그래프 | OPS, NUT |
| 원가율 모니터 | 목표 대비 실제 원가율 | OPS, PUR |
| 클레임 현황 | 이번 달 건수, 미처리, 재발 | OPS, CS |

---

## 4. 신규 DB 테이블

| 테이블 | 용도 |
|--------|------|
| `demand_forecasts` | 예측 결과 (site_id, date, meal_type, predicted, confidence) |
| `actual_headcounts` | 실제 식수 (site_id, date, meal_type, actual, served) |
| `waste_records` | 잔반 기록 (site_id, date, menu_plan_item_id, waste_kg, waste_pct) |
| `menu_preferences` | 메뉴 선호도 (site_id, recipe_id, preference_score, period) |
| `site_events` | 이벤트 캘린더 (site_id, date, event_type, adjustment_factor) |
| `cost_analyses` | 원가 분석 결과 (menu_plan_id, target_cost, actual_cost, variance) |
| `claims` | 클레임 원장 (site_id, date, category, severity, description) |
| `claim_actions` | 조치 이력 (claim_id, action_type, assignee, status, due_date) |

---

## 5. 신규 AI Tool (Agent 확장)

| Tool | 설명 |
|------|------|
| `forecast_headcount` | 날짜·현장·이벤트 기반 식수 예측 |
| `record_waste` | 잔반 데이터 입력 및 피드백 루프 트리거 |
| `simulate_cost` | 식단 원가 시뮬레이션 및 대체 제안 |
| `register_claim` | 클레임 접수 + 자동 분류 + 심각도 판정 |
| `analyze_claim` | 클레임 원인 분석 가설 생성 (RAG 조회 포함) |
| `track_claim_action` | 조치 등록/진행 상태 업데이트 |

**Agent Intent 추가** (16 → 22개):
- `forecast_demand` — 수요예측 요청
- `record_actual` — 실적 입력 (식수/잔반)
- `optimize_cost` — 원가 시뮬레이션/최적화
- `manage_claim` — 클레임 접수/조회
- `analyze_claim_root_cause` — 원인분석
- `generate_quality_report` — 품질/클레임 리포트

---

## 6. 신규 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/forecast/headcount` | 식수 예측 조회 |
| POST | `/forecast/headcount` | 예측 생성/갱신 |
| POST | `/forecast/actual` | 실제 식수 등록 |
| POST | `/waste/records` | 잔반 기록 등록 |
| GET | `/waste/records` | 잔반 이력 조회 |
| PUT | `/menu-preferences/{site_id}` | 선호도 업데이트 |
| POST | `/cost/simulate` | 원가 시뮬레이션 |
| GET | `/cost/analyses` | 원가 분석 이력 |
| GET | `/site-events` | 이벤트 캘린더 조회 |
| POST | `/site-events` | 이벤트 등록 |
| GET | `/claims` | 클레임 목록 조회 |
| POST | `/claims` | 클레임 접수 |
| GET | `/claims/{id}` | 클레임 상세 |
| PUT | `/claims/{id}/status` | 상태 업데이트 |
| POST | `/claims/{id}/actions` | 조치 등록 |
| GET | `/claims/{id}/actions` | 조치 이력 |
| GET | `/reports/quality` | 품질/클레임 리포트 |
| GET | `/dashboard/forecast` | 예측 대시보드 데이터 |
| GET | `/dashboard/cost` | 원가 대시보드 데이터 |
| GET | `/dashboard/quality` | 품질 대시보드 데이터 |

---

## 7. 신규 Frontend 페이지 및 컴포넌트

### 신규 페이지 (App Router)

| 경로 | 설명 | 주요 역할 |
|------|------|----------|
| `/forecast` | 수요예측 현황 + 예측 조회 | OPS, KIT, NUT |
| `/waste` | 잔반 입력 + 현황 분석 | KIT, NUT, OPS |
| `/cost-optimizer` | 원가 시뮬레이션 + 분석 | OPS, NUT, PUR |
| `/claims` | 클레임 목록 + 접수 | CS, OPS |
| `/claims/[id]` | 클레임 상세 + 조치 | CS, OPS |

### 신규 컴포넌트 (예상 20+개)

**수요예측**: `forecast-chart`, `headcount-input-form`, `event-calendar-widget`, `forecast-confidence-badge`

**잔반**: `waste-input-form`, `waste-trend-chart`, `menu-preference-rating`, `waste-by-menu-table`

**원가**: `cost-simulation-panel`, `cost-variance-indicator`, `budget-vs-actual-chart`, `menu-swap-suggestion-card`

**클레임**: `claim-register-form`, `claim-category-badge`, `claim-severity-indicator`, `claim-action-tracker`, `claim-list-table`, `claim-analysis-panel`, `root-cause-hypothesis-card`, `quality-report-viewer`

---

## 8. 기술 구현 특이사항

### 수요예측 알고리즘 (Phase 1: 단순 모델)

```python
# 가중 이동평균 예측 (외부 ML 라이브러리 불필요)
def weighted_moving_average(actuals: list[int], weights: list[float]) -> float:
    return sum(a * w for a, w in zip(actuals[-len(weights):], weights)) / sum(weights)

# 요일 계수 (과거 데이터 학습)
DOW_COEFFICIENTS = {0: 1.0, 1: 0.98, 2: 0.97, 3: 0.96, 4: 0.95, 5: 0.7, 6: 0.3}
```

**확장 고려**: `prophet` 또는 `lightgbm` 추가 (requirements.txt 선택적 의존성)

### 잔반 피드백 → RAG 컨텍스트 주입

```python
# generate_menu_plan Tool 내부 확장
preference_context = await get_site_preferences(db, site_id)
# 선호도 낮은 메뉴 → RAG 쿼리에서 down-weight
```

### 클레임 심각도 자동 HACCP 연동

```python
# SAFE-002: 위생/알레르겐 심각 클레임 → incident 자동 생성
if claim.category in ["위생/HACCP", "알레르겐"] and claim.severity == "high":
    await trigger_haccp_incident(db, claim)
```

---

## 9. 개발 일정 (7주)

| 주차 | 내용 |
|------|------|
| Week 1 | DB 스키마 (8 테이블) + Alembic 마이그레이션 |
| Week 2 | 수요예측 API + Tool (forecast_headcount, record_waste) |
| Week 3 | 원가 시뮬레이션 API + Tool (simulate_cost) |
| Week 4 | 클레임 관리 API + Tool (register_claim, analyze_claim, track_claim_action) |
| Week 5 | Frontend 페이지 5개 + 컴포넌트 20개 |
| Week 6 | Agent Intent 확장 (16→22) + 통합 대시보드 위젯 |
| Week 7 | 통합 테스트 + 피드백 루프 End-to-End 검증 |

---

## 10. 목표 KPI

| KPI | 목표 |
|-----|------|
| 식수 예측 오차율 | ≤ 10% (MAPE) |
| 잔반률 감소 | 파일럿 현장 기준 -15% (6주 기간) |
| 원가율 개선 | 목표 원가 내 식단 제안 성공률 ≥ 80% |
| 클레임 분류 정확도 | ≥ 90% (Claude 자동 분류) |
| 클레임 처리 소요 시간 | 평균 -30% 단축 |
| 재발 클레임률 | ≤ 5% |

---

## 11. 의존성

- **MVP 1 필수**: menu_plans, recipes, haccp_incidents (기존 테이블 참조)
- **MVP 2 필수**: purchase_orders, vendors, vendor_prices, inventory (발주 원가 연동)
- **GCloud 인프라**: Cloud Run + Cloud SQL (이미 설계 완료, `docs/infra/gcloud-architecture.md`)
