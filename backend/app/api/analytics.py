import csv
import io
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import Date, Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import require_roles
from app.models import (
    AIConversation,
    AIMessage,
    Appointment,
    AuditLog,
    Department,
    Doctor,
    Document,
    Patient,
    Prescription,
    User,
    Visit,
)
from app.services.scheduling import hospital_tz

router = APIRouter(prefix="/api/admin", tags=["admin"])
MAX_RANGE_DAYS = 366


def _range(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    end = date_to or datetime.now(hospital_tz()).date()
    start = date_from or end - timedelta(days=29)
    if end < start or (end - start).days > MAX_RANGE_DAYS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid date range")
    return start, end


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    tz = hospital_tz()
    return (
        datetime.combine(start, datetime.min.time(), tzinfo=tz),
        datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=tz),
    )


async def compute_summary(db: AsyncSession, start: date, end: date) -> dict[str, Any]:
    lo, hi = _bounds(start, end)
    tzname = get_settings().hospital_timezone
    in_range = (Appointment.starts_at >= lo) & (Appointment.starts_at < hi)
    day = cast(func.timezone(tzname, Appointment.starts_at), Date)

    per_day_rows = (
        await db.execute(
            select(day.label("d"), Appointment.status, func.count())
            .where(in_range)
            .group_by("d", Appointment.status)
        )
    ).all()
    per_day: dict[str, dict[str, int]] = {}
    for d, st, n in per_day_rows:
        per_day.setdefault(d.isoformat(), {})[st] = n
    series: list[dict[str, Any]] = []
    cur = start
    while cur <= end:
        counts = per_day.get(cur.isoformat(), {})
        series.append(
            {
                "date": cur.isoformat(),
                "total": sum(counts.values()),
                **{k: counts.get(k, 0) for k in ("booked", "completed", "cancelled", "no_show")},
            }
        )
        cur += timedelta(days=1)

    totals: dict[str, int] = {
        k: sum(int(s[k]) for s in series)
        for k in ("total", "booked", "completed", "cancelled", "no_show")
    }
    attended = totals["completed"] + totals["no_show"]
    no_show_rate = totals["no_show"] / attended if attended else 0.0

    lead = (
        await db.execute(
            select(
                func.avg(func.extract("epoch", Appointment.starts_at - Appointment.created_at))
            ).where(in_range, Appointment.status != "cancelled")
        )
    ).scalar()
    avg_lead_hours = round(float(lead) / 3600, 1) if lead is not None else None

    dept_rows = (
        await db.execute(
            select(Department.name, func.count(Appointment.id))
            .select_from(Appointment)
            .join(Doctor, Doctor.id == Appointment.doctor_id)
            .join(Department, Department.id == Doctor.department_id)
            .where(in_range, Appointment.status.in_(("booked", "completed", "no_show")))
            .group_by(Department.name)
            .order_by(func.count(Appointment.id).desc())
        )
    ).all()

    msg_in_range = (AIMessage.created_at >= lo) & (AIMessage.created_at < hi)
    convs = (
        await db.execute(
            select(AIConversation.kind, func.count())
            .where(AIConversation.created_at >= lo, AIConversation.created_at < hi)
            .group_by(AIConversation.kind)
        )
    ).all()
    src = AIMessage.meta["source"].astext
    sources: dict[str | None, int] = dict(
        (
            await db.execute(
                select(src, func.count())
                .where(msg_in_range, AIMessage.role == "assistant")
                .group_by(src)
            )
        ).all()
    )
    perf = (
        await db.execute(
            select(
                func.avg(cast(AIMessage.meta["latency_ms"].astext, Float)),
                func.coalesce(func.sum(cast(AIMessage.meta["input_tokens"].astext, Float)), 0),
                func.coalesce(func.sum(cast(AIMessage.meta["output_tokens"].astext, Float)), 0),
            ).where(msg_in_range, src == "llm")
        )
    ).one()
    return {
        "range": {"from": start.isoformat(), "to": end.isoformat(), "timezone": tzname},
        "appointments": {"totals": totals, "per_day": series},
        "no_show_rate": round(no_show_rate, 4),
        "avg_booking_lead_hours": avg_lead_hours,
        "department_load": [{"department": n, "appointments": c} for n, c in dept_rows],
        "ai_usage": {
            "conversations": {k: c for k, c in convs},
            "llm_replies": sources.get("llm", 0),
            "rule_based_emergency_responses": sources.get("rules", 0),
            "degraded_responses": sources.get("fallback", 0),
            "avg_latency_ms": round(float(perf[0]), 1) if perf[0] is not None else None,
            "input_tokens": int(perf[1]),
            "output_tokens": int(perf[2]),
        },
    }


@router.get("/analytics/summary")
async def analytics_summary(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> dict[str, Any]:
    start, end = _range(date_from, date_to)
    return await compute_summary(db, start, end)


def _csv_cell(value: Any) -> Any:
    """Neutralise spreadsheet formula injection."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


@router.get("/analytics/export.csv")
async def analytics_export(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> Response:
    start, end = _range(date_from, date_to)
    data = await compute_summary(db, start, end)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "total", "booked", "completed", "cancelled", "no_show"])
    for row in data["appointments"]["per_day"]:
        w.writerow(
            [
                _csv_cell(row[k])
                for k in ("date", "total", "booked", "completed", "cancelled", "no_show")
            ]
        )
    w.writerow([])
    w.writerow(["department", "appointments"])
    for d in data["department_load"]:
        w.writerow([_csv_cell(d["department"]), d["appointments"]])
    w.writerow([])
    w.writerow(["no_show_rate", data["no_show_rate"]])
    w.writerow(["avg_booking_lead_hours", data["avg_booking_lead_hours"]])
    return Response(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="analytics_{start}_{end}.csv"'},
    )


@router.get("/audit-logs")
async def audit_logs(
    user_id: uuid.UUID | None = None,
    resource_type: str | None = Query(default=None, max_length=40),
    action: str | None = Query(default=None, max_length=16),
    status_code: int | None = None,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> dict[str, Any]:
    stmt = select(AuditLog)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type.startswith(resource_type))
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if status_code:
        stmt = stmt.where(AuditLog.status_code == status_code)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= _bounds(date_from, date_from)[0])
    if date_to:
        stmt = stmt.where(AuditLog.created_at < _bounds(date_to, date_to)[1])
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        await db.execute(stmt.order_by(AuditLog.id.desc()).offset((page - 1) * size).limit(size))
    ).scalars()
    items = [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat(),
            "user_id": str(r.user_id) if r.user_id else None,
            "role": r.role,
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "method": r.method,
            "path": r.path,
            "status_code": r.status_code,
            "ip": r.ip,
            "request_id": r.request_id,
        }
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/patients/{patient_id}/export")
async def export_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> dict[str, Any]:
    """Data-subject export (admin-controlled). The access itself is audit-logged."""
    patient = await db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")

    appts = list(
        (
            await db.execute(select(Appointment).where(Appointment.patient_id == patient_id))
        ).scalars()
    )
    visits = list((await db.execute(select(Visit).where(Visit.patient_id == patient_id))).scalars())
    visit_ids = [v.id for v in visits] or [uuid.uuid4()]
    rx = list(
        (
            await db.execute(select(Prescription).where(Prescription.visit_id.in_(visit_ids)))
        ).scalars()
    )
    docs = list(
        (await db.execute(select(Document).where(Document.patient_id == patient_id))).scalars()
    )

    def plain(o: Any) -> dict[str, Any]:
        return {
            c.key: getattr(o, c.key)
            for c in o.__table__.columns
            if c.key not in ("insurance_id_encrypted", "storage_key", "search_vector")
        }

    return jsonable_encoder(
        {
            "exported_at": datetime.now(UTC),
            "patient": plain(patient),
            "appointments": [plain(a) for a in appts],
            "visits": [plain(v) for v in visits],
            "prescriptions": [plain(p) for p in rx],
            "documents": [plain(d) for d in docs],
        }
    )


@router.post("/patients/{patient_id}/deletion-request", status_code=status.HTTP_202_ACCEPTED)
async def deletion_request(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
) -> dict[str, str]:
    """Erasure request handling: the patient is soft-deleted and their portal account deactivated.
    Clinical data is retained per retention policy; hard deletion is a manual, documented DB operation.
    """
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    patient.deleted_at = datetime.now(UTC)
    if patient.user_id:
        user = await db.get(User, patient.user_id)
        if user:
            user.is_active = False
    await db.commit()
    return {"status": "soft_deleted", "note": "Clinical records retained per retention policy"}
