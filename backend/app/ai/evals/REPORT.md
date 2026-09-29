# Triage evaluation report
Generated 2026-09-29 21:06 UTC. Cases: 37 ({'emergency': 15, 'urgent': 8, 'routine': 8, 'self-care': 6}).

Caveat: the cases were written by the same team that wrote the rules. The rule results below show the rule set covers these cases, not that it generalises; extend `cases.json` with real, de-identified cases over time.

## 1. Rule-based red-flag pre-check (deterministic, no LLM)
- Emergency recall: **15/15** (100%)
- False positives on non-emergency cases: **0/22**

## 2. Full pipeline with LLM (rules first, then model)
**NOT RUN.** Run `python -m app.ai.evals.run --live` with `ANTHROPIC_API_KEY` set to fill this in.
