"""Demand domain tools — forecast, waste, cost simulation, claim management."""
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.claim import Claim, ClaimAction
from app.models.orm.cost import CostAnalysis
from app.models.orm.forecast import ActualHeadcount, DemandForecast, SiteEvent
from app.models.orm.haccp import HaccpIncident
from app.models.orm.menu_plan import MenuPlan, MenuPlanItem
from app.models.orm.purchase import Bom, BomItem, VendorPrice
from app.models.orm.recipe import Recipe
from app.models.orm.waste import MenuPreference, WasteRecord
from app.services.forecast_service import run_wma_forecast

logger = logging.getLogger(__name__)

SYSTEM_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def forecast_headcount(
    db: AsyncSession,
    site_id: str,
    forecast_date: str,
    meal_type: str,
    model: str = "wma",
    force_recalc: bool = False,
    created_by: UUID | None = None,
) -> dict:
    """WMA 기반 식수 예측 + 이벤트 보정.

    1. 과거 실적 조회 (actual_headcounts, 최근 8주)
    2. 이벤트 계수 (site_events)
    3. WMA 계산 + 신뢰도 추정
    4. DemandForecast 저장
    """
    site_uuid = UUID(site_id)
    target_date = date.fromisoformat(forecast_date)
    dow = target_date.weekday()  # 0=월요일

    # 1. 과거 8주 동일 요일 실적 조회
    eight_weeks_ago = target_date - timedelta(weeks=8)
    actuals_rows = (await db.execute(
        select(ActualHeadcount).where(
            ActualHeadcount.site_id == site_uuid,
            ActualHeadcount.meal_type == meal_type,
            ActualHeadcount.record_date >= eight_weeks_ago,
            ActualHeadcount.record_date < target_date,
        ).order_by(ActualHeadcount.record_date)
    )).scalars().all()

    # 동일 요일 필터링
    same_dow_actuals = [
        row.actual for row in actuals_rows
        if row.record_date.weekday() == dow
    ]

    # 2. 이벤트 보정 계수
    event_row = (await db.execute(
        select(SiteEvent).where(
            SiteEvent.site_id == site_uuid,
            SiteEvent.event_date == target_date,
        ).limit(1)
    )).scalar_one_or_none()

    event_factor = float(event_row.adjustment_factor) if event_row else 1.0

    # 3. WMA 예측 실행
    result = run_wma_forecast(
        actuals=same_dow_actuals,
        dow=dow,
        event_factor=event_factor,
        site_capacity=500,
    )

    # 4. DemandForecast 저장
    forecast = DemandForecast(
        site_id=site_uuid,
        forecast_date=target_date,
        meal_type=meal_type,
        predicted_min=result.predicted_min,
        predicted_mid=result.predicted_mid,
        predicted_max=result.predicted_max,
        confidence_pct=Decimal(str(result.confidence_pct)),
        model_used=model,
        input_factors={
            "actuals_count": len(same_dow_actuals),
            "event_factor": event_factor,
            "dow": dow,
        },
        risk_factors=result.risk_factors,
        created_by=created_by or SYSTEM_USER_ID,
    )
    db.add(forecast)
    await db.flush()

    return {
        "forecast_id": str(forecast.id),
        "forecast_date": forecast_date,
        "meal_type": meal_type,
        "predicted_min": result.predicted_min,
        "predicted_mid": result.predicted_mid,
        "predicted_max": result.predicted_max,
        "confidence_pct": result.confidence_pct,
        "risk_factors": result.risk_factors,
        "model_used": model,
        "actuals_used": len(same_dow_actuals),
        "event_factor": event_factor,
        "source": "[출처: 과거 실적 WMA + 이벤트 보정]",
    }


async def record_waste(
    db: AsyncSession,
    site_id: str,
    record_date: str,
    meal_type: str,
    waste_items: list[dict],
    recorded_by: UUID | None = None,
) -> dict:
    """잔반 기록 저장 + MenuPreference EWMA 업데이트.

    Args:
        waste_items: [{item_name, waste_pct?, waste_kg?, recipe_id?, served_count?}]
    """
    site_uuid = UUID(site_id)
    target_date = date.fromisoformat(record_date)
    saved_count = 0
    preferences_updated = []

    for item_data in waste_items:
        item_name = item_data.get("item_name", "")
        waste_pct = item_data.get("waste_pct")
        waste_kg = item_data.get("waste_kg")
        recipe_id_str = item_data.get("recipe_id")
        served_count = item_data.get("served_count")

        recipe_uuid = UUID(recipe_id_str) if recipe_id_str else None

        wr = WasteRecord(
            site_id=site_uuid,
            record_date=target_date,
            meal_type=meal_type,
            item_name=item_name,
            waste_pct=Decimal(str(waste_pct)) if waste_pct is not None else None,
            waste_kg=Decimal(str(waste_kg)) if waste_kg is not None else None,
            recipe_id=recipe_uuid,
            served_count=served_count,
            recorded_by=recorded_by or SYSTEM_USER_ID,
        )
        db.add(wr)
        saved_count += 1

        # EWMA MenuPreference 업데이트
        if recipe_uuid and waste_pct is not None:
            pref = (await db.execute(
                select(MenuPreference).where(
                    MenuPreference.site_id == site_uuid,
                    MenuPreference.recipe_id == recipe_uuid,
                )
            )).scalar_one_or_none()

            new_score_delta = -(float(waste_pct) / 50.0)  # 50% 잔반 = 0점 기준
            if pref:
                old_score = float(pref.preference_score)
                new_score = round(0.7 * old_score + 0.3 * new_score_delta, 3)
                # Clamp to [-1.0, 1.0]
                new_score = max(-1.0, min(1.0, new_score))
                pref.preference_score = Decimal(str(new_score))
                pref.waste_avg_pct = Decimal(str(round(
                    (float(pref.waste_avg_pct) * pref.serve_count + float(waste_pct)) / (pref.serve_count + 1), 2
                )))
                pref.serve_count = pref.serve_count + 1
                pref.last_served = target_date
            else:
                new_score = round(max(-1.0, min(1.0, 0.3 * new_score_delta)), 3)
                pref = MenuPreference(
                    site_id=site_uuid,
                    recipe_id=recipe_uuid,
                    preference_score=Decimal(str(new_score)),
                    waste_avg_pct=Decimal(str(waste_pct)),
                    serve_count=1,
                    last_served=target_date,
                )
                db.add(pref)

            preferences_updated.append({
                "recipe_id": recipe_id_str,
                "preference_score": float(pref.preference_score),
                "waste_avg_pct": float(pref.waste_avg_pct),
                "serve_count": pref.serve_count,
            })

    await db.flush()

    return {
        "saved_count": saved_count,
        "record_date": record_date,
        "meal_type": meal_type,
        "preferences_updated": preferences_updated,
        "source": "[출처: 잔반 기록 저장 완료]",
    }


async def simulate_cost(
    db: AsyncSession,
    site_id: str,
    menu_plan_id: str,
    target_cost_per_meal: float,
    headcount: int,
    suggest_alternatives_flag: bool = True,
    created_by: UUID | None = None,
) -> dict:
    """식단 원가 시뮬레이션 + MVP2 purchase_tools 연동.

    1. BOM 조회 또는 menu_plan_items에서 원가 계산
    2. 현재 단가 × 수량 → 총 원가 계산
    3. target vs actual 편차 계산
    4. 원가 초과 시 대체 제안
    5. CostAnalysis 저장
    """
    site_uuid = UUID(site_id)
    plan_uuid = UUID(menu_plan_id)

    # Load menu plan
    plan = (await db.execute(select(MenuPlan).where(MenuPlan.id == plan_uuid))).scalar_one_or_none()
    if not plan:
        return {"error": "Menu plan not found"}

    # Try to load existing BOM first
    bom = (await db.execute(
        select(Bom).where(Bom.menu_plan_id == plan_uuid)
    )).scalar_one_or_none()

    cost_breakdown = []
    total_estimated = 0.0

    if bom:
        # Use BOM items
        bom_items = (await db.execute(
            select(BomItem).where(BomItem.bom_id == bom.id)
        )).scalars().all()

        for bi in bom_items:
            if bi.unit_price and bi.order_quantity:
                subtotal = float(bi.unit_price) * float(bi.order_quantity)
                total_estimated += subtotal
                cost_breakdown.append({
                    "item_name": bi.item_name,
                    "quantity": float(bi.order_quantity),
                    "unit": bi.unit,
                    "unit_price": float(bi.unit_price),
                    "subtotal": round(subtotal, 2),
                })
    else:
        # Fall back: load menu plan items → recipes → ingredients → prices
        mp_items = (await db.execute(
            select(MenuPlanItem).where(MenuPlanItem.menu_plan_id == plan_uuid)
        )).scalars().all()

        recipe_ids = [mp.recipe_id for mp in mp_items if mp.recipe_id]
        if recipe_ids:
            recipes = (await db.execute(
                select(Recipe).where(Recipe.id.in_(recipe_ids))
            )).scalars().all()
            recipes_map = {str(r.id): r for r in recipes}

            # Aggregate ingredient costs
            ingredient_costs: dict[str, dict] = {}
            for mp in mp_items:
                if not mp.recipe_id:
                    continue
                recipe = recipes_map.get(str(mp.recipe_id))
                if not recipe or not recipe.ingredients:
                    continue
                scale = headcount / (recipe.servings_base or 1)
                for ing in recipe.ingredients:
                    iid = ing.get("item_id")
                    if not iid:
                        continue
                    amount = float(ing.get("amount", 0)) * scale
                    if iid not in ingredient_costs:
                        ingredient_costs[iid] = {"name": ing.get("name", ""), "qty": 0.0, "unit": ing.get("unit", "g")}
                    ingredient_costs[iid]["qty"] += amount

            # Get prices
            if ingredient_costs:
                item_uuids = [UUID(iid) for iid in ingredient_costs.keys()]
                vps = (await db.execute(
                    select(VendorPrice).where(
                        VendorPrice.item_id.in_(item_uuids),
                        VendorPrice.is_current == True,
                    ).order_by(VendorPrice.unit_price)
                )).scalars().all()

                price_map: dict[str, float] = {}
                for vp in vps:
                    iid = str(vp.item_id)
                    if iid not in price_map:
                        price_map[iid] = float(vp.unit_price)

                for iid, data in ingredient_costs.items():
                    up = price_map.get(iid, 0.0)
                    subtotal = data["qty"] * up
                    total_estimated += subtotal
                    cost_breakdown.append({
                        "item_name": data["name"],
                        "quantity": round(data["qty"], 3),
                        "unit": data["unit"],
                        "unit_price": up,
                        "subtotal": round(subtotal, 2),
                    })

    # Compute per-meal cost
    cost_per_meal = total_estimated / headcount if headcount > 0 else 0.0
    target_total = target_cost_per_meal * headcount
    variance_pct = round((cost_per_meal - target_cost_per_meal) / target_cost_per_meal * 100, 2) if target_cost_per_meal > 0 else 0.0

    if abs(variance_pct) < 10:
        alert_triggered = "none"
    elif abs(variance_pct) < 20:
        alert_triggered = "warning"
    else:
        alert_triggered = "critical"

    # Suggestions: identify high-cost items
    suggestions = []
    if suggest_alternatives_flag and variance_pct > 10:
        # Sort by subtotal desc, suggest top 3 items
        sorted_items = sorted(cost_breakdown, key=lambda x: x["subtotal"], reverse=True)
        for item in sorted_items[:3]:
            suggestions.append({
                "item_name": item["item_name"],
                "current_cost": item["subtotal"],
                "suggestion": f"{item['item_name']} 대체품 검토 또는 수량 조정 권장",
            })

    # Save CostAnalysis
    analysis = CostAnalysis(
        site_id=site_uuid,
        menu_plan_id=plan_uuid,
        analysis_type="simulation",
        target_cost=Decimal(str(round(target_total, 2))),
        estimated_cost=Decimal(str(round(total_estimated, 2))),
        headcount=headcount,
        cost_breakdown={"items": cost_breakdown},
        variance_pct=Decimal(str(variance_pct)),
        alert_triggered=alert_triggered,
        suggestions=suggestions,
        created_by=created_by or SYSTEM_USER_ID,
    )
    db.add(analysis)
    await db.flush()

    return {
        "analysis_id": str(analysis.id),
        "menu_plan_id": menu_plan_id,
        "headcount": headcount,
        "target_cost_per_meal": target_cost_per_meal,
        "estimated_cost_per_meal": round(cost_per_meal, 2),
        "estimated_cost": round(total_estimated, 2),
        "target_cost": round(target_total, 2),
        "variance_pct": variance_pct,
        "alert_triggered": alert_triggered,
        "cost_breakdown": cost_breakdown,
        "suggestions": suggestions,
        "source": "[출처: 레시피 BOM + 현재 단가 기준]",
    }


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
    lot_number: str | None = None,
    reporter_name: str | None = None,
    reporter_role: str | None = None,
    created_by: UUID | None = None,
) -> dict:
    """클레임 접수 + 심각도 검증 + SAFE-002 자동 트리거.

    1. 클레임 저장 (Claim)
    2. 위생/알레르겐 + high/critical → haccp_incidents 자동 생성 (SAFE-002)
    3. 동일 카테고리 최근 재발 확인 → is_recurring 업데이트
    """
    site_uuid = UUID(site_id)
    incident_dt = datetime.fromisoformat(incident_date)

    # 3. 재발 확인: 최근 30일 동일 카테고리
    thirty_days_ago = incident_dt - timedelta(days=30)
    recent_same = (await db.execute(
        select(func.count(Claim.id)).where(
            Claim.site_id == site_uuid,
            Claim.category == category,
            Claim.incident_date >= thirty_days_ago,
            Claim.incident_date < incident_dt,
        )
    )).scalar() or 0

    is_recurring = recent_same > 0
    recurrence_count = int(recent_same)

    # 1. 클레임 저장
    claim = Claim(
        site_id=site_uuid,
        incident_date=incident_dt,
        category=category,
        severity=severity,
        status="open",
        title=title,
        description=description,
        menu_plan_id=UUID(menu_plan_id) if menu_plan_id else None,
        recipe_id=UUID(recipe_id) if recipe_id else None,
        lot_number=lot_number,
        reporter_name=reporter_name,
        reporter_role=reporter_role,
        is_recurring=is_recurring,
        recurrence_count=recurrence_count,
        created_by=created_by or SYSTEM_USER_ID,
    )
    db.add(claim)
    await db.flush()

    # 2. SAFE-002: 위생/알레르겐 high/critical → HACCP incident 자동 생성
    haccp_incident_created = False
    haccp_incident_id = None
    if category in ["위생/HACCP", "알레르겐"] and severity in ["high", "critical"]:
        incident = HaccpIncident(
            site_id=site_uuid,
            incident_type="claim_triggered",
            description=f"[클레임 자동 생성] {title}",
            severity=severity,
            status="open",
            reported_by=created_by or SYSTEM_USER_ID,
        )
        db.add(incident)
        await db.flush()
        claim.haccp_incident_id = incident.id
        haccp_incident_created = True
        haccp_incident_id = str(incident.id)
        logger.warning(f"SAFE-002: HACCP incident auto-created for claim {claim.id} (category={category}, severity={severity})")

    await db.flush()

    return {
        "claim_id": str(claim.id),
        "status": "open",
        "category": category,
        "severity": severity,
        "is_recurring": is_recurring,
        "recurrence_count": recurrence_count,
        "haccp_incident_created": haccp_incident_created,
        "haccp_incident_id": haccp_incident_id,
        "source": "[출처: 클레임 접수 완료 — SAFE-002 적용]",
    }


async def analyze_claim(
    db: AsyncSession,
    claim_id: str,
    use_rag: bool = True,
) -> dict:
    """클레임 원인 분석 가설 생성 (RAG + DB 조회).

    1. 클레임 로드
    2. 관련 데이터 조회: 식단, 레시피, 로트, HACCP 기록
    3. RAG 검색 (use_rag=True)
    4. 가설 목록 생성
    5. Claim.ai_hypotheses 업데이트
    """
    claim_uuid = UUID(claim_id)
    claim = (await db.execute(
        select(Claim).where(Claim.id == claim_uuid)
    )).scalar_one_or_none()
    if not claim:
        return {"error": "Claim not found"}

    related_data: dict = {}
    hypotheses = []

    # Load related menu plan
    if claim.menu_plan_id:
        plan = (await db.execute(
            select(MenuPlan).where(MenuPlan.id == claim.menu_plan_id)
        )).scalar_one_or_none()
        if plan:
            related_data["menu_plan"] = {
                "id": str(plan.id),
                "title": plan.title,
                "period_start": str(plan.period_start),
                "period_end": str(plan.period_end),
                "status": plan.status,
            }
            hypotheses.append({
                "hypothesis": f"식단 '{plan.title}' 관련 품질 문제",
                "evidence": ["연관 식단 식별됨"],
                "confidence": "medium",
            })

    # Load related recipe
    if claim.recipe_id:
        recipe = (await db.execute(
            select(Recipe).where(Recipe.id == claim.recipe_id)
        )).scalar_one_or_none()
        if recipe:
            related_data["recipe"] = {
                "id": str(recipe.id),
                "name": recipe.name,
                "category": recipe.category,
            }
            hypotheses.append({
                "hypothesis": f"레시피 '{recipe.name}' 조리 공정 또는 재료 문제",
                "evidence": ["연관 레시피 식별됨"],
                "confidence": "medium",
            })

    # Load lot number related data
    if claim.lot_number:
        related_data["lot_number"] = claim.lot_number
        hypotheses.append({
            "hypothesis": f"로트 {claim.lot_number} 원자재 품질 문제",
            "evidence": [f"클레임에 로트 번호 {claim.lot_number} 기재됨"],
            "confidence": "high",
        })

    # Load recent HACCP incidents for same site
    incident_date = claim.incident_date
    two_weeks_ago = incident_date - timedelta(days=14)
    haccp_incidents = (await db.execute(
        select(HaccpIncident).where(
            HaccpIncident.site_id == claim.site_id,
            HaccpIncident.created_at >= two_weeks_ago,
        ).limit(5)
    )).scalars().all()

    if haccp_incidents:
        related_data["recent_haccp_incidents"] = [
            {
                "id": str(inc.id),
                "incident_type": inc.incident_type,
                "severity": inc.severity,
                "status": inc.status,
            }
            for inc in haccp_incidents
        ]
        hypotheses.append({
            "hypothesis": "최근 HACCP 위생 관리 미흡으로 인한 연쇄 문제",
            "evidence": [f"최근 14일 내 {len(haccp_incidents)}건 HACCP 사고 기록"],
            "confidence": "medium",
        })

    # Category-specific hypotheses
    if claim.category == "알레르겐":
        hypotheses.append({
            "hypothesis": "알레르겐 교차 오염 또는 라벨링 오류",
            "evidence": ["알레르겐 클레임 카테고리"],
            "confidence": "high",
            "safety_note": "SAFE-001: 즉각적인 알레르겐 재확인 필요",
        })
    elif claim.category == "이물":
        hypotheses.append({
            "hypothesis": "원자재 세척 불량 또는 이물질 혼입",
            "evidence": ["이물 클레임 카테고리"],
            "confidence": "medium",
        })
    elif claim.category == "온도":
        hypotheses.append({
            "hypothesis": "CCP 온도 관리 실패 또는 운반 중 온도 상승",
            "evidence": ["온도 관련 클레임"],
            "confidence": "medium",
        })

    # RAG search for similar incidents
    rag_references = []
    if use_rag:
        try:
            from app.rag.pipeline import RAGPipeline
            rag = RAGPipeline()
            query = f"{claim.description} 원인 분석 유사 사례"
            docs = await rag.retrieve(query, top_k=3)
            for doc in docs:
                rag_references.append({
                    "title": doc.get("title", ""),
                    "snippet": doc.get("content", "")[:200],
                    "score": doc.get("score", 0),
                })
            if rag_references:
                hypotheses.append({
                    "hypothesis": "유사 과거 사례 기반 원인 추정",
                    "evidence": [f"RAG 검색 {len(rag_references)}건 유사 문서 발견"],
                    "confidence": "low",
                    "rag_references": rag_references,
                })
        except Exception as e:
            logger.warning(f"RAG search failed for claim analysis: {e}")

    # Update claim ai_hypotheses
    claim.ai_hypotheses = hypotheses
    await db.flush()

    return {
        "claim_id": claim_id,
        "hypotheses": hypotheses,
        "related_data": related_data,
        "rag_references_count": len(rag_references),
        "source": "[출처: DB 연관 데이터 + RAG 유사 사례]",
    }


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
    """클레임 조치 등록 + 상태 자동 업데이트.

    1. ClaimAction 저장
    2. Claim.status → 'action_taken' (open/investigating에서)
    3. 모든 action.status == 'done' → Claim.status = 'closed'
    """
    claim_uuid = UUID(claim_id)
    claim = (await db.execute(
        select(Claim).where(Claim.id == claim_uuid)
    )).scalar_one_or_none()
    if not claim:
        return {"error": "Claim not found"}

    due_dt = datetime.fromisoformat(due_date) if due_date else None

    action = ClaimAction(
        claim_id=claim_uuid,
        action_type=action_type,
        description=description,
        assignee_id=UUID(assignee_id) if assignee_id else None,
        assignee_role=assignee_role,
        due_date=due_dt,
        status="pending",
        created_by=created_by or SYSTEM_USER_ID,
    )
    db.add(action)
    await db.flush()

    # Update claim status
    if claim.status in ("open", "investigating"):
        claim.status = "action_taken"

    # Check if all actions are done → close
    all_actions = (await db.execute(
        select(ClaimAction).where(ClaimAction.claim_id == claim_uuid)
    )).scalars().all()

    if all_actions and all(a.status == "done" for a in all_actions):
        claim.status = "closed"
        claim.resolved_at = datetime.now(tz=timezone.utc)

    await db.flush()

    return {
        "action_id": str(action.id),
        "claim_id": claim_id,
        "claim_status": claim.status,
        "action_type": action_type,
        "assignee_role": assignee_role,
        "due_date": due_date,
        "source": "[출처: 클레임 조치 등록 완료]",
    }
