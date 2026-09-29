"""Versioned prompt templates: files named <name>.v<N>.md under ai/prompts/, highest version wins."""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROMPT_DIR = Path(__file__).parent / "prompts"
_FILE = re.compile(r"^(?P<name>[a-z_]+)\.v(?P<version>\d+)\.md$")


@dataclass(frozen=True)
class Prompt:
    name: str
    version: str
    template: str

    def render(self, **values: str) -> str:
        out = self.template
        for key, value in values.items():
            out = out.replace("{{" + key + "}}", value)
        if "{{" in out:
            missing = re.findall(r"\{\{(\w+)\}\}", out)
            raise ValueError(f"unfilled prompt variables: {missing}")
        return out


@lru_cache
def load_prompt(name: str, version: int | None = None) -> Prompt:
    candidates: dict[int, Path] = {}
    for path in PROMPT_DIR.iterdir():
        m = _FILE.match(path.name)
        if m and m["name"] == name:
            candidates[int(m["version"])] = path
    if not candidates:
        raise FileNotFoundError(f"no prompt named {name!r}")
    chosen = version if version is not None else max(candidates)
    return Prompt(name=name, version=f"v{chosen}", template=candidates[chosen].read_text().strip())
