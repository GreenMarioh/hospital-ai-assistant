"""PII minimisation before anything is sent to the LLM."""

import re
from datetime import UTC, date, datetime

from app.models import Patient

_PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+"), "[email]"),
    (re.compile(r"(?<!\d)(\+?\d[\d\s().-]{7,}\d)(?!\d)"), "[phone]"),
    (re.compile(r"\b(?:\d[ -]?){12,19}\b"), "[number]"),
]


def scrub(text: str | None, extra_names: tuple[str, ...] = ()) -> str:
    """Remove emails, phone/ID-like numbers and (optionally) known names from free text."""
    if not text:
        return ""
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    for name in extra_names:
        if len(name) > 1:
            text = re.sub(re.escape(name), "[name]", text, flags=re.IGNORECASE)
    return text


def age_years(dob: date, today: date | None = None) -> int:
    today = today or datetime.now(UTC).date()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def patient_context(patient: Patient, include_allergies: bool = False) -> dict:
    """Only what clinical routing needs: age, sex, blood group never sent; no names, contacts or insurance."""
    ctx: dict = {"age_years": age_years(patient.date_of_birth)}
    if patient.sex:
        ctx["sex"] = patient.sex
    if include_allergies:
        ctx["allergies"] = list(patient.allergies or [])
    return ctx


def patient_names(patient: Patient) -> tuple[str, ...]:
    return (patient.first_name, patient.last_name)
