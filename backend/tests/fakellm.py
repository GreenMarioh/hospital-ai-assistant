from typing import Any

from app.ai.client import LLMResponse, ToolUse
from app.ai.errors import AIUnavailable


class FakeLLM:
    """Scripted LLM: each call pops the next item (str text, LLMResponse, or Exception)."""

    model = "fake-model"

    def __init__(self, *script: Any) -> None:
        self.script = list(script)
        self.calls: list[dict[str, Any]] = []

    async def complete(
        self, *, purpose, system, messages, tools=None, max_tokens=1500, json_output=False
    ):
        self.calls.append(
            {
                "purpose": purpose,
                "system": system,
                "messages": messages,
                "tools": tools,
                "json_output": json_output,
            }
        )
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, LLMResponse):
            return item
        return LLMResponse(
            text=item, stop_reason="end_turn", input_tokens=10, output_tokens=5, latency_ms=1.0
        )


def tool_call(name: str, args: dict, call_id: str = "tu_1") -> LLMResponse:
    return LLMResponse(
        text="", tool_uses=[ToolUse(call_id, name, args)], stop_reason="tool_use",
        raw_content=[{"type": "tool_use", "id": call_id, "name": name, "input": args}],
    )  # fmt: skip


DOWN = AIUnavailable("down")
