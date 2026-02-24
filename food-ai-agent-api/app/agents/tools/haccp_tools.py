"""HACCP domain tools - checklists, completion, audit reports."""
import logging
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm.haccp import HaccpChecklist, HaccpIncident, HaccpRecord
from app.models.orm.site import Site
from app.rag.pipeline import RAGPipeline

logger = logging.getLogger(__name__)

# Default daily checklist template
DEFAULT_DAILY_TEMPLATE = {
    "items": [
        {"id": 1, "category": "temperature", "point": "냉장고 온도 확인", "target": "0~5도", "input_type": "number"},
        {"id": 2, "category": "temperature", "point": "냉동고 온도 확인", "target": "-18도 이하", "input_type": "number"},
        {"id": 3, "category": "cleanliness", "point": "조리장 바닥 청소 상태", "target": "이물질 없음", "input_type": "checkbox"},
        {"id": 4, "category": "hygiene", "point": "종업원 건강 체크", "target": "증상 없음", "input_type": "checkbox"},
        {"id": 5, "category": "storage", "point": "보존식 보관 확인", "target": "144시간, -18도", "input_type": "checkbox"},
        {"id": 6, "category": "inspection", "point": "식재료 검수 기록", "target": "상태 이상 없음", "input_type": "checkbox"},
        {"id": 7, "category": "cleanliness", "point": "칼/도마 소독 확인", "target": "200ppm 염소", "input_type": "checkbox"},
        {"id": 8, "category": "temperature", "point": "배식대 온도 확인", "target": "60도 이상", "input_type": "number"},
        {"id": 9, "category": "cleanliness", "point": "식기 세척/소독 확인", "target": "세척기 82도 이상", "input_type": "checkbox"},
        {"id": 10, "category": "hygiene", "point": "손 세척/소독 확인", "target": "작업 전후", "input_type": "checkbox"},
    ]
}

DEFAULT_WEEKLY_TEMPLATE = {
    "items": [
        {"id": 1, "category": "facility", "point": "방충/방서 시설 점검", "target": "포충등, 트랩 정상", "input_type": "checkbox"},
        {"id": 2, "category": "facility", "point": "환기 시설 점검", "target": "정상 작동", "input_type": "checkbox"},
        {"id": 3, "category": "facility", "point": "급배수 시설 점검", "target": "누수/역류 없음", "input_type": "checkbox"},
        {"id": 4, "category": "storage", "point": "식재료 창고 정리", "target": "선입선출 확인", "input_type": "checkbox"},
        {"id": 5, "category": "hygiene", "point": "위생 교육 실시 확인", "target": "전 직원 참여", "input_type": "checkbox"},
        {"id": 6, "category": "equipment", "point": "조리기구 상태 점검", "target": "파손/마모 없음", "input_type": "checkbox"},
        {"id": 7, "category": "documentation", "point": "HACCP 문서 최신화 확인", "target": "누락 없음", "input_type": "checkbox"},
    ]
}


async def generate_haccp_checklist(
    db: AsyncSession,
    site_id: str,
    date_str: str,
    checklist_type: str,
    meal_type: str | None = None,
) -> dict:
    """Generate HACCP checklist using template + RAG HACCP guide context."""
    site_uuid = UUID(site_id)
    target_date = date.fromisoformat(date_str)

    site = (await db.execute(select(Site).where(Site.id == site_uuid))).scalar_one_or_none()
    if not site:
        return {"error": "Site not found"}

    # Check for existing checklist
    existing = (await db.execute(
        select(HaccpChecklist).where(
            HaccpChecklist.site_id == site_uuid,
            HaccpChecklist.date == target_date,
            HaccpChecklist.checklist_type == checklist_type,
        )
    )).scalar_one_or_none()

    if existing:
        return {
            "checklist_id": str(existing.id),
            "status": existing.status,
            "message": "이미 생성된 점검표가 있습니다.",
            "template": existing.template,
        }

    # RAG: search HACCP guides for site-specific items
    rag = RAGPipeline(db)
    rag_context = await rag.retrieve(
        f"{site.name} {checklist_type} HACCP 점검",
        doc_types=["haccp_guide"],
    )

    # Select template
    template = DEFAULT_DAILY_TEMPLATE if checklist_type == "daily" else DEFAULT_WEEKLY_TEMPLATE

    # Enhance with site rules if available
    if site.rules and "haccp_extra_items" in site.rules:
        extra = site.rules["haccp_extra_items"]
        max_id = max(item["id"] for item in template["items"])
        for i, extra_item in enumerate(extra):
            template["items"].append({
                "id": max_id + i + 1,
                "category": extra_item.get("category", "custom"),
                "point": extra_item.get("point", ""),
                "target": extra_item.get("target", ""),
                "input_type": extra_item.get("input_type", "checkbox"),
            })

    # Create checklist record
    checklist = HaccpChecklist(
        site_id=site_uuid,
        date=target_date,
        checklist_type=checklist_type,
        meal_type=meal_type,
        template=template,
        status="pending",
    )
    db.add(checklist)
    await db.flush()

    return {
        "checklist_id": str(checklist.id),
        "site": site.name,
        "date": date_str,
        "type": checklist_type,
        "meal_type": meal_type,
        "template": template,
        "total_items": len(template["items"]),
        "rag_guides_referenced": len(rag_context.chunks),
        "status": "pending",
    }


async def check_haccp_completion(
    db: AsyncSession,
    site_id: str,
    date_str: str,
) -> dict:
    """Check HACCP checklist completion status for a site/date."""
    site_uuid = UUID(site_id)
    target_date = date.fromisoformat(date_str)

    checklists = (await db.execute(
        select(HaccpChecklist).where(
            HaccpChecklist.site_id == site_uuid,
            HaccpChecklist.date == target_date,
        )
    )).scalars().all()

    if not checklists:
        return {
            "site_id": site_id,
            "date": date_str,
            "total_checklists": 0,
            "message": "해당 날짜에 생성된 점검표가 없습니다.",
        }

    results = []
    for cl in checklists:
        records = (await db.execute(
            select(HaccpRecord).where(HaccpRecord.checklist_id == cl.id)
        )).scalars().all()

        total_items = len(cl.template.get("items", [])) if cl.template else 0
        completed_items = len(records)
        non_compliant = [r for r in records if r.is_compliant is False]

        results.append({
            "checklist_id": str(cl.id),
            "type": cl.checklist_type,
            "meal_type": cl.meal_type,
            "status": cl.status,
            "total_items": total_items,
            "completed_items": completed_items,
            "completion_rate": round(completed_items / total_items * 100, 1) if total_items > 0 else 0,
            "non_compliant_count": len(non_compliant),
            "non_compliant_items": [
                {"point": r.ccp_point, "target": r.target_value, "actual": r.actual_value}
                for r in non_compliant
            ],
        })

    completed = sum(1 for r in results if r["status"] == "completed")
    overdue = sum(1 for r in results if r["status"] in ("pending", "overdue"))

    return {
        "site_id": site_id,
        "date": date_str,
        "total_checklists": len(results),
        "completed": completed,
        "overdue": overdue,
        "checklists": results,
    }


async def generate_audit_report(
    db: AsyncSession,
    site_id: str,
    start_date: str,
    end_date: str,
    include_sections: list[str] | None = None,
) -> dict:
    """Generate HACCP audit report for a date range."""
    site_uuid = UUID(site_id)
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    sections = include_sections or ["checklists", "ccp_records", "incidents"]

    site = (await db.execute(select(Site).where(Site.id == site_uuid))).scalar_one_or_none()
    if not site:
        return {"error": "Site not found"}

    report: dict = {
        "site": site.name,
        "period": f"{start_date} ~ {end_date}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if "checklists" in sections:
        checklists = (await db.execute(
            select(HaccpChecklist).where(
                HaccpChecklist.site_id == site_uuid,
                HaccpChecklist.date >= start,
                HaccpChecklist.date <= end,
            )
        )).scalars().all()

        total = len(checklists)
        completed = sum(1 for c in checklists if c.status == "completed")
        report["checklists"] = {
            "total": total,
            "completed": completed,
            "completion_rate": round(completed / total * 100, 1) if total > 0 else 0,
        }

    if "ccp_records" in sections:
        # Count CCP records via checklists in the period
        checklist_ids = [c.id for c in checklists] if "checklists" in sections else []
        if checklist_ids:
            records = (await db.execute(
                select(HaccpRecord).where(HaccpRecord.checklist_id.in_(checklist_ids))
            )).scalars().all()
            non_compliant = [r for r in records if r.is_compliant is False]
            report["ccp_records"] = {
                "total": len(records),
                "compliant": len(records) - len(non_compliant),
                "non_compliant": len(non_compliant),
                "compliance_rate": round((len(records) - len(non_compliant)) / len(records) * 100, 1) if records else 0,
            }
        else:
            report["ccp_records"] = {"total": 0, "compliant": 0, "non_compliant": 0, "compliance_rate": 0}

    if "incidents" in sections:
        incidents = (await db.execute(
            select(HaccpIncident).where(
                HaccpIncident.site_id == site_uuid,
                HaccpIncident.created_at >= datetime.combine(start, datetime.min.time()),
                HaccpIncident.created_at <= datetime.combine(end, datetime.max.time()),
            )
        )).scalars().all()

        report["incidents"] = {
            "total": len(incidents),
            "by_severity": {},
            "by_status": {},
        }
        for inc in incidents:
            report["incidents"]["by_severity"][inc.severity] = report["incidents"]["by_severity"].get(inc.severity, 0) + 1
            report["incidents"]["by_status"][inc.status] = report["incidents"]["by_status"].get(inc.status, 0) + 1

    return report
