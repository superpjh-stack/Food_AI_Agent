"""Tool registry - defines all 17 domain tools as Claude Tool Use JSON schemas."""

MENU_TOOLS = [
    {
        "name": "generate_menu_plan",
        "description": "Generate weekly meal plan alternatives for a site. Returns 2+ alternatives with nutrition summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site_id": {"type": "string", "format": "uuid", "description": "Target site UUID"},
                "period_start": {"type": "string", "format": "date", "description": "Start date (YYYY-MM-DD)"},
                "period_end": {"type": "string", "format": "date", "description": "End date (YYYY-MM-DD)"},
                "meal_types": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["breakfast", "lunch", "dinner", "snack"]},
                    "description": "Meal types to include",
                },
                "target_headcount": {"type": "integer", "description": "Number of servings"},
                "budget_per_meal": {"type": "number", "description": "Target cost per meal in KRW"},
                "preferences": {"type": "object", "description": "User preferences and restrictions"},
                "num_alternatives": {"type": "integer", "default": 2, "description": "Number of alternatives to generate"},
            },
            "required": ["site_id", "period_start", "period_end", "meal_types", "target_headcount"],
        },
    },
    {
        "name": "validate_nutrition",
        "description": "Validate a menu plan against nutrition policy. Returns pass/warning/fail per day and criteria.",
        "input_schema": {
            "type": "object",
            "properties": {
                "menu_plan_id": {"type": "string", "format": "uuid"},
                "policy_id": {"type": "string", "format": "uuid", "description": "Optional specific policy to validate against"},
            },
            "required": ["menu_plan_id"],
        },
    },
    {
        "name": "tag_allergens",
        "description": "Auto-tag allergens for menu plan items or recipe ingredients based on allergen policy. Marks uncertain items as 'needs verification'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_type": {"type": "string", "enum": ["menu_plan", "recipe"]},
                "target_id": {"type": "string", "format": "uuid"},
            },
            "required": ["target_type", "target_id"],
        },
    },
    {
        "name": "check_diversity",
        "description": "Check menu diversity: cooking method bias, ingredient repetition, category balance over the plan period.",
        "input_schema": {
            "type": "object",
            "properties": {
                "menu_plan_id": {"type": "string", "format": "uuid"},
            },
            "required": ["menu_plan_id"],
        },
    },
]

RECIPE_TOOLS = [
    {
        "name": "search_recipes",
        "description": "Search recipes using hybrid search (BM25 keyword + vector semantic). Returns ranked results with relevance scores.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query in natural language"},
                "category": {"type": "string", "description": "Filter by category (한식, 중식, 양식, 일식)"},
                "allergen_exclude": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Allergens to exclude from results",
                },
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "scale_recipe",
        "description": "Scale recipe ingredients from base servings to target servings. Includes seasoning adjustment guide for large batches (350+ servings).",
        "input_schema": {
            "type": "object",
            "properties": {
                "recipe_id": {"type": "string", "format": "uuid"},
                "target_servings": {"type": "integer", "description": "Target number of servings"},
            },
            "required": ["recipe_id", "target_servings"],
        },
    },
]

HACCP_TOOLS = [
    {
        "name": "generate_haccp_checklist",
        "description": "Generate HACCP inspection checklist template for a site/date based on HACCP guide documents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site_id": {"type": "string", "format": "uuid"},
                "date": {"type": "string", "format": "date"},
                "checklist_type": {"type": "string", "enum": ["daily", "weekly"]},
                "meal_type": {"type": "string", "description": "Optional meal type filter"},
            },
            "required": ["site_id", "date", "checklist_type"],
        },
    },
    {
        "name": "check_haccp_completion",
        "description": "Check HACCP checklist completion status for a site/date. Returns missing/overdue items.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site_id": {"type": "string", "format": "uuid"},
                "date": {"type": "string", "format": "date"},
            },
            "required": ["site_id", "date"],
        },
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
                "include_sections": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["checklists", "ccp_records", "incidents", "training"]},
                },
            },
            "required": ["site_id", "start_date", "end_date"],
        },
    },
]

WORK_ORDER_TOOLS = [
    {
        "name": "generate_work_order",
        "description": "레시피 기반 조리 작업지시서를 생성합니다. 조리 순서, CCP 체크포인트, 필요 식재료량을 포함합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "recipe_id": {"type": "string", "description": "레시피 UUID"},
                "planned_servings": {"type": "integer", "description": "예정 조리 인원수"},
                "planned_date": {"type": "string", "format": "date", "description": "조리 예정일 (YYYY-MM-DD)"},
                "site_id": {"type": "string", "description": "사이트 ID"},
            },
            "required": ["recipe_id", "planned_servings", "planned_date"],
        },
    },
]

DASHBOARD_TOOLS = [
    {
        "name": "query_dashboard",
        "description": "Get operational dashboard data: today's menu status, HACCP completion, alerts, recent activity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site_id": {"type": "string", "format": "uuid"},
                "date": {"type": "string", "format": "date", "description": "Target date (default: today)"},
            },
            "required": ["site_id"],
        },
    },
]

PURCHASE_TOOLS = [
    {
        "name": "calculate_bom",
        "description": "확정된 식단의 레시피별 원재료 소요량을 집계하여 BOM을 생성합니다. 인분 스케일링과 수율을 반영합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "menu_plan_id": {"type": "string", "description": "식단 ID (confirmed 상태여야 함)"},
                "headcount": {"type": "integer", "description": "예정 식수 (명)"},
                "apply_inventory": {"type": "boolean", "description": "재고 우선 차감 반영 여부", "default": True},
            },
            "required": ["menu_plan_id", "headcount"],
        },
    },
    {
        "name": "generate_purchase_order",
        "description": "BOM을 기반으로 벤더별 발주서 초안을 생성합니다. 최저가 벤더를 자동 선택하거나 지정 벤더로 생성합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bom_id": {"type": "string", "description": "BOM ID"},
                "vendor_strategy": {
                    "type": "string",
                    "enum": ["lowest_price", "preferred", "split"],
                    "description": "벤더 선택 전략: 최저가/선호벤더/분할발주",
                    "default": "lowest_price",
                },
                "delivery_date": {"type": "string", "description": "납품 희망일 (YYYY-MM-DD)"},
                "vendor_id": {"type": "string", "description": "지정 벤더 ID (preferred 전략 시)"},
            },
            "required": ["bom_id", "delivery_date"],
        },
    },
    {
        "name": "compare_vendors",
        "description": "특정 품목 또는 품목 목록에 대해 벤더별 단가, 납기, 품질 점수를 비교합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_ids": {"type": "array", "items": {"type": "string"}, "description": "품목 ID 목록"},
                "site_id": {"type": "string", "description": "현장 ID (단가 계약 확인용)"},
                "compare_period": {"type": "integer", "description": "단가 추이 비교 기간 (주)", "default": 4},
            },
            "required": ["item_ids"],
        },
    },
    {
        "name": "detect_price_risk",
        "description": "최근 단가 변동을 분석하여 급등/공급 리스크 품목을 탐지하고 영향 메뉴를 추정합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site_id": {"type": "string"},
                "threshold_pct": {"type": "number", "description": "급등 임계치 (%)", "default": 15},
                "compare_weeks": {"type": "integer", "description": "비교 기간 (주 전)", "default": 1},
                "menu_plan_id": {"type": "string", "description": "영향 식단 ID (선택)"},
            },
            "required": ["site_id"],
        },
    },
    {
        "name": "suggest_alternatives",
        "description": "특정 품목의 대체품 또는 대체 벤더를 추천합니다. 알레르겐 규정과 영양 정책을 반영합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item_id": {"type": "string", "description": "대체할 품목 ID"},
                "site_id": {"type": "string"},
                "reason": {
                    "type": "string",
                    "enum": ["price_spike", "out_of_stock", "quality"],
                    "description": "대체 이유",
                },
                "allergen_policy_id": {"type": "string", "description": "알레르겐 정책 ID"},
            },
            "required": ["item_id", "site_id"],
        },
    },
    {
        "name": "check_inventory",
        "description": "현장의 재고 현황을 조회합니다. 유통기한 임박, 부족 품목을 우선 표시합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site_id": {"type": "string", "description": "현장 ID"},
                "item_ids": {"type": "array", "items": {"type": "string"}, "description": "특정 품목 필터 (선택)"},
                "alert_days": {"type": "integer", "description": "유통기한 임박 기준 (일)", "default": 7},
                "include_lots": {"type": "boolean", "description": "로트 상세 포함 여부", "default": False},
            },
            "required": ["site_id"],
        },
    },
]

DEMAND_TOOLS = [
    {
        "name": "forecast_headcount",
        "description": "과거 실적과 이벤트를 반영하여 특정 날짜·식사의 식수를 예측합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "site_id": {"type": "string", "format": "uuid"},
                "forecast_date": {"type": "string", "format": "date"},
                "meal_type": {"type": "string", "enum": ["breakfast", "lunch", "dinner", "snack"]},
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
                "category": {
                    "type": "string",
                    "enum": ["맛/품질", "이물", "양/분량", "온도", "알레르겐", "위생/HACCP", "서비스", "기타"],
                },
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
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
                "action_type": {
                    "type": "string",
                    "enum": ["recipe_fix", "vendor_warning", "staff_training", "haccp_update", "other"],
                },
                "description": {"type": "string"},
                "assignee_role": {"type": "string", "enum": ["NUT", "PUR", "KIT", "QLT", "OPS", "CS"]},
                "assignee_id": {"type": "string", "format": "uuid"},
                "due_date": {"type": "string", "format": "date-time"},
            },
            "required": ["claim_id", "action_type", "description", "assignee_role"],
        },
    },
]

# Agent → tools mapping
AGENT_TOOLS = {
    "menu": MENU_TOOLS + WORK_ORDER_TOOLS + DEMAND_TOOLS[:1],   # + forecast_headcount
    "recipe": RECIPE_TOOLS + WORK_ORDER_TOOLS,
    "haccp": HACCP_TOOLS + DEMAND_TOOLS[3:4],                   # + register_claim (SAFE-002)
    "general": DASHBOARD_TOOLS + DEMAND_TOOLS,
    "purchase": PURCHASE_TOOLS + DEMAND_TOOLS[2:3],             # + simulate_cost
    "demand": DEMAND_TOOLS,
    "claim": DEMAND_TOOLS[3:],                                  # register_claim, analyze_claim, track_claim_action
}

ALL_TOOLS = (
    MENU_TOOLS + RECIPE_TOOLS + WORK_ORDER_TOOLS +
    HACCP_TOOLS + DASHBOARD_TOOLS + PURCHASE_TOOLS + DEMAND_TOOLS
)


def get_tools_for_agent(agent_type: str) -> list[dict]:
    """Return the tool definitions for a specific agent type."""
    return AGENT_TOOLS.get(agent_type, DASHBOARD_TOOLS)


def get_tool_names_for_agent(agent_type: str) -> set[str]:
    """Return the set of tool names available to a specific agent."""
    return {t["name"] for t in get_tools_for_agent(agent_type)}
