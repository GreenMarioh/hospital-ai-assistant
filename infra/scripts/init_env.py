#!/usr/bin/env python3
"""Create .env from .env.example (if missing) and fill blank/placeholder secrets with random values."""

import base64
import re
import secrets
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[2]
env, example = root / ".env", root / ".env.example"
created = not env.exists()
if created:
    shutil.copy(example, env)
text = env.read_text()


def fill(key: str, value: str, placeholder: str) -> None:
    global text
    m = re.search(rf"^{key}=(.*)$", text, re.M)
    current = (m.group(1).split("#")[0].strip() if m else "")
    if not m or current in ("", placeholder) or current.startswith("change-me"):
        line = f"{key}={value}"
        text = re.sub(rf"^{key}=.*$", line, text, flags=re.M) if m else text + f"\n{line}\n"


fill("SECRET_KEY", secrets.token_urlsafe(48), "change-me-32+chars-random")
fill("FIELD_ENCRYPTION_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(), "change-me-fernet-key")
pg, app = secrets.token_hex(12), secrets.token_hex(12)
# DB passwords are only randomised on first creation: an existing Postgres volume keeps its old passwords.
if created and "POSTGRES_PASSWORD=change-me" in text:
    text = text.replace("POSTGRES_PASSWORD=change-me", f"POSTGRES_PASSWORD={pg}")
    text = text.replace("hospital_migrator:change-me@", f"hospital_migrator:{pg}@")
if created and "APP_DB_PASSWORD=change-me-too" in text:
    text = text.replace("APP_DB_PASSWORD=change-me-too", f"APP_DB_PASSWORD={app}")
    text = text.replace("hospital_app:change-me-too@", f"hospital_app:{app}@")
env.write_text(text)
env.chmod(0o600)
print(f"{env} ready (secrets generated where they were blank or placeholders)")
