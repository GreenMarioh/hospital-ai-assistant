"""Hospital FAQ bot: keyword retrieval (TF-IDF) over knowledge_base/*.md, answered by the LLM from excerpts."""

import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.ai.client import LLM
from app.ai.errors import AIUnavailable
from app.ai.guards import DISCLAIMER, sanitize_reply
from app.ai.prompts import load_prompt
from app.schemas.ai import FaqOut, FaqSource

NO_ANSWER = (
    "I don't have that information. Please contact the front desk, open every day from 08:00 to 20:00. "
    "If this is an emergency, call your local emergency number."
)
_STOP = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "do",
        "does",
        "for",
        "from",
        "how",
        "i",
        "in",
        "is",
        "it",
        "me",
        "my",
        "of",
        "on",
        "or",
        "the",
        "to",
        "what",
        "when",
        "where",
        "which",
        "who",
        "will",
        "with",
        "you",
        "your",
    ]
)
_WORD = re.compile(r"[a-z0-9]+")


def _candidates() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        Path("/app/knowledge_base"),
        here.parents[2] / "knowledge_base",
        here.parents[3] / "knowledge_base",
    ]


def _tokens(text: str) -> list[str]:
    out = []
    for w in _WORD.findall(text.lower()):
        if w in _STOP:
            continue
        out.append(w[:-1] if len(w) > 3 and w.endswith("s") else w)
    return out


@dataclass(frozen=True)
class Chunk:
    file: str
    title: str
    text: str
    tokens: tuple[str, ...]


@lru_cache
def load_chunks(directory: str | None = None) -> tuple[Chunk, ...]:
    root = Path(directory) if directory else next((p for p in _candidates() if p.is_dir()), None)
    if root is None:
        return ()
    chunks: list[Chunk] = []
    for path in sorted(root.glob("*.md")):
        doc_title, section = path.stem, None
        buf: list[str] = []

        def flush(
            section: str | None, buf: list[str], path: Path = path, doc_title: str = doc_title
        ) -> None:
            body = "\n".join(buf).strip()
            if body and section:
                title = f"{doc_title}: {section}"
                chunks.append(
                    Chunk(
                        path.name, section, f"{section}\n{body}", tuple(_tokens(f"{title} {body}"))
                    )
                )

        for line in path.read_text().splitlines():
            if line.startswith("## "):
                flush(section, buf)
                section, buf = line[3:].strip(), []
            elif line.startswith("# "):
                doc_title = line[2:].strip()
            else:
                buf.append(line)
        flush(section, buf)
    return tuple(chunks)


def retrieve(question: str, k: int = 3, chunks: tuple[Chunk, ...] | None = None) -> list[Chunk]:
    chunks = chunks if chunks is not None else load_chunks()
    q = set(_tokens(question))
    if not q or not chunks:
        return []
    n = len(chunks)
    df = {t: sum(1 for c in chunks if t in c.tokens) for t in q}
    scored = []
    for c in chunks:
        score = sum(
            (1 + math.log(c.tokens.count(t))) * math.log(1 + n / df[t])
            for t in q
            if df[t] and t in c.tokens
        )
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    if scored and len(q) >= 2 and scored[0][0] < 1.0:
        return []  # only a weak, incidental match: better to admit we don't know
    return [c for _, c in scored[:k]]


async def answer(llm_getter, question: str) -> FaqOut:  # type: ignore[no-untyped-def]
    hits = retrieve(question)
    sources = [FaqSource(title=c.title, file=c.file) for c in hits]
    if not hits:
        return FaqOut(answer=NO_ANSWER, sources=[], ai_generated=False, disclaimer=DISCLAIMER)
    try:
        llm: LLM = llm_getter()
        prompt = load_prompt("faq")
        context = "\n\n".join(f"[{c.file}] {c.text}" for c in hits)
        resp = await llm.complete(
            purpose="faq",
            system=prompt.render(),
            messages=[
                {
                    "role": "user",
                    "content": f"<context>\n{context}\n</context>\n<question>{question}</question>",
                }
            ],
            max_tokens=600,
        )
        text, _ = sanitize_reply(resp.text.strip())
        return FaqOut(
            answer=text or NO_ANSWER, sources=sources, ai_generated=True, disclaimer=DISCLAIMER
        )
    except AIUnavailable:
        # Degraded mode: return the best excerpt verbatim.
        return FaqOut(
            answer=hits[0].text[:700],
            sources=sources[:1],
            ai_generated=False,
            disclaimer=DISCLAIMER,
        )
