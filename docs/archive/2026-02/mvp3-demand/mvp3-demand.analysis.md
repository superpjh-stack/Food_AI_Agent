# MVP 3 (Demand/Cost/Claim) Analysis Report

> **Analysis Type**: Gap Analysis (Design vs Implementation)
>
> **Project**: Food AI Agent
> **Version**: 1.0.0
> **Analyst**: gap-detector
> **Date**: 2026-02-24
> **Design Doc**: [mvp3-demand.design.md](../02-design/features/mvp3-demand.design.md)

---

## 1. Analysis Overview

### 1.1 Analysis Purpose

Verify that the MVP 3 (Demand Forecasting / Cost Optimization / Claim Management) implementation matches the design document across all layers: DB, API, Agent Tools, Frontend, and Tests.

### 1.2 Analysis Scope

- **Design Document**: `docs/02-design/features/mvp3-demand.design.md`
- **Implementation Paths**:
  - Backend: `food-ai-agent-api/app/` (models, routers, services, agents/tools)
  - Frontend: `food-ai-agent-web/` (pages, components, hooks)
  - Tests: `food-ai-agent-api/tests/`
- **Analysis Date**: 2026-02-24

---

## 2. Gap Analysis (Design vs Implementation)

### 2.1 ORM Models (8 models)

| Design Model | File | Status | Notes |
|-------------|------|:------:|-------|
| DemandForecast | `app/models/orm/forecast.py` | MATCH | 12 columns, index matches |
| ActualHeadcount | `app/models/orm/forecast.py` | MATCH | 10 columns, index matches |
| SiteEvent | `app/models/orm/forecast.py` | MATCH | 9 columns, index matches |
| WasteRecord | `app/models/orm/waste.py` | MATCH | 13 columns, index matches |
| MenuPreference | `app/models/orm/waste.py` | MATCH | 7 columns, unique index matches |
| CostAnalysis | `app/models/orm/cost.py` | MATCH | 13 columns, 2 indexes match |
| Claim | `app/models/orm/claim.py` | MATCH | 21 columns, 3 indexes match |
| ClaimAction | `app/models/orm/claim.py` | MATCH | 11 columns, index matches |

**`__init__.py` imports**: All 8 models (DemandForecast, ActualHeadcount, SiteEvent, WasteRecord, MenuPreference, CostAnalysis, Claim, ClaimAction) properly imported and exported in `__all__`.

**ORM Score: 8/8 (100%)**

### 2.2 Alembic Migration

| Design | Implementation | Status |
|--------|---------------|:------:|
| `003_mvp3_demand_cost_claim.py` with 8 tables | `alembic/versions/003_mvp3_demand_cost_claim.py` (185 lines) | MATCH |

All 8 tables created with full column definitions (not abbreviated), all indexes created, `downgrade()` drops all 8 tables in correct reverse order.

**Migration Score: 1/1 (100%)**

### 2.3 Service Layer

| Design | Implementation | Status | Notes |
|--------|---------------|:------:|-------|
| `forecast_service.py` | `app/services/forecast_service.py` (65 lines) | MATCH | |
| `DOW_COEFFICIENTS` | Matches design exactly | MATCH | 7 day coefficients |
| `WMA_WEIGHTS` | Matches design exactly | MATCH | 7-week weights |
| `ForecastResult` NamedTuple | 5 fields match | MATCH | |
| `run_wma_forecast()` | Signature + logic matches | MATCH | Enhanced: adds `max(0, mid-margin)` guard, weekend risk factor |

**Service Score: 5/5 (100%)**

### 2.4 Agent Tools (demand_tools.py)

| Design Tool | Implementation | Status | Notes |
|-------------|---------------|:------:|-------|
| `forecast_headcount` | L25-114 (90 lines) | MATCH | Full WMA + event + DB save |
| `record_waste` | L117-206 (90 lines) | MATCH | EWMA preference update |
| `simulate_cost` | L209-372 (164 lines) | MATCH | BOM + VendorPrice + CostAnalysis save |
| `register_claim` | L375-465 (91 lines) | MATCH | SAFE-002 trigger implemented |
| `analyze_claim` | L468-617 (150 lines) | MATCH | RAG + DB + hypotheses generation |
| `track_claim_action` | L620-681 (62 lines) | MATCH | Status auto-update + close logic |

**Tools Score: 6/6 (100%)**

### 2.5 Tool Registry (registry.py)

| Design Item | Implementation | Status | Notes |
|-------------|---------------|:------:|-------|
| DEMAND_TOOLS list (6 tools) | L268-376, 6 tool schemas | MATCH | Exact schema match |
| AGENT_TOOLS["menu"] += forecast_headcount | L380 `DEMAND_TOOLS[:1]` | MATCH | |
| AGENT_TOOLS["haccp"] += register_claim | L382 `DEMAND_TOOLS[3:4]` | MATCH | SAFE-002 |
| AGENT_TOOLS["general"] += DEMAND_TOOLS | L383 | MATCH | |
| AGENT_TOOLS["purchase"] += simulate_cost | L384 `DEMAND_TOOLS[2:3]` | MATCH | |
| AGENT_TOOLS["demand"] = DEMAND_TOOLS | L385 | MATCH | |
| AGENT_TOOLS["claim"] = DEMAND_TOOLS[3:] | L386 | MATCH | |
| ALL_TOOLS includes DEMAND_TOOLS | L389-392 | MATCH | |

**Registry Score: 8/8 (100%)**

### 2.6 Intent Router (intent_router.py)

| Design Intent | Implementation | Status |
|---------------|---------------|:------:|
| `forecast_demand` -> "demand" | L53 | MATCH |
| `record_actual` -> "demand" | L54 | MATCH |
| `optimize_cost` -> "demand" | L55 | MATCH |
| `manage_claim` -> "claim" | L56 | MATCH |
| `analyze_claim_root_cause` -> "claim" | L57 | MATCH |
| `generate_quality_report` -> "claim" | L58 | MATCH |
| INTENT_SYSTEM_PROMPT descriptions | L80-85 | MATCH | All 6 descriptions present |

**Intent Router Score: 7/7 (100%)**

### 2.7 Existing File Modifications

| Design Change | Implementation | Status | Notes |
|---------------|---------------|:------:|-------|
| `menu_tools.py` preference_context | L79, L94, L117 | MATCH | Loads low-preference recipes, injects into prompt |
| `dashboard_tools.py` forecast/waste/cost/claims widgets | L97-183 | MATCH | 4 widget data sections implemented |

**Modifications Score: 2/2 (100%)**

### 2.8 Pydantic Schemas

| Design Schema | File | Status | Notes |
|---------------|------|:------:|-------|
| ForecastRequest | `schemas/forecast.py` | MATCH | 4 fields |
| ForecastResponse | `schemas/forecast.py` | MATCH | 11 fields + Config |
| ActualHeadcountCreate | `schemas/forecast.py` | MATCH | 7 fields |
| SiteEventCreate | `schemas/forecast.py` | MATCH | 7 fields, `adjustment_factor` has `ge`/`le` validators |
| WasteRecordCreate | `schemas/waste.py` | MATCH | Refactored: uses nested `WasteItemCreate` list (improved) |
| MenuPreferenceUpdate | `schemas/waste.py` | MATCH | 3 fields |
| CostSimulateRequest | `schemas/cost.py` | MATCH | 5 fields |
| CostSimulateResponse | `schemas/cost.py` | MATCH | 11 fields (enhanced: adds per-meal cost) |
| ClaimCreate | `schemas/claim.py` | MATCH | 11 fields |
| ClaimResponse | `schemas/claim.py` | MATCH | 18 fields (enhanced: includes all ORM fields) |
| ClaimActionCreate | `schemas/claim.py` | MATCH | 5 fields |

Additional schemas not in design (implementation enhancements):
- `ActualHeadcountResponse`, `SiteEventUpdate`, `SiteEventResponse`
- `WasteRecordResponse`, `MenuPreferenceResponse`, `WasteSummaryItem`, `WasteSummaryResponse`
- `CostAnalysisResponse`, `CostTrendPoint`, `CostTrendResponse`
- `ClaimStatusUpdate`, `ClaimActionResponse`, `QualityReportResponse`

**Schema Score: 11/11 (100%)**

### 2.9 API Routers

#### 2.9.1 Forecast Router (8 endpoints)

| Design Endpoint | Implementation | Status |
|----------------|---------------|:------:|
| GET `/api/v1/forecast/headcount` | L25 `list_forecasts` | MATCH |
| POST `/api/v1/forecast/headcount` | L67 `create_forecast` | MATCH |
| POST `/api/v1/forecast/actual` | L89 `record_actual` | MATCH |
| GET `/api/v1/forecast/actual` | L112 `list_actuals` | MATCH |
| GET `/api/v1/site-events` | L156 `list_site_events` | MATCH |
| POST `/api/v1/site-events` | L177 `create_site_event` | MATCH |
| PUT `/api/v1/site-events/{id}` | L199 `update_site_event` | MATCH |
| DELETE `/api/v1/site-events/{id}` | L228 `delete_site_event` | MATCH |

#### 2.9.2 Waste Router (5 endpoints)

| Design Endpoint | Implementation | Status |
|----------------|---------------|:------:|
| POST `/api/v1/waste/records` | L20 `create_waste_record` | MATCH |
| GET `/api/v1/waste/records` | L46 `list_waste_records` | MATCH |
| GET `/api/v1/waste/summary` | L88 `waste_summary` | MATCH |
| PUT `/api/v1/waste/preferences/{site_id}` | L170 `update_preferences` | MATCH |
| GET `/api/v1/waste/preferences/{site_id}` | L143 `get_preferences` | MATCH |

#### 2.9.3 Cost Router (4 endpoints)

| Design Endpoint | Implementation | Status |
|----------------|---------------|:------:|
| POST `/api/v1/cost/simulate` | L19 `simulate_cost` | MATCH |
| GET `/api/v1/cost/analyses` | L40 `list_analyses` | MATCH |
| GET `/api/v1/cost/analyses/{id}` | L78 `get_analysis` | MATCH |
| GET `/api/v1/cost/trend` | L93 `cost_trend` | MATCH |

#### 2.9.4 Claims Router (7 design + 1 bonus)

| Design Endpoint | Implementation | Status |
|----------------|---------------|:------:|
| GET `/api/v1/claims` | L25 `list_claims` | MATCH |
| POST `/api/v1/claims` | L75 `create_claim` | MATCH |
| GET `/api/v1/claims/{id}` | L161 `get_claim` | MATCH |
| PUT `/api/v1/claims/{id}/status` | L176 `update_claim_status` | MATCH |
| POST `/api/v1/claims/{id}/actions` | L200 `add_claim_action` | MATCH |
| GET `/api/v1/claims/{id}/actions` | L223 `list_claim_actions` | MATCH |
| GET `/api/v1/reports/quality` | L100 `quality_report` | MATCH |
| POST `/api/v1/claims/{id}/analyze` | L237 `analyze_claim` | ADDED | Not in design; exposes AI analysis via REST |

#### 2.9.5 main.py Router Registration

All 4 routers registered (forecast, waste, cost, claims) at L46-49.

**API Score: 25/24 (100% + 1 bonus endpoint)**

### 2.10 Frontend Hooks

| Design Hook | Implementation | Status | Notes |
|-------------|---------------|:------:|-------|
| `useForecast.ts` | `lib/hooks/use-forecast.ts` | MATCH | Path changed: `hooks/` -> `lib/hooks/` |
| `useWaste.ts` | `lib/hooks/use-waste.ts` | MATCH | Path changed |
| `useCostAnalysis.ts` | `lib/hooks/use-cost-analysis.ts` | MATCH | Path changed, kebab-case filename |
| `useClaims.ts` | `lib/hooks/use-claims.ts` | MATCH | Path changed |

**Hooks Score: 4/4 (100%)**

### 2.11 Frontend Components

#### Forecast (4 components)

| Design Component | Implementation | Status |
|-----------------|---------------|:------:|
| `forecast-chart.tsx` | `components/forecast/forecast-chart.tsx` | MATCH |
| `headcount-input-form.tsx` | `components/forecast/headcount-input-form.tsx` | MATCH |
| `event-calendar-widget.tsx` | `components/forecast/event-calendar-widget.tsx` | MATCH |
| `forecast-confidence-badge.tsx` | `components/forecast/forecast-confidence-badge.tsx` | MATCH |

#### Waste (4 components)

| Design Component | Implementation | Status |
|-----------------|---------------|:------:|
| `waste-input-form.tsx` | `components/waste/waste-input-form.tsx` | MATCH |
| `waste-trend-chart.tsx` | `components/waste/waste-trend-chart.tsx` | MATCH |
| `menu-preference-rating.tsx` | `components/waste/menu-preference-rating.tsx` | MATCH |
| `waste-by-menu-table.tsx` | `components/waste/waste-by-menu-table.tsx` | MATCH |

#### Cost (4 components)

| Design Component | Implementation | Status |
|-----------------|---------------|:------:|
| `cost-simulation-panel.tsx` | `components/cost/cost-simulation-panel.tsx` | MATCH |
| `cost-variance-indicator.tsx` | `components/cost/cost-variance-indicator.tsx` | MATCH |
| `budget-vs-actual-chart.tsx` | `components/cost/budget-vs-actual-chart.tsx` | MATCH |
| `menu-swap-suggestion-card.tsx` | `components/cost/menu-swap-suggestion-card.tsx` | MATCH |

#### Claims (8 components)

| Design Component | Implementation | Status |
|-----------------|---------------|:------:|
| `claim-register-form.tsx` | `components/claims/claim-register-form.tsx` | MATCH |
| `claim-category-badge.tsx` | `components/claims/claim-category-badge.tsx` | MATCH |
| `claim-severity-indicator.tsx` | `components/claims/claim-severity-indicator.tsx` | MATCH |
| `claim-action-tracker.tsx` | `components/claims/claim-action-tracker.tsx` | MATCH |
| `claim-list-table.tsx` | `components/claims/claim-list-table.tsx` | MATCH |
| `claim-analysis-panel.tsx` | `components/claims/claim-analysis-panel.tsx` | MATCH |
| `root-cause-hypothesis-card.tsx` | `components/claims/root-cause-hypothesis-card.tsx` | MATCH |
| `quality-report-viewer.tsx` | `components/claims/quality-report-viewer.tsx` | MATCH |

**Components Score: 20/20 (100%)**

### 2.12 Frontend Pages

| Design Page | Implementation | Status |
|------------|---------------|:------:|
| `forecast/page.tsx` | `app/(main)/forecast/page.tsx` (122 lines) | MATCH |
| `waste/page.tsx` | `app/(main)/waste/page.tsx` | MATCH |
| `cost-optimizer/page.tsx` | `app/(main)/cost-optimizer/page.tsx` | MATCH |
| `claims/page.tsx` | `app/(main)/claims/page.tsx` (131 lines) | MATCH |
| `claims/[id]/page.tsx` | `app/(main)/claims/[id]/page.tsx` (203 lines) | MATCH |

**Pages Score: 5/5 (100%)**

### 2.13 Dashboard Widgets

| Design Widget | Implementation | Status |
|--------------|---------------|:------:|
| `forecast-status-widget.tsx` | `components/dashboard/forecast-status-widget.tsx` | MATCH |
| `waste-rate-widget.tsx` | `components/dashboard/waste-rate-widget.tsx` | MATCH |
| `cost-rate-widget.tsx` | `components/dashboard/cost-rate-widget.tsx` | MATCH |
| `claims-summary-widget.tsx` | `components/dashboard/claims-summary-widget.tsx` | MATCH |

**Dashboard Widgets Score: 4/4 (100%)**

### 2.14 Sidebar Navigation

| Design Nav Item | Implementation | Status |
|----------------|---------------|:------:|
| `/forecast` "수요예측" TrendingUp | L14 `{ href: '/forecast', label: '수요예측', icon: 'TrendingUp' }` | MATCH |
| `/waste` "잔반관리" Trash2 | L15 `{ href: '/waste', label: '잔반관리', icon: 'Trash2' }` | MATCH |
| `/cost-optimizer` "원가최적화" Calculator | L16 `{ href: '/cost-optimizer', label: '원가최적화', icon: 'Calculator' }` | MATCH |
| `/claims` "클레임" AlertCircle | L17 `{ href: '/claims', label: '클레임', icon: 'AlertCircle' }` | MATCH |

**Sidebar Score: 4/4 (100%)**

### 2.15 Tests

| Design Test | Implementation | Status |
|-------------|---------------|:------:|
| `test_forecast/test_wma_algorithm.py` | 6 test functions (60 lines) | MATCH |
| `test_forecast/test_forecast_api.py` | exists | MATCH |
| `test_waste/test_waste_api.py` | exists | MATCH |
| `test_cost/test_cost_simulation.py` | exists | MATCH |
| `test_claims/test_claim_flow.py` | exists | MATCH |
| `test_claims/test_safe002_trigger.py` | 4 test functions (88 lines) | MATCH |

**Tests Score: 6/6 (100%)**

---

## 3. Match Rate Summary

```
+---------------------------------------------+
|  Overall Match Rate: 100%                    |
+---------------------------------------------+
|  Category            | Items  | Score        |
|  ORM Models          | 8/8    | 100%         |
|  Alembic Migration   | 1/1    | 100%         |
|  Service Layer       | 5/5    | 100%         |
|  Agent Tools         | 6/6    | 100%         |
|  Tool Registry       | 8/8    | 100%         |
|  Intent Router       | 7/7    | 100%         |
|  File Modifications  | 2/2    | 100%         |
|  Pydantic Schemas    | 11/11  | 100%         |
|  API Endpoints       | 25/24  | 100% (+1)   |
|  Frontend Hooks      | 4/4    | 100%         |
|  Frontend Components | 20/20  | 100%         |
|  Frontend Pages      | 5/5    | 100%         |
|  Dashboard Widgets   | 4/4    | 100%         |
|  Sidebar Nav         | 4/4    | 100%         |
|  Tests               | 6/6    | 100%         |
|                      |        |              |
|  TOTAL               |116/116 | 100%         |
+---------------------------------------------+
```

---

## 4. Added Features (Design X, Implementation O)

| Item | Location | Description | Impact |
|------|----------|-------------|--------|
| POST `/{id}/analyze` endpoint | `routers/claims.py:237` | Exposes `analyze_claim` tool as REST endpoint | Low (positive) |
| Additional Pydantic schemas | `schemas/*.py` | Response/Update schemas for CRUD completeness | Low (positive) |
| Weekend risk factor in WMA | `forecast_service.py:55-56` | Adds dow 5/6 risk warning | Low (positive) |
| `max(0, mid-margin)` guard | `forecast_service.py:59` | Prevents negative predicted_min | Low (positive) |
| Hook path: `lib/hooks/` | `food-ai-agent-web/lib/hooks/` | Follows existing project convention over design | None (naming only) |

---

## 5. Overall Scores

| Category | Score | Status |
|----------|:-----:|:------:|
| Design Match | 100% | PASS |
| Architecture Compliance | 100% | PASS |
| Convention Compliance | 100% | PASS |
| **Overall** | **100%** | **PASS** |

---

## 6. Safety Rules Verification

| Rule | Design Requirement | Implementation | Status |
|------|-------------------|----------------|:------:|
| SAFE-002 | Hygiene/allergen high/critical claim -> HACCP incident | `demand_tools.py:437-451` + test coverage | MATCH |
| SAFE-001 | Allergen claim -> immediate re-verification note | `analyze_claim` hypothesis L563-569 | MATCH |

---

## 7. Key Statistics

| Metric | Value |
|--------|-------|
| Design document | 1007 lines |
| New ORM models | 8 (across 4 files) |
| New DB tables | 8 (via Alembic 003) |
| New API endpoints | 25 (8 forecast + 5 waste + 4 cost + 8 claims) |
| New Agent tools | 6 (in demand_tools.py, 682 lines) |
| New intents | 6 (total now: 22) |
| New frontend components | 20 (4 forecast + 4 waste + 4 cost + 8 claims) |
| New frontend pages | 5 |
| New dashboard widgets | 4 |
| New hooks | 4 |
| New test files | 6 |
| Agent tools total | 23 (11 MVP1 + 6 MVP2 + 6 MVP3) |
| Total intents | 22 (11 MVP1 + 5 MVP2 + 6 MVP3) |

---

## 8. Recommended Actions

### 8.1 Immediate

None required. Match rate is 100%.

### 8.2 Documentation Updates

- [ ] Update design document Section 4.4 to include bonus `POST /{id}/analyze` endpoint
- [ ] Note hook path convention (`lib/hooks/` vs `hooks/`) in design for consistency

### 8.3 Future Improvements

- [ ] Add more test cases to `test_forecast_api.py` (edge cases: missing site, invalid dates)
- [ ] Add `test_waste_api.py` EWMA calculation verification
- [ ] Consider adding `test_analyze_claim.py` for RAG integration coverage
- [ ] Add E2E Playwright tests for forecast/waste/cost/claims pages

---

## 9. Post-Analysis Action

```
Match Rate = 100% (>= 90%)
-> "Design and implementation match perfectly."
-> Recommend: /pdca report mvp3-demand
```

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-02-24 | Initial gap analysis - 100% match | gap-detector |
