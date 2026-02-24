"""Intent classification and query rewriting using Claude lightweight calls."""
import json
import logging
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class UserContext:
    current_screen: str = "dashboard"
    user_role: str = "NUT"
    site_name: str = ""
    site_id: str = ""


@dataclass
class IntentResult:
    intent: str
    confidence: float
    entities: dict
    agent: str  # menu, recipe, haccp, general

    @property
    def needs_clarification(self) -> bool:
        return self.confidence < 0.7


# Intent → Agent mapping
INTENT_AGENT_MAP = {
    "menu_generate": "menu",
    "menu_validate": "menu",
    "recipe_search": "recipe",
    "recipe_scale": "recipe",
    "work_order": "recipe",
    "haccp_checklist": "haccp",
    "haccp_record": "haccp",
    "haccp_incident": "haccp",
    "dashboard": "general",
    "settings": "general",
    "general": "general",
    # MVP 2 purchase intents
    "purchase_bom": "purchase",
    "purchase_order": "purchase",
    "purchase_risk": "purchase",
    "inventory_check": "purchase",
    "inventory_receive": "purchase",
    # MVP 3 demand / cost / claim intents
    "forecast_demand": "demand",
    "record_actual": "demand",
    "optimize_cost": "demand",
    "manage_claim": "claim",
    "analyze_claim_root_cause": "claim",
    "generate_quality_report": "claim",
}

INTENT_SYSTEM_PROMPT = """You are an intent classifier for a Korean food service management system.
Classify the user message into exactly one intent.

Intents:
- menu_generate: Creating or modifying meal plans (식단 생성, 식단 짜줘, 메뉴 만들어)
- menu_validate: Checking nutrition or allergens for existing plans (영양 검증, 알레르겐 확인)
- recipe_search: Finding recipes or recipe information (레시피 검색, 어떤 요리, 조리법)
- recipe_scale: Scaling recipes for different serving sizes (몇인분, 재료 환산, 스케일링)
- work_order: Generating or viewing work orders / production instructions (작업지시서, 조리 순서)
- haccp_checklist: Creating or checking HACCP checklists (점검표, 체크리스트)
- haccp_record: Recording CCP values or viewing HACCP records (온도 기록, CCP)
- haccp_incident: Reporting or managing food safety incidents (사고, 이상, 식중독)
- dashboard: Viewing operational status or summaries (현황, 대시보드, 오늘 상태)
- settings: Managing master data, policies, or system configuration (설정, 식재료 등록, 정책)
- purchase_bom: 식단 소요량 집계, BOM 산출 요청 (BOM, 소요량, 발주 수량, 식재료 필요)
- purchase_order: 발주서 생성/조회/수정/승인 요청 (발주서, 주문, 발주, 재발주, 벤더)
- purchase_risk: 단가 급등 경보, 공급 리스크, 대체품 추천 (단가, 급등, 공급 위기, 납품 지연, 대체품)
- inventory_check: 재고 현황 조회, 유통기한 조회, 부족 품목 (재고, 냉장, 유통기한, 남은 것)
- inventory_receive: 납품 검수 체크리스트, 입고 기록 (납품, 검수, 입고, 배달)
- forecast_demand: 식수 예측, 수요 예측, 급식 인원 예상 요청 (식수 예측, 내일 몇명, 수요 예측)
- record_actual: 실제 식수 입력, 잔반 기록, 배식 실적 등록 (오늘 식수, 잔반 입력, 실적 기록)
- optimize_cost: 원가 시뮬레이션, 예산 분석, 원가율 최적화, 대체 메뉴 원가 (원가, 예산, 비용)
- manage_claim: 클레임 접수, 민원 등록, 불만 사항 처리 (클레임, 불만, 민원, CS)
- analyze_claim_root_cause: 클레임 원인 분석, 가설 생성, 재발방지 조치 (원인 분석, 왜, 가설)
- generate_quality_report: 품질 리포트, 클레임 통계, 월간 품질 현황 (품질 리포트, 클레임 현황)
- general: General questions, greetings, or unclear requests

Context: current_screen={screen}, user_role={role}, site={site_name}

Return ONLY valid JSON: {{"intent": "...", "confidence": 0.0-1.0, "entities": {{}}, "agent": "menu|recipe|haccp|general|purchase|demand|claim"}}"""

QUERY_REWRITE_PROMPT = """You are a search query optimizer for a Korean food service knowledge base.
Given the user's conversational message and detected intent, rewrite it as an optimal search query.

Rules:
- Remove conversational fillers (그거, 좀, 해줘)
- Add implied context (site name, date range, meal type)
- Keep Korean food terminology
- Keep it concise (under 50 characters preferred)
- If the message is already a good search query, return it as-is

User message: {message}
Intent: {intent}
Context: site={site_name}, role={role}

Return ONLY the rewritten search query text, nothing else."""


class IntentRouter:
    """Classify user intent and optimize search queries."""

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def classify(self, message: str, context: UserContext) -> IntentResult:
        """Classify user message into one of 11 intents."""
        system = INTENT_SYSTEM_PROMPT.format(
            screen=context.current_screen,
            role=context.user_role,
            site_name=context.site_name,
        )

        try:
            response = await self.client.messages.create(
                model=settings.claude_model,
                max_tokens=200,
                temperature=0,
                system=system,
                messages=[{"role": "user", "content": message}],
            )

            text = response.content[0].text.strip()
            # Parse JSON response
            data = json.loads(text)

            intent = data.get("intent", "general")
            agent = data.get("agent") or INTENT_AGENT_MAP.get(intent, "general")

            return IntentResult(
                intent=intent,
                confidence=float(data.get("confidence", 0.5)),
                entities=data.get("entities", {}),
                agent=agent,
            )
        except Exception as e:
            logger.warning(f"Intent classification failed, falling back to general: {e}")
            return IntentResult(
                intent="general",
                confidence=0.3,
                entities={},
                agent="general",
            )

    async def rewrite_query(self, message: str, intent: str, context: UserContext) -> str:
        """Rewrite conversational message into optimized search query."""
        prompt = QUERY_REWRITE_PROMPT.format(
            message=message,
            intent=intent,
            site_name=context.site_name,
            role=context.user_role,
        )

        try:
            response = await self.client.messages.create(
                model=settings.claude_model,
                max_tokens=100,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            rewritten = response.content[0].text.strip()
            return rewritten if rewritten else message
        except Exception as e:
            logger.warning(f"Query rewrite failed, using original: {e}")
            return message
