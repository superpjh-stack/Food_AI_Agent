# PDCA Iterator Agent Memory - Food AI Agent Project

## Project Structure

- Backend: `food-ai-agent-api/` (FastAPI + SQLAlchemy AsyncSession + PostgreSQL/pgvector)
- Frontend: `food-ai-agent-web/` (Next.js 14, TypeScript, Zustand, Tailwind)
- Tests: `food-ai-agent-api/tests/` (pytest-asyncio, httpx AsyncClient)
- Design docs: `docs/02-design/features/food-ai-agent.design.md`
- Analysis: `docs/03-analysis/food-ai-agent.analysis.md`

## Auth/RBAC Patterns

- `require_role("ADM")` — returns `Depends(role_checker)`, use as default value (not `Depends(require_role(...))`)
- `Depends(get_current_user)` — for read-only endpoints open to all authenticated users
- DB session: `db: AsyncSession = Depends(get_db)`

## Gap Completion Record (2026-02-23)

### Gap 1 — Master Data CRUD (14 stubs -> real implementation)
Implemented full SQLAlchemy AsyncSession CRUD for:
- `routers/sites.py` — GET list, GET/:id, POST, PATCH, DELETE (soft)
- `routers/items.py` — GET list (+category filter+search), GET/:id, POST, PATCH, DELETE (soft)
- `routers/policies.py` — nutrition (GET list, GET/:id, POST, PATCH) + allergen (GET list, GET/:id, POST, PATCH)
- `routers/users.py` — GET list, GET/:id, POST, PATCH role, PATCH active, PATCH general

All use Pydantic v2 `model_dump(exclude_unset=True)` pattern for partial updates.

### Gap 2 — generate_work_order tool
- Added `WORK_ORDER_TOOLS` list to `app/agents/tools/registry.py`
- Updated `AGENT_TOOLS`: menu + recipe agents now include work_order tool
- Created `app/agents/tools/work_order_tools.py` with `generate_work_order()` function
- Patched `app/agents/orchestrator.py`: import + dispatch entry + site_id injection

### Gap 3 — site-selector.tsx
- Created `food-ai-agent-web/components/layout/site-selector.tsx`
  - Fetches `/sites` on mount, populates Zustand site-store
  - Custom dropdown (no shadcn dependency) with aria roles
- Updated `food-ai-agent-web/components/layout/header.tsx` to use SiteSelector

### Gap 4 — Test files
- `tests/test_recipes.py` — 8 tests (list, create, get, not_found, search, scale, update, RBAC)
- `tests/test_work_orders.py` — 6 tests (generate, list, detail, status flow, today filter, RBAC)
- Pattern: helper `_create_recipe()` / `_setup_confirmed_plan()` for setup
- `pytest.skip()` used when menu plan has no recipe items (non-blocking)

### Gap 5 — Settings pages (optional)
- `app/(main)/settings/page.tsx` — tab nav landing page
- `app/(main)/settings/sites/page.tsx` — sites table + SiteSelector
- `app/(main)/settings/items/page.tsx` — items table with category filter + pagination
- `app/(main)/settings/users/page.tsx` — users table with role filter (ADM only)
- `app/(main)/settings/policies/page.tsx` — nutrition/allergen tab view

## MVP3 Completion Record (2026-02-24)

### MVP3 — Demand Forecast / Waste / Cost / Claims (100% match rate)

**New ORM Models**: `forecast.py` (DemandForecast, ActualHeadcount, SiteEvent), `waste.py` (WasteRecord, MenuPreference), `cost.py` (CostAnalysis), `claim.py` (Claim, ClaimAction)

**Migration**: `alembic/versions/003_mvp3_demand_cost_claim.py` — 8 tables

**Service**: `app/services/forecast_service.py` — WMA algorithm with DOW_COEFFICIENTS + WMA_WEIGHTS

**Agent Tool**: `app/agents/tools/demand_tools.py` — 6 functions (forecast_headcount, record_waste, simulate_cost, register_claim, analyze_claim, track_claim_action)

**SAFE-002 Pattern**: In `register_claim()`, when category in ["위생/HACCP", "알레르겐"] AND severity in ["high", "critical"], auto-create `HaccpIncident` with `reported_by=created_by or SYSTEM_USER_ID` (reported_by is NOT NULL)

**Bug fixed**: HaccpIncident.reported_by is NOT NULL — always provide it when auto-creating incidents

**API Routers**: forecast.py, waste.py, cost.py, claims.py — all registered in main.py

**Claims routing**: GET /reports/quality MUST be placed BEFORE GET /{id} to avoid FastAPI routing conflict

**Frontend**: 4 hooks (use-forecast, use-waste, use-cost-analysis, use-claims), 20 components across forecast/waste/cost/claims, 4 dashboard widgets, 5 pages (forecast, waste, cost-optimizer, claims, claims/[id])

**Tests**: 24 tests across 4 directories (test_forecast, test_waste, test_cost, test_claims) + conftest.py updated with OPS_ID, CS_ID, PUR_ID + ops_headers, cs_headers, pur_headers fixtures

**Project uses lib/http.ts, NOT lib/api.ts** — hooks call http() directly, no separate api.ts needed

## Key Conventions

- Backend response format: `{"success": bool, "data": ..., "meta": {...}}`
- Error format: `{"success": false, "error": {"code": "...", "message": "..."}}`
- `http()` in frontend strips wrapper and returns `json.data` — handle both array and object shapes
- ORM flush pattern: `db.add(obj); await db.flush()` (no explicit commit in routers — session commit happens in `get_db` dependency)
- Soft delete: set `is_active = False`, not hard delete (except explicit admin delete)
