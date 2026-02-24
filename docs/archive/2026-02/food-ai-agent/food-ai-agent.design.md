# Food AI Agent - MVP 1 Design Document
- **Version**: 1.0.0
- **Date**: 2026-02-23
- **Phase**: PDCA Design
- **Author**: CTO Lead (food-ai-cto-team)
- **Prerequisite**: [food-ai-agent.plan.md](../../01-plan/features/food-ai-agent.plan.md)

---

## 1. Database Schema (PostgreSQL + SQLAlchemy 2.0)

### 1.1 Schema Overview

PostgreSQL을 SQLAlchemy 2.0 async ORM으로 직접 연결하며, Alembic으로 마이그레이션을 관리한다. 모든 테이블은 `id (UUID PK)`, `created_at`, `updated_at` 컬럼을 기본 포함한다. Multi-site 데이터 격리는 서비스 레이어에서 `site_id` WHERE clause 필터링으로 구현한다 (RLS 미사용).

### 1.2 Master Tables

#### `sites`
```sql
CREATE TABLE sites (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        VARCHAR(200) NOT NULL,
  type        VARCHAR(50) NOT NULL,           -- school, corporate, hospital, etc.
  capacity    INTEGER NOT NULL DEFAULT 0,     -- max headcount
  address     TEXT,
  operating_hours JSONB,                      -- {"mon": {"start": "06:00", "end": "20:00"}, ...}
  rules       JSONB DEFAULT '{}',             -- site-specific rules
  is_active   BOOLEAN DEFAULT TRUE,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

#### `items` (식재료 마스터)
```sql
CREATE TABLE items (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name              VARCHAR(200) NOT NULL,
  category          VARCHAR(100) NOT NULL,      -- 육류, 수산, 채소, 양념, etc.
  sub_category      VARCHAR(100),
  spec              VARCHAR(200),               -- 규격 (예: 국내산/1kg)
  unit              VARCHAR(50) NOT NULL,        -- g, kg, ml, L, ea
  allergens         TEXT[] DEFAULT '{}',         -- {'우유','대두','밀',...}
  storage_condition VARCHAR(100),               -- 냉장, 냉동, 실온
  substitute_group  VARCHAR(100),               -- 대체 가능 그룹
  nutrition_per_100g JSONB,                     -- {"kcal":250,"protein":20,"sodium":500,...}
  is_active         BOOLEAN DEFAULT TRUE,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_items_category ON items(category);
CREATE INDEX idx_items_allergens ON items USING GIN(allergens);
CREATE INDEX idx_items_name_search ON items USING GIN(to_tsvector('simple', name));
```

#### `nutrition_policies`
```sql
CREATE TABLE nutrition_policies (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id     UUID REFERENCES sites(id),       -- NULL = global default
  name        VARCHAR(200) NOT NULL,
  meal_type   VARCHAR(50),                      -- lunch, dinner, all
  criteria    JSONB NOT NULL,                   -- {"kcal":{"min":500,"max":800},"sodium":{"max":2000},...}
  is_active   BOOLEAN DEFAULT TRUE,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

#### `allergen_policies`
```sql
CREATE TABLE allergen_policies (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id           UUID REFERENCES sites(id),
  name              VARCHAR(200) NOT NULL,
  legal_allergens   TEXT[] DEFAULT ARRAY[
    '난류','우유','메밀','땅콩','대두','밀','고등어','게',
    '새우','돼지고기','복숭아','토마토','아황산류','호두',
    '닭고기','쇠고기','오징어','조개류','잣','쑥','홍합','전복'
  ],
  custom_allergens  TEXT[] DEFAULT '{}',         -- site-specific additions
  display_format    VARCHAR(50) DEFAULT 'number', -- number, text, icon
  is_active         BOOLEAN DEFAULT TRUE,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);
```

#### `users` (자체 JWT 인증)
```sql
CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           VARCHAR(300) NOT NULL UNIQUE,
  hashed_password VARCHAR(500) NOT NULL,
  name            VARCHAR(200) NOT NULL,
  role            VARCHAR(10) NOT NULL,            -- NUT, KIT, QLT, OPS, ADM
  site_ids        UUID[] DEFAULT '{}',             -- accessible sites
  preferences     JSONB DEFAULT '{}',
  is_active       BOOLEAN DEFAULT TRUE,
  last_login_at   TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_users_email ON users(email);
```

**SQLAlchemy Model Example:**
```python
from sqlalchemy import Column, String, Boolean, ARRAY, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email = Column(String(300), unique=True, nullable=False)
    hashed_password = Column(String(500), nullable=False)
    name = Column(String(200), nullable=False)
    role = Column(String(10), nullable=False)
    site_ids = Column(ARRAY(UUID(as_uuid=True)), server_default="{}")
    preferences = Column(JSONB, server_default="{}")
    is_active = Column(Boolean, server_default="true")
    last_login_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
```

### 1.3 Operational Tables

#### `menu_plans`
```sql
CREATE TABLE menu_plans (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id     UUID NOT NULL REFERENCES sites(id),
  title       VARCHAR(300),
  period_start DATE NOT NULL,
  period_end   DATE NOT NULL,
  status      VARCHAR(20) NOT NULL DEFAULT 'draft', -- draft, review, confirmed, archived
  version     INTEGER NOT NULL DEFAULT 1,
  parent_id   UUID REFERENCES menu_plans(id),   -- for version history
  budget_per_meal NUMERIC(10,2),                -- target cost per meal
  target_headcount INTEGER,
  nutrition_policy_id UUID REFERENCES nutrition_policies(id),
  allergen_policy_id UUID REFERENCES allergen_policies(id),
  created_by  UUID NOT NULL,
  confirmed_by UUID,
  confirmed_at TIMESTAMPTZ,
  ai_generation_params JSONB,                   -- AI generation parameters used
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_menu_plans_site_period ON menu_plans(site_id, period_start, period_end);
CREATE INDEX idx_menu_plans_status ON menu_plans(status);
```

#### `menu_plan_items`
```sql
CREATE TABLE menu_plan_items (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  menu_plan_id  UUID NOT NULL REFERENCES menu_plans(id) ON DELETE CASCADE,
  date          DATE NOT NULL,
  meal_type     VARCHAR(20) NOT NULL,            -- breakfast, lunch, dinner, snack
  course        VARCHAR(50) NOT NULL,            -- main, soup, side1, side2, side3, dessert, rice
  item_name     VARCHAR(300) NOT NULL,
  recipe_id     UUID REFERENCES recipes(id),
  nutrition     JSONB,                           -- {"kcal":350,"protein":15,"sodium":800,...}
  allergens     TEXT[] DEFAULT '{}',
  sort_order    INTEGER DEFAULT 0,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_menu_plan_items_plan ON menu_plan_items(menu_plan_id);
CREATE INDEX idx_menu_plan_items_date ON menu_plan_items(date, meal_type);
```

#### `menu_plan_validations`
```sql
CREATE TABLE menu_plan_validations (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  menu_plan_id   UUID NOT NULL REFERENCES menu_plans(id) ON DELETE CASCADE,
  validation_type VARCHAR(50) NOT NULL,          -- nutrition, allergen, diversity
  status         VARCHAR(20) NOT NULL,           -- pass, warning, fail
  details        JSONB NOT NULL,                 -- detailed validation results
  validated_at   TIMESTAMPTZ DEFAULT NOW()
);
```

#### `recipes`
```sql
CREATE TABLE recipes (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name            VARCHAR(300) NOT NULL,
  version         INTEGER NOT NULL DEFAULT 1,
  category        VARCHAR(100),                  -- 한식, 중식, 양식, 일식, etc.
  sub_category    VARCHAR(100),                  -- 구이, 볶음, 조림, 탕, etc.
  servings_base   INTEGER NOT NULL DEFAULT 1,    -- base serving count
  prep_time_min   INTEGER,
  cook_time_min   INTEGER,
  difficulty      VARCHAR(20),                   -- easy, medium, hard
  ingredients     JSONB NOT NULL,                -- [{"item_id":"...","name":"양파","amount":200,"unit":"g"}]
  steps           JSONB NOT NULL,                -- [{"order":1,"description":"...","duration_min":10,"ccp":null}]
  ccp_points      JSONB DEFAULT '[]',            -- [{"step_order":3,"type":"temperature","target":"75도 이상","critical":true}]
  nutrition_per_serving JSONB,                   -- {"kcal":350,"protein":15,...}
  allergens       TEXT[] DEFAULT '{}',
  tags            TEXT[] DEFAULT '{}',
  source          VARCHAR(200),                  -- SOP document name / origin
  is_active       BOOLEAN DEFAULT TRUE,
  created_by      UUID,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recipes_name_search ON recipes USING GIN(to_tsvector('simple', name));
CREATE INDEX idx_recipes_category ON recipes(category, sub_category);
CREATE INDEX idx_recipes_tags ON recipes USING GIN(tags);
```

#### `recipe_documents` (RAG)
```sql
CREATE TABLE recipe_documents (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recipe_id   UUID REFERENCES recipes(id),       -- NULL for standalone SOP docs
  doc_type    VARCHAR(50) NOT NULL,              -- recipe, sop, haccp_guide, policy
  title       VARCHAR(300) NOT NULL,
  content     TEXT NOT NULL,                     -- full text content
  chunk_index INTEGER DEFAULT 0,                 -- chunk order within document
  metadata    JSONB DEFAULT '{}',                -- source, version, etc.
  embedding   vector(1536),                      -- pgvector embedding
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_recipe_docs_embedding ON recipe_documents USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_recipe_docs_type ON recipe_documents(doc_type);
```

#### `work_orders`
```sql
CREATE TABLE work_orders (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  menu_plan_id    UUID NOT NULL REFERENCES menu_plans(id),
  site_id         UUID NOT NULL REFERENCES sites(id),
  date            DATE NOT NULL,
  meal_type       VARCHAR(20) NOT NULL,
  recipe_id       UUID NOT NULL REFERENCES recipes(id),
  recipe_name     VARCHAR(300) NOT NULL,
  scaled_servings INTEGER NOT NULL,
  scaled_ingredients JSONB NOT NULL,             -- scaled ingredient list
  steps           JSONB NOT NULL,                -- steps with CCP markers
  seasoning_notes TEXT,                          -- large-batch seasoning adjustments
  equipment_notes TEXT,
  deadline_time   TIME,                          -- meal service time
  status          VARCHAR(20) DEFAULT 'pending', -- pending, in_progress, completed
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_work_orders_site_date ON work_orders(site_id, date, meal_type);
```

#### `haccp_checklists`
```sql
CREATE TABLE haccp_checklists (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id     UUID NOT NULL REFERENCES sites(id),
  date        DATE NOT NULL,
  checklist_type VARCHAR(20) NOT NULL,           -- daily, weekly
  meal_type   VARCHAR(20),                       -- NULL for general daily checks
  template    JSONB NOT NULL,                    -- checklist items template
  status      VARCHAR(20) DEFAULT 'pending',     -- pending, in_progress, completed, overdue
  completed_by UUID,
  completed_at TIMESTAMPTZ,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_haccp_checklists_site_date ON haccp_checklists(site_id, date);
CREATE INDEX idx_haccp_checklists_status ON haccp_checklists(status);
```

#### `haccp_records`
```sql
CREATE TABLE haccp_records (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  checklist_id    UUID NOT NULL REFERENCES haccp_checklists(id),
  ccp_point       VARCHAR(200) NOT NULL,         -- check point name
  category        VARCHAR(50),                   -- temperature, time, cleanliness, etc.
  target_value    VARCHAR(100),                  -- expected (e.g., "75도 이상")
  actual_value    VARCHAR(100),                  -- recorded value
  is_compliant    BOOLEAN,
  corrective_action TEXT,                        -- if non-compliant
  photo_url       TEXT,
  recorded_by     UUID NOT NULL,
  recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_haccp_records_checklist ON haccp_records(checklist_id);
```

#### `haccp_incidents`
```sql
CREATE TABLE haccp_incidents (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  site_id     UUID NOT NULL REFERENCES sites(id),
  incident_type VARCHAR(50) NOT NULL,            -- food_safety, contamination, temperature, other
  severity    VARCHAR(20) NOT NULL,              -- low, medium, high, critical
  description TEXT NOT NULL,
  steps_taken JSONB DEFAULT '[]',                -- [{step, description, completed, completed_at}]
  status      VARCHAR(20) DEFAULT 'open',        -- open, in_progress, resolved, closed
  reported_by UUID NOT NULL,
  resolved_by UUID,
  resolved_at TIMESTAMPTZ,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

#### `audit_logs`
```sql
CREATE TABLE audit_logs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL,
  site_id     UUID,
  action      VARCHAR(50) NOT NULL,              -- create, update, confirm, reject, delete
  entity_type VARCHAR(50) NOT NULL,              -- menu_plan, recipe, haccp_checklist, etc.
  entity_id   UUID NOT NULL,
  changes     JSONB,                             -- {field: {old: ..., new: ...}}
  reason      TEXT,
  ai_context  JSONB,                             -- AI generation params/sources if applicable
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_site_date ON audit_logs(site_id, created_at);
```

#### `conversations` (AI Chat)
```sql
CREATE TABLE conversations (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID NOT NULL,
  site_id       UUID,
  context_type  VARCHAR(50),                     -- menu, recipe, haccp, general
  context_ref   UUID,                            -- related entity ID (menu_plan_id, etc.)
  title         VARCHAR(300),
  messages      JSONB NOT NULL DEFAULT '[]',     -- [{role, content, tool_calls, citations, timestamp}]
  is_active     BOOLEAN DEFAULT TRUE,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_user ON conversations(user_id, is_active);
```

### 1.4 Entity Relationship Diagram (Text)

```
sites ──1:N──> menu_plans
sites ──1:N──> haccp_checklists
sites ──1:N──> haccp_incidents
sites ──1:N──> work_orders
sites ──1:N──> nutrition_policies
sites ──1:N──> allergen_policies

users ──M:N──> sites (via site_ids[])

menu_plans ──1:N──> menu_plan_items
menu_plans ──1:N──> menu_plan_validations
menu_plans ──1:N──> work_orders
menu_plans ──self──> menu_plans (version chain via parent_id)

menu_plan_items ──N:1──> recipes

recipes ──1:N──> recipe_documents (RAG chunks)
recipes ──1:N──> work_orders

haccp_checklists ──1:N──> haccp_records

audit_logs ──poly──> any entity (entity_type + entity_id)
conversations ──poly──> any entity (context_type + context_ref)
```

---

## 2. AI Agent Architecture

AI Agent는 Food AI Agent 시스템의 핵심 두뇌이다. Knowledge Base → Embedding → Retrieval → Agentic Loop → Response의 전체 파이프라인을 상세히 정의한다.

### 2.1 Knowledge Base Design

AI Agent가 참조하는 내부 지식 기반의 구성과 갱신 전략:

```
┌──────────────────────────────────────────────────────────────┐
│                    Knowledge Base                             │
├──────────────┬───────────────────┬───────────┬───────────────┤
│ Type         │ Source            │ Update    │ RAG Indexed   │
├──────────────┼───────────────────┼───────────┼───────────────┤
│ 표준레시피    │ recipes + steps   │ 실시간    │ Yes (chunks)  │
│ SOP 문서     │ recipe_documents  │ 배치 업로드│ Yes (chunks) │
│ HACCP 가이드 │ recipe_documents  │ 배치 업로드│ Yes (chunks) │
│ 영양 정책    │ nutrition_policies│ 실시간    │ No (SQL 직접) │
│ 알레르겐 규정│ allergen_policies │ 실시간    │ No (SQL 직접) │
│ 식재료 마스터│ items             │ 실시간    │ No (SQL 직접) │
│ 현장 룰     │ sites.rules       │ 실시간    │ No (SQL 직접) │
│ 클레임 이력  │ claims (MVP 4)    │ 실시간    │ Future        │
└──────────────┴───────────────────┴───────────┴───────────────┘
```

**RAG Indexed vs SQL Direct:**
- 비정형 텍스트 (레시피 서술, SOP 문서, HACCP 가이드) → pgvector 임베딩 검색
- 정형 데이터 (영양 기준값, 알레르겐 목록, 식재료 정보) → SQL 직접 조회 (Tool 내)

### 2.2 Embedding & Indexing Pipeline

문서를 Knowledge Base에 인덱싱하는 파이프라인:

```
[Document Upload] ── /api/v1/documents/upload
     ↓
[Loader] ── 포맷별 텍스트 추출
     ├── PDF: PyMuPDF (fitz)
     ├── DOCX: python-docx
     ├── Markdown: 직접 파싱
     └── TXT: UTF-8 읽기
     ↓
[Preprocessor]
     ├── 한국어 정규화 (유니코드 NFKC)
     ├── 불필요 공백/특수문자 정리
     └── 메타데이터 추출 (제목, 버전, 날짜)
     ↓
[Chunker] ── RecursiveCharacterTextSplitter
     ├── chunk_size = 1000 characters
     ├── chunk_overlap = 200 characters
     ├── separators: ["\n## ", "\n### ", "\n\n", "\n", " "]
     └── 한국어 문장 경계 우선 분리
     ↓
[Embedder] ── OpenAI text-embedding-3-small
     ├── dimension: 1536
     ├── batch_size: 100 (API 호출 최소화)
     └── 에러 시 exponential backoff 재시도
     ↓
[Store] ── recipe_documents 테이블
     ├── content: 청크 원문
     ├── embedding: vector(1536)
     ├── metadata: {doc_type, recipe_id, source, version, chunk_index}
     └── 중복 검출: (recipe_id, doc_type, chunk_index) 기준
```

**pgvector 인덱스 설정:**
```sql
-- IVFFlat 인덱스 (문서 수 < 100K)
CREATE INDEX idx_recipe_docs_embedding
  ON recipe_documents USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- 검색 시 probe 설정
SET ivfflat.probes = 10;
```

### 2.3 Retrieval Pipeline

질의 시간에 Knowledge Base에서 관련 문서를 검색하는 파이프라인:

```
[User Query + Context]
     ↓
[Query Rewriter] (선택적, Claude 경량 호출)
     ├── 대화 문맥에서 독립적인 검색 쿼리로 변환
     ├── 예: "그거 나트륨 괜찮아?" → "A현장 다음주 중식 식단 나트륨 기준 검증"
     └── confidence < 0.7이면 원본 쿼리 사용
     ↓
┌─────────────────────────────────────────────────────┐
│  [Parallel Search]                                  │
│                                                     │
│  ┌─────────────────────┐ ┌────────────────────────┐│
│  │ BM25 Keyword Search  │ │ Vector Semantic Search ││
│  │ PostgreSQL FTS       │ │ pgvector cosine sim    ││
│  │ to_tsvector('simple')│ │ embedding <=> query_vec││
│  │ → top-20 results     │ │ → top-20 results       ││
│  └──────────┬──────────┘ └──────────┬─────────────┘│
│             └──────────┬────────────┘               │
│                        ↓                            │
│  [RRF Fusion] ── Reciprocal Rank Fusion             │
│     score(d) = Σ 1/(k + rank_i)                    │
│     k = 60 (smoothing constant)                     │
│     keyword_weight = 0.3                            │
│     vector_weight = 0.7                             │
│                        ↓                            │
│  [Reranker] (선택적)                                │
│     Claude 기반 관련도 재평가 (0-10 점수)            │
│     "다음 쿼리에 대해 각 문서의 관련성을 평가하세요"  │
│                        ↓                            │
│  [Context Builder] → top-5 chunks 선택              │
│     ├── 청크 원문 + 메타데이터(출처, 버전, 날짜)     │
│     ├── 인접 청크 포함 (같은 문서의 앞뒤 청크)       │
│     └── 총 컨텍스트 크기 제한: ~4000 tokens          │
└─────────────────────────────────────────────────────┘
     ↓
[Retrieved Context] → Agentic Loop에 전달
```

**검색 SQL 예시 (하이브리드):**
```sql
-- Vector search
SELECT id, content, metadata,
       embedding <=> $1::vector AS distance
FROM recipe_documents
WHERE doc_type = ANY($2)
ORDER BY embedding <=> $1::vector
LIMIT 20;

-- BM25 keyword search
SELECT id, content, metadata,
       ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', $1)) AS rank
FROM recipe_documents
WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', $1)
ORDER BY rank DESC
LIMIT 20;
```

### 2.4 Agentic Loop (ReAct Pattern)

AI Agent의 핵심 실행 루프. ReAct(Reason-Act-Observe) 패턴으로 다단계 추론과 도구 호출을 수행:

```python
# ReAct Loop 구현 (의사코드)
async def agentic_loop(
    query: str,
    retrieved_context: list[str],
    user: User,
    site: Site,
    conversation_history: list[dict],
    max_iterations: int = 10
) -> AsyncGenerator[SSEEvent, None]:

    # 1. System Prompt 구성
    system_prompt = build_system_prompt(
        agent_type=intent.agent,       # menu / recipe / haccp
        user_role=user.role,
        site_rules=site.rules,
        safety_guardrails=SAFETY_RULES
    )

    # 2. 메시지 구성
    messages = [
        {"role": "system", "content": system_prompt},
        # Retrieved Context를 system 메시지에 포함
        {"role": "system", "content": format_rag_context(retrieved_context)},
        # 대화 이력 (sliding window, 최근 10턴)
        *conversation_history[-20:],
        {"role": "user", "content": query}
    ]

    # 3. ReAct Loop
    for iteration in range(max_iterations):
        response = await claude_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            temperature=0.3,
            messages=messages,
            tools=get_tools_for_agent(intent.agent),
            stream=True
        )

        # 스트리밍 처리
        async for event in response:
            if event.type == "content_block_delta":
                yield SSEEvent(type="text_delta", content=event.delta.text)

            elif event.type == "content_block_start" and event.content_block.type == "tool_use":
                tool_name = event.content_block.name
                yield SSEEvent(type="tool_call", name=tool_name, status="started")

        # 종료 조건 확인
        if response.stop_reason == "end_turn":
            # 출처 추출 및 첨부
            citations = extract_citations(response, retrieved_context)
            yield SSEEvent(type="citations", sources=citations)
            yield SSEEvent(type="done")
            return

        # Tool 실행
        if response.stop_reason == "tool_use":
            for tool_call in response.tool_calls:
                # 안전 검사: 권한 확인
                check_tool_permission(tool_call, user)

                # Tool 실행
                result = await execute_tool(tool_call.name, tool_call.input)
                yield SSEEvent(type="tool_result", name=tool_call.name, data=result)

                # 결과를 메시지에 추가
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": tool_call.id, "content": str(result)}
                ]})

    # 최대 반복 초과
    yield SSEEvent(type="text_delta", content="처리가 복잡하여 부분 결과를 제공합니다.")
    yield SSEEvent(type="done")
```

**ReAct 실행 예시 (식단 생성):**
```
Iteration 1: [Reason] 사용자가 A현장 350식 중식 5일 식단을 요청
             [Act] generate_menu_plan(site_id, period, meal_types, headcount, budget)
             [Observe] 2안 생성됨

Iteration 2: [Reason] 생성된 식단의 영양 기준 확인 필요
             [Act] validate_nutrition(menu_plan_id)
             [Observe] 수요일 나트륨 초과 발견

Iteration 3: [Reason] 알레르겐 태깅 필요
             [Act] tag_allergens(target_type="menu_plan", target_id)
             [Observe] 대두, 밀, 우유 확인. 메밀 "확인 필요" 1건

Iteration 4: [Reason] 모든 검증 완료, 결과 정리
             [End Turn] 2안 + 영양 검증 + 알레르겐 + 나트륨 초과 경고 응답
```

### 2.5 Domain-Specific RAG Strategies

각 도메인 Agent별로 검색 전략을 차별화:

#### Menu Agent RAG
```
검색 대상: recipes, nutrition_policies, allergen_policies, sites.rules
전략:
  1. 현장(site) 룰 로드 (SQL 직접) → 제약 조건 확인
  2. 영양 정책 로드 (SQL 직접) → 검증 기준 확보
  3. 레시피 검색 (RAG 하이브리드) → 메뉴 후보 확보
     - 필터: category, allergen_exclude, is_active=true
  4. 알레르겐 정책 로드 (SQL 직접) → 태깅 기준 확보
우선순위: 현장 룰 > 영양 정책 > 레시피 DB
```

#### Recipe Agent RAG
```
검색 대상: recipes, recipe_documents (SOP), items
전략:
  1. 레시피 하이브리드 검색 (RAG) → 표준레시피 매칭
  2. SOP 문서 검색 (RAG, doc_type='sop') → 조리 가이드
  3. 식재료 조회 (SQL 직접) → 스케일링/영양 계산
  4. 트러블슈팅: SOP + 레시피 동시 검색
우선순위: 표준레시피 > SOP 문서 > 일반 지식
```

#### HACCP Agent RAG
```
검색 대상: recipe_documents (haccp_guide), haccp_checklists (이력), sites.rules
전략:
  1. HACCP 가이드 검색 (RAG, doc_type='haccp_guide') → 규정/절차
  2. 점검 이력 조회 (SQL 직접) → 최근 기록 참조
  3. 현장 룰 로드 (SQL 직접) → 현장 특화 기준
  4. 사고 대응: HACCP 가이드 최우선 + 단계별 체크리스트 생성
우선순위: HACCP 가이드 > 현장 룰 > 점검 이력
```

### 2.6 Prompt Engineering Strategy

#### System Prompt 구조 (공통)
```
[Role Definition]
  당신은 {domain} 전문 AI 어시스턴트입니다. (한국 급식업체용)

[Capabilities]
  가능한 작업 목록 (도메인별 차별화)

[Safety Rules]
  - 알레르겐 미확인 → "확인 필요" 태그 필수
  - 식중독 의심 → 즉시 대응 플로우
  - 대량조리 → 조미료 보정 경고
  - 확정 금지 (사람 승인 필요)

[Citation Rules]
  - 반드시 [출처: {doc_title} v{version}] 형식으로 인용
  - 근거 없는 추론은 [가정] 으로 표기
  - RAG 검색 결과 없으면 "내부 문서 미확인" 경고

[Context]
  현장: {site_name} ({site_type}, {capacity}식)
  정책: {policy_summary}
  사용자: {user_name} ({user_role})

[Retrieved Documents]
  --- 검색 결과 1: {title} (출처: {source}, v{version}) ---
  {chunk_content}
  --- 검색 결과 2: ... ---
  ...

[Response Format]
  - 한국어 기본, 전문용어는 한국어(영어) 병기
  - 표/리스트 형식 선호 (역할별 응답 형태 정의)
  - 항상 마지막에 출처/가정/리스크 요약
```

#### Few-shot 예시 (도메인별 3-5개)
```
[Menu Agent 예시]
User: "다음주 중식 5일 식단 짜줘"
Assistant: "A현장 기준으로 중식 5일 식단 2안을 생성하겠습니다.
[출처: A현장 영양정책 v2.1]에 따라 1식 기준 칼로리 600-800kcal, 나트륨 2000mg 이하로 설정합니다.
..."

[Recipe Agent 예시]
User: "제육볶음 350인분 재료 알려줘"
Assistant: "[출처: 표준레시피 - 제육볶음 v3] 기준 4인분에서 350인분으로 스케일링합니다.
[가정] 대량조리(350식) 시 양념류는 단순 비례가 아닌 80-85% 수준으로 보정합니다.
..."
```

#### Chain-of-Thought (CoT) 적용
- **영양 계산**: 단계별 계산 과정 명시 (재료 → 100g당 영양 → 1인분 → 합산)
- **알레르겐 추론**: 원재료 → 성분 분석 → 알레르겐 매핑 과정 표시
- **위험도 판단**: 상황 분석 → 규정 참조 → 심각도 분류 과정 투명화

### 2.7 Intent Router Detail

```python
# Intent classification using Claude (경량 분류 호출)
INTENT_SYSTEM_PROMPT = """
You are an intent classifier for a Korean food service management system.
Classify the user message into exactly one intent.

Intents:
- menu_generate: Creating or modifying meal plans
- menu_validate: Checking nutrition or allergens for existing plans
- recipe_search: Finding recipes or recipe information
- recipe_scale: Scaling recipes for different serving sizes
- work_order: Generating or viewing work orders / production instructions
- haccp_checklist: Creating or checking HACCP checklists
- haccp_record: Recording CCP values or viewing HACCP records
- haccp_incident: Reporting or managing food safety incidents
- dashboard: Viewing operational status or summaries
- settings: Managing master data, policies, or system configuration
- general: General questions, greetings, or unclear requests

Context: current_screen={screen}, user_role={role}, site={site_name}

Return JSON: {"intent": "...", "confidence": 0.0-1.0, "entities": {...}, "agent": "menu|recipe|haccp|general"}
"""

# Config: model="claude-sonnet-4-6", max_tokens=200, temperature=0
# Low-confidence (<0.7) → fallback to general agent with clarification
# Intent → Agent mapping: menu_*/menu, recipe_*/work_order/recipe, haccp_*/haccp, else/general
```

### 2.8 Tool Definitions (Claude Tool Use)

11개 도메인 도구의 JSON Schema 정의:

```json
{
  "tools": [
    {
      "name": "generate_menu_plan",
      "description": "Generate weekly meal plan alternatives for a site. Returns 2+ alternatives with nutrition summary.",
      "input_schema": {
        "type": "object",
        "properties": {
          "site_id": {"type": "string", "format": "uuid"},
          "period_start": {"type": "string", "format": "date"},
          "period_end": {"type": "string", "format": "date"},
          "meal_types": {"type": "array", "items": {"type": "string", "enum": ["breakfast","lunch","dinner","snack"]}},
          "target_headcount": {"type": "integer"},
          "budget_per_meal": {"type": "number"},
          "preferences": {"type": "object", "description": "User preferences and restrictions"},
          "num_alternatives": {"type": "integer", "default": 2}
        },
        "required": ["site_id", "period_start", "period_end", "meal_types", "target_headcount"]
      }
    },
    {
      "name": "validate_nutrition",
      "description": "Validate a menu plan against nutrition policy. Returns pass/warning/fail per day and criteria.",
      "input_schema": {
        "type": "object",
        "properties": {
          "menu_plan_id": {"type": "string", "format": "uuid"},
          "policy_id": {"type": "string", "format": "uuid"}
        },
        "required": ["menu_plan_id"]
      }
    },
    {
      "name": "tag_allergens",
      "description": "Auto-tag allergens for menu plan items or recipe ingredients based on allergen policy.",
      "input_schema": {
        "type": "object",
        "properties": {
          "target_type": {"type": "string", "enum": ["menu_plan", "recipe"]},
          "target_id": {"type": "string", "format": "uuid"}
        },
        "required": ["target_type", "target_id"]
      }
    },
    {
      "name": "check_diversity",
      "description": "Check menu diversity: cooking method bias, ingredient repetition, category balance.",
      "input_schema": {
        "type": "object",
        "properties": {
          "menu_plan_id": {"type": "string", "format": "uuid"}
        },
        "required": ["menu_plan_id"]
      }
    },
    {
      "name": "search_recipes",
      "description": "Search recipes using hybrid search (BM25 keyword + vector semantic). Returns ranked results with relevance scores.",
      "input_schema": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "category": {"type": "string"},
          "allergen_exclude": {"type": "array", "items": {"type": "string"}},
          "max_results": {"type": "integer", "default": 10}
        },
        "required": ["query"]
      }
    },
    {
      "name": "scale_recipe",
      "description": "Scale recipe ingredients from base servings to target servings. Includes seasoning adjustment guide for large batches.",
      "input_schema": {
        "type": "object",
        "properties": {
          "recipe_id": {"type": "string", "format": "uuid"},
          "target_servings": {"type": "integer"}
        },
        "required": ["recipe_id", "target_servings"]
      }
    },
    {
      "name": "generate_work_order",
      "description": "Generate production work order with scaled ingredients, cooking steps, CCP checkpoints, and timeline.",
      "input_schema": {
        "type": "object",
        "properties": {
          "menu_plan_id": {"type": "string", "format": "uuid"},
          "site_id": {"type": "string", "format": "uuid"},
          "date": {"type": "string", "format": "date"},
          "meal_type": {"type": "string"}
        },
        "required": ["menu_plan_id", "site_id", "date", "meal_type"]
      }
    },
    {
      "name": "generate_haccp_checklist",
      "description": "Generate HACCP inspection checklist template for a site/date based on HACCP guide documents.",
      "input_schema": {
        "type": "object",
        "properties": {
          "site_id": {"type": "string", "format": "uuid"},
          "date": {"type": "string", "format": "date"},
          "checklist_type": {"type": "string", "enum": ["daily", "weekly"]},
          "meal_type": {"type": "string"}
        },
        "required": ["site_id", "date", "checklist_type"]
      }
    },
    {
      "name": "check_haccp_completion",
      "description": "Check HACCP checklist completion status for a site/date. Returns missing/overdue items.",
      "input_schema": {
        "type": "object",
        "properties": {
          "site_id": {"type": "string", "format": "uuid"},
          "date": {"type": "string", "format": "date"}
        },
        "required": ["site_id", "date"]
      }
    },
    {
      "name": "generate_audit_report",
      "description": "Generate HACCP audit report: checklists, CCP records, incidents, training for a period.",
      "input_schema": {
        "type": "object",
        "properties": {
          "site_id": {"type": "string", "format": "uuid"},
          "start_date": {"type": "string", "format": "date"},
          "end_date": {"type": "string", "format": "date"},
          "include_sections": {"type": "array", "items": {"type": "string", "enum": ["checklists","ccp_records","incidents","training"]}}
        },
        "required": ["site_id", "start_date", "end_date"]
      }
    },
    {
      "name": "query_dashboard",
      "description": "Get operational dashboard data: today's menu status, HACCP completion, alerts, recent activity.",
      "input_schema": {
        "type": "object",
        "properties": {
          "site_id": {"type": "string", "format": "uuid"},
          "date": {"type": "string", "format": "date"}
        },
        "required": ["site_id"]
      }
    }
  ]
}
```

---

## 3. API Endpoints

### 3.1 FastAPI (AI Gateway) - `/api/v1`

#### Chat & Agent
| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/chat` | Send message to AI agent (SSE streaming) | JWT |
| GET | `/chat/conversations` | List user conversations | JWT |
| GET | `/chat/conversations/{id}` | Get conversation detail | JWT |
| DELETE | `/chat/conversations/{id}` | Delete conversation | JWT |

#### Menu Plans
| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/menu-plans/generate` | AI generate menu plan | NUT, OPS |
| GET | `/menu-plans` | List menu plans (with filters) | NUT, OPS, KIT |
| GET | `/menu-plans/{id}` | Get menu plan detail | NUT, OPS, KIT |
| PUT | `/menu-plans/{id}` | Update menu plan | NUT |
| POST | `/menu-plans/{id}/validate` | Run nutrition/allergen validation | NUT, OPS |
| POST | `/menu-plans/{id}/confirm` | Confirm menu plan (with approval) | OPS |
| POST | `/menu-plans/{id}/revert` | Revert to previous version | NUT, OPS |

#### Recipes
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/recipes` | List/search recipes | ALL |
| GET | `/recipes/{id}` | Get recipe detail | ALL |
| POST | `/recipes` | Create recipe | NUT, ADM |
| PUT | `/recipes/{id}` | Update recipe (creates new version) | NUT, ADM |
| POST | `/recipes/{id}/scale` | Scale recipe for servings | NUT, KIT |
| POST | `/recipes/search` | Hybrid RAG search | ALL |

#### Work Orders
| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/work-orders/generate` | Generate work orders from menu plan | NUT, OPS |
| GET | `/work-orders` | List work orders (site/date filter) | KIT, NUT, OPS |
| GET | `/work-orders/{id}` | Get work order detail | KIT, NUT, OPS |
| PUT | `/work-orders/{id}/status` | Update work order status | KIT |

#### HACCP
| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/haccp/checklists/generate` | Generate checklist from template | QLT, OPS |
| GET | `/haccp/checklists` | List checklists (site/date filter) | QLT, OPS |
| GET | `/haccp/checklists/{id}` | Get checklist detail | QLT, OPS |
| POST | `/haccp/records` | Submit CCP record | QLT, KIT |
| GET | `/haccp/records` | List records (checklist filter) | QLT, OPS |
| POST | `/haccp/incidents` | Report incident | QLT, ALL |
| GET | `/haccp/incidents` | List incidents | QLT, OPS |
| PUT | `/haccp/incidents/{id}` | Update incident | QLT, OPS |
| POST | `/haccp/reports/audit` | Generate audit report | QLT, OPS |
| GET | `/haccp/completion-status` | Check daily completion | QLT, OPS |

#### Dashboard
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/dashboard/overview` | Today's operational overview | OPS, NUT |
| GET | `/dashboard/alerts` | Active alerts and notifications | ALL |

#### RAG Document Management
| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/documents/upload` | Upload and index document | ADM, NUT |
| GET | `/documents` | List indexed documents | ALL |
| DELETE | `/documents/{id}` | Remove document from index | ADM |

### 3.2 Additional CRUD Endpoints (FastAPI)

Frontend는 모든 데이터를 FastAPI를 통해 접근한다 (BaaS 없음).

#### Auth
| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/auth/login` | 로그인 (email + password → JWT) | Public |
| POST | `/auth/register` | 사용자 등록 | ADM |
| POST | `/auth/refresh` | JWT 갱신 | JWT |
| GET | `/auth/me` | 현재 사용자 정보 | JWT |

#### Master Data
| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/sites` | 현장 목록 | ALL |
| GET | `/sites/{id}` | 현장 상세 | ALL |
| POST | `/sites` | 현장 생성 | ADM |
| PUT | `/sites/{id}` | 현장 수정 | ADM |
| GET | `/items` | 식재료 목록/검색 | ALL |
| POST | `/items` | 식재료 등록 | ADM |
| PUT | `/items/{id}` | 식재료 수정 | ADM |
| GET | `/policies/nutrition` | 영양 정책 목록 | NUT, OPS, ADM |
| POST | `/policies/nutrition` | 영양 정책 생성 | OPS, ADM |
| GET | `/policies/allergen` | 알레르겐 정책 목록 | NUT, OPS, ADM |
| POST | `/policies/allergen` | 알레르겐 정책 생성 | OPS, ADM |
| GET | `/users` | 사용자 목록 | OPS, ADM |
| PUT | `/users/{id}` | 사용자 수정 | ADM |
| GET | `/audit-logs` | 감사 로그 조회 | OPS, ADM |

### 3.3 API Response Format

```typescript
// Success
{
  "success": true,
  "data": { ... },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 150
  }
}

// Error
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "영양 기준을 초과합니다",
    "details": { ... }
  }
}

// SSE Streaming (Chat)
data: {"type": "text_delta", "content": "식단을 생성하겠습니다..."}
data: {"type": "tool_call", "name": "generate_menu_plan", "status": "started"}
data: {"type": "tool_result", "name": "generate_menu_plan", "data": {...}}
data: {"type": "text_delta", "content": "2안을 생성했습니다. "}
data: {"type": "citations", "sources": [{"title": "...", "type": "..."}]}
data: {"type": "done"}
```

---

## 4. UI/UX Design

### 4.1 Layout Structure

```
┌──────────────────────────────────────────────────────────┐
│ [Logo] Food AI Agent    [Site Selector ▼]  [🔔] [User ▼] │
├────────┬─────────────────────────────────────────────────┤
│        │                                                 │
│  Nav   │              Main Content Area                  │
│        │                                                 │
│ [Dash] │  ┌─────────────────────────────────────────┐   │
│ [Menu] │  │                                         │   │
│ [Recp] │  │         Page Content                    │   │
│ [Ktch] │  │                                         │   │
│ [HACP] │  │                                         │   │
│ [Sett] │  │                                         │   │
│        │  │                                         │   │
│        │  └─────────────────────────────────────────┘   │
│        │                                                 │
│        │  ┌─────────────────────────────────────────┐   │
│        │  │         AI Chat Panel (expandable)       │   │
│        │  │  [💬 무엇을 도와드릴까요?          Send]  │   │
│        │  └─────────────────────────────────────────┘   │
├────────┴─────────────────────────────────────────────────┤
│ Footer (minimal)                                         │
└──────────────────────────────────────────────────────────┘
```

### 4.2 Screen Flows

#### 4.2.1 식단 설계실 (`/menu-studio`)

```
[식단 목록]
    │
    ├── [+ 새 식단 생성] ──> [AI 생성 Dialog]
    │                          │
    │                          ├── 현장 선택
    │                          ├── 기간 (시작~종료)
    │                          ├── 식사 유형 (조/중/석)
    │                          ├── 식수
    │                          ├── 예산/원가 목표
    │                          ├── 선호/금기 (자유 입력)
    │                          └── [AI 생성 시작] ──> Loading (SSE)
    │                                                    │
    │                                                    v
    │                                              [생성 결과]
    │                                                │
    │                                                ├── 안 1 / 안 2 (탭 전환)
    │                                                ├── 일별 식단표 (그리드)
    │                                                ├── 영양 요약 (차트)
    │                                                ├── 알레르겐 태그 표시
    │                                                └── [이 안 선택] / [재생성]
    │
    ├── [식단 상세] ──> [식단 편집 뷰]
    │                      │
    │                      ├── 캘린더/그리드 뷰 (일별 메뉴)
    │                      ├── 메뉴 항목 드래그/수정
    │                      ├── [검증 실행] ──> 영양/알레르겐/다양성 결과 패널
    │                      │                    ├── Pass ✓ / Warning ⚠ / Fail ✗
    │                      │                    └── 보정 추천 (AI)
    │                      ├── [확정 요청] ──> 승인자 선택 ──> 상태 변경 (review)
    │                      └── [버전 이력] ──> 이전 버전 비교/롤백
    │
    └── [승인 대기] ──> [확정/반려] (OPS 권한)
```

#### 4.2.2 레시피 라이브러리 (`/recipes`)

```
[레시피 검색]
    │
    ├── 검색바 (AI 하이브리드 검색)
    │     ├── 자연어 검색 ("매콤한 돼지고기 볶음")
    │     ├── 필터: 카테고리, 알레르겐 제외, 난이도
    │     └── 결과 목록 (카드 그리드)
    │           ├── 레시피명, 카테고리, 소요시간
    │           ├── 알레르겐 뱃지
    │           └── 매칭 점수 (관련도)
    │
    ├── [레시피 상세]
    │     ├── 기본 정보 (이름, 카테고리, 기준 인분)
    │     ├── 재료 목록 (알레르겐 하이라이트)
    │     ├── 조리 순서 (CCP 포인트 표시)
    │     ├── 영양 정보
    │     ├── [스케일링] ──> 목표 인분 입력 ──> 환산 결과
    │     │                    └── 조미료 보정 가이드
    │     └── [작업지시서 생성] ──> WorkOrder 미리보기 ──> 저장/인쇄
    │
    └── [레시피 등록/수정] (NUT, ADM)
          ├── 기본 정보 입력
          ├── 재료 추가 (Item 마스터 검색)
          ├── 조리 순서 편집 (CCP 포인트 추가)
          └── [저장] ──> 버전 자동 증가
```

#### 4.2.3 생산/조리 모드 (`/kitchen`)

```
[오늘의 작업지시서]
    │
    ├── 날짜/식사 선택
    ├── 작업지시서 목록 (카드)
    │     ├── 메뉴명, 식수, 상태
    │     └── 마감 시각 표시
    │
    ├── [작업지시서 상세]
    │     ├── 레시피명, 목표 식수
    │     ├── 환산된 재료 목록
    │     ├── 조리 순서 (체크리스트 형태)
    │     │     ├── [x] Step 1: ...
    │     │     ├── [!CCP] Step 3: 중심온도 75도 이상 확인 ──> 온도 입력
    │     │     └── [ ] Step 5: ...
    │     ├── 조미료 보정 노트
    │     └── [완료] ──> 상태 변경
    │
    └── [AI 질문] (우측 채팅)
          ├── "국이 너무 짠데 어떻게 하나요?"
          └── Agent: 보정 방법 + 근거 제시
```

#### 4.2.4 위생/HACCP (`/haccp`)

```
[HACCP 대시보드]
    │
    ├── 오늘 점검 현황 (완료/미완료/지연)
    ├── 미완료 체크리스트 알림
    │
    ├── [점검표]
    │     ├── [자동 생성] ──> 현장/날짜/유형 선택 ──> AI 생성
    │     ├── 점검표 목록 (상태 필터)
    │     └── [점검표 상세]
    │           ├── 체크 항목 목록
    │           │     ├── [x] 냉장고 온도 확인: __°C (입력)
    │           │     ├── [ ] 조리장 바닥 청소 상태
    │           │     └── [!] 보존식 보관 확인 (사진 첨부)
    │           └── [제출] ──> 완료 처리 + 감사 로그
    │
    ├── [CCP 기록]
    │     ├── 기록 입력 (온도/시간)
    │     ├── 부적합 시 시정조치 입력
    │     └── 사진 첨부 (선택)
    │
    ├── [사고/이벤트]
    │     ├── [신규 보고] ──> 유형/심각도/설명 입력
    │     │                    └── AI: 즉시 대응 단계 안내
    │     └── 이벤트 이력/상태 관리
    │
    └── [감사 리포트]
          ├── 기간/현장 선택
          └── [생성] ──> PDF 미리보기 ──> 다운로드
```

#### 4.2.5 운영 대시보드 (`/dashboard`)

```
┌─────────────────────────────────────────────────────┐
│  운영 대시보드                        2026-02-23 (월) │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ 오늘의 식단   │  │ HACCP 체크   │  │ 알림      │ │
│  │              │  │              │  │           │ │
│  │ A현장: 확정  │  │ 완료: 8/12   │  │ ⚠ 점검표  │ │
│  │ B현장: 검토중│  │ 지연: 2건    │  │   3건 미완│ │
│  │ C현장: 초안  │  │ 미시작: 2건  │  │ ⚠ 식단    │ │
│  └──────────────┘  └──────────────┘  │   승인대기│ │
│                                       └───────────┘ │
│  ┌──────────────────────────────────────────────┐   │
│  │ 이번주 현황                                    │   │
│  │                                              │   │
│  │ 식단 확정률: ████████░░ 80%                   │   │
│  │ HACCP 완료율: ██████░░░░ 60%                  │   │
│  │ 작업지시서 생성: 15/20                         │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │ 최근 활동                                      │   │
│  │ 10:30 NUT 김영양 - A현장 다음주 식단 생성       │   │
│  │ 10:15 QLT 박위생 - B현장 일일점검 완료          │   │
│  │ 09:50 KIT 이조리 - 중식 작업지시서 조회         │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 4.3 AI Chat Panel Design

```
┌─────────────────────────────────────────┐
│ AI Assistant           [현재: 식단 설계실] │
├─────────────────────────────────────────┤
│                                         │
│  🤖 안녕하세요! 식단 설계를 도와드리겠     │
│     습니다. 무엇을 하시겠어요?            │
│                                         │
│  👤 다음주 A현장 중식 5일 식단 짜줘       │
│     350식, 예산 3500원/식                │
│                                         │
│  🤖 A현장 중식 식단을 생성하겠습니다.      │
│                                         │
│     ⏳ 식단 생성 중...                   │
│     ✅ 영양 검증 완료                    │
│     ✅ 알레르겐 태깅 완료                 │
│                                         │
│     📋 2안을 생성했습니다.               │
│                                         │
│     [안 1 보기] [안 2 보기]              │
│                                         │
│     근거: A현장 영양정책(v2.1),          │
│           표준레시피DB (23건 참조)        │
│                                         │
│     ⚠ 수요일 나트륨 기준 초과 (2,150mg)  │
│       → 국 변경 추천: 미역국→맑은콩나물국 │
│                                         │
├─────────────────────────────────────────┤
│ [메시지 입력...]                  [전송] │
└─────────────────────────────────────────┘
```

### 4.4 Component Library (shadcn/ui based)

| Component | Usage | Notes |
|---|---|---|
| `DataTable` | 식단 목록, 레시피 목록, 점검표 목록 | 정렬/필터/페이지네이션 |
| `Calendar` | 식단 캘린더 뷰, HACCP 일정 | 일/주 뷰 전환 |
| `Card` | 대시보드 위젯, 작업지시서 카드 | 상태 뱃지 포함 |
| `Dialog/Sheet` | AI 생성 폼, 상세 보기 | Sheet for side panels |
| `Badge` | 알레르겐 태그, 상태 표시 | 색상 코드: pass/warn/fail |
| `Tabs` | 식단 안 전환, 상세 탭 | |
| `Command` | AI 검색 (레시피) | Command palette style |
| `Chart` | 영양 차트, 대시보드 KPI | Recharts 기반 |
| `Toast` | 알림, 성공/에러 메시지 | |
| `Checkbox` | HACCP 점검, 작업지시서 체크 | |

---

## 5. Security & Access Control

### 5.1 RBAC Matrix (MVP 1)

| Resource | NUT | KIT | QLT | OPS | ADM |
|---|---|---|---|---|---|
| Dashboard | R | R (own site) | R (own site) | RW | RW |
| Menu Plans | CRUD | R | - | CRUD + Approve | CRUD |
| Recipes | CRUD | R | - | R | CRUD |
| Work Orders | CR | R + Update Status | - | R | CRUD |
| HACCP Checklists | - | R | CRUD | R | CRUD |
| HACCP Records | - | CR | CRUD | R | CRUD |
| HACCP Incidents | - | CR | CRUD | RW | CRUD |
| Sites | R | R (own) | R (own) | R | CRUD |
| Items | R | R | R | R | CRUD |
| Policies | R | - | R | RW | CRUD |
| Users | - | - | - | R | CRUD |
| Audit Logs | R (own) | R (own) | R (own) | R | R |
| AI Chat | RW | RW | RW | RW | RW |

R=Read, C=Create, U=Update, D=Delete

### 5.2 Authentication (JWT)

```python
# FastAPI Auth Flow
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT payload: {"sub": user_id, "role": "NUT", "site_ids": [...], "exp": ...}
# Access token: 30 min, Refresh token: 7 days

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user = await db.get(User, payload["sub"])
    return user

def require_role(*roles: str):
    async def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return Depends(checker)
```

### 5.3 Data Isolation

- 서비스 레이어에서 모든 쿼리에 `site_id` 필터 적용 (WHERE clause)
- 사용자는 `users.site_ids[]`에 포함된 현장만 접근 가능
- ADM/OPS는 다현장 접근 가능 (정책에 따라)
- AI Agent는 사용자 권한 내에서만 데이터 접근/수정

```python
# Service layer site filtering pattern
async def get_menu_plans(db: AsyncSession, user: User, site_id: UUID):
    if site_id not in user.site_ids and user.role not in ("ADM", "OPS"):
        raise HTTPException(403, "No access to this site")
    query = select(MenuPlan).where(MenuPlan.site_id == site_id)
    result = await db.execute(query)
    return result.scalars().all()
```

### 5.4 Audit Trail

모든 "확정/수정/삭제" 작업은 `audit_logs` 테이블에 자동 기록:
- 사용자 ID, 시간, 액션, 변경 내용
- AI가 관여한 경우 `ai_context`에 모델/프롬프트/소스 기록

---

## 6. Project Structure

### 6.1 Frontend (Next.js 14)

```
food-ai-agent-web/
├── app/
│   ├── layout.tsx                 # Root layout (providers, nav)
│   ├── page.tsx                   # Redirect to /dashboard
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── layout.tsx
│   ├── (main)/
│   │   ├── layout.tsx             # Main layout (sidebar, chat panel)
│   │   ├── dashboard/page.tsx
│   │   ├── menu-studio/
│   │   │   ├── page.tsx           # Menu plan list
│   │   │   ├── [id]/page.tsx      # Menu plan detail/edit
│   │   │   └── new/page.tsx       # AI generation flow
│   │   ├── recipes/
│   │   │   ├── page.tsx           # Recipe search/list
│   │   │   └── [id]/page.tsx      # Recipe detail
│   │   ├── kitchen/
│   │   │   └── page.tsx           # Work orders view
│   │   ├── haccp/
│   │   │   ├── page.tsx           # HACCP dashboard
│   │   │   ├── checklists/
│   │   │   │   └── [id]/page.tsx
│   │   │   ├── incidents/
│   │   │   │   └── page.tsx
│   │   │   └── reports/page.tsx
│   │   └── settings/
│   │       ├── page.tsx
│   │       ├── sites/page.tsx
│   │       ├── items/page.tsx
│   │       ├── policies/page.tsx
│   │       └── users/page.tsx
├── components/
│   ├── ui/                        # shadcn/ui components
│   ├── layout/
│   │   ├── sidebar.tsx
│   │   ├── header.tsx
│   │   └── site-selector.tsx
│   ├── chat/
│   │   ├── chat-panel.tsx
│   │   ├── chat-message.tsx
│   │   ├── chat-input.tsx
│   │   └── tool-call-display.tsx
│   ├── menu/
│   │   ├── menu-plan-table.tsx
│   │   ├── menu-calendar.tsx
│   │   ├── menu-generation-form.tsx
│   │   ├── nutrition-chart.tsx
│   │   ├── allergen-badge.tsx
│   │   └── validation-panel.tsx
│   ├── recipe/
│   │   ├── recipe-search.tsx
│   │   ├── recipe-card.tsx
│   │   ├── recipe-detail.tsx
│   │   ├── recipe-scaler.tsx
│   │   └── work-order-view.tsx
│   ├── haccp/
│   │   ├── checklist-form.tsx
│   │   ├── ccp-record-input.tsx
│   │   ├── incident-form.tsx
│   │   └── audit-report.tsx
│   └── dashboard/
│       ├── overview-cards.tsx
│       ├── weekly-status.tsx
│       └── activity-feed.tsx
├── lib/
│   ├── http.ts                    # FastAPI fetch wrapper (base URL, headers, error handling)
│   ├── api.ts                     # API endpoint functions (typed)
│   ├── auth.ts                    # JWT token management (login, refresh, storage)
│   ├── hooks/                     # Custom React hooks
│   │   ├── use-chat.ts
│   │   ├── use-menu-plans.ts
│   │   ├── use-recipes.ts
│   │   └── use-haccp.ts
│   ├── stores/                    # Zustand stores
│   │   ├── site-store.ts
│   │   └── chat-store.ts
│   └── utils/
│       ├── allergen.ts
│       ├── nutrition.ts
│       └── format.ts
├── types/
│   └── index.ts                   # TypeScript type definitions
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

### 6.2 Backend (FastAPI)

```
food-ai-agent-api/
├── app/
│   ├── main.py                    # FastAPI app entry
│   ├── config.py                  # Settings (env vars)
│   ├── dependencies.py            # Dependency injection
│   ├── auth/
│   │   ├── jwt.py                 # JWT token create/verify (python-jose)
│   │   ├── oauth2.py              # OAuth2PasswordBearer scheme
│   │   ├── password.py            # Password hashing (passlib + bcrypt)
│   │   └── dependencies.py        # get_current_user, require_role Depends
│   ├── middleware/
│   │   ├── rbac.py                # Role-based access check
│   │   └── audit.py               # Audit log middleware
│   ├── routers/
│   │   ├── auth.py                # /api/v1/auth (login, register, refresh, me)
│   │   ├── chat.py                # /api/v1/chat
│   │   ├── menu_plans.py          # /api/v1/menu-plans
│   │   ├── recipes.py             # /api/v1/recipes
│   │   ├── work_orders.py         # /api/v1/work-orders
│   │   ├── haccp.py               # /api/v1/haccp
│   │   ├── dashboard.py           # /api/v1/dashboard
│   │   ├── documents.py           # /api/v1/documents
│   │   ├── sites.py               # /api/v1/sites
│   │   ├── items.py               # /api/v1/items
│   │   ├── policies.py            # /api/v1/policies
│   │   ├── users.py               # /api/v1/users
│   │   └── audit_logs.py          # /api/v1/audit-logs
│   ├── agents/
│   │   ├── orchestrator.py        # Agent orchestrator
│   │   ├── intent_router.py       # Intent classification
│   │   ├── prompts/
│   │   │   ├── system.py          # System prompts per agent
│   │   │   ├── menu.py
│   │   │   ├── recipe.py
│   │   │   └── haccp.py
│   │   └── tools/
│   │       ├── registry.py        # Tool registry
│   │       ├── menu_tools.py      # Menu generation/validation tools
│   │       ├── recipe_tools.py    # Recipe search/scale tools
│   │       ├── haccp_tools.py     # HACCP checklist/record tools
│   │       └── dashboard_tools.py # Dashboard query tools
│   ├── services/
│   │   ├── menu_service.py        # Menu plan business logic
│   │   ├── recipe_service.py      # Recipe business logic
│   │   ├── haccp_service.py       # HACCP business logic
│   │   ├── nutrition_service.py   # Nutrition calculation
│   │   ├── allergen_service.py    # Allergen detection
│   │   └── audit_service.py       # Audit log service
│   ├── rag/
│   │   ├── pipeline.py            # RAG pipeline orchestration
│   │   ├── loader.py              # Document loader
│   │   ├── chunker.py             # Text chunking
│   │   ├── embedder.py            # Embedding generation
│   │   └── retriever.py           # Hybrid search (keyword + vector)
│   ├── db/
│   │   ├── database.py            # AsyncEngine, async_sessionmaker 설정
│   │   ├── base.py                # DeclarativeBase (SQLAlchemy)
│   │   └── session.py             # get_db Depends (async session)
│   ├── models/
│   │   ├── orm/                   # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── site.py
│   │   │   ├── item.py
│   │   │   ├── policy.py
│   │   │   ├── menu_plan.py
│   │   │   ├── recipe.py
│   │   │   ├── work_order.py
│   │   │   ├── haccp.py
│   │   │   ├── audit_log.py
│   │   │   └── conversation.py
│   │   └── schemas/               # Pydantic request/response models
│   │       ├── common.py
│   │       ├── auth.py
│   │       ├── menu.py
│   │       ├── recipe.py
│   │       └── haccp.py
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/                  # Migration files
├── tests/
│   ├── test_agents/
│   ├── test_services/
│   └── test_routers/
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

## 7. Key Implementation Notes

### 7.1 SSE Streaming for AI Chat
- FastAPI `StreamingResponse` with `text/event-stream` content type
- Claude API streaming → parse tool calls → execute → continue stream
- Frontend uses `EventSource` or `fetch` with `ReadableStream`

### 7.2 Menu Plan Generation Flow
1. User submits generation parameters
2. Load site rules, nutrition policy, allergen policy
3. Search existing recipes (RAG) matching constraints
4. Call Claude with tools: generate meal combinations
5. Validate nutrition (tool call within agent loop)
6. Tag allergens (tool call)
7. Return 2+ alternatives with validation results

### 7.3 RAG Document Ingestion
1. Upload document via `/documents/upload`
2. Extract text (PDF: PyMuPDF, DOCX: python-docx)
3. Split into chunks (1000 chars, 200 overlap)
4. Generate embeddings (batch)
5. Store in `recipe_documents` with metadata

### 7.4 HACCP Overdue Alert Logic
- APScheduler (또는 Celery Beat) cron job이 설정된 시간에 점검
- If `haccp_checklists.status = 'pending'` past deadline → mark `overdue`
- Push notification to QLT and OPS users

---

## 8. Design Decisions Log

| # | Decision | Options Considered | Choice | Rationale |
|---|---|---|---|---|
| D-001 | Vector DB | Pinecone, Weaviate, pgvector | pgvector (PostgreSQL 확장 직접) | 별도 벡터 DB 불필요, 단일 DB 운영 |
| D-002 | Agent Framework | LangChain, LlamaIndex, Custom | Custom | 도메인 특화 제어, 의존성 최소화 |
| D-003 | Multi-site isolation | Separate DBs, Schema per site, RLS, App-layer | App-layer (서비스 레이어 site_id 필터) | 유연성, ORM 통합 용이, RLS 없이 단순 관리 |
| D-004 | Streaming protocol | WebSocket, SSE, Polling | SSE | 단방향 충분, HTTP 호환, 구현 단순 |
| D-005 | Embedding model | Voyage, OpenAI ada-3 | OpenAI text-embedding-3-small | 비용 효율, 1536 dim, 한국어 성능 |
| D-006 | Frontend state | Redux, Zustand, Jotai | Zustand + TanStack Query | 경량 + 서버 상태 캐싱 분리 |
| D-007 | Auth | bkend.ai Auth, NextAuth, Custom JWT | Custom JWT (python-jose + bcrypt) | FastAPI 통합, 전체 제어, 외부 의존 최소화 |
| D-008 | ORM | Raw SQL, SQLAlchemy, Tortoise | SQLAlchemy 2.0 async + Alembic | 타입 안전, 마이그레이션, 생태계 성숙 |
| D-009 | File Storage | bkend.ai Storage, S3, Local | 로컬 (초기) → MinIO (확장) | 초기 단순, S3 호환 API로 무중단 전환 |
| D-010 | Scheduler | bkend.ai scheduled, Celery, APScheduler | APScheduler (초기) / Celery Beat (확장) | 단일 프로세스 시작, 필요 시 분산 전환 |

---

## 9. References

- [food-ai-agent.plan.md](../../01-plan/features/food-ai-agent.plan.md) - MVP 1 Plan
- [food_ai-agent_req.md](../../../food_ai-agent_req.md) - Full Requirements
- Anthropic Claude Tool Use Documentation
- SQLAlchemy 2.0 Async Documentation
- Alembic Migration Documentation
- python-jose JWT Documentation
- Next.js 14 App Router Documentation
- pgvector Documentation
