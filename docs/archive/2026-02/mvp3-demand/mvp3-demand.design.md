# MVP 3 Design: 수요예측/원가최적화/클레임 관리

- **문서 버전**: 1.0.0
- **작성일**: 2026-02-24
- **PDCA 단계**: Design
- **참조 Plan**: `docs/01-plan/features/mvp3-demand.plan.md`

---

## 1. DB 스키마 설계 (SQLAlchemy 2.0 ORM)

### 1.1 신규 ORM 파일 구조

```
food-ai-agent-api/app/models/orm/
  ├── forecast.py      # DemandForecast, ActualHeadcount, SiteEvent
  ├── waste.py         # WasteRecord, MenuPreference
  ├── cost.py          # CostAnalysis
  └── claim.py         # Claim, ClaimAction
```

---

### 1.2 `forecast.py`

```python
# food-ai-agent-api/app/models/orm/forecast.py

from sqlalchemy import Column, String, Integer, Numeric, Date, Text, TIMESTAMP, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class DemandForecast(Base):
    """식수 예측 결과 (site별 날짜+식사별)"""
    __tablename__ = "demand_forecasts"

    id             = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id        = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    forecast_date  = Column(Date, nullable=False)                        # 예측 대상 날짜
    meal_type      = Column(String(20), nullable=False)                  # breakfast/lunch/dinner/snack
    predicted_min  = Column(Integer, nullable=False)                     # 예측 식수 하한
    predicted_mid  = Column(Integer, nullable=False)                     # 예측 식수 중앙값
    predicted_max  = Column(Integer, nullable=False)                     # 예측 식수 상한
    confidence_pct = Column(Numeric(5, 2), server_default="70.0")       # 신뢰도 (%)
    model_used     = Column(String(50), server_default="'wma'")         # wma / prophet / lgbm
    input_factors  = Column(JSONB, server_default="{}")                  # 예측에 사용된 입력 인자
    risk_factors   = Column(JSONB, server_default="[]")                  # 리스크 요인 목록
    generated_at   = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    created_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index("ix_demand_forecasts_site_date", "site_id", "forecast_date"),
    )


class ActualHeadcount(Base):
    """실제 식수/배식 실적 (잔반 계산 기준)"""
    __tablename__ = "actual_headcounts"

    id           = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id      = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    record_date  = Column(Date, nullable=False)
    meal_type    = Column(String(20), nullable=False)
    planned      = Column(Integer, nullable=False)                       # 계획 식수
    actual       = Column(Integer, nullable=False)                       # 실제 식수
    served       = Column(Integer)                                       # 실제 배식량 (접시 수)
    notes        = Column(Text)
    recorded_at  = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    recorded_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index("ix_actual_headcounts_site_date", "site_id", "record_date"),
    )


class SiteEvent(Base):
    """현장 이벤트 캘린더 (식수 예측 보정용)"""
    __tablename__ = "site_events"

    id                = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id           = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    event_date        = Column(Date, nullable=False)
    event_type        = Column(String(50), nullable=False)               # holiday / school_trip / corporate / closure / other
    event_name        = Column(String(200))
    adjustment_factor = Column(Numeric(4, 2), server_default="1.0")     # 1.0=정상, 0.7=70%, 0.0=휴무
    affects_meal_types = Column(JSONB, server_default='["lunch"]')      # 영향받는 식사 유형
    notes             = Column(Text)
    created_at        = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    created_by        = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index("ix_site_events_site_date", "site_id", "event_date"),
    )
```

---

### 1.3 `waste.py`

```python
# food-ai-agent-api/app/models/orm/waste.py

from sqlalchemy import Column, String, Integer, Numeric, Date, Text, TIMESTAMP, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class WasteRecord(Base):
    """잔반 기록 (날짜·메뉴별)"""
    __tablename__ = "waste_records"

    id                 = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id            = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    record_date        = Column(Date, nullable=False)
    meal_type          = Column(String(20), nullable=False)
    menu_plan_item_id  = Column(UUID(as_uuid=True), ForeignKey("menu_plan_items.id"))  # 선택
    recipe_id          = Column(UUID(as_uuid=True), ForeignKey("recipes.id"))          # 선택
    item_name          = Column(String(200), nullable=False)                            # 메뉴명 (비정규화)
    waste_kg           = Column(Numeric(8, 3))                                          # 잔반량 (kg)
    waste_pct          = Column(Numeric(5, 2))                                          # 잔반률 (%)
    served_count       = Column(Integer)                                                # 배식 인원
    notes              = Column(Text)
    recorded_at        = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    recorded_by        = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index("ix_waste_records_site_date", "site_id", "record_date"),
    )


class MenuPreference(Base):
    """메뉴 선호도 누적 (잔반 피드백 → 식단 생성 가중치)"""
    __tablename__ = "menu_preferences"

    id              = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id         = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    recipe_id       = Column(UUID(as_uuid=True), ForeignKey("recipes.id"), nullable=False)
    # preference_score: -1.0 (매우 비선호) ~ 1.0 (매우 선호), 누적 EWMA
    preference_score = Column(Numeric(4, 3), server_default="0.0")
    waste_avg_pct   = Column(Numeric(5, 2), server_default="0.0")       # 평균 잔반률
    serve_count     = Column(Integer, server_default="0")                # 제공 횟수
    last_served     = Column(Date)
    updated_at      = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        Index("ix_menu_preferences_site_recipe", "site_id", "recipe_id", unique=True),
    )
```

---

### 1.4 `cost.py`

```python
# food-ai-agent-api/app/models/orm/cost.py

from sqlalchemy import Column, String, Numeric, Date, Text, TIMESTAMP, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class CostAnalysis(Base):
    """원가 분석 결과 (식단 확정/실발주 원가 추적)"""
    __tablename__ = "cost_analyses"

    id               = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id          = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    menu_plan_id     = Column(UUID(as_uuid=True), ForeignKey("menu_plans.id"))           # 분석 대상 식단
    analysis_type    = Column(String(30), nullable=False)                                # simulation / confirmed / actual
    target_cost      = Column(Numeric(12, 2))                                            # 목표 원가 (1인, KRW)
    estimated_cost   = Column(Numeric(12, 2))                                            # 시뮬레이션 원가
    actual_cost      = Column(Numeric(12, 2))                                            # 실발주 원가 (확정 후)
    headcount        = Column(Integer)                                                   # 기준 식수
    cost_breakdown   = Column(JSONB, server_default="{}")                               # 품목별 원가 상세
    variance_pct     = Column(Numeric(7, 2))                                             # 목표 대비 편차 (%)
    alert_triggered  = Column(String(10))                                                # none / warning / critical
    suggestions      = Column(JSONB, server_default="[]")                               # AI 대체 제안 목록
    created_at       = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    created_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index("ix_cost_analyses_site", "site_id"),
        Index("ix_cost_analyses_menu_plan", "menu_plan_id"),
    )
```

---

### 1.5 `claim.py`

```python
# food-ai-agent-api/app/models/orm/claim.py

from sqlalchemy import Column, String, Integer, Boolean, Text, TIMESTAMP, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


CLAIM_CATEGORIES = ["맛/품질", "이물", "양/분량", "온도", "알레르겐", "위생/HACCP", "서비스", "기타"]
CLAIM_SEVERITIES = ["low", "medium", "high", "critical"]
CLAIM_STATUSES   = ["open", "investigating", "action_taken", "closed", "recurred"]


class Claim(Base):
    """클레임 원장"""
    __tablename__ = "claims"

    id              = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    site_id         = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False)
    incident_date   = Column(TIMESTAMP(timezone=True), nullable=False)                  # 발생 일시
    category        = Column(String(30), nullable=False)                                # CLAIM_CATEGORIES
    severity        = Column(String(20), nullable=False, server_default="'medium'")     # CLAIM_SEVERITIES
    status          = Column(String(30), nullable=False, server_default="'open'")       # CLAIM_STATUSES
    title           = Column(String(300), nullable=False)
    description     = Column(Text, nullable=False)
    menu_plan_id    = Column(UUID(as_uuid=True), ForeignKey("menu_plans.id"))           # 관련 식단 (선택)
    recipe_id       = Column(UUID(as_uuid=True), ForeignKey("recipes.id"))             # 관련 레시피 (선택)
    lot_number      = Column(String(100))                                               # 관련 로트 번호 (선택)
    reporter_name   = Column(String(100))                                               # 접수자 이름
    reporter_role   = Column(String(20))                                                # CS / OPS / KIT
    haccp_incident_id = Column(UUID(as_uuid=True), ForeignKey("haccp_incidents.id"))   # SAFE-002 연동
    ai_hypotheses   = Column(JSONB, server_default="[]")                               # Claude 원인 가설 목록
    root_cause      = Column(Text)                                                      # 확정 원인 (사람 입력)
    is_recurring    = Column(Boolean, server_default="false")
    recurrence_count = Column(Integer, server_default="0")
    resolved_at     = Column(TIMESTAMP(timezone=True))
    created_at      = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    created_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    updated_at      = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        Index("ix_claims_site_date", "site_id", "incident_date"),
        Index("ix_claims_category_severity", "category", "severity"),
        Index("ix_claims_status", "status"),
    )


class ClaimAction(Base):
    """클레임 조치 이력"""
    __tablename__ = "claim_actions"

    id           = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    claim_id     = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    action_type  = Column(String(50), nullable=False)                                  # recipe_fix / vendor_warning / staff_training / haccp_update / other
    description  = Column(Text, nullable=False)
    assignee_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    assignee_role = Column(String(20))                                                  # NUT / PUR / KIT / QLT
    due_date     = Column(TIMESTAMP(timezone=True))
    status       = Column(String(20), server_default="'pending'")                     # pending / in_progress / done
    result_notes = Column(Text)
    completed_at = Column(TIMESTAMP(timezone=True))
    created_at   = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    created_by   = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    __table_args__ = (
        Index("ix_claim_actions_claim_id", "claim_id"),
    )
```

---

## 2. Alembic 마이그레이션

```
food-ai-agent-api/alembic/versions/003_mvp3_demand_cost_claim.py
```

```python
"""MVP3: demand_forecasts, actual_headcounts, site_events, waste_records,
         menu_preferences, cost_analyses, claims, claim_actions

Revision ID: 003
Revises: 002
Create Date: 2026-02-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '003'
down_revision = '002'


def upgrade():
    # demand_forecasts
    op.create_table('demand_forecasts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('site_id', UUID(as_uuid=True), sa.ForeignKey('sites.id'), nullable=False),
        sa.Column('forecast_date', sa.Date, nullable=False),
        sa.Column('meal_type', sa.String(20), nullable=False),
        sa.Column('predicted_min', sa.Integer, nullable=False),
        sa.Column('predicted_mid', sa.Integer, nullable=False),
        sa.Column('predicted_max', sa.Integer, nullable=False),
        sa.Column('confidence_pct', sa.Numeric(5,2), server_default='70.0'),
        sa.Column('model_used', sa.String(50), server_default="'wma'"),
        sa.Column('input_factors', JSONB, server_default='{}'),
        sa.Column('risk_factors', JSONB, server_default='[]'),
        sa.Column('generated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id')),
    )
    op.create_index('ix_demand_forecasts_site_date', 'demand_forecasts', ['site_id', 'forecast_date'])

    # actual_headcounts
    op.create_table('actual_headcounts', ...)  # same pattern

    # site_events
    op.create_table('site_events', ...)

    # waste_records
    op.create_table('waste_records', ...)

    # menu_preferences
    op.create_table('menu_preferences', ...)
    op.create_index('ix_menu_preferences_site_recipe', 'menu_preferences',
                    ['site_id', 'recipe_id'], unique=True)

    # cost_analyses
    op.create_table('cost_analyses', ...)

    # claims
    op.create_table('claims', ...)

    # claim_actions
    op.create_table('claim_actions', ...)


def downgrade():
    for table in ['claim_actions', 'claims', 'cost_analyses',
                  'menu_preferences', 'waste_records', 'site_events',
                  'actual_headcounts', 'demand_forecasts']:
        op.drop_table(table)
```

---

## 3. Pydantic 스키마

```
food-ai-agent-api/app/models/schemas/
  ├── forecast.py
  ├── waste.py
  ├── cost.py
  └── claim.py
```

### 3.1 `forecast.py` 스키마 요약

```python
class ForecastRequest(BaseModel):
    site_id: UUID
    forecast_date: date
    meal_type: str
    model: str = "wma"

class ForecastResponse(BaseModel):
    id: UUID
    site_id: UUID
    forecast_date: date
    meal_type: str
    predicted_min: int
    predicted_mid: int
    predicted_max: int
    confidence_pct: float
    risk_factors: list[str]
    model_used: str
    generated_at: datetime

class ActualHeadcountCreate(BaseModel):
    site_id: UUID
    record_date: date
    meal_type: str
    planned: int
    actual: int
    served: int | None = None
    notes: str | None = None

class SiteEventCreate(BaseModel):
    site_id: UUID
    event_date: date
    event_type: str  # holiday / school_trip / corporate / closure / other
    event_name: str | None = None
    adjustment_factor: float = 1.0
    affects_meal_types: list[str] = ["lunch"]
    notes: str | None = None
```

### 3.2 `waste.py` 스키마 요약

```python
class WasteRecordCreate(BaseModel):
    site_id: UUID
    record_date: date
    meal_type: str
    item_name: str
    menu_plan_item_id: UUID | None = None
    recipe_id: UUID | None = None
    waste_kg: float | None = None
    waste_pct: float | None = None
    served_count: int | None = None
    notes: str | None = None

class MenuPreferenceUpdate(BaseModel):
    recipe_id: UUID
    preference_score: float  # -1.0 ~ 1.0
    waste_pct: float | None = None
```

### 3.3 `cost.py` 스키마 요약

```python
class CostSimulateRequest(BaseModel):
    site_id: UUID
    menu_plan_id: UUID
    target_cost_per_meal: float  # KRW
    headcount: int

class CostSimulateResponse(BaseModel):
    menu_plan_id: UUID
    estimated_cost: float
    target_cost: float
    variance_pct: float
    alert_triggered: str  # none / warning / critical
    cost_breakdown: list[dict]
    suggestions: list[dict]
    analysis_id: UUID
```

### 3.4 `claim.py` 스키마 요약

```python
class ClaimCreate(BaseModel):
    site_id: UUID
    incident_date: datetime
    category: str
    severity: str = "medium"
    title: str
    description: str
    menu_plan_id: UUID | None = None
    recipe_id: UUID | None = None
    lot_number: str | None = None
    reporter_name: str | None = None
    reporter_role: str | None = None

class ClaimResponse(BaseModel):
    id: UUID
    site_id: UUID
    incident_date: datetime
    category: str
    severity: str
    status: str
    title: str
    description: str
    ai_hypotheses: list[dict]
    root_cause: str | None
    is_recurring: bool
    recurrence_count: int
    actions: list["ClaimActionResponse"]
    created_at: datetime

class ClaimActionCreate(BaseModel):
    action_type: str  # recipe_fix / vendor_warning / staff_training / haccp_update / other
    description: str
    assignee_role: str  # NUT / PUR / KIT / QLT
    assignee_id: UUID | None = None
    due_date: datetime | None = None
```

---

## 4. API 엔드포인트 상세 설계

### 4.1 `routers/forecast.py` — 수요예측

| Method | Path | Handler | Auth |
|--------|------|---------|------|
| GET | `/api/v1/forecast/headcount` | `list_forecasts` | OPS/NUT/KIT |
| POST | `/api/v1/forecast/headcount` | `create_forecast` | OPS/NUT |
| POST | `/api/v1/forecast/actual` | `record_actual` | KIT/NUT |
| GET | `/api/v1/forecast/actual` | `list_actuals` | OPS/NUT |
| GET | `/api/v1/site-events` | `list_events` | ALL |
| POST | `/api/v1/site-events` | `create_event` | OPS/NUT |
| PUT | `/api/v1/site-events/{id}` | `update_event` | OPS/NUT |
| DELETE | `/api/v1/site-events/{id}` | `delete_event` | OPS |

```python
# routers/forecast.py (핵심 로직)
@router.post("/headcount", response_model=ForecastResponse)
async def create_forecast(
    req: ForecastRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_roles(["OPS", "NUT"])),
):
    # 1. 과거 실적 조회 (최근 8주)
    actuals = await get_recent_actuals(db, req.site_id, req.meal_type, weeks=8)
    # 2. 이벤트 보정 계수 조회
    event = await get_event_on_date(db, req.site_id, req.forecast_date)
    # 3. WMA 예측 실행
    result = run_wma_forecast(actuals, event_factor=event.adjustment_factor if event else 1.0)
    # 4. DB 저장 및 반환
    forecast = DemandForecast(site_id=req.site_id, ...)
    db.add(forecast)
    await db.flush()
    return ForecastResponse.model_validate(forecast)
```

### 4.2 `routers/waste.py` — 잔반 관리

| Method | Path | Handler | Auth |
|--------|------|---------|------|
| POST | `/api/v1/waste/records` | `create_waste_record` | KIT/NUT |
| GET | `/api/v1/waste/records` | `list_waste_records` | OPS/NUT/KIT |
| GET | `/api/v1/waste/summary` | `waste_summary` | OPS/NUT |
| PUT | `/api/v1/waste/preferences/{site_id}` | `update_preferences` | NUT |
| GET | `/api/v1/waste/preferences/{site_id}` | `get_preferences` | NUT/OPS |

### 4.3 `routers/cost.py` — 원가 최적화

| Method | Path | Handler | Auth |
|--------|------|---------|------|
| POST | `/api/v1/cost/simulate` | `simulate_cost` | OPS/NUT/PUR |
| GET | `/api/v1/cost/analyses` | `list_analyses` | OPS/NUT/PUR |
| GET | `/api/v1/cost/analyses/{id}` | `get_analysis` | OPS/NUT/PUR |
| GET | `/api/v1/cost/trend` | `cost_trend` | OPS |

### 4.4 `routers/claims.py` — 클레임 관리

| Method | Path | Handler | Auth |
|--------|------|---------|------|
| GET | `/api/v1/claims` | `list_claims` | CS/OPS |
| POST | `/api/v1/claims` | `create_claim` | CS/OPS/KIT |
| GET | `/api/v1/claims/{id}` | `get_claim` | CS/OPS |
| PUT | `/api/v1/claims/{id}/status` | `update_status` | CS/OPS |
| POST | `/api/v1/claims/{id}/actions` | `add_action` | CS/OPS |
| GET | `/api/v1/claims/{id}/actions` | `list_actions` | CS/OPS |
| GET | `/api/v1/reports/quality` | `quality_report` | OPS |

### 4.5 `routers/dashboard.py` 확장 (기존 파일 수정)

```python
# GET /api/v1/dashboard/forecast  — 수요예측 위젯
# GET /api/v1/dashboard/cost      — 원가 위젯
# GET /api/v1/dashboard/quality   — 클레임 위젯
# (기존 query_dashboard Tool의 데이터 소스 확장)
```

---

## 5. Agent Tools 설계

### 5.1 신규 Tool 파일

```
food-ai-agent-api/app/agents/tools/
  └── demand_tools.py    # forecast_headcount, record_waste, simulate_cost,
                         # register_claim, analyze_claim, track_claim_action
```

### 5.2 `demand_tools.py` 함수 시그니처

```python
async def forecast_headcount(
    db: AsyncSession,
    site_id: str,
    forecast_date: str,
    meal_type: str,
    model: str = "wma",
    force_recalc: bool = False,
) -> dict:
    """WMA 기반 식수 예측 + 이벤트 보정"""
    # 1. 과거 실적 조회 (actual_headcounts, 최근 8주)
    # 2. 이벤트 계수 (site_events)
    # 3. 선호도 기반 리스크 (menu_preferences, 잔반률 높은 경우)
    # 4. WMA 계산 + 신뢰도 추정
    # 5. DemandForecast 저장
    return {"predicted_mid": ..., "predicted_min": ..., "predicted_max": ...,
            "confidence_pct": ..., "risk_factors": [...]}


async def record_waste(
    db: AsyncSession,
    site_id: str,
    record_date: str,
    meal_type: str,
    waste_items: list[dict],  # [{item_name, waste_pct, recipe_id?}]
    recorded_by: UUID | None = None,
) -> dict:
    """잔반 기록 저장 + MenuPreference EWMA 업데이트"""
    # 1. WasteRecord 저장 (복수)
    # 2. MenuPreference.preference_score EWMA 갱신
    #    new_score = 0.7 * old_score + 0.3 * (-waste_pct / 50)  # 50%를 0점 기준
    # 3. 잔반률 > 30% → 식단 생성 시 빈도 경고 플래그 설정
    return {"saved_count": ..., "preferences_updated": [...]}


async def simulate_cost(
    db: AsyncSession,
    site_id: str,
    menu_plan_id: str,
    target_cost_per_meal: float,
    headcount: int,
    suggest_alternatives: bool = True,
) -> dict:
    """식단 원가 시뮬레이션 + MVP2 purchase_tools 연동"""
    # 1. BOM 조회 (Bom 또는 calculate_bom 재사용)
    # 2. 현재 단가 × 수량 → 총 원가 계산
    # 3. target vs actual 편차 계산
    # 4. 원가 초과 품목 식별 → suggest_alternatives Tool 호출 (MVP2)
    # 5. CostAnalysis 저장
    return {"estimated_cost": ..., "variance_pct": ..., "alert_triggered": ...,
            "suggestions": [...], "analysis_id": ...}


async def register_claim(
    db: AsyncSession,
    site_id: str,
    incident_date: str,
    category: str,
    severity: str,
    title: str,
    description: str,
    menu_plan_id: str | None = None,
    recipe_id: str | None = None,
    reporter_role: str | None = None,
    created_by: UUID | None = None,
) -> dict:
    """클레임 접수 + 심각도 검증 + SAFE-002 자동 트리거"""
    # 1. 클레임 저장 (Claim)
    # 2. 위생/알레르겐 + high/critical → haccp_incidents 자동 생성 (SAFE-002)
    # 3. 동일 카테고리 최근 재발 확인 → is_recurring 업데이트
    # 4. Claude에게 즉각 가설 생성 요청 (analyze_claim 호출 옵션)
    return {"claim_id": ..., "status": "open", "haccp_incident_created": bool, ...}


async def analyze_claim(
    db: AsyncSession,
    claim_id: str,
    use_rag: bool = True,
) -> dict:
    """클레임 원인 분석 가설 생성 (RAG + DB 조회)"""
    # 1. 클레임 로드
    # 2. 관련 데이터 조회: 식단, 레시피 버전, 로트, HACCP 기록, 공급업체
    # 3. RAG 검색: 유사 사고 문서 (use_rag=True)
    # 4. 가설 목록 생성 (Claude가 이 결과를 받아 최종 응답 생성)
    # 5. Claim.ai_hypotheses 업데이트
    return {"hypotheses": [...], "related_data": {...}, "rag_references": [...]}


async def track_claim_action(
    db: AsyncSession,
    claim_id: str,
    action_type: str,
    description: str,
    assignee_role: str,
    assignee_id: str | None = None,
    due_date: str | None = None,
    created_by: UUID | None = None,
) -> dict:
    """클레임 조치 등록 + 상태 자동 업데이트"""
    # 1. ClaimAction 저장
    # 2. Claim.status → 'action_taken' (open/investigating에서)
    # 3. 모든 action.status == 'done' → Claim.status = 'closed'
    return {"action_id": ..., "claim_status": ..., "assigned_to": ...}
```

---

## 6. Tool Registry 업데이트

```python
# food-ai-agent-api/app/agents/tools/registry.py 수정

DEMAND_TOOLS = [
    {
        "name": "forecast_headcount",
        "description": "과거 실적과 이벤트를 반영하여 특정 날짜·식사의 식수를 예측합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site_id": {"type": "string", "format": "uuid"},
                "forecast_date": {"type": "string", "format": "date"},
                "meal_type": {"type": "string", "enum": ["breakfast","lunch","dinner","snack"]},
                "model": {"type": "string", "enum": ["wma"], "default": "wma"},
            },
            "required": ["site_id", "forecast_date", "meal_type"],
        },
    },
    {
        "name": "record_waste",
        "description": "날짜·메뉴별 잔반량을 기록하고 선호도 점수를 자동 갱신합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site_id": {"type": "string"},
                "record_date": {"type": "string", "format": "date"},
                "meal_type": {"type": "string"},
                "waste_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_name": {"type": "string"},
                            "waste_pct": {"type": "number"},
                            "recipe_id": {"type": "string"},
                        },
                        "required": ["item_name"],
                    },
                },
            },
            "required": ["site_id", "record_date", "meal_type", "waste_items"],
        },
    },
    {
        "name": "simulate_cost",
        "description": "식단 원가를 시뮬레이션하고 목표 원가 초과 시 대체 메뉴를 제안합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site_id": {"type": "string"},
                "menu_plan_id": {"type": "string"},
                "target_cost_per_meal": {"type": "number", "description": "1인 목표 원가 (KRW)"},
                "headcount": {"type": "integer"},
                "suggest_alternatives": {"type": "boolean", "default": True},
            },
            "required": ["site_id", "menu_plan_id", "target_cost_per_meal", "headcount"],
        },
    },
    {
        "name": "register_claim",
        "description": "클레임을 접수하고 자동 분류·심각도 판정·HACCP 연동을 수행합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site_id": {"type": "string"},
                "incident_date": {"type": "string", "format": "date-time"},
                "category": {"type": "string",
                             "enum": ["맛/품질","이물","양/분량","온도","알레르겐","위생/HACCP","서비스","기타"]},
                "severity": {"type": "string", "enum": ["low","medium","high","critical"], "default": "medium"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "menu_plan_id": {"type": "string"},
                "recipe_id": {"type": "string"},
                "lot_number": {"type": "string"},
            },
            "required": ["site_id", "incident_date", "category", "title", "description"],
        },
    },
    {
        "name": "analyze_claim",
        "description": "클레임의 원인 가설을 생성합니다. 관련 식단, 레시피, 로트, HACCP 기록을 자동 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_id": {"type": "string", "format": "uuid"},
                "use_rag": {"type": "boolean", "default": True, "description": "유사 사고 문서 RAG 검색 포함"},
            },
            "required": ["claim_id"],
        },
    },
    {
        "name": "track_claim_action",
        "description": "클레임에 대한 조치를 등록하고 진행 상태를 업데이트합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_id": {"type": "string", "format": "uuid"},
                "action_type": {"type": "string",
                                "enum": ["recipe_fix","vendor_warning","staff_training","haccp_update","other"]},
                "description": {"type": "string"},
                "assignee_role": {"type": "string", "enum": ["NUT","PUR","KIT","QLT","OPS","CS"]},
                "assignee_id": {"type": "string", "format": "uuid"},
                "due_date": {"type": "string", "format": "date-time"},
            },
            "required": ["claim_id", "action_type", "description", "assignee_role"],
        },
    },
]

# registry.py 하단 수정
AGENT_TOOLS = {
    "menu": MENU_TOOLS + WORK_ORDER_TOOLS + DEMAND_TOOLS[:1],   # forecast_headcount 추가
    "recipe": RECIPE_TOOLS + WORK_ORDER_TOOLS,
    "haccp": HACCP_TOOLS + DEMAND_TOOLS[3:4],                    # register_claim 추가 (SAFE-002)
    "general": DASHBOARD_TOOLS + DEMAND_TOOLS,                   # 전체 접근
    "purchase": PURCHASE_TOOLS + DEMAND_TOOLS[2:3],             # simulate_cost 추가
    "demand": DEMAND_TOOLS,
    "claim": DEMAND_TOOLS[3:],                                   # register_claim, analyze_claim, track_claim_action
}

ALL_TOOLS = (MENU_TOOLS + RECIPE_TOOLS + WORK_ORDER_TOOLS +
             HACCP_TOOLS + DASHBOARD_TOOLS + PURCHASE_TOOLS + DEMAND_TOOLS)
```

---

## 7. Intent Router 확장

```python
# food-ai-agent-api/app/agents/intent_router.py 수정
# 기존 16 intents → 22 intents

NEW_INTENTS = [
    "forecast_demand",          # "이번 주 식수 예측해줘", "다음달 급식 인원 예상"
    "record_actual",            # "오늘 잔반 입력", "실제 식수 기록"
    "optimize_cost",            # "원가 시뮬레이션", "예산 내 식단", "원가율 확인"
    "manage_claim",             # "클레임 접수", "불만 등록", "CS 처리"
    "analyze_claim_root_cause", # "원인 분석", "왜 이런 클레임이?", "가설 생성"
    "generate_quality_report",  # "품질 리포트", "클레임 현황", "이번달 불만 통계"
]

# System Prompt 추가 (intent_router.py 내 INTENT_LIST 확장)
INTENT_DESCRIPTIONS = {
    ...기존 16개...,
    "forecast_demand": "식수 예측, 수요 예측, 급식 인원 예상 요청",
    "record_actual": "실제 식수 입력, 잔반 기록, 배식 실적 등록",
    "optimize_cost": "원가 시뮬레이션, 예산 분석, 원가율 최적화, 대체 메뉴 원가",
    "manage_claim": "클레임 접수, 민원 등록, 불만 사항 처리",
    "analyze_claim_root_cause": "클레임 원인 분석, 가설 생성, 재발방지 조치",
    "generate_quality_report": "품질 리포트, 클레임 통계, 월간 품질 현황",
}
```

---

## 8. 수요예측 알고리즘 상세

```python
# food-ai-agent-api/app/services/forecast_service.py (신규)

from typing import NamedTuple

DOW_COEFFICIENTS = {0: 1.00, 1: 0.98, 2: 0.97, 3: 0.96, 4: 0.95, 5: 0.70, 6: 0.30}
WMA_WEIGHTS = [0.05, 0.05, 0.10, 0.10, 0.15, 0.20, 0.35]  # 최근 7주, 최신에 가중


class ForecastResult(NamedTuple):
    predicted_min: int
    predicted_mid: int
    predicted_max: int
    confidence_pct: float
    risk_factors: list[str]


def run_wma_forecast(
    actuals: list[int],          # 최근 N주 동일 요일 실적 (최신순)
    dow: int,                    # 예측 대상 요일 (0=월)
    event_factor: float = 1.0,  # 이벤트 보정 계수 (0.0~1.0)
    site_capacity: int = 500,
) -> ForecastResult:
    if len(actuals) < 4:
        # 데이터 부족: 계획 식수 × DOW 계수
        confidence = 50.0
        mid = int(site_capacity * DOW_COEFFICIENTS[dow] * event_factor)
    else:
        weights = WMA_WEIGHTS[-len(actuals):]
        w_sum = sum(weights)
        mid = int(sum(a * w for a, w in zip(actuals, weights)) / w_sum * event_factor)
        # 신뢰도: 표준편차 기반
        import statistics
        std = statistics.stdev(actuals[-4:]) if len(actuals) >= 2 else mid * 0.1
        confidence = max(40.0, min(95.0, 100.0 - (std / mid * 100)))

    margin = max(10, int(mid * 0.1))
    risk_factors = []
    if event_factor < 0.9:
        risk_factors.append(f"이벤트 보정 적용 ({event_factor:.0%})")
    if len(actuals) < 4:
        risk_factors.append("과거 실적 부족 (4주 미만)")

    return ForecastResult(
        predicted_min=mid - margin,
        predicted_mid=mid,
        predicted_max=mid + margin,
        confidence_pct=round(confidence, 1),
        risk_factors=risk_factors,
    )
```

---

## 9. Frontend 설계

### 9.1 신규 페이지 구조

```
food-ai-agent-web/app/(main)/
  ├── forecast/
  │   └── page.tsx                     # 수요예측 메인
  ├── waste/
  │   └── page.tsx                     # 잔반 관리
  ├── cost-optimizer/
  │   └── page.tsx                     # 원가 최적화
  └── claims/
      ├── page.tsx                     # 클레임 목록
      └── [id]/
          └── page.tsx                 # 클레임 상세
```

### 9.2 신규 컴포넌트 구조

```
food-ai-agent-web/components/
  ├── forecast/
  │   ├── forecast-chart.tsx           # 예측 vs 실제 라인 차트 (recharts)
  │   ├── headcount-input-form.tsx     # 실제 식수 입력 폼
  │   ├── event-calendar-widget.tsx    # 이벤트 캘린더 (미니)
  │   └── forecast-confidence-badge.tsx # 신뢰도 배지 (색상: 높음/중간/낮음)
  ├── waste/
  │   ├── waste-input-form.tsx         # 잔반 입력 폼 (다중 메뉴)
  │   ├── waste-trend-chart.tsx        # 잔반률 추이 차트
  │   ├── menu-preference-rating.tsx   # 별점/이모지 선호도 입력
  │   └── waste-by-menu-table.tsx      # 메뉴별 잔반률 테이블
  ├── cost/
  │   ├── cost-simulation-panel.tsx    # 원가 시뮬레이션 입력 + 결과
  │   ├── cost-variance-indicator.tsx  # 목표 대비 편차 인디케이터
  │   ├── budget-vs-actual-chart.tsx   # 예산 vs 실제 원가 바 차트
  │   └── menu-swap-suggestion-card.tsx # AI 대체 메뉴 제안 카드
  └── claims/
      ├── claim-register-form.tsx      # 클레임 접수 폼
      ├── claim-category-badge.tsx     # 카테고리 배지
      ├── claim-severity-indicator.tsx # 심각도 인디케이터 (low~critical)
      ├── claim-action-tracker.tsx     # 조치 타임라인
      ├── claim-list-table.tsx         # 클레임 목록 테이블
      ├── claim-analysis-panel.tsx     # 원인 분석 패널
      ├── root-cause-hypothesis-card.tsx # Claude 가설 카드
      └── quality-report-viewer.tsx   # 품질 리포트 뷰어
```

### 9.3 신규 React Hooks

```typescript
// food-ai-agent-web/hooks/
├── useForecast.ts        // useQuery/useMutation for forecast endpoints
├── useWaste.ts           // waste records + preferences
├── useCostAnalysis.ts    // cost simulation + analyses
└── useClaims.ts          // claims CRUD + actions
```

### 9.4 대시보드 신규 위젯

```
food-ai-agent-web/components/dashboard/
  ├── forecast-status-widget.tsx  # 이번 주 예측 식수 vs 실제
  ├── waste-rate-widget.tsx       # 현장별 잔반률 게이지
  ├── cost-rate-widget.tsx        # 원가율 목표 대비
  └── claims-summary-widget.tsx  # 이번달 클레임 건수/미처리
```

### 9.5 내비게이션 추가 (기존 sidebar 수정)

```typescript
// 기존: dashboard / menu-studio / recipes / kitchen / haccp / settings
// 추가:
{ href: '/forecast', label: '수요예측', icon: TrendingUp, roles: ['OPS','NUT','KIT'] },
{ href: '/waste', label: '잔반관리', icon: Trash2, roles: ['KIT','NUT','OPS'] },
{ href: '/cost-optimizer', label: '원가최적화', icon: Calculator, roles: ['OPS','NUT','PUR'] },
{ href: '/claims', label: '클레임', icon: AlertCircle, roles: ['CS','OPS'] },
```

---

## 10. 기존 파일 수정 목록

| 파일 | 수정 내용 |
|------|----------|
| `app/models/orm/__init__.py` | forecast, waste, cost, claim 모듈 import 추가 |
| `app/main.py` | 4개 신규 router include |
| `app/agents/tools/registry.py` | DEMAND_TOOLS 추가, AGENT_TOOLS 매핑 확장 |
| `app/agents/intent_router.py` | 6개 intent 추가, INTENT_DESCRIPTIONS 확장 |
| `app/agents/tools/menu_tools.py` | `generate_menu_plan`: preference_context 주입 |
| `app/agents/tools/dashboard_tools.py` | 수요예측/원가/클레임 위젯 데이터 추가 |
| `food-ai-agent-web/components/layout/sidebar.tsx` | 4개 메뉴 항목 추가 |
| `food-ai-agent-web/lib/api.ts` | 신규 API 클라이언트 함수 추가 |

---

## 11. 테스트 설계

```
food-ai-agent-api/tests/
  ├── test_forecast/
  │   ├── test_wma_algorithm.py        # 예측 알고리즘 단위 테스트
  │   └── test_forecast_api.py         # API 통합 테스트
  ├── test_waste/
  │   └── test_waste_api.py
  ├── test_cost/
  │   └── test_cost_simulation.py      # 원가 시뮬레이션 + suggest_alternatives 연동
  └── test_claims/
      ├── test_claim_flow.py           # 접수 → 분석 → 조치 → 완료 E2E
      └── test_safe002_trigger.py      # 위생 클레임 → HACCP incident 자동 생성
```

**예상 신규 테스트**: 30~35개

---

## 12. 구현 순서 (Do Phase 기준)

1. **DB Layer**: `forecast.py`, `waste.py`, `cost.py`, `claim.py` + Alembic migration `003`
2. **Service Layer**: `forecast_service.py` (WMA), `claim_service.py` (SAFE-002 연동)
3. **Tools**: `demand_tools.py` (6개 함수)
4. **Registry + Intent Router**: tool schema + 6 intents 추가
5. **Routers**: `forecast.py`, `waste.py`, `cost.py`, `claims.py` + `dashboard.py` 확장
6. **main.py**: router 등록
7. **Frontend**: hooks → components → pages → sidebar
8. **Tests**: 단위 + 통합 테스트
