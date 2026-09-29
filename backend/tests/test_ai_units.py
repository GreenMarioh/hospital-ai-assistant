import json
from datetime import UTC, datetime

import anthropic
import httpx2
import pytest

from app.ai import client as client_mod
from app.ai.client import AnthropicLLM, CircuitBreaker
from app.ai.errors import AIInvalidOutput, AIUnavailable
from app.ai.evals.run import load_cases, rule_results
from app.ai.faq import load_chunks, retrieve
from app.ai.guards import sanitize_reply, violates_safety
from app.ai.pii import age_years, scrub
from app.ai.prompts import load_prompt
from app.ai.redflags import detect_red_flags
from app.ai.structured import complete_json, extract_json
from app.schemas.ai import TriageLLMOutput
from tests.fakellm import FakeLLM


def test_eval_set_size_and_emergency_recall_is_100_percent():
    cases = load_cases()
    assert len(cases) >= 30
    r = rule_results(cases)
    assert r["emergency_total"] >= 10 and r["missed"] == [] and r["false_positives"] == []


@pytest.mark.parametrize(
    "text",
    [
        "chest pain", "his face has gone droopy", "slurring her words", "numbness on one side", "Chest tightness since morning", "my speech is slurred", "he is unconscious",
        "I can't breathe", "there is severe bleeding", "I want to end my life", "throat closing", "she had a seizure",
        "I am coughing up blood", "he has a stab wound",
    ],
)  # fmt: skip
def test_red_flags_detected(text):
    assert detect_red_flags(text)


@pytest.mark.parametrize(
    "text", ["mild headache", "runny nose and cough", "knee pain", "skin rash on my arm"]
)
def test_red_flags_not_triggered_by_minor_complaints(text):
    assert detect_red_flags(text) == []


def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! {"a": 1} hope that helps') == {"a": 1}
    with pytest.raises(json.JSONDecodeError):
        extract_json("no json here")


async def test_complete_json_retries_once_then_succeeds_or_fails():
    ok = json.dumps({"reply": "hi", "ready": False})
    llm = FakeLLM("not json", ok)
    out, _ = await complete_json(
        llm, TriageLLMOutput, purpose="t", system="s", messages=[{"role": "user", "content": "x"}]
    )
    assert out.reply == "hi" and len(llm.calls) == 2
    assert "not valid" in llm.calls[1]["messages"][-1]["content"]
    with pytest.raises(AIInvalidOutput):
        await complete_json(
            FakeLLM("bad", "worse"), TriageLLMOutput, purpose="t", system="s", messages=[]
        )
    # schema violation (ready without urgency) is treated as invalid too
    bad = json.dumps({"reply": "r", "ready": True})
    with pytest.raises(AIInvalidOutput):
        await complete_json(
            FakeLLM(bad, bad), TriageLLMOutput, purpose="t", system="s", messages=[]
        )


def test_prompts_are_versioned_files():
    p = load_prompt("triage")
    assert p.version == "v1"
    assert "{{" not in p.render(max_turns="8", patient_context="{}", departments="A, B")
    with pytest.raises(ValueError):
        p.render(max_turns="8")
    with pytest.raises(FileNotFoundError):
        load_prompt("does_not_exist")


def test_scrub_and_age():
    s = scrub("Call me on +1 (555) 123-4567 or a.b@c.com, I'm John Smith", ("John", "Smith"))
    assert "555" not in s and "@" not in s and "John" not in s and "Smith" not in s
    assert (
        age_years(
            datetime(2000, 6, 15, tzinfo=UTC).date(), datetime(2020, 6, 14, tzinfo=UTC).date()
        )
        == 19
    )
    assert scrub(None) == ""


def test_output_guard():
    assert violates_safety("You probably have pneumonia")
    assert violates_safety("It sounds like a case of migraine")
    assert violates_safety("Take 500 mg of paracetamol")
    assert violates_safety("Try some ibuprofen")
    assert not violates_safety(
        "You have an appointment on Tuesday. Please book a visit with General Medicine."
    )
    text, replaced = sanitize_reply("You likely have the flu")
    assert replaced and "can't give a diagnosis" in text


def test_faq_retrieval():
    assert load_chunks()
    top = retrieve("What are the visiting hours for the ICU?")
    assert top and "ICU" in top[0].text
    assert retrieve("how do I get to parking")[0].file == "emergency-directions.md"
    assert retrieve("quantum chromodynamics lecture schedule") == []
    assert retrieve("") == []


def test_circuit_breaker_states():
    now = [0.0]
    cb = CircuitBreaker(threshold=2, reset_s=10, clock=lambda: now[0])
    assert cb.allow()
    cb.failure()
    cb.failure()
    assert cb.is_open and not cb.allow()
    now[0] = 11
    assert cb.allow()  # half-open probe
    cb.success()
    assert not cb.is_open and cb.allow()


def _resp(text="hi"):
    from types import SimpleNamespace as NS

    return NS(
        content=[NS(type="text", text=text)],
        stop_reason="end_turn",
        usage=NS(input_tokens=3, output_tokens=2),
    )


class StubMessages:
    def __init__(self, *items):
        self.items, self.calls = list(items), 0

    async def create(self, **kw):
        self.calls += 1
        self.last = kw
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class StubClient:
    def __init__(self, *items):
        self.messages = StubMessages(*items)


def _status_err(cls, code):
    req = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("err", response=httpx2.Response(code, request=req), body=None)


async def _nosleep(_):
    return None


async def test_llm_retries_transient_errors_then_succeeds(monkeypatch):
    monkeypatch.setattr(client_mod.get_settings(), "anthropic_effort", "low")
    stub = StubClient(
        _status_err(anthropic.InternalServerError, 500),
        _status_err(anthropic.RateLimitError, 429),
        _resp("ok"),
    )
    llm = AnthropicLLM(client=stub, model="m", sleep=_nosleep)
    out = await llm.complete(purpose="t", system="s", messages=[{"role": "user", "content": "x"}])
    assert out.text == "ok" and stub.messages.calls == 3 and out.input_tokens == 3
    assert stub.messages.last["output_config"] == {"effort": "low"}
    assert "temperature" not in stub.messages.last


async def test_llm_does_not_retry_client_errors_and_trips_breaker():
    stub = StubClient(*[_status_err(anthropic.BadRequestError, 400)] * 3)
    llm = AnthropicLLM(
        client=stub, model="m", breaker=CircuitBreaker(threshold=2, reset_s=60), sleep=_nosleep
    )
    for _ in range(2):
        with pytest.raises(AIUnavailable):
            await llm.complete(purpose="t", system="s", messages=[])
    assert stub.messages.calls == 2  # one attempt each: 400s are not retried
    with pytest.raises(AIUnavailable, match="circuit open"):
        await llm.complete(purpose="t", system="s", messages=[])
    assert stub.messages.calls == 2  # breaker short-circuits without calling the provider


async def test_llm_gives_up_after_max_attempts():
    stub = StubClient(
        *[anthropic.APIConnectionError(request=httpx2.Request("POST", "https://x"))] * 3
    )
    llm = AnthropicLLM(client=stub, model="m", sleep=_nosleep)
    with pytest.raises(AIUnavailable):
        await llm.complete(purpose="t", system="s", messages=[])
    assert stub.messages.calls == 3


def test_get_llm_unavailable_when_unconfigured():
    client_mod.set_llm(None)
    with pytest.raises(AIUnavailable):
        client_mod.get_llm()
