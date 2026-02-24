# Food AI Agent - MVP 1 Plan
- **Version**: 1.0.0
- **Date**: 2026-02-23
- **Phase**: PDCA Plan
- **Author**: CTO Lead (food-ai-cto-team)

---

## 1. Executive Summary

Food AI Agent는 위탁급식/단체급식 운영사를 위한 AI 에이전트 시스템이다. MVP 1은 **식단 생성-검증-문서화** 파이프라인에 집중하여, 영양사/메뉴팀(NUT), 조리/생산(KIT), 위생/HACCP(QLT) 역할의 핵심 업무를 AI로 지원한다.

### MVP 1 한 줄 목표
> 식단 편성부터 영양/알레르겐 검증, 표준레시피 검색, 작업지시서 생성, HACCP 점검표 관리까지를 대화형 AI Agent로 자동화한다.

---

## 2. Technology Stack

### 2.1 Frontend
| Layer | Technology | Rationale |
|---|---|---|
| Framework | **Next.js 14 (App Router)** | RSC/Streaming 지원, 파일 기반 라우팅, SEO |
| Language | TypeScript 5.x | 타입 안정성, DX |
| Styling | Tailwind CSS + shadcn/ui | 빠른 UI 구축, 일관된 디자인 시스템 |
| State | Zustand + React Query (TanStack) | 경량 전역 상태 + 서버 상태 캐싱 |
| Forms | React Hook Form + Zod | 유효성 검증, 타입 안전 폼 |

### 2.2 Backend
| Layer | Technology | Rationale |
|---|---|---|
| API Server | **Python FastAPI** | AI Agent 오케스트레이션, RAG 파이프라인, Tool Calling, 전체 API |
| DB | **PostgreSQL** + SQLAlchemy 2.0 (async) | 직접 연결, asyncpg 드라이버, ORM 매핑 |
| Migration | **Alembic** | 스키마 버전 관리, 마이그레이션 자동화 |
| Auth | **python-jose (JWT)** + OAuth2PasswordBearer | 자체 JWT 발급/검증, FastAPI Depends 패턴 |
| Vector DB | **pgvector** (PostgreSQL 확장) | 별도 벡터 DB 불필요, 단일 DB 운영 |
| Storage | 로컬 파일시스템 (초기) / MinIO (확장) | S3 호환, 단순 시작 후 확장 |
| AI Model | **Claude claude-sonnet-4-6 (Anthropic)** | 한국어 성능, Tool Use, 긴 컨텍스트 |
| Embedding | OpenAI text-embedding-3-small | 문서 벡터화 (1536 dim) |

### 2.3 Infrastructure
| Layer | Technology | Rationale |
|---|---|---|
| Hosting (FE) | Vercel | Next.js 최적 배포 |
| Hosting (API) | Railway / Fly.io | FastAPI 컨테이너 배포 |
| Hosting (DB) | Railway PostgreSQL / Supabase DB | 관리형 PostgreSQL + pgvector 지원 |
| CI/CD | GitHub Actions | 자동 빌드/배포 |
| Monitoring | Sentry + Vercel Analytics | 에러/성능 추적 |

---

## 3. MVP 1 Scope Definition

### 3.1 포함 기능 (In Scope)

#### A. 공통 기반 (COM)
| ID | Feature | Priority | Description |
|---|---|---|---|
| FR-COM-001 | 대화형 요청 처리 | P0 | 자연어 텍스트 입력 → 요약 + 액션 출력 |
| FR-COM-002 | 의도 분류 (Intent Router) | P0 | 메뉴/영양/레시피/위생 등 자동 분류 |
| FR-COM-003 | 근거/출처 표시 | P0 | RAG 문서/데이터 소스 표시 |
| FR-COM-005 | 감사 로그 | P1 | 주요 변경 이력 자동 기록 |

> FR-COM-004 (승인 워크플로우)는 MVP 1에서 **간소화 버전** (단일 승인자, 확정/반려)만 구현.

#### B. 식단/영양/알레르겐 (MENU)
| ID | Feature | Priority | Description |
|---|---|---|---|
| FR-MENU-001 | 주간 식단 자동 생성 | P0 | 현장/기간/식수/예산 입력 → 2안 이상 생성 |
| FR-MENU-002 | 영양 기준 검증 | P0 | 칼로리/단백질/나트륨 등 정책 기반 검증 |
| FR-MENU-003 | 알레르겐 자동 태깅 | P0 | 원재료→알레르겐 추출, 법정 표시 생성 |
| FR-MENU-004 | 다양성/편중 감지 | P1 | 튀김 빈도, 식재료 반복 경고 |
| FR-MENU-006 | 식단 버전 관리 | P1 | 초안/검토/확정 상태, 변경 이력 |

> FR-MENU-005 (고객사 룰 엔진)는 MVP 1에서 **기본 룰 3~5개** 지원 (JSON 기반 룰 정의).

#### C. 표준레시피/조리 (RECP)
| ID | Feature | Priority | Description |
|---|---|---|---|
| FR-RECP-001 | 표준레시피 RAG 검색 | P0 | 하이브리드 검색 (키워드 + 벡터) |
| FR-RECP-002 | 인분 스케일링 | P1 | 기준→목표 인분 환산, 염도 보정 가이드 |
| FR-RECP-003 | 작업지시서 생성 | P0 | 조리 순서/설비/마감시각 기반 자동 생성 |
| FR-RECP-005 | CCP 체크 항목 포함 | P0 | 공정 단계별 온도/시간 CCP 삽입 |

> FR-RECP-004 (조리 중 Q&A)는 MVP 1에서 **기본 FAQ 기반** 응답만 지원.

#### D. 위생/HACCP (HAC)
| ID | Feature | Priority | Description |
|---|---|---|---|
| FR-HAC-001 | 일일/주간 점검표 생성 | P0 | 현장/공정별 체크리스트 템플릿 |
| FR-HAC-002 | CCP 기록 입력 가이드 | P0 | 누락 방지 알림, 마감 전 체크 |
| FR-HAC-003 | 위해 이벤트 대응 플로우 | P1 | 격리/보고/기록 단계 안내 (기본) |
| FR-HAC-004 | 감사 리포트 출력 | P1 | 기간/현장 선택 → 이력 패키징 |

#### E. 대시보드 (RPT) - 기본
| ID | Feature | Priority | Description |
|---|---|---|---|
| FR-RPT-001 | 운영 대시보드 | P1 | 오늘/이번주 핵심 현황 (식단 상태, HACCP 누락, 알림) |

### 3.2 제외 기능 (Out of Scope for MVP 1)
- FR-FCST-* : 수요 예측/잔반 최적화 (MVP 3)
- FR-PUR-* : BOM/구매/발주 자동화 (MVP 2)
- FR-INV-* : 재고/입고/검수 (MVP 2)
- FR-CLM-* : 클레임 관리 (MVP 4)
- FR-RPT-002/003 : KPI 리포트, 제안서 생성 (MVP 2+)

---

## 4. Architecture Overview

Food AI Agent의 핵심은 **RAG + LLM 기반 AI Agent**이다. 사용자의 자연어 요청을 이해하고, 내부 Knowledge Base에서 근거를 검색하며, 도메인 도구를 호출하여 실행까지 완결하는 "운영 두뇌" 역할을 한다.

### 4.1 System Architecture (High-Level)

```
[User Browser]
    |
    v
[Next.js 14 App Router] ── SSR/RSC ──> [Vercel]
    |
    └── REST/SSE ──> [FastAPI (Full Backend)]
                        |
                  ┌─────┴──────────────────────────────────┐
                  │          Infrastructure Layer            │
                  │  Auth (JWT+RBAC) | REST API (CRUD)      │
                  └─────┬──────────────────────────────────┘
                        |
                  ┌─────┴──────────────────────────────────┐
                  │          AI Agent Core                   │
                  │                                         │
                  │  [Intent Router] ─ Claude (경량 분류)    │
                  │        ↓                                │
                  │  [Query Rewriter] ─ 검색 최적화 쿼리     │
                  │        ↓                                │
                  │  ┌──────────────────────────────┐      │
                  │  │      RAG Pipeline             │      │
                  │  │  BM25 + Vector → RRF → Top-K │      │
                  │  └──────────┬───────────────────┘      │
                  │             ↓                           │
                  │  ┌──────────────────────────────┐      │
                  │  │   Agentic Loop (ReAct)        │      │
                  │  │   Claude claude-sonnet-4-6             │      │
                  │  │   + Retrieved Context         │      │
                  │  │   + Tool Definitions (11)     │      │
                  │  │   Reason → Act → Observe →... │      │
                  │  └──────────┬───────────────────┘      │
                  │             ↓                           │
                  │  [Tool Execution] → [Service Layer]    │
                  │        ↓                                │
                  │  [Response + Citations + Risk]          │
                  └─────────────────────────────────────────┘
                        |
                  ┌─────┴──────────────────────────────────┐
                  │          Data Layer                      │
                  │  SQLAlchemy 2.0 (async)                 │
                  │  PostgreSQL + pgvector                   │
                  │  Knowledge Base (recipe_documents)       │
                  └─────────────────────────────────────────┘
```

### 4.2 AI Agent Pipeline (End-to-End)

```
[User Query]
     ↓
[Intent Router] ─── Claude (경량 분류 호출, ~200 tokens)
     ↓
[Query Rewriter] ─── 검색 최적화된 쿼리 생성 (선택적)
     ↓
┌────────────────────────────────────────┐
│           RAG Pipeline                 │
│  [Hybrid Search]                       │
│    ├── BM25 (키워드, PostgreSQL FTS)   │
│    └── Vector Search (pgvector cosine) │
│         ↓                              │
│  [RRF Fusion + Reranker]              │
│         ↓                              │
│  [Context Builder] → top-K chunks     │
└────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────┐
│         Agentic Loop (ReAct)           │
│  [Claude claude-sonnet-4-6]                     │
│    System Prompt (role + safety)       │
│    + Retrieved Context (RAG)           │
│    + Conversation History              │
│    + Tool Definitions (11 tools)       │
│         ↓                              │
│  Reason → Tool Call → Observe → ...   │
│  (최대 10 반복, 완성 조건 충족 시 종료)│
└────────────────────────────────────────┘
     ↓
[Response] = Answer + Citations + Risk/Assumptions
```

### 4.3 Knowledge Base (RAG Sources)

AI Agent가 참조하는 내부 지식 기반 구성:

| Type | Source Table | Update | Usage |
|---|---|---|---|
| 표준레시피 | `recipes` + `recipe_documents` | 실시간 | 레시피 검색, 작업지시서 생성 |
| SOP 문서 | `recipe_documents` (doc_type=sop) | 배치 업로드 | 조리 가이드, 트러블슈팅 |
| HACCP 가이드 | `recipe_documents` (doc_type=haccp_guide) | 배치 업로드 | 점검표 생성, 사고 대응 |
| 영양 정책 | `nutrition_policies` | 실시간 | 식단 검증 기준 |
| 알레르겐 규정 | `allergen_policies` | 실시간 | 알레르겐 태깅/표시 |
| 식재료 마스터 | `items` | 실시간 | 영양 계산, 알레르겐 추출 |
| 현장 룰 | `sites.rules` | 실시간 | 현장 특화 제약 조건 |

### 4.4 LLM Call Patterns

시스템 내 LLM(Claude claude-sonnet-4-6) 호출은 두 가지 패턴으로 구분:

| Pattern | Usage | Model Config | Token Budget |
|---|---|---|---|
| **경량 분류** (Classify) | Intent Router, Query Rewriter | max_tokens=200, temperature=0 | ~500 input + 200 output |
| **풀 도메인 처리** (Agentic) | 식단 생성, 검증, HACCP 등 | max_tokens=4096, temperature=0.3, tool_use | ~8K input + 4K output, 최대 10 iterations |

- 경량 호출: 빠르고 저렴, 구조화된 JSON 응답
- 풀 처리: 스트리밍(SSE), 도구 호출 포함, 출처/근거 필수

### 4.5 Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Agent Pattern | ReAct (Reason-Act-Observe) | 다단계 추론 + 도구 호출 + 자기 검증 |
| Agent Framework | Custom (FastAPI + Claude Tool Use) | 급식 도메인 특화 제어, 불필요한 추상화 회피 |
| RAG Strategy | Hybrid Search (BM25 + Vector + RRF) | 키워드 정확도 + 의미 검색 결합 |
| RAG Storage | pgvector (PostgreSQL 확장) | 별도 벡터 DB 불필요, 운영 단순화 |
| Streaming | SSE (Server-Sent Events) | AI 응답 실시간 스트리밍 |
| Auth | FastAPI JWT (python-jose) + RBAC Depends | 자체 JWT 발급/검증, 미들웨어 패턴 |
| ORM | SQLAlchemy 2.0 async + Alembic | 타입 안전 DB 접근, 마이그레이션 관리 |
| Multi-site | site_id 기반 서비스 레이어 필터링 | 모든 쿼리에 site_id WHERE clause 적용 |

---

## 4A. AI Agent Core Design Principles

### Principle 1: RAG-First
모든 도메인 응답은 내부 Knowledge Base를 최우선 근거로 사용한다. 표준레시피, SOP, HACCP 가이드, 영양 정책 등 사내 문서가 LLM의 일반 지식보다 항상 우선한다.

### Principle 2: Transparency (출처 필수)
모든 AI 응답에 참조한 문서/데이터의 출처를 명시한다. `[출처: {문서명} v{버전}]` 형식으로 인용하며, 근거가 없는 추론은 가정(assumption)으로 표기한다.

### Principle 3: Safety-in-Loop
Agentic Loop 내부에서 안전 검사를 수행한다:
- 알레르겐 미확인 항목 → "확인 필요" 태그 자동 삽입
- HACCP CCP 관련 → 규정 문서 참조 강제
- 식중독 의심 키워드 감지 → 즉시 incident response flow 트리거

### Principle 4: Human-in-the-Loop
AI는 "추천/초안"까지만 생성한다. 식단 확정, 발주 승인, 공식 기록 등은 반드시 사람(OPS/NUT)의 승인 단계를 거친다.

### Principle 5: Graceful Degradation
RAG 검색 결과가 없거나 신뢰도가 낮을 경우:
- "해당 문서를 찾을 수 없습니다. 확인이 필요합니다." 안내
- 일반 지식 기반 응답 시 반드시 "내부 문서 미확인" 경고 표시
- 절대 확인 불가 정보를 확정적으로 제시하지 않음

---

## 5. User Roles & Permissions (MVP 1)

| Role | Code | MVP 1 Access |
|---|---|---|
| 영양사/메뉴팀 | NUT | 식단 생성/수정, 영양검증, 알레르겐 태깅, 레시피 검색, 작업지시서 생성 |
| 조리/생산 | KIT | 작업지시서 조회, 레시피 검색, 조리 Q&A (기본), CCP 기록 |
| 위생/HACCP | QLT | 점검표 생성/조회, CCP 기록 입력, 이벤트 대응, 감사 리포트 |
| 운영/관리 | OPS | 대시보드, 식단 승인/확정, 전체 조회 |
| 시스템 관리자 | ADM | 전체 설정, 마스터 데이터 관리, 사용자/권한 관리 |

> PUR, CS 역할은 MVP 2, MVP 4에서 활성화.

---

## 6. MVP 1 Screen Map

### 6.1 구현 화면 (6개)

| # | Screen | Route | Primary Role | Key Features |
|---|---|---|---|---|
| 1 | 운영 대시보드 | `/dashboard` | OPS | 오늘의 식단 상태, HACCP 체크 현황, 알림 |
| 2 | 식단 설계실 | `/menu-studio` | NUT | AI 식단 생성, 영양/알레르겐 검증, 확정 |
| 3 | 레시피 라이브러리 | `/recipes` | NUT, KIT | RAG 검색, 레시피 상세, 스케일링 |
| 4 | 생산/조리 모드 | `/kitchen` | KIT | 작업지시서, CCP 체크, 조리 Q&A |
| 5 | 위생/HACCP | `/haccp` | QLT | 점검표, CCP 기록, 감사 리포트 |
| 6 | 설정/마스터 | `/settings` | ADM | 현장/품목/정책/사용자 관리 |

### 6.2 공통 컴포넌트
- **AI Chat Panel**: 화면 우측 또는 하단에 상시 노출, 컨텍스트 인식 대화
- **Notification Center**: 헤더 알림 (HACCP 누락, 식단 승인 요청 등)
- **Site Selector**: 현장 전환 (다현장 운영)

---

## 7. Data Entities (MVP 1)

### 7.1 Master Data
| Entity | Key Fields | Notes |
|---|---|---|
| Site | id, name, type, capacity, operating_hours, rules_json | 현장 정보 |
| Item | id, name, category, spec, unit, allergens[], storage_condition | 식재료 마스터 |
| NutritionPolicy | id, site_id, meal_type, criteria_json | 영양 기준 정책 |
| AllergenPolicy | id, site_id, legal_allergens[], custom_allergens[] | 알레르겐 표시 정책 |
| User | id, name, email, hashed_password, role, site_ids[] | 자체 JWT 인증 |

### 7.2 Operational Data
| Entity | Key Fields | Notes |
|---|---|---|
| MenuPlan | id, site_id, period, status(draft/review/confirmed), version, meals[] | 식단 |
| MenuPlanItem | id, menu_plan_id, date, meal_type, course, item_name, recipe_id | 식단 상세 |
| Recipe | id, name, version, category, servings_base, ingredients[], steps[], ccp[] | 표준레시피 |
| RecipeDocument | id, recipe_id, content, embedding_vector | RAG용 문서 |
| WorkOrder | id, menu_plan_id, site_id, date, meal_type, recipe_id, scaled_servings, steps[] | 작업지시서 |
| HACCPChecklist | id, site_id, date, type(daily/weekly), items[], status, completed_by | 점검표 |
| HACCPRecord | id, checklist_id, ccp_point, value, photo_url, recorded_by, recorded_at | CCP 기록 |
| AuditLog | id, user_id, action, entity_type, entity_id, changes_json, reason, created_at | 감사 로그 |
| Conversation | id, user_id, site_id, messages[], context_type | AI 대화 이력 |

---

## 8. AI Agent Features Detail

### 8.1 Intent Router
```
Input: user message + context (current screen, site, role)
Output: { intent, confidence, sub_intent, entities }

Intents:
- menu_generate: 식단 생성 요청
- menu_validate: 영양/알레르겐 검증
- recipe_search: 레시피 검색
- recipe_scale: 인분 스케일링
- work_order: 작업지시서 생성
- haccp_checklist: 점검표 생성/조회
- haccp_record: CCP 기록
- report: 리포트/현황 조회
- general: 일반 질문/안내
```

### 8.2 Tool Definitions (MVP 1)
| Tool | Input | Output | Used By |
|---|---|---|---|
| `generate_menu_plan` | site, period, meals, budget, rules | MenuPlan (2+ alternatives) | Menu Agent |
| `validate_nutrition` | menu_plan_id | Validation report (pass/fail per criteria) | Menu Agent |
| `tag_allergens` | menu_plan_id or recipe_id | Allergen list + display text | Menu Agent |
| `check_diversity` | menu_plan_id, period | Diversity warnings | Menu Agent |
| `search_recipes` | query, filters | Recipe results with scores | Recipe Agent |
| `scale_recipe` | recipe_id, target_servings | Scaled ingredients + seasoning guide | Recipe Agent |
| `generate_work_order` | menu_plan_id, site_id, date | WorkOrder document | Recipe Agent |
| `generate_haccp_checklist` | site_id, date, meal_type | Checklist template | HACCP Agent |
| `check_haccp_completion` | site_id, date | Completion status + missing items | HACCP Agent |
| `generate_audit_report` | site_id, date_range | Audit report (HACCP + records) | HACCP Agent |

### 8.3 Safety Guardrails
- **알레르겐 미확인**: 해당 항목에 "확인 필요" 태그 + 경고 메시지
- **식중독 의심 키워드**: 즉시 대응 플로우 트리거 (격리/보고/기록)
- **대량조리 스케일링**: 조미료/염도 보정 경고 자동 포함
- **확정 권한 검증**: 승인 권한 없는 사용자의 확정 시도 차단
- **근거 필수**: 모든 AI 응답에 출처/가정/리스크 표시

---

## 9. MVP 1 Success Criteria (KPI)

### 9.1 Product KPIs
| KPI | Target | Measurement |
|---|---|---|
| 식단 생성 시간 단축 | 기존 대비 60% 이상 | 생성 요청→확정까지 소요 시간 |
| 영양 기준 적합률 | 95% 이상 (AI 생성 식단) | 자동 검증 통과율 |
| 알레르겐 태깅 정확도 | 99% 이상 | 수동 검증 대비 일치율 |
| HACCP 점검 누락률 | 5% 이하 | 마감 시간 기준 미완료 비율 |
| 레시피 검색 만족도 | 4.0/5.0 이상 | 사용자 피드백 (검색 결과 적합성) |

### 9.2 Technical KPIs
| KPI | Target | Measurement |
|---|---|---|
| 대시보드 응답 시간 | 3초 이내 | P95 latency |
| AI 응답 시간 (스트리밍 첫 토큰) | 2초 이내 | TTFB |
| 시스템 가용성 | 99.5% (운영 시간대) | Uptime monitoring |
| RAG 검색 정확도 (Top-5) | 80% 이상 | Relevance scoring |

### 9.3 Business KPIs
| KPI | Target | Measurement |
|---|---|---|
| 파일럿 현장 수 | 3개 이상 | 실제 운영 현장 적용 |
| MAU (Monthly Active Users) | 파일럿 현장 영양사/조리사 80% 이상 | 로그인 및 기능 사용 |
| NPS (Net Promoter Score) | 30 이상 | 사용자 설문 |

---

## 10. Team Structure & Responsibilities

| Role | Agent/Person | Responsibilities |
|---|---|---|
| CTO Lead | food-ai-cto (this agent) | Architecture, tech decisions, design docs |
| Product Manager | product-manager | Requirements, prioritization, user stories |
| Frontend Architect | frontend-architect | Next.js UI, components, UX flow |
| Backend Expert | bkend-expert | PostgreSQL schema, FastAPI, RAG pipeline |

---

## 11. Development Phases (MVP 1)

### Phase 1: Foundation (Week 1-2)
- PostgreSQL 설정 (pgvector 확장 활성화)
- SQLAlchemy 2.0 ORM 모델 정의 + Alembic 마이그레이션
- FastAPI 프로젝트 초기화 (JWT Auth, RBAC, 프로젝트 구조, Claude API 연동)
- Next.js 프로젝트 초기화 (App Router, 디자인 시스템)

### Phase 2: Core AI (Week 3-4)
- Intent Router 구현
- Agent Orchestrator + Tool Registry
- RAG Pipeline (문서 로더, 청커, 임베더, 검색)
- Tool 구현: generate_menu_plan, validate_nutrition, tag_allergens

### Phase 3: Menu & Recipe (Week 5-6)
- 식단 설계실 UI (생성/검증/확정 flow)
- 레시피 라이브러리 UI (RAG 검색, 상세, 스케일링)
- 작업지시서 생성 (WorkOrder)
- 식단 버전 관리

### Phase 4: HACCP & Dashboard (Week 7-8)
- 위생/HACCP UI (점검표, CCP 기록, 감사 리포트)
- 운영 대시보드 UI
- 알림 시스템 (HACCP 누락, 식단 승인 요청)
- AI Chat Panel (컨텍스트 인식)

### Phase 5: Integration & QA (Week 9-10)
- 마스터 데이터 관리 UI (설정)
- E2E 테스트, 보안 점검
- 파일럿 현장 데이터 마이그레이션
- 사용자 교육/문서

---

## 12. Risk & Mitigation

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| AI 환각 (잘못된 영양/알레르겐 정보) | High | Medium | Safety guardrails, 출처 필수, 사용자 확인 단계 |
| RAG 검색 정확도 부족 | Medium | Medium | 하이브리드 검색, 리랭킹, 사용자 피드백 루프 |
| DB 인프라 운영 부담 | Medium | Low | 관리형 PostgreSQL (Railway/Supabase) 활용 |
| 현장 데이터 부재/품질 | High | High | MVP 1에서 샘플 데이터 + 수동 입력 지원 |
| Claude API 비용 | Medium | Medium | 캐싱, 간단 쿼리 분기, 토큰 모니터링 |

---

## 13. Open Decisions (Design Phase에서 결정)

1. 식단 생성 프롬프트 템플릿 구조
2. 알레르겐 분류 체계 (법정 21종 + 커스텀)
3. 파일 업로드/문서 관리 방식 (로컬 → MinIO 전환 시점)
4. 실시간 알림 채널 (WebSocket vs SSE vs Polling)
5. PostgreSQL 호스팅 최종 선택 (Railway vs Supabase DB)

---

## 14. References

- [food_ai-agent_req.md](../../food_ai-agent_req.md) - 전체 기능명세서
- [CLAUDE.md](../../CLAUDE.md) - 프로젝트 가이드
- Anthropic Claude API Documentation (Tool Use)
- Next.js 14 App Router Documentation
- SQLAlchemy 2.0 Async Documentation
- pgvector Documentation
