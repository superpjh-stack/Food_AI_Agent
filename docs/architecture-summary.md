# Food AI Agent — 종합 아키텍처 요약

> 생성일: 2026-02-25 | CTO Lead 분석

---

## 1. 프로젝트 개요

**Food AI Agent**는 위탁급식/단체급식 운영사(다현장)를 위한 AI 에이전트 시스템이다.
메뉴(영양/알레르겐) - 구매(단가/발주) - 생산(레시피/공정) - 배식(수요/잔반) - 위생(HACCP) - 클레임 전 과정을 대화형 AI로 연결한다.

- **MVP 1** (완료): 식단/레시피/HACCP AI 자동화 (96% match)
- **MVP 2** (완료): 구매/발주/BOM 자동화 (100% match)
- **MVP 3** (완료): 수요예측/원가최적화/클레임 관리 (100% match)
- **MVP 4** (계획): 클레임 고도화 / CS 관리 / 벤더 품질
- 총 구현: **~188+ 파일**, 52개 통합 테스트, 16개+ DB 테이블

---

## 2. 시스템 전체 구조도

```
                         Internet
                            |
              +-------------+-------------+
              |                           |
        Vercel (CDN)              Cloud Run (asia-northeast3)
     Next.js 14 FE               FastAPI API + AI Gateway
     (App Router, TS)             (Python 3.11, SSE Streaming)
              |                           |
              +---- HTTPS REST/SSE -------+
                                          |
                              +-----------+-----------+
                              |                       |
                       VPC Connector          Secret Manager
                       (10.8.0.0/28)          (4 secrets)
                              |
                    Cloud SQL PG16
                    (Private IP, pgvector)
                    16+ tables, embeddings
                              |
                    Cloud Storage (GCS)
                    (HACCP photos, docs)
```

---

## 3. 기술 스택 레이어별 상세

| Layer | Technology | Details |
|---|---|---|
| **Frontend** | Next.js 14 App Router + TypeScript + Tailwind CSS + shadcn/ui | 13개 라우트 그룹, 14개 컴포넌트 디렉토리 |
| **State Management** | Zustand (UI) + TanStack Query (서버) | 경량 클라이언트 + 서버 상태 캐싱 분리 |
| **Backend** | Python FastAPI + uvicorn | 22개 라우터, SSE 스트리밍, /health 엔드포인트 |
| **ORM** | SQLAlchemy 2.0 async + Alembic | 타입 안전 async DB, 마이그레이션 관리 |
| **AI Model** | Claude claude-sonnet-4-6 (Anthropic) | Tool Use, max_tokens=4096, temp=0.3 |
| **Embedding** | OpenAI text-embedding-3-small (1536 dim) | 한국어 성능, 비용 효율 |
| **DB** | PostgreSQL 16 + pgvector | 단일 DB, 벡터 + 관계형 통합 |
| **Auth** | JWT (python-jose) + bcrypt + OAuth2PasswordBearer | 5-Role RBAC |
| **Cloud** | GCP asia-northeast3 (Seoul) | Cloud Run + Cloud SQL + Secret Manager |
| **CI/CD** | GitHub Actions + Workload Identity Federation | 무키 인증, Staging→Prod 파이프라인 |

---

## 4. AI Agent 아키텍처 (RAG + ReAct + Tools)

**핵심 파일**: `food-ai-agent-api/app/agents/`

```
User Message
  -> IntentRouter (intent_router.py)
       Claude 경량 분류 (~200 tokens, temp=0)
       11 intents -> agent type 매핑
  -> Query Rewriter (검색 최적화)
  -> RAG Pipeline (rag/pipeline.py)
       ├── loader.py    (문서 로딩)
       ├── chunker.py   (청킹)
       ├── embedder.py  (벡터 임베딩)
       ├── retriever.py (하이브리드 검색)
       │    ├── BM25 keyword (PostgreSQL FTS)
       │    ├── Vector cosine (pgvector, top-20)
       │    └── RRF Fusion -> Reranker -> top-5
       └── pipeline.py  (오케스트레이션)
  -> AgentOrchestrator (orchestrator.py)
       ReAct Agentic Loop (max 10 iterations)
       Claude claude-sonnet-4-6 (streaming, tool_use)
       Reason -> Act -> Observe -> ...
```

**Agent Tool 구현체** (`agents/tools/`):

| Tool File | Tools |
|---|---|
| `menu_tools.py` | generate_menu_plan, validate_nutrition, tag_allergens, check_diversity |
| `recipe_tools.py` | search_recipes, scale_recipe |
| `work_order_tools.py` | generate_work_order |
| `haccp_tools.py` | generate_haccp_checklist, check_haccp_completion |
| `dashboard_tools.py` | query_dashboard, generate_audit_report |
| `purchase_tools.py` | (MVP2) BOM 산출, 발주서 생성, 단가 급등 감지 |
| `demand_tools.py` | (MVP3) 수요 예측 도구 |
| `registry.py` | Tool 등록/조회 레지스트리 |

**System Prompt 구축**: `agents/prompts/system.py` — agent_type별 도메인 특화 프롬프트 빌더. user_role, site_name, RAG 컨텍스트 동적 주입.

**설계 원칙**:
1. RAG-First: 내부 KB 최우선 근거
2. Transparency: 모든 응답에 출처 인용 필수
3. Safety-in-Loop: 알레르겐/HACCP 안전 검사 내장
4. Human-in-the-Loop: 확정/발주는 사람 승인 필수
5. Graceful Degradation: RAG 미확인시 경고

---

## 5. 데이터 모델 요약

**마스터 테이블** (5개):

| ORM File | Table | 용도 |
|---|---|---|
| `site.py` | sites | 현장(사업장) 마스터 |
| `item.py` | items | 식재료 마스터 |
| `policy.py` | nutrition_policies, allergen_policies | 영양/알레르겐 정책 |
| `user.py` | users | 사용자 (5 roles) |

**운영 테이블** (11개+):

| ORM File | Table(s) | 용도 |
|---|---|---|
| `menu_plan.py` | menu_plans, menu_plan_items, menu_plan_validations | 식단 계획/검증 |
| `recipe.py` | recipes, recipe_documents (pgvector) | 레시피 + 벡터 임베딩 |
| `work_order.py` | work_orders | 작업지시서 |
| `haccp.py` | haccp_checklists, haccp_records, haccp_incidents | HACCP 점검/기록/사고 |
| `conversation.py` | conversations | AI 대화 이력 |
| `audit_log.py` | audit_logs | 감사 로그 |
| `purchase.py` | purchase_orders, purchase_order_items, vendors | 구매/발주 (MVP2) |
| `inventory.py` | inventory, inventory_lots | 재고/로트 (MVP2) |
| `forecast.py` | demand_forecasts | 수요 예측 (MVP3) |
| `waste.py` | waste_records | 잔반 기록 (MVP3) |
| `cost.py` | cost_analyses | 원가 분석 (MVP3) |
| `claim.py` | claims | 클레임 관리 (MVP3) |

**Multi-site 격리**: 모든 쿼리에 `site_id` WHERE clause 적용 (서비스 레이어 필터링).

---

## 6. 보안 아키텍처 (JWT + RBAC)

**인증 모듈** (`auth/`):

| File | 역할 |
|---|---|
| `jwt.py` | JWT 토큰 발급/검증 (python-jose, HS256) |
| `password.py` | bcrypt 해싱 |
| `oauth2.py` | OAuth2PasswordBearer 스킴 |
| `dependencies.py` | FastAPI Depends — get_current_user, require_role |

**5-Role RBAC**:

| Role | 약어 | 주요 권한 |
|---|---|---|
| 영양사/메뉴팀 | NUT | 식단 CRUD, 레시피, 작업지시서 생성 |
| 조리/생산 | KIT | 작업지시서/레시피 조회, CCP 기록 |
| 위생/HACCP | QLT | 점검표 CRUD, CCP 기록, 사고 관리 |
| 운영/관리 | OPS | 대시보드, 식단 승인/확정, 정책 수정 |
| 시스템 관리자 | ADM | 전체 마스터 CRUD, 사용자/권한 관리 |

**보안 정책**:
- JWT Access Token: 30분, Refresh Token: 7일
- 추천/초안은 넓게 허용, 확정/발주/공식기록은 승인 워크플로우 필수
- SAFE-001~004 안전 제약 (알레르겐, 식중독, 스케일링, 승인)
- 모든 확정/수정/삭제시 `audit_logs` 기록 필수

---

## 7. 클라우드 배포 아키텍처 (GCP)

**Region**: asia-northeast3 (Seoul)

| Resource | Service | Config |
|---|---|---|
| **Frontend** | Vercel | CDN 글로벌, Next.js 14 |
| **API** | Cloud Run | 2 vCPU, 2Gi RAM, timeout=300s, scale 0-10 |
| **Database** | Cloud SQL PG16 | Private IP, pgvector, SSD, auto-backup |
| **Secrets** | Secret Manager | database-url, jwt-secret, anthropic-api-key, openai-api-key |
| **Registry** | Artifact Registry | Docker images (`food-ai` repo) |
| **Network** | VPC Connector | 10.8.0.0/28, e2-micro, 2-3 instances |
| **Storage** | Cloud Storage | HACCP 사진, 문서 저장 |
| **IAM** | Service Account | `food-ai-api-sa` (cloudsql.client, secretAccessor, storage.objectViewer) |

**인프라 프로비저닝**: `infra/gcloud-setup.sh` — 460줄 자동화 스크립트
- 11개 GCP API enable
- Artifact Registry, Cloud SQL, VPC Connector, Secret Manager, Service Account 생성
- Workload Identity Federation (GitHub Actions OIDC) 설정
- 초기 Cloud Run placeholder 배포

---

## 8. CI/CD 파이프라인

**파일**: `.github/workflows/deploy-api.yml`

**트리거**: `master` 브랜치에 `food-ai-agent-api/**` 변경시

```
Job 1: Test
  ├── PostgreSQL 16 + pgvector 서비스 컨테이너
  ├── pip install + alembic upgrade head
  └── pytest --tb=short -q

Job 2: Build & Push (test 성공 후)
  ├── Workload Identity Federation 인증 (무키)
  ├── Docker build + push to Artifact Registry
  └── SHA tag + latest tag

Job 3: Deploy Staging (build 성공 후)
  ├── Cloud Run deploy (staging, min=0, max=5)
  ├── Env: APP_ENV=staging, secrets from Secret Manager
  └── Smoke test: curl /health

Job 4: Deploy Production (staging 성공 + 수동 승인)
  ├── GitHub Environment: production (manual approval)
  ├── Cloud Run deploy (production, min=1, max=10)
  └── Health check 검증
```

**핵심 보안**: Workload Identity Federation으로 서비스 계정 키 없이 GitHub Actions에서 GCP 인증. `id-token: write` 퍼미션 사용.

---

## 9. MVP 현황 및 로드맵

| MVP | 상태 | Match Rate | 핵심 기능 |
|---|---|---|---|
| **MVP 1** | 완료 (아카이브) | 96% | 식단 AI 생성/검증, 레시피 RAG 검색, HACCP 자동화, 대시보드 |
| **MVP 2** | 완료 (아카이브) | 100% | BOM 자동산출, 발주서 생성, 단가 급등 감지, 재고/로트 추적 |
| **MVP 3** | 완료 (아카이브) | 100% | 수요예측, 원가최적화, 잔반 관리, 클레임 관리 |
| **MVP 4** | 계획 | - | 클레임 고도화, CS 관리, 벤더 품질 평가 |

**현재 단계**: GCloud 인프라 프로비저닝 및 배포 준비

**다음 단계**:
1. GCloud 인프라 프로비저닝 (VPC, Cloud SQL, Artifact Registry, Secret Manager)
2. DB 마이그레이션 (pg_dump → Cloud SQL import), pgvector 검증
3. Cloud Run 배포, SSE 스트리밍 테스트, CI/CD 활성화
4. 파일럿 운영 + 구매팀 온보딩 (1개월)
5. MVP 4 클레임 고도화 기획 (3개월)

---

## 코드베이스 규모 요약

| Area | Count |
|---|---|
| Backend Routers | 22개 (auth, chat, menu_plans, recipes, ... claims) |
| ORM Models | 18개 파일 (16+ DB 테이블) |
| Agent Tools | 8개 파일 (11+ tool functions) |
| RAG Components | 5개 (loader, chunker, embedder, retriever, pipeline) |
| Frontend Routes | 13개 페이지 그룹 (dashboard, menu-studio, recipes, kitchen, haccp, ...) |
| Frontend Components | 14개 디렉토리 (chat, claims, cost, dashboard, ...) |
| Tests | 52+ 통합 테스트 파일/디렉토리 |
| Infra Scripts | gcloud-setup.sh (460줄), deploy-api.yml (238줄) |
