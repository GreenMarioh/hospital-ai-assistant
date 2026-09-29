from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RecordVersion, User


async def snapshot(
    db: AsyncSession, entity_type: str, entity: object, columns: list[str], user: User
) -> int:
    """Store the pre-edit state as the next immutable version; returns the new version number."""
    entity_id = entity.id  # type: ignore[attr-defined]
    current = (
        await db.execute(
            select(func.coalesce(func.max(RecordVersion.version), 0)).where(
                RecordVersion.entity_type == entity_type, RecordVersion.entity_id == entity_id
            )
        )
    ).scalar_one()
    data = jsonable_encoder({c: getattr(entity, c) for c in columns})
    db.add(
        RecordVersion(
            entity_type=entity_type,
            entity_id=entity_id,
            version=current + 1,
            data=data,
            changed_by=user.id,
        )
    )
    return current + 2  # the live record is one ahead of the latest snapshot
