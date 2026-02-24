# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Food AI Agent** — 위탁급식/단체급식 운영사(다현장)를 위한 AI 에이전트 시스템.
메뉴(영양/알레르겐)–구매(단가/발주)–생산(레시피/공정)–배식(수요/잔반)–위생(HACCP)–클레임 전 과정을 대화형 AI로 연결.

- 요구사항: `food_ai-agent_req.md`
- Plan: `docs/01-plan/features/food-ai-agent.plan.md`
- Design: `docs/02-design/features/food-ai-agent.design.md`
- PDCA 현재 단계: **Do (MVP 1 구현 준비)**

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 App Router + TypeScript + Tailwind CSS + shadcn/ui |
| State | Zustand (UI) + TanStack Query (서버 상태) |
| Forms | React Hook Form + Zod |
| Backend | Python FastAPI (전체 API + AI Gateway + SSE 스트리밍) |
| AI Model | Claude claude-sonnet-4-6 (`claude-sonnet-4-6`) |
| DB | PostgreSQL + pgvector (SQLAlchemy 2.0 async + Alembic) |
| Auth | FastAPI JWT (python-jose + bcrypt + OAuth2PasswordBearer) |
| Storage | Cloud Storage (GCS, S3 호환) |
| Hosting | Vercel (FE) + Cloud Run (API) + Cloud SQL PostgreSQL 16 (DB) |
| Infra | Google Cloud Platform (asia-northeast3, Seoul) |
| Secrets | Secret Manager (API 키, DB URL, JWT) |
| Registry | Artifact Registry (Docker 이미지) |
| CI/CD | GitHub Actions + Workload Identity Federation |

## Project Structure

```
food-ai-agent-web/      # Next.js 14 Frontend
food-ai-agent-api/      # Python FastAPI AI Gateway
docs/
  01-plan/features/food-ai-agent.plan.md
  02-design/features/food-ai-agent.design.md
food_ai-agent_req.md    # 전체 기능명세서
```

### Frontend Routes (App Router)
- `/dashboard` — 운영 대시보드
- `/menu-studio` — 식단 설계실 (AI 생성/검증/확정)
- `/recipes` — 레시피 라이브러리 (RAG 검색)
- `/kitchen` — 생산/조리 모드 (작업지시서/CCP)
- `/haccp` — 위생/HACCP (점검표/기록/감사)
- `/settings` — 설정/마스터/권한

### Backend Modules (FastAPI)
- `agents/orchestrator.py` — Agent 오케스트레이션
- `agents/intent_router.py` — 의도 분류 (11 intents)
- `agents/tools/` — Tool 구현체 (menu/recipe/haccp/dashboard)
- `agents/prompts/` — 도메인별 System Prompt
- `rag/` — 문서 로더→청커→임베더→하이브리드 검색
- `services/` — 비즈니스 로직 (menu/recipe/haccp/nutrition/allergen)
- `auth/` — JWT (python-jose) + OAuth2 + password hashing
- `db/` — AsyncEngine, session, SQLAlchemy Base
- `models/orm/` — SQLAlchemy ORM 모델
- `models/schemas/` — Pydantic request/response 스키마
- `middleware/` — RBAC + Audit Log

## User Roles (RBAC)

| 약어 | 역할 | 주요 권한 |
|---|---|---|
| NUT | 영양사/메뉴팀 | 식단 CRUD, 레시피 조회/생성, 작업지시서 생성 |
| KIT | 조리/생산 | 작업지시서 조회, 레시피 조회, CCP 기록 |
| QLT | 위생/HACCP | 점검표 CRUD, CCP 기록, 사고 관리, 감사 리포트 |
| OPS | 운영/관리 | 대시보드, 식단 승인/확정, 정책 수정, 전체 조회 |
| ADM | 시스템 관리자 | 마스터 CRUD, 사용자/권한 관리, 전체 설정 |

**권한 원칙**: 추천/초안은 넓게, 확정/발주/공식 기록은 승인 워크플로우 필수

## Key Architecture Decisions

| 결정 | 선택 | 이유 |
|---|---|---|
| Agent Framework | Custom FastAPI + Claude Tool Use | 급식 도메인 특화, 불필요한 추상화 회피 |
| Vector DB | pgvector (PostgreSQL 확장 직접) | 별도 벡터 DB 불필요, 단일 DB 운영 |
| Streaming | SSE (Server-Sent Events) | 단방향 충분, HTTP 호환 |
| Auth | FastAPI JWT (python-jose) + RBAC Depends | 자체 JWT 발급/검증, 미들웨어 패턴 |
| ORM | SQLAlchemy 2.0 async + Alembic | 타입 안전 DB 접근, 마이그레이션 관리 |
| Multi-site 격리 | 서비스 레이어 site_id 필터링 | 모든 쿼리에 site_id WHERE clause 적용 |
| Embedding | OpenAI text-embedding-3-small (1536 dim) | 비용 효율, 한국어 성능 |
| Frontend State | Zustand + TanStack Query 분리 | 경량 UI 상태 + 서버 상태 캐싱 분리 |
| Cloud Deploy | Cloud Run (서버리스 컨테이너) | Scale-to-zero, SSE 300s timeout, VPC 격리 |
| DB Cloud | Cloud SQL PG16 + pgvector | Private IP, 자동 백업, pgvector 네이티브 지원 |

## Core Database Tables (PostgreSQL + SQLAlchemy 2.0)

**마스터**: `sites`, `items`, `nutrition_policies`, `allergen_policies`, `users`

**운영**: `menu_plans`, `menu_plan_items`, `menu_plan_validations`, `recipes`, `recipe_documents` (pgvector), `work_orders`, `haccp_checklists`, `haccp_records`, `haccp_incidents`, `audit_logs`, `conversations`

## AI Agent Architecture (RAG + LLM Core)

```
User Message
  → Intent Router (Claude 경량 분류, ~200 tokens)
  → Query Rewriter (검색 최적화 쿼리, 선택적)
  → RAG Pipeline
      ├── BM25 keyword search (PostgreSQL FTS)
      ├── Vector search (pgvector cosine, top-20)
      └── RRF Fusion → Reranker → top-5 context
  → Agentic Loop (ReAct Pattern)
      ├── Claude claude-sonnet-4-6 (streaming, tool_use)
      ├── System Prompt (role + safety + RAG context)
      ├── Tool Definitions (11 tools)
      └── Reason → Act → Observe → ... (max 10 iterations)
              ↓
      Response + Citations + Risk/Assumptions
```

**Knowledge Base**: 표준레시피, SOP 문서, HACCP 가이드 (pgvector 임베딩) + 영양 정책, 알레르겐 규정, 식재료 마스터 (SQL 직접)

**LLM Call Patterns**:
- 경량 분류 (Intent/Query Rewrite): max_tokens=200, temperature=0
- 풀 도메인 처리 (Agentic Loop): max_tokens=4096, temperature=0.3, tool_use, streaming

**11 Tools**: `generate_menu_plan`, `validate_nutrition`, `tag_allergens`, `check_diversity`, `search_recipes`, `scale_recipe`, `generate_work_order`, `generate_haccp_checklist`, `check_haccp_completion`, `generate_audit_report`, `query_dashboard`

**AI Agent Design Principles**:
1. **RAG-First**: 내부 Knowledge Base 최우선 근거
2. **Transparency**: 모든 응답에 [출처: doc v{version}] 인용 필수
3. **Safety-in-Loop**: Agentic Loop 내 알레르겐/HACCP 안전 검사
4. **Human-in-the-Loop**: 확정/발주는 반드시 사람 승인
5. **Graceful Degradation**: RAG 결과 없으면 "내부 문서 미확인" 경고

## Safety Constraints (코드에 항상 적용)

- 알레르겐 미확인 → `"확인 필요"` 태그 필수 (SAFE-001)
- 식중독 의심 키워드 → 즉시 incident response flow 트리거 (SAFE-002)
- 대량조리 스케일링 → 조미료/염도 보정 경고 필수 (SAFE-003)
- 확정/승인 없이 menu_plans.status = 'confirmed' 금지 (SAFE-004)
- AI 응답에 항상 출처/가정/리스크 포함 (NFR-007)
- 모든 확정/수정/삭제 → `audit_logs` 기록 필수 (NFR-006)

## Development Commands

```bash
# Backend (FastAPI) — food-ai-agent-api/
pip install -r requirements.txt
cp .env.example .env                              # 환경변수 설정
uvicorn app.main:app --reload --port 8000         # 개발 서버
alembic upgrade head                              # DB 마이그레이션 실행
alembic revision --autogenerate -m "description" # 새 마이그레이션 생성
pytest                                            # 전체 테스트
pytest tests/test_agents/                        # 에이전트 테스트만

# Frontend (Next.js) — food-ai-agent-web/
npm install
npm run dev     # http://localhost:3000 (API → localhost:8000 프록시)
npm run build
npm run lint
```

## Environment Variables (.env.example 참고)

```
# Application
APP_ENV=production
DEBUG=false

# Database (로컬 개발)
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/food_ai_agent

# Database (Cloud SQL — Cloud Run 배포시)
# Unix socket: postgresql+asyncpg://user:pass@/food_ai_agent?host=/cloudsql/PROJECT:REGION:INSTANCE
# Private IP:  postgresql+asyncpg://user:pass@10.x.x.x:5432/food_ai_agent

# JWT
JWT_SECRET_KEY=...   # Secret Manager에서 주입
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=["https://foodai.example.com"]

# AI (Secret Manager에서 주입)
ANTHROPIC_API_KEY=...
CLAUDE_MODEL=claude-sonnet-4-6
OPENAI_API_KEY=...   # 임베딩용 (text-embedding-3-small)
```

## Google Cloud 배포 아키텍처

```
Internet
  → Vercel (Next.js FE, CDN 글로벌)
  → Cloud Run (FastAPI API, asia-northeast3)
      ↕ VPC Connector
  → Cloud SQL PostgreSQL 16 (Private IP, pgvector 내장)
  → Cloud Storage (HACCP 사진, 문서)
  → Secret Manager (DATABASE_URL, JWT_SECRET_KEY, API Keys)
  → Artifact Registry (Docker 이미지)
```

**배포 명령어 (gcloud CLI)**
```bash
# Cloud Run 배포
gcloud run deploy food-ai-agent-api \
  --image=asia-northeast3-docker.pkg.dev/PROJECT/food-ai/api:latest \
  --region=asia-northeast3 \
  --set-secrets="DATABASE_URL=database-url:latest" \
  --add-cloudsql-instances=PROJECT:asia-northeast3:food-ai-agent-db \
  --vpc-connector=food-ai-connector \
  --timeout=300 --cpu=2 --memory=2Gi

# CI/CD: .github/workflows/deploy-api.yml 자동화됨
```

## MVP 1 Scope

Phase 1 (Foundation), Phase 2 (Core AI), Phase 3 (Menu & Recipe), Phase 4 (HACCP & Dashboard), Phase 5 (Integration & QA) — 총 10주 계획.

**MVP 1 KPI**: 식단 생성 60% 시간 단축, 알레르겐 정확도 99%, HACCP 누락률 5% 이하, RAG 검색 Top-5 정확도 80%.
