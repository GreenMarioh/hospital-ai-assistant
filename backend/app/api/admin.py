from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import user_out
from app.core.db import get_db
from app.core.deps import require_roles
from app.core.security import hash_password_async
from app.models import Department, Doctor, User
from app.schemas.auth import AdminCreateUser, UserOut
from app.schemas.scheduling import DepartmentIn, DepartmentOut
from app.services.auth import get_role

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db), _: User = Depends(require_roles("admin"))
) -> list[UserOut]:
    users = (await db.execute(select(User).order_by(User.created_at))).scalars().all()
    return [user_out(u) for u in users]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: AdminCreateUser,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> UserOut:
    email = body.email.lower()
    if (await db.execute(select(User).where(User.email == email))).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    if body.role == "doctor" and (
        body.department_id is None or not await db.get(Department, body.department_id)
    ):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Valid department_id required")
    role = await get_role(db, body.role)
    user = User(
        email=email,
        password_hash=await hash_password_async(body.password),
        full_name=body.full_name,
        role_id=role.id,
    )
    db.add(user)
    await db.flush()
    if body.role == "doctor" and body.department_id is not None:
        db.add(
            Doctor(
                user_id=user.id,
                department_id=body.department_id,
                specialization=body.specialization,
            )
        )
    await db.commit()
    await db.refresh(user)
    return user_out(user)


@router.patch("/users/{user_id}/active", response_model=UserOut)
async def set_active(
    user_id: str,
    active: bool,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
) -> UserOut:
    import uuid

    user = await db.get(User, uuid.UUID(user_id))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id and not active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate yourself")
    user.is_active = active
    await db.commit()
    return user_out(user)


@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
async def create_department(
    body: DepartmentIn,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> Department:
    name = body.name.strip()
    if (
        await db.execute(select(Department).where(Department.name.ilike(name)))
    ).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Department already exists")
    dept = Department(name=name, description=body.description)
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@router.put("/departments/{department_id}", response_model=DepartmentOut)
async def update_department(
    department_id: int,
    body: DepartmentIn,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("admin")),
) -> Department:
    dept = await db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Department not found")
    clash = (
        await db.execute(
            select(Department).where(
                Department.name.ilike(body.name.strip()), Department.id != department_id
            )
        )
    ).scalar_one_or_none()
    if clash:
        raise HTTPException(status.HTTP_409_CONFLICT, "Department already exists")
    dept.name, dept.description = body.name.strip(), body.description
    await db.commit()
    return dept
