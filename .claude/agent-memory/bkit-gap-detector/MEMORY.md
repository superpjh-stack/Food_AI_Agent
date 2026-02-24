# Gap Detector Memory - Food AI Agent

## Project Overview
- **Type**: Food service management AI agent (Korean catering/institutional meals)
- **Stack**: FastAPI (Python) + Next.js 14 (TypeScript) + PostgreSQL/pgvector
- **AI**: Claude Sonnet + OpenAI embeddings, ReAct pattern, 23 domain tools

## Key Paths
- Design: `docs/02-design/features/food-ai-agent.design.md`
- Plan: `docs/01-plan/features/food-ai-agent.plan.md`
- Backend: `food-ai-agent-api/app/`
- Frontend: `food-ai-agent-web/`
- Analysis: `docs/03-analysis/food-ai-agent.analysis.md`

## Last Analysis (2026-02-23)
- Overall Match Rate: 88.5%
- DB Schema: 100% (16/16 tables)
- API: 91% (40 full + 14 stubs out of 54)
- RAG Pipeline: 100%
- ReAct Agent: 96% (10/11 tools - missing `generate_work_order` in registry)
- UI: 85% (missing Settings pages, site-selector)
- HACCP: 100%
- Auth/RBAC: 95%
- Tests: 75% (4 files, many areas untested)
- Infra: 100%

## Key Gaps (MVP 1)
1. Settings pages (5) not created - Phase 5 items
2. Master Data CRUD (14 endpoints) are stubs
3. `generate_work_order` not in agent tool registry
4. `site-selector.tsx` component missing
5. Service layer files empty (logic in routers)
6. Test coverage limited to auth, menu_plans, haccp, chat

## MVP 2 Purchase Analysis (2026-02-23, Act-1 Complete)
- Design: `docs/02-design/features/mvp2-purchase.design.md` (804 lines, complete)
- Analysis: `docs/03-analysis/mvp2-purchase.analysis.md`
- Overall Match Rate: **100%** (Act-1 post-implementation)
- 120 trackable items: 10 DB, 34 API, 6 tools, 5 intents, 3 registry, 5 pages, 14 components, 4 hooks, 2 schemas, 7 seed/tests, 5 supporting, 2 sidebar, 4 routers, 8 ORM imports, 11 types
- All items implemented: ORM models, routers, tools, intents, registry, prompts, schemas, frontend pages/components/hooks/types, seed, 55 tests, alembic migration
- Safety rules SAFE-PUR-001 through 004 all verified
- AI tools now: 17 (11 MVP1 + 6 MVP2), intents: 16 (11 + 5)
- Ready for: `/pdca report mvp2-purchase`

## MVP 3 Demand/Cost/Claim Analysis (2026-02-24)
- Design: `docs/02-design/features/mvp3-demand.design.md` (1007 lines)
- Analysis: `docs/03-analysis/mvp3-demand.analysis.md`
- Overall Match Rate: **100%** (116/116 items)
- 116 trackable items: 8 ORM, 1 migration, 5 service, 6 tools, 8 registry, 7 intents, 2 file mods, 11 schemas, 25 API, 4 hooks, 20 components, 5 pages, 4 widgets, 4 sidebar, 6 tests
- All implemented: 8 new DB tables, 25 API endpoints, 6 agent tools, 6 intents, 20 components, 5 pages
- Safety rules: SAFE-002 (HACCP auto-trigger) verified with test coverage
- AI tools now: 23 (11 MVP1 + 6 MVP2 + 6 MVP3), intents: 22 (11 + 5 + 6)
- Hooks at `lib/hooks/` (project convention, not `hooks/` root)
- Bonus: extra `POST /{id}/analyze` REST endpoint not in design
- Ready for: `/pdca report mvp3-demand`
