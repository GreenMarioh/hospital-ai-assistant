# Triage evaluation report
Generated 2026-11-08 09:23 UTC. Cases: 60 ({'emergency': 23, 'urgent': 15, 'routine': 13, 'self-care': 9}).

Caveat: the cases were written by the same team that wrote the rules. The rule results below show the rule set covers these cases, not that it generalises; extend `cases.json` with real, de-identified cases over time.

## 1. Rule-based red-flag pre-check (deterministic, no LLM)
- Emergency recall: **23/23** (100%)
- False positives on non-emergency cases: **0/37**

## 2. Full pipeline with LLM (rules first, then model)
- Model: `gemini-3.5-flash-lite`, prompt `v1`
- Urgency accuracy: **80%** (48/60)
- Department accuracy: **77%** (46/60)
- Under-triaged (emergency/urgent predicted as routine/self-care): ['u12']

| id | expected | got | dept expected | dept got | source |
|---|---|---|---|---|---|
| e01 | emergency | emergency | Emergency | Emergency | rules |
| e02 | emergency | emergency | Emergency | Emergency | rules |
| e03 | emergency | emergency | Emergency | Emergency | rules |
| e04 | emergency | emergency | Emergency | Emergency | rules |
| e05 | emergency | emergency | Emergency | Emergency | rules |
| e06 | emergency | emergency | Emergency | Emergency | rules |
| e07 | emergency | emergency | Emergency | Emergency | rules |
| e08 | emergency | emergency | Emergency | Emergency | rules |
| e09 | emergency | emergency | Emergency | Emergency | rules |
| e10 | emergency | emergency | Emergency | Emergency | rules |
| e11 | emergency | emergency | Emergency | Emergency | rules |
| e12 | emergency | emergency | Emergency | Emergency | rules |
| e13 | emergency | emergency | Emergency | Emergency | rules |
| e14 | emergency | emergency | Emergency | Emergency | rules |
| e15 | emergency | emergency | Emergency | Emergency | rules |
| u01 | urgent | urgent | General Medicine | General Medicine | llm |
| u02 | urgent | urgent | Pediatrics | Pediatrics | llm |
| u03 | urgent | urgent | Orthopedics | Orthopedics | llm |
| u04 | urgent | emergency | General Medicine | Emergency | llm |
| u05 | urgent | emergency | Cardiology | Emergency | llm |
| u06 | urgent | urgent | Neurology | Neurology | llm |
| u07 | urgent | emergency | Dermatology | Emergency | llm |
| u08 | urgent | emergency | Pediatrics | Emergency | llm |
| r01 | routine | routine | Neurology | General Medicine | llm |
| r02 | routine | urgent | Cardiology | Cardiology | llm |
| r03 | routine | routine | Orthopedics | Orthopedics | llm |
| r04 | routine | routine | Dermatology | Dermatology | llm |
| r05 | routine | routine | Pediatrics | Pediatrics | llm |
| r06 | routine | routine | General Medicine | General Medicine | llm |
| r07 | routine | routine | Orthopedics | Orthopedics | llm |
| r08 | routine | routine | Dermatology | Dermatology | llm |
| s01 | self-care | self-care | General Medicine | General Medicine | llm |
| s02 | self-care | self-care | General Medicine | General Medicine | llm |
| s03 | self-care | self-care | General Medicine | Dermatology | llm |
| s04 | self-care | self-care | General Medicine | Orthopedics | llm |
| s05 | self-care | self-care | General Medicine | General Medicine | llm |
| s06 | self-care | self-care | General Medicine | General Medicine | llm |
| e16 | emergency | emergency | Emergency | Emergency | rules |
| e17 | emergency | emergency | Emergency | Emergency | rules |
| e18 | emergency | emergency | Emergency | Emergency | rules |
| e19 | emergency | emergency | Emergency | Emergency | rules |
| e20 | emergency | emergency | Emergency | Emergency | rules |
| e21 | emergency | emergency | Emergency | Emergency | rules |
| e22 | emergency | emergency | Emergency | Emergency | rules |
| e23 | emergency | emergency | Emergency | Emergency | rules |
| u09 | urgent | emergency | General Medicine | Emergency | llm |
| u10 | urgent | emergency | General Medicine | Emergency | llm |
| u11 | urgent | emergency | Orthopedics | Emergency | llm |
| u12 | urgent | routine | Dermatology | Dermatology | llm |
| u13 | urgent | emergency | General Medicine | Emergency | llm |
| u14 | urgent | urgent | General Medicine | General Medicine | llm |
| u15 | urgent | emergency | Pediatrics | Emergency | llm |
| r09 | routine | routine | Cardiology | General Medicine | llm |
| r10 | routine | routine | Orthopedics | Orthopedics | llm |
| r11 | routine | routine | Neurology | Neurology | llm |
| r12 | routine | routine | Dermatology | Dermatology | llm |
| r13 | routine | routine | General Medicine | General Medicine | llm |
| s07 | self-care | self-care | General Medicine | General Medicine | llm |
| s08 | self-care | self-care | General Medicine | Orthopedics | llm |
| s09 | self-care | routine | General Medicine | General Medicine | llm |
