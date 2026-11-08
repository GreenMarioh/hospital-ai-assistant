"""LLM client wrapper (Google Gemini): timeouts, retries with backoff, circuit breaker, usage logging.

Two models are used: a Gemini Pro model for clinical reasoning (triage, summaries) and a Gemini
Flash model for latency-sensitive conversational work (booking assistant, FAQ). Routing is by
`purpose`; see `FLASH_PURPOSES`.

Callers speak a small provider-neutral message format, translated here:
  {"role": "user" | "assistant", "content": str | list[block]}
  block = {"type": "tool_use", "id", "name", "input"}            (assistant)
        | {"type": "tool_result", "tool_use_id", "name", "content"}  (user)
        | a native `types.Part` echoed back from `LLMResponse.raw_content`
Tools are {"name", "description", "input_schema": <JSON Schema>}.
"""

import asyncio
import json
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

import httpx
import httpx2
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.ai.errors import AIUnavailable
from app.core.config import get_settings

log = logging.getLogger("app.ai")

REQUEST_TIMEOUT_S = 30.0
MAX_ATTEMPTS = 3
THINKING_LEVELS = {"minimal", "low", "medium", "high"}
# Gemini counts thinking tokens against max_output_tokens. Callers size `max_tokens` for the visible
# answer, so add headroom for thoughts; it is only a cap, unused tokens are not billed.
THINKING_HEADROOM_TOKENS = 8192
# Conversational, latency-sensitive purposes go to Flash; everything else (clinical) goes to Pro.
FLASH_PURPOSES = frozenset({"booking", "faq"})

_TRANSPORT_ERRORS: tuple[type[BaseException], ...] = (
    httpx.TransportError,
    httpx2.TransportError,
    TimeoutError,
)


@dataclass
class ToolUse:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class LLMResponse:
    text: str
    tool_uses: list[ToolUse] = field(default_factory=list)
    stop_reason: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    raw_content: list[Any] = field(default_factory=list)  # echoed back verbatim in tool loops
    model: str = ""


class LLM(Protocol):
    async def complete(
        self,
        *,
        purpose: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1500,
        json_output: bool = False,
    ) -> LLMResponse: ...


class CircuitBreaker:
    """Opens after `threshold` consecutive failures; lets one probe through after `reset_s`."""

    def __init__(
        self, threshold: int = 5, reset_s: float = 60.0, clock: Callable[[], float] = time.monotonic
    ):
        self.threshold, self.reset_s, self.clock = threshold, reset_s, clock
        self.failures = 0
        self.opened_at: float | None = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if self.clock() - self.opened_at >= self.reset_s:
            self.opened_at = self.clock()  # half-open: one probe, re-arm the timer
            return True
        return False

    def success(self) -> None:
        self.failures, self.opened_at = 0, None

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = self.clock()

    @property
    def is_open(self) -> bool:
        return self.opened_at is not None and self.clock() - self.opened_at < self.reset_s


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, genai_errors.APIError):
        return exc.code == 429 or exc.code >= 500
    return isinstance(exc, _TRANSPORT_ERRORS)


def _tool_result_payload(content: Any) -> dict[str, Any]:
    """Gemini wants a JSON object as the function response."""
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except json.JSONDecodeError:
            return {"output": content}
    return content if isinstance(content, dict) else {"output": content}


def _to_part(block: Any) -> types.Part:
    if isinstance(block, types.Part):
        return block
    if isinstance(block, str):
        return types.Part.from_text(text=block)
    kind = block.get("type")
    if kind == "text":
        return types.Part.from_text(text=block["text"])
    if kind == "tool_use":
        return types.Part(
            function_call=types.FunctionCall(
                id=block.get("id"), name=block["name"], args=block.get("input") or {}
            )
        )
    if kind == "tool_result":
        return types.Part(
            function_response=types.FunctionResponse(
                id=block.get("tool_use_id"),
                name=block["name"],
                response=_tool_result_payload(block.get("content")),
            )
        )
    raise ValueError(f"unsupported content block: {kind!r}")


def to_contents(messages: list[dict[str, Any]]) -> list[types.Content]:
    contents = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        content = m["content"]
        blocks = content if isinstance(content, list) else [content]
        contents.append(types.Content(role=role, parts=[_to_part(b) for b in blocks]))
    return contents


def to_tools(tools: list[dict[str, Any]]) -> list[Any]:
    return [
        types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=t["name"],
                    description=t.get("description", ""),
                    parameters_json_schema=t.get("input_schema") or {"type": "object"},
                )
                for t in tools
            ]
        )
    ]


class GeminiLLM:
    def __init__(
        self,
        client: Any | None = None,
        model: str | None = None,
        flash_model: str | None = None,
        breaker: CircuitBreaker | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        s = get_settings()
        self.model = model or s.gemini_model
        self.flash_model = flash_model or s.gemini_flash_model
        self.client = client or genai.Client(
            api_key=s.gemini_api_key,
            http_options=types.HttpOptions(timeout=int(REQUEST_TIMEOUT_S * 1000)),
        )
        self.breaker = breaker or CircuitBreaker()
        self.sleep = sleep
        self.thinking = {
            self.model: _level(s.gemini_thinking_level),
            self.flash_model: _level(s.gemini_flash_thinking_level),
        }

    def model_for(self, purpose: str) -> str:
        return self.flash_model if purpose in FLASH_PURPOSES else self.model

    def _config(
        self,
        model: str,
        system: str,
        tools: list[dict[str, Any]] | None,
        max_tokens: int,
        json_output: bool,
    ) -> types.GenerateContentConfig:
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens + THINKING_HEADROOM_TOKENS,
            # We run the tool loop ourselves (booking.py); never let the SDK call anything.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        if tools:
            cfg.tools = to_tools(tools)
        if json_output and not tools:
            cfg.response_mime_type = "application/json"
        if level := self.thinking.get(model):
            cfg.thinking_config = types.ThinkingConfig(thinking_level=level)
        return cfg

    async def complete(
        self,
        *,
        purpose: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1500,
        json_output: bool = False,
    ) -> LLMResponse:
        if not self.breaker.allow():
            raise AIUnavailable("circuit open")
        model = self.model_for(purpose)
        kwargs: dict[str, Any] = {
            "model": model,
            "contents": to_contents(messages),
            "config": self._config(model, system, tools, max_tokens, json_output),
        }
        last: Exception | None = None
        for attempt in range(MAX_ATTEMPTS):
            start = time.perf_counter()
            try:
                resp = await self.client.aio.models.generate_content(**kwargs)
            except Exception as exc:  # noqa: BLE001 - classified below
                last = exc
                log.warning(
                    "ai call failed",
                    extra={"purpose": purpose, "attempt": attempt + 1, "error": type(exc).__name__},
                )
                if not _retryable(exc):
                    break
                if attempt < MAX_ATTEMPTS - 1:
                    jitter = random.uniform(0, 0.25)  # nosec B311 - retry jitter, not security
                    await self.sleep(0.5 * 2**attempt + jitter)
                continue
            latency = (time.perf_counter() - start) * 1000
            self.breaker.success()
            out = self._parse(resp, latency, model)
            # Metadata only: never log prompts or completions (PHI).
            log.info(
                "ai call",
                extra={
                    "purpose": purpose,
                    "model": model,
                    "input_tokens": out.input_tokens,
                    "output_tokens": out.output_tokens,
                    "latency_ms": round(latency, 1),
                    "stop_reason": out.stop_reason,
                },
            )
            return out
        self.breaker.failure()
        raise AIUnavailable(f"provider error: {type(last).__name__}") from last

    @staticmethod
    def _parse(resp: Any, latency: float, model: str) -> LLMResponse:
        candidate = resp.candidates[0] if resp.candidates else None
        parts = list(candidate.content.parts or []) if candidate and candidate.content else []
        text = "".join(p.text for p in parts if p.text and not p.thought)
        tool_uses = [
            ToolUse(
                p.function_call.id or f"call_{i}",
                p.function_call.name or "",
                dict(p.function_call.args or {}),
            )
            for i, p in enumerate(parts)
            if p.function_call
        ]
        # Fill in missing call ids so tool results can reference them; keep everything else
        # (incl. thought signatures, which Gemini requires back in multi-step tool loops) verbatim.
        for i, p in enumerate(parts):
            if p.function_call and not p.function_call.id:
                p.function_call.id = f"call_{i}"
        if tool_uses:
            stop = "tool_use"
        elif candidate and candidate.finish_reason:
            stop = str(getattr(candidate.finish_reason, "value", candidate.finish_reason))
        elif resp.prompt_feedback and resp.prompt_feedback.block_reason:
            stop = f"blocked:{resp.prompt_feedback.block_reason}"
        else:
            stop = None
        usage = resp.usage_metadata
        return LLMResponse(
            text=text,
            tool_uses=tool_uses,
            stop_reason=stop,
            input_tokens=(usage.prompt_token_count or 0) if usage else 0,
            output_tokens=(
                (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
                if usage
                else 0
            ),
            latency_ms=latency,
            raw_content=parts,
            model=model,
        )


def _level(value: str) -> str:
    v = (value or "").strip().lower()
    return v if v in THINKING_LEVELS else ""


_override: LLM | None = None


def set_llm(llm: LLM | None) -> None:
    """Test hook: inject a fake client."""
    global _override
    _override = llm


@lru_cache
def _default_llm() -> GeminiLLM:
    return GeminiLLM()


def ai_configured() -> bool:
    s = get_settings()
    return _override is not None or (s.ai_enabled and bool(s.gemini_api_key))


def get_llm() -> LLM:
    """FastAPI dependency. Raises AIUnavailable when AI is disabled or unconfigured."""
    if _override is not None:
        return _override
    if not ai_configured():
        raise AIUnavailable("AI disabled or not configured")
    return _default_llm()
