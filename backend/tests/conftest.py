import os
import uuid

import asyncpg
import pytest
import pytest_asyncio
from argon2 import PasswordHasher
from cryptography.fernet import Fernet

TEST_DB = "hospital_test"
ADMIN_DSN = os.environ.get(
    "TEST_ADMIN_DSN", "postgresql://hospital_migrator:change-me@127.0.0.1:5433/postgres"
)
os.environ["DATABASE_URL"] = (
    f"postgresql+asyncpg://hospital_migrator:change-me@127.0.0.1:5433/{TEST_DB}"
)
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["FIELD_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["SECRET_KEY"] = "test-secret-key-test-secret-key-test-secret"
os.environ["ENVIRONMENT"] = "test"
os.environ["AI_ENABLED"] = "true"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["UPLOAD_DIR"] = "/tmp/hospital-test-uploads"

from app.core import security

security._hasher = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.db import SessionLocal, audit_engine, engine
from app.main import app
from app.models import Base
from app.seed import seed

PASSWORD = "DemoPass!12345"
ADMIN = ("admin@hospital.example.com", "ChangeMe!12345")
TRANSIENT = [
    "audit_logs", "refresh_tokens", "password_reset_tokens", "appointments", "waitlist_entries",
    "visits", "prescriptions", "documents", "record_versions", "notifications", "ai_summaries",
    "ai_messages", "ai_conversations", "availability_exceptions",
]  # fmt: skip


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _database():
    conn = await asyncpg.connect(ADMIN_DSN)
    await conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
    await conn.execute(f"CREATE DATABASE {TEST_DB}")
    await conn.close()
    async with engine.begin() as c:
        await c.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        await c.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        await seed(db)
    yield
    await engine.dispose()
    await audit_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean():
    async with engine.begin() as c:
        await c.execute(text(f"TRUNCATE {', '.join(TRANSIENT)} RESTART IDENTITY CASCADE"))
        await c.execute(
            text("UPDATE users SET failed_attempts=0, locked_until=NULL, is_active=true")
        )
        await c.execute(
            text("DELETE FROM users WHERE email NOT LIKE '%@hospital.example.com' "
                 "AND email NOT LIKE '%@example.com'")
        )  # fmt: skip
    yield


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def login_headers(client: AsyncClient, email: str, password: str = PASSWORD) -> dict:
    r = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def unique_email():
    return lambda: f"user-{uuid.uuid4().hex[:10]}@tests.dev"
