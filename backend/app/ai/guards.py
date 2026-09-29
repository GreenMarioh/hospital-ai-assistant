"""Output safety guard: the assistant must never diagnose or recommend medication."""

import re

DISCLAIMER = (
    "AI-generated decision support, not a diagnosis or medical advice. "
    "Requires clinician review. In an emergency call your local emergency number."
)
SAFE_FALLBACK_REPLY = (
    "I can't give a diagnosis or medication advice. Based on what you've told me, "
    "please consider booking an appointment so a clinician can assess you."
)

_CONDITIONS = (
    r"infection|flu|influenza|covid|pneumonia|migraine|appendicitis|cancer|diabetes|arthritis|asthma|"
    r"bronchitis|angina|heart\s+attack|stroke|anxiety|depression|allergy|eczema|psoriasis|gastritis|"
    r"ulcer|hypertension|anemia|tumou?r|fracture|sprain|concussion|sinusitis|tonsillitis"
)
_DIAGNOSIS = re.compile(
    r"\byou\s+(likely|probably|possibly|may|might|could)\s+(well\s+)?have\b|"
    rf"\byou\s+(have|are\s+suffering\s+from|suffer\s+from|are\s+diagnosed\s+with)\s+(an?\s+)?({_CONDITIONS})\b|"
    rf"\b(this|it|that)\s+(is|sounds\s+like|looks\s+like|could\s+be|might\s+be|may\s+be|seems\s+to\s+be)\s+(an?\s+)?(case\s+of\s+)?({_CONDITIONS})\b|"
    r"\bdiagnos(is|ed)\s+(is|as|with)\b|\bthe\s+diagnosis\b",
    re.IGNORECASE,
)
_MEDICATION = re.compile(
    r"\b(take|taking|use|apply|try|give)\s+(some\s+|an?\s+|the\s+)?"
    r"(\d+\s*(mg|mcg|ml|g|tablets?|pills?)|ibuprofen|paracetamol|acetaminophen|aspirin|antibiotics?|"
    r"amoxicillin|naproxen|antihistamines?|cough\s+syrup|painkillers?|steroids?|antacids?)\b|"
    r"\bprescribe\b|\bdosage\b",
    re.IGNORECASE,
)


def violates_safety(text: str) -> bool:
    return bool(_DIAGNOSIS.search(text) or _MEDICATION.search(text))


def sanitize_reply(text: str) -> tuple[str, bool]:
    """Returns (safe text, was_replaced)."""
    if violates_safety(text):
        return SAFE_FALLBACK_REPLY, True
    return text, False
