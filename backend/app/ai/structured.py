"""Structured LLM output: JSON extraction + Pydantic validation, one repair retry, then fail."""

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from app.ai.client import LLM, LLMResponse
from app.ai.errors import AIInvalidOutput

log = logging.getLogger("app.ai")
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def extract_json(text: str) -> Any:
    text = _FENCE.sub("", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


async def complete_json[T: BaseModel](
    llm: LLM,
    model_cls: type[T],
    *,
    purpose: str,
    system: str,
    messages: list[dict[str, Any]],
    max_tokens: int = 1500,
) -> tuple[T, LLMResponse]:
    """Returns the validated object and the (last) response. Retries once on invalid output."""
    convo = list(messages)
    last_error = ""
    for attempt in range(2):
        resp = await llm.complete(
            purpose=purpose, system=system, messages=convo, max_tokens=max_tokens, json_output=True
        )
        try:
            return model_cls.model_validate(extract_json(resp.text)), resp
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = type(exc).__name__
            log.warning(
                "ai invalid output",
                extra={"purpose": purpose, "attempt": attempt + 1, "error": last_error},
            )
            convo = [
                *messages,
                {"role": "assistant", "content": resp.text or "{}"},
                {
                    "role": "user",
                    "content": "That was not valid. Reply with ONLY one JSON object matching the required schema.",
                },
            ]
    raise AIInvalidOutput(f"{purpose}: invalid model output ({last_error})")
