from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import require_role
from app.db.session import get_db
from app.models.orm.audit_log import AuditLog
from app.models.orm.haccp import HaccpChecklist, HaccpRecord, HaccpIncident
from app.models.orm.user import User
from app.models.schemas.haccp import (
    ChecklistGenerateRequest,
    CcpRecordRequest,
    IncidentRequest,
    AuditReportRequest,
)

router = APIRouter()

# ── Default checklist templates ──

DAILY_TEMPLATE = [
    {"item": "식재료 입고 검수 (온도/외관/유통기한)", "category": "receiving", "is_ccp": False},
    {"item": "냉장고 온도 확인 (0~5°C)", "category": "temperature", "is_ccp": True, "target": "0~5°C"},
    {"item": "냉동고 온도 확인 (-18°C 이하)", "category": "temperature", "is_ccp": True, "target": "-18°C 이하"},
    {"item": "조리 종사자 건강상태 확인", "category": "personnel", "is_ccp": False},
    {"item": "조리 종사자 손 세척 확인", "category": "hygiene", "is_ccp": False},
    {"item": "조리실 청결 상태 확인", "category": "cleanliness", "is_ccp": False},
    {"item": "가열 조리 중심온도 확인 (75°C 1분 이상)", "category": "temperature", "is_ccp": True, "target": "75°C, 1분"},
    {"item": "배식 온도 확인 (60°C 이상 / 5°C 이하)", "category": "temperature", "is_ccp": True, "target": "60°C↑ or 5°C↓"},
    {"item": "보존식 채취 및 보관 (144시간)", "category": "storage", "is_ccp": False},
    {"item": "조리 기구 세척·소독 확인", "category": "cleanliness", "is_ccp": False},
]

WEEKLY_TEMPLATE = [
    {"item": "급수 시설 점검 및 수질 확인", "category": "water", "is_ccp": False},
    {"item": "방충·방서 시설 점검", "category": "pest", "is_ccp": False},
    {"item": "환기 시설 점검", "category": "ventilation", "is_ccp": False},
    {"item": "배수구 및 폐기물 처리 점검", "category": "waste", "is_ccp": False},
    {"item": "비식품 보관 구역 분리 확인", "category": "storage", "is_ccp": False},
    {"item": "소독제/세제 보관 상태 확인", "category": "chemicals", "is_ccp": False},
    {"item": "위생 교육 이수 현황 확인", "category": "training", "is_ccp": False},
]


# ── Checklists ──

@router.post("/checklists/generate")
async def generate_checklist(
    body: ChecklistGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("QLT", "OPS", "ADM"),
):
    """Generate HACCP checklist from templates."""
    template = DAILY_TEMPLATE if body.checklist_type == "daily" else WEEKLY_TEMPLATE

    checklist = HaccpChecklist(
        site_id=body.site_id,
        date=body.date,
        checklist_type=body.checklist_type,
        meal_type=body.meal_type,
        template=template,
        status="pending",
    )
    db.add(checklist)
    await db.flush()

    # Audit log
    db.add(AuditLog(
        user_id=current_user.id,
        site_id=body.site_id,
        action="create",
        entity_type="haccp_checklist",
        entity_id=checklist.id,
    ))

    return {"success": True, "data": _checklist_to_dict(checklist)}


@router.get("/checklists")
async def list_checklists(
    site_id: UUID | None = Query(None),
    date_filter: date | None = Query(None, alias="date"),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("QLT", "OPS", "ADM"),
):
    """List checklists with filters."""
    query = select(HaccpChecklist)
    count_query = select(func.count(HaccpChecklist.id))

    if site_id:
        query = query.where(HaccpChecklist.site_id == site_id)
        count_query = count_query.where(HaccpChecklist.site_id == site_id)
    if date_filter:
        query = query.where(HaccpChecklist.date == date_filter)
        count_query = count_query.where(HaccpChecklist.date == date_filter)
    if status:
        query = query.where(HaccpChecklist.status == status)
        count_query = count_query.where(HaccpChecklist.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(HaccpChecklist.date.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    checklists = result.scalars().all()

    return {
        "success": True,
        "data": [_checklist_to_dict(c) for c in checklists],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.get("/checklists/{checklist_id}")
async def get_checklist(
    checklist_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("QLT", "OPS", "ADM"),
):
    """Get checklist detail with records."""
    query = (
        select(HaccpChecklist)
        .options(selectinload(HaccpChecklist.records))
        .where(HaccpChecklist.id == checklist_id)
    )
    result = await db.execute(query)
    checklist = result.scalar_one_or_none()
    if not checklist:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Checklist not found"}}

    data = _checklist_to_dict(checklist)
    data["records"] = [
        {
            "id": str(r.id),
            "ccp_point": r.ccp_point,
            "category": r.category,
            "target_value": r.target_value,
            "actual_value": r.actual_value,
            "is_compliant": r.is_compliant,
            "corrective_action": r.corrective_action,
            "recorded_by": str(r.recorded_by),
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
        }
        for r in checklist.records
    ]
    return {"success": True, "data": data}


# ── Records ──

@router.post("/records")
async def submit_record(
    body: CcpRecordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("QLT", "KIT", "ADM"),
):
    """Submit CCP record."""
    record = HaccpRecord(
        checklist_id=body.checklist_id,
        ccp_point=body.ccp_point,
        category=body.category,
        target_value=body.target_value,
        actual_value=body.actual_value,
        is_compliant=body.is_compliant,
        corrective_action=body.corrective_action,
        recorded_by=current_user.id,
    )
    db.add(record)

    # Update checklist status to in_progress if pending
    result = await db.execute(
        select(HaccpChecklist).where(HaccpChecklist.id == body.checklist_id)
    )
    checklist = result.scalar_one_or_none()
    if checklist and checklist.status == "pending":
        checklist.status = "in_progress"

    # Audit log
    if checklist:
        db.add(AuditLog(
            user_id=current_user.id,
            site_id=checklist.site_id,
            action="create",
            entity_type="haccp_record",
            entity_id=record.id,
            changes={"ccp_point": body.ccp_point, "is_compliant": body.is_compliant},
        ))

    await db.flush()
    return {
        "success": True,
        "data": {
            "id": str(record.id),
            "checklist_id": str(record.checklist_id),
            "ccp_point": record.ccp_point,
            "actual_value": record.actual_value,
            "is_compliant": record.is_compliant,
        },
    }


@router.get("/records")
async def list_records(
    checklist_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("QLT", "OPS", "ADM"),
):
    """List records filtered by checklist."""
    query = select(HaccpRecord)
    if checklist_id:
        query = query.where(HaccpRecord.checklist_id == checklist_id)
    query = query.order_by(HaccpRecord.recorded_at.desc())
    result = await db.execute(query)
    records = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": str(r.id),
                "checklist_id": str(r.checklist_id),
                "ccp_point": r.ccp_point,
                "category": r.category,
                "target_value": r.target_value,
                "actual_value": r.actual_value,
                "is_compliant": r.is_compliant,
                "corrective_action": r.corrective_action,
                "recorded_by": str(r.recorded_by),
                "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            }
            for r in records
        ],
    }


# ── Submit (complete) checklist ──

@router.post("/checklists/{checklist_id}/submit")
async def submit_checklist(
    checklist_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("QLT", "KIT", "ADM"),
):
    """Mark checklist as completed."""
    result = await db.execute(
        select(HaccpChecklist).where(HaccpChecklist.id == checklist_id)
    )
    checklist = result.scalar_one_or_none()
    if not checklist:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Checklist not found"}}

    checklist.status = "completed"
    checklist.completed_by = current_user.id
    checklist.completed_at = datetime.now(timezone.utc)

    db.add(AuditLog(
        user_id=current_user.id,
        site_id=checklist.site_id,
        action="update",
        entity_type="haccp_checklist",
        entity_id=checklist.id,
        changes={"status": {"old": "in_progress", "new": "completed"}},
    ))
    await db.flush()

    return {"success": True, "data": _checklist_to_dict(checklist)}


# ── Incidents ──

@router.post("/incidents")
async def report_incident(
    body: IncidentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("QLT", "NUT", "KIT", "OPS", "ADM"),
):
    """Report a new incident."""
    # Immediate response steps based on severity
    response_steps = _get_response_steps(body.incident_type, body.severity)

    incident = HaccpIncident(
        site_id=body.site_id,
        incident_type=body.incident_type,
        severity=body.severity,
        description=body.description,
        steps_taken=response_steps,
        status="open",
        reported_by=current_user.id,
    )
    db.add(incident)

    db.add(AuditLog(
        user_id=current_user.id,
        site_id=body.site_id,
        action="create",
        entity_type="haccp_incident",
        entity_id=incident.id,
        changes={"severity": body.severity, "type": body.incident_type},
    ))
    await db.flush()

    return {
        "success": True,
        "data": _incident_to_dict(incident),
    }


@router.get("/incidents")
async def list_incidents(
    site_id: UUID | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("QLT", "OPS", "ADM"),
):
    """List incidents with filters."""
    query = select(HaccpIncident)
    count_query = select(func.count(HaccpIncident.id))

    if site_id:
        query = query.where(HaccpIncident.site_id == site_id)
        count_query = count_query.where(HaccpIncident.site_id == site_id)
    if status:
        query = query.where(HaccpIncident.status == status)
        count_query = count_query.where(HaccpIncident.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(HaccpIncident.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    incidents = result.scalars().all()

    return {
        "success": True,
        "data": [_incident_to_dict(i) for i in incidents],
        "meta": {"page": page, "per_page": per_page, "total": total},
    }


@router.put("/incidents/{incident_id}")
async def update_incident(
    incident_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("QLT", "OPS", "ADM"),
):
    """Update incident status or details."""
    result = await db.execute(
        select(HaccpIncident).where(HaccpIncident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    if not incident:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Incident not found"}}

    old_status = incident.status
    if "status" in body:
        incident.status = body["status"]
        if body["status"] == "resolved":
            incident.resolved_by = current_user.id
            incident.resolved_at = datetime.now(timezone.utc)
    if "steps_taken" in body:
        incident.steps_taken = body["steps_taken"]

    db.add(AuditLog(
        user_id=current_user.id,
        site_id=incident.site_id,
        action="update",
        entity_type="haccp_incident",
        entity_id=incident.id,
        changes={"status": {"old": old_status, "new": incident.status}},
    ))
    await db.flush()

    return {"success": True, "data": _incident_to_dict(incident)}


# ── Reports ──

@router.post("/reports/audit")
async def generate_audit_report(
    body: AuditReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("QLT", "OPS", "ADM"),
):
    """Generate audit report for a period."""
    # Checklists stats
    cl_query = (
        select(HaccpChecklist)
        .where(HaccpChecklist.site_id == body.site_id)
        .where(HaccpChecklist.date >= body.start_date)
        .where(HaccpChecklist.date <= body.end_date)
    )
    cl_result = await db.execute(cl_query)
    checklists = cl_result.scalars().all()

    total_cl = len(checklists)
    completed_cl = sum(1 for c in checklists if c.status == "completed")
    overdue_cl = sum(1 for c in checklists if c.status in ("pending", "overdue"))

    # CCP records stats
    checklist_ids = [c.id for c in checklists]
    total_records = 0
    compliant_records = 0
    noncompliant_records = 0
    if checklist_ids:
        rec_query = select(HaccpRecord).where(HaccpRecord.checklist_id.in_(checklist_ids))
        rec_result = await db.execute(rec_query)
        records = rec_result.scalars().all()
        total_records = len(records)
        compliant_records = sum(1 for r in records if r.is_compliant)
        noncompliant_records = sum(1 for r in records if r.is_compliant is False)

    # Incidents stats
    inc_query = (
        select(HaccpIncident)
        .where(HaccpIncident.site_id == body.site_id)
        .where(HaccpIncident.created_at >= datetime.combine(body.start_date, datetime.min.time()))
        .where(HaccpIncident.created_at <= datetime.combine(body.end_date, datetime.max.time()))
    )
    inc_result = await db.execute(inc_query)
    incidents = inc_result.scalars().all()

    severity_counts = {}
    for inc in incidents:
        severity_counts[inc.severity] = severity_counts.get(inc.severity, 0) + 1

    report = {
        "period": {"start": str(body.start_date), "end": str(body.end_date)},
        "site_id": str(body.site_id),
        "checklists": {
            "total": total_cl,
            "completed": completed_cl,
            "overdue": overdue_cl,
            "completion_rate": round(completed_cl / total_cl * 100, 1) if total_cl else 0,
        },
        "ccp_records": {
            "total": total_records,
            "compliant": compliant_records,
            "noncompliant": noncompliant_records,
            "compliance_rate": round(compliant_records / total_records * 100, 1) if total_records else 0,
        },
        "incidents": {
            "total": len(incidents),
            "by_severity": severity_counts,
            "resolved": sum(1 for i in incidents if i.status in ("resolved", "closed")),
        },
    }

    return {"success": True, "data": report}


# ── Completion status ──

@router.get("/completion-status")
async def check_completion_status(
    site_id: UUID = Query(...),
    target_date: date = Query(None, alias="date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role("QLT", "OPS", "ADM"),
):
    """Check daily HACCP completion status."""
    if not target_date:
        target_date = date.today()

    query = (
        select(HaccpChecklist)
        .where(HaccpChecklist.site_id == site_id)
        .where(HaccpChecklist.date == target_date)
    )
    result = await db.execute(query)
    checklists = result.scalars().all()

    total = len(checklists)
    completed = sum(1 for c in checklists if c.status == "completed")
    in_progress = sum(1 for c in checklists if c.status == "in_progress")
    pending = sum(1 for c in checklists if c.status == "pending")
    overdue = sum(1 for c in checklists if c.status == "overdue")

    return {
        "success": True,
        "data": {
            "date": str(target_date),
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "overdue": overdue,
            "completion_rate": round(completed / total * 100, 1) if total else 0,
        },
    }


# ── Helpers ──

def _checklist_to_dict(c: HaccpChecklist) -> dict:
    return {
        "id": str(c.id),
        "site_id": str(c.site_id),
        "date": str(c.date),
        "checklist_type": c.checklist_type,
        "meal_type": c.meal_type,
        "template": c.template,
        "status": c.status,
        "completed_at": c.completed_at.isoformat() if c.completed_at else None,
    }


def _incident_to_dict(i: HaccpIncident) -> dict:
    return {
        "id": str(i.id),
        "site_id": str(i.site_id),
        "incident_type": i.incident_type,
        "severity": i.severity,
        "description": i.description,
        "steps_taken": i.steps_taken or [],
        "status": i.status,
        "reported_by": str(i.reported_by),
        "created_at": i.created_at.isoformat() if i.created_at else None,
        "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
    }


def _get_response_steps(incident_type: str, severity: str) -> list[dict]:
    """Return immediate response steps based on incident type and severity."""
    base_steps = [
        {"step": 1, "action": "현장 상황 확인 및 기록", "done": False},
        {"step": 2, "action": "관련 식품/구역 격리", "done": False},
    ]

    if severity in ("high", "critical"):
        base_steps.extend([
            {"step": 3, "action": "해당 식품 즉시 제공 중단", "done": False},
            {"step": 4, "action": "관리자 및 보건소 즉시 보고", "done": False},
            {"step": 5, "action": "보존식 확보 및 샘플 보관", "done": False},
            {"step": 6, "action": "관련 조리종사자 업무 중단", "done": False},
            {"step": 7, "action": "해당 구역 소독 실시", "done": False},
        ])
    else:
        base_steps.extend([
            {"step": 3, "action": "원인 분석 및 시정조치", "done": False},
            {"step": 4, "action": "관리자 보고", "done": False},
            {"step": 5, "action": "재발 방지 대책 수립", "done": False},
        ])

    if incident_type == "temperature":
        base_steps.append({"step": len(base_steps) + 1, "action": "온도계 교정 확인", "done": False})
    elif incident_type == "contamination":
        base_steps.append({"step": len(base_steps) + 1, "action": "오염원 추적 조사", "done": False})

    return base_steps
