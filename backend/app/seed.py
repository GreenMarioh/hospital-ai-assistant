"""Idempotent seed: roles, departments, demo doctors, admin, staff and synthetic patients.

Run: python -m app.seed   (only synthetic demo data; never real patient data)
"""

import asyncio
import os
from datetime import date, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import encrypt_field
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import Department, Doctor, DoctorAvailability, Patient, Role, User

ROLES = ["admin", "doctor", "staff", "patient"]
DEPARTMENTS = {
    "Cardiology": "Heart and vascular care",
    "General Medicine": "Primary and internal medicine",
    "Orthopedics": "Bones, joints and muscles",
    "Pediatrics": "Child health",
    "Dermatology": "Skin conditions",
    "Neurology": "Nervous system",
    "Emergency": "Emergency and trauma care",
}
DOCTORS = [
    ("Asha Rao", "Cardiology", "Cardiologist"),
    ("Vikram Shah", "General Medicine", "Physician"),
    ("Meera Nair", "Orthopedics", "Orthopedic surgeon"),
    ("Rohan Iyer", "Pediatrics", "Pediatrician"),
    ("Neha Kapoor", "Dermatology", "Dermatologist"),
    ("Arjun Menon", "Neurology", "Neurologist"),
]
PATIENTS = [
    ("Demo", "Patient One", date(1985, 3, 14), "9000000001", ["penicillin"], "O+"),
    ("Demo", "Patient Two", date(1992, 7, 2), "9000000002", [], "A+"),
    ("Demo", "Patient Three", date(1968, 11, 30), "9000000003", ["latex"], "B-"),
]


async def _get_or_create_user(
    db: AsyncSession, email: str, name: str, role: Role, password: str
) -> User:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(
            email=email, full_name=name, role_id=role.id, password_hash=hash_password(password)
        )
        db.add(user)
        await db.flush()
    return user


async def seed(db: AsyncSession) -> None:
    roles: dict[str, Role] = {}
    for name in ROLES:
        role = (await db.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
        if role is None:
            role = Role(name=name)
            db.add(role)
            await db.flush()
        roles[name] = role

    depts: dict[str, Department] = {}
    for dept_name, desc in DEPARTMENTS.items():
        found = (
            await db.execute(select(Department).where(Department.name == dept_name))
        ).scalar_one_or_none()
        if found is None:
            found = Department(name=dept_name, description=desc)
            db.add(found)
            await db.flush()
        depts[dept_name] = found

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@hospital.example.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "ChangeMe!12345")
    await _get_or_create_user(db, admin_email, "System Admin", roles["admin"], admin_password)

    demo_pw = os.environ.get("DEMO_PASSWORD", "DemoPass!12345")
    if get_settings().environment != "prod":
        await _get_or_create_user(
            db, "staff@hospital.example.com", "Front Desk", roles["staff"], demo_pw
        )
        for i, (name, dept_key, spec) in enumerate(DOCTORS):
            email = f"doctor{i + 1}@hospital.example.com"
            user = await _get_or_create_user(db, email, f"Dr. {name}", roles["doctor"], demo_pw)
            doc = (
                await db.execute(select(Doctor).where(Doctor.user_id == user.id))
            ).scalar_one_or_none()
            if doc is None:
                doc = Doctor(user_id=user.id, department_id=depts[dept_key].id, specialization=spec)
                db.add(doc)
                await db.flush()
                for weekday in range(5):
                    db.add(
                        DoctorAvailability(
                            doctor_id=doc.id, weekday=weekday, start_time=time(9), end_time=time(17)
                        )
                    )
        for i, (first, last, dob, phone, allergies, bg) in enumerate(PATIENTS):
            email = f"patient{i + 1}@example.com"
            user = await _get_or_create_user(
                db, email, f"{first} {last}", roles["patient"], demo_pw
            )
            exists = (
                await db.execute(select(Patient).where(Patient.user_id == user.id))
            ).scalar_one_or_none()
            if exists is None and get_settings().field_encryption_key:
                db.add(
                    Patient(
                        user_id=user.id,
                        first_name=first,
                        last_name=last,
                        date_of_birth=dob,
                        phone=phone,
                        email=email,
                        allergies=allergies,
                        blood_group=bg,
                        insurance_provider="Demo Insurance",
                        insurance_id_encrypted=encrypt_field(f"DEMO-{i + 1:06d}"),
                    )
                )
    await db.commit()


async def main() -> None:
    async with SessionLocal() as db:
        await seed(db)
    print("seed complete")


if __name__ == "__main__":
    asyncio.run(main())
