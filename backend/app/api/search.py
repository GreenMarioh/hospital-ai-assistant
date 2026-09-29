from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_roles
from app.models import Patient, User, Visit
from app.schemas.records import SearchHit
from app.services.access import get_doctor_for_user, get_patient_for_user

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/records", response_model=list[SearchHit])
async def search_records(
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("doctor", "patient")),
) -> list[SearchHit]:
    """Full-text search over visit records, scoped to what the caller may read."""
    tsq = func.websearch_to_tsquery("english", q)
    stmt = (
        select(
            Visit.id,
            Visit.patient_id,
            func.ts_headline(
                "english",
                func.concat_ws(" ", Visit.chief_complaint, Visit.notes, Visit.diagnosis),
                tsq,
                "MaxFragments=1,MaxWords=25,MinWords=8",
            ),
            func.ts_rank(Visit.search_vector, tsq),
        )
        .where(Visit.search_vector.op("@@")(tsq), Visit.deleted_at.is_(None))
        .order_by(func.ts_rank(Visit.search_vector, tsq).desc())
        .limit(limit)
    )
    if user.role.name == "doctor":
        doctor = await get_doctor_for_user(db, user)
        stmt = stmt.where(Visit.doctor_id == (doctor.id if doctor else None))
    else:
        patient: Patient | None = await get_patient_for_user(db, user)
        stmt = stmt.where(Visit.patient_id == (patient.id if patient else None))
    rows = (await db.execute(stmt)).all()
    return [SearchHit(visit_id=r[0], patient_id=r[1], snippet=r[2], rank=float(r[3])) for r in rows]
