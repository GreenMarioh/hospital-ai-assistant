"""LLM client wrapper: timeouts, retries with backoff, circuit breaker, usage logging."""

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Protocol

import anthropic

from app.ai.errors import AIUnavailable
from app.core.config import get_settings

log = logging.getLogger("app.ai")

REQUEST_TIMEOUT_S = 30.0
MAX_ATTEMPTS = 3


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


class LLM(Protocol):
    async def complete(
        self,
        *,
        purpose: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1500,
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
    if isinstance(exc, anthropic.RateLimitError | anthropic.APIConnectionError):
        return True
    return isinstance(exc, anthropic.APIStatusError) and exc.status_code >= 500


class AnthropicLLM:
    def __init__(
        self,
        client: anthropic.AsyncAnthropic | None = None,
        model: str | None = None,
        breaker: CircuitBreaker | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        s = get_settings()
        self.model = model or s.anthropic_model
        self.client = client or anthropic.AsyncAnthropic(
            api_key=s.anthropic_api_key, timeout=REQUEST_TIMEOUT_S, max_retries=0
        )
        self.breaker = breaker or CircuitBreaker()
        self.sleep = sleep
        self.effort = s.anthropic_effort

    async def complete(
        self,
        *,
        purpose: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        if not self.breaker.allow():
            raise AIUnavailable("circuit open")
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        if self.effort:
            kwargs["output_config"] = {"effort": self.effort}
        last: Exception | None = None
        for attempt in range(MAX_ATTEMPTS):
            start = time.perf_counter()
            try:
                resp = await self.client.messages.create(**kwargs)
            except Exception as exc:  # noqa: BLE001 - classified below
                last = exc
                log.warning(
                    "ai call failed",
                    extra={"purpose": purpose, "attempt": attempt + 1, "error": type(exc).__name__},
                )
                if not _retryable(exc):
                    break
                if attempt < MAX_ATTEMPTS - 1:
                    await self.sleep(0.5 * 2**attempt + random.uniform(0, 0.25))
                continue
            latency = (time.perf_counter() - start) * 1000
            self.breaker.success()
            out = self._parse(resp, latency)
            # Metadata only: never log prompts or completions (PHI).
            log.info(
                "ai call",
                extra={
                    "purpose": purpose,
                    "model": self.model,
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
    def _parse(resp: Any, latency: float) -> LLMResponse:
        text = "".join(b.text for b in resp.content if b.type == "text")
        tool_uses = [
            ToolUse(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"
        ]
        return LLMResponse(
            text=text,
            tool_uses=tool_uses,
            stop_reason=resp.stop_reason,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            latency_ms=latency,
            raw_content=list(resp.content),
        )


_override: LLM | None = None


def set_llm(llm: LLM | None) -> None:
    """Test hook: inject a fake client."""
    global _override
    _override = llm


@lru_cache
def _default_llm() -> AnthropicLLM:
    return AnthropicLLM()


def ai_configured() -> bool:
    s = get_settings()
    return _override is not None or (s.ai_enabled and bool(s.anthropic_api_key))


def get_llm() -> LLM:
    """FastAPI dependency. Raises AIUnavailable when AI is disabled or unconfigured."""
    if _override is not None:
        return _override
    if not ai_configured():
        raise AIUnavailable("AI disabled or not configured")
    return _default_llm()
