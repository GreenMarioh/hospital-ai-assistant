import json
from datetime import UTC, datetime

import httpx2
import pytest
from google.genai import errors as genai_errors

from app.ai import client as client_mod
from app.ai.client import CircuitBreaker, GeminiLLM
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


def _resp(text="hi", parts=None):
    from google.genai import types

    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(role="model", parts=parts or [types.Part(text=text)]),
                finish_reason=types.FinishReason.STOP,
            )
        ],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=3, candidates_token_count=2, thoughts_token_count=4
        ),
    )


class StubModels:
    def __init__(self, *items):
        self.items, self.calls = list(items), 0

    async def generate_content(self, **kw):
        self.calls += 1
        self.last = kw
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class StubClient:
    def __init__(self, *items):
        from types import SimpleNamespace as NS

        self.models = StubModels(*items)
        self.aio = NS(models=self.models)


def _api_err(code):
    cls = genai_errors.ServerError if code >= 500 else genai_errors.ClientError
    return cls(code, {"error": {"code": code, "message": "err", "status": "X"}})


async def _nosleep(_):
    return None


def _llm(stub, **kw):
    return GeminiLLM(client=stub, model="pro", flash_model="flash", sleep=_nosleep, **kw)


async def test_llm_retries_transient_errors_then_succeeds(monkeypatch):
    monkeypatch.setattr(client_mod.get_settings(), "gemini_thinking_level", "low")
    stub = StubClient(_api_err(500), _api_err(429), _resp("ok"))
    llm = _llm(stub)
    out = await llm.complete(
        purpose="triage", system="s", messages=[{"role": "user", "content": "x"}]
    )
    assert out.text == "ok" and stub.models.calls == 3
    assert out.input_tokens == 3 and out.output_tokens == 6 and out.model == "pro"
    cfg = stub.models.last["config"]
    assert stub.models.last["model"] == "pro"
    assert cfg.system_instruction == "s" and cfg.thinking_config.thinking_level == "LOW"
    assert cfg.temperature is None


async def test_llm_routes_conversational_purposes_to_flash():
    stub = StubClient(_resp("a"), _resp("b"))
    llm = _llm(stub)
    assert (await llm.complete(purpose="faq", system="s", messages=[])).model == "flash"
    assert stub.models.last["model"] == "flash"
    assert stub.models.last["config"].thinking_config is None  # empty setting omits it
    await llm.complete(purpose="briefing", system="s", messages=[], json_output=True)
    assert stub.models.last["model"] == "pro"
    assert stub.models.last["config"].response_mime_type == "application/json"


async def test_llm_tool_calls_round_trip():
    from google.genai import types

    call = types.Part(
        function_call=types.FunctionCall(name="search_doctors", args={"department": "Cardiology"}),
        thought_signature=b"sig",
    )
    stub = StubClient(_resp(parts=[call]), _resp("done"))
    llm = _llm(stub)
    tools = [{"name": "search_doctors", "description": "d", "input_schema": {"type": "object"}}]
    msgs = [{"role": "user", "content": "book cardiology"}]
    r1 = await llm.complete(purpose="booking", system="s", messages=msgs, tools=tools)
    assert r1.stop_reason == "tool_use" and r1.tool_uses[0].name == "search_doctors"
    assert r1.tool_uses[0].input == {"department": "Cardiology"} and r1.tool_uses[0].id
    decl = stub.models.last["config"].tools[0].function_declarations[0]
    assert decl.name == "search_doctors" and decl.parameters_json_schema == {"type": "object"}
    tu = r1.tool_uses[0]
    msgs += [
        {"role": "assistant", "content": r1.raw_content},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tu.id, "name": tu.name, "content": "[1, 2]"}
        ]},
    ]  # fmt: skip
    await llm.complete(purpose="booking", system="s", messages=msgs, tools=tools)
    contents = stub.models.last["contents"]
    assert [c.role for c in contents] == ["user", "model", "user"]
    assert contents[1].parts[0].thought_signature == b"sig"  # echoed back verbatim
    fr = contents[2].parts[0].function_response
    assert fr.name == "search_doctors" and fr.id == tu.id and fr.response == {"output": [1, 2]}


async def test_llm_skips_thought_parts_in_text():
    from google.genai import types

    stub = StubClient(
        _resp(parts=[types.Part(text="thinking...", thought=True), types.Part(text="answer")])
    )
    out = await _llm(stub).complete(purpose="faq", system="s", messages=[])
    assert out.text == "answer"


async def test_llm_does_not_retry_client_errors_and_trips_breaker():
    stub = StubClient(*[_api_err(400)] * 3)
    llm = _llm(stub, breaker=CircuitBreaker(threshold=2, reset_s=60))
    for _ in range(2):
        with pytest.raises(AIUnavailable):
            await llm.complete(purpose="t", system="s", messages=[])
    assert stub.models.calls == 2  # one attempt each: 400s are not retried
    with pytest.raises(AIUnavailable, match="circuit open"):
        await llm.complete(purpose="t", system="s", messages=[])
    assert stub.models.calls == 2  # breaker short-circuits without calling the provider


async def test_llm_gives_up_after_max_attempts():
    stub = StubClient(*[httpx2.ConnectError("down")] * 3)
    llm = _llm(stub)
    with pytest.raises(AIUnavailable):
        await llm.complete(purpose="t", system="s", messages=[])
    assert stub.models.calls == 3


def test_get_llm_unavailable_when_unconfigured():
    client_mod.set_llm(None)
    with pytest.raises(AIUnavailable):
        client_mod.get_llm()
