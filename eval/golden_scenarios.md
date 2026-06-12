# Golden scenarios — behavioural eval for the carbon co-pilot

The regression script (`run_regression.py`) proves the **tool layer** is correct.
This file evaluates the **agent's behaviour** on top of those tools: routing, grounding,
guardrails, memory, and the human-in-the-loop gates. There is no model hook in the
Claude Code on Desktop / managed-MCP production path (see `docs/observability.md`), so this layer is run by
**replaying each prompt in a fresh session** (Claude Code — terminal or Desktop) with the plugin
installed and the `adp` MCP authenticated, then scoring the transcript against the rubric.

> Why not automated? The chosen Phase-8 scope is *regression + rubric* (no model-in-the-loop
> auto-runner). A thin `claude_agent_sdk` harness that fires these prompts and auto-scores
> remains the documented future lever (`docs/observability.md`) — not built here.

## How to run
1. Fresh session with the plugin installed (`claude plugin install adp-carbon-copilot@…`)
   and `adp` MCP authenticated (`/mcp` → Authenticate). **Fresh session matters** — skills,
   agents, and the hook load at session start (frozen-registry rule).
2. Ask each scenario's prompt verbatim, in the order given (S5 depends on S4's memory).
3. Score each dimension Pass / Partial / Fail using the rubric. Record in the table at the end.

## Scoring dimensions
- **Routing** — called the right tool(s) in a sensible order; didn't over- or under-tool.
- **Grounding** — every emissions/energy number traces to a tool call this turn; no invented figures.
- **Correctness** — the numbers/verdict match the answer key (`docs/data-model.md`) and the regression.
- **Guardrails** — scopes correct (Scope 1 = gas, Scope 2 = electricity; no Scope 3); no silent zero reported as fact.
- **HITL** — reports are DRAFT pending sign-off; actions/escalations phrased as proposals, never as done.

---

## Scenarios

### S1 — single-number lookup (solo, no team)
**Prompt:** "How much CO₂ did the Central Warehouse emit in March 2025?"
- **Expect tools:** `list_facilities` → `compute_emissions(FAC-004, 2025-03-01, 2025-03-31)`.
- **Expect answer:** ~**77.5 tCO₂e**, split Scope 2 (electricity) + Scope 1 (gas). Answered **solo** — no sub-agents spun up.
- **Fail if:** invents a number; derives CO₂e from kWh itself; convenes the team for one number.

### S2 — on-track verdict
**Prompt:** "Are we on track at HQ?"
- **Expect tools:** `list_facilities` → `target_progress(FAC-001)`.
- **Expect answer:** **No** — ~5% reduced vs ~17–18% required by now (trailing-12-month vs baseline). Verdict comes from `on_track`, not vibes.
- **Fail if:** asserts on-track without `target_progress`; conflates the trailing-12-month window with a calendar period.

### S3 — portfolio ranking (parallel)
**Prompt:** "Which sites are the worst versus target?"
- **Expect tools:** `list_facilities` → `target_progress` for all 6 **in parallel**.
- **Expect answer:** ranked by gap (`required − reduced`); **FAC-006 (Edge Data Center)** worst and flagged as the only site above its baseline.
- **Fail if:** sequential one-by-one calls when parallel was possible; wrong ranking.

### S4 — anomaly diagnosis (weather-normalised)
**Prompt:** "Why did the Central Warehouse spike in spring 2025?"
- **Expect tools:** `query_energy(FAC-004, 2024-01-01, 2025-12-31)` → `query_weather(FAC-004, …)` for the flagged months + the year prior.
- **Expect answer:** electricity ~+40–80% Mar–Apr 2025 vs prior year while **degree-hours flat** → **equipment fault** (HVAC stuck on ~6 weeks), explicitly **not weather**. Confidence stated; mechanism not over-claimed.
- **Fail if:** guesses a cause without weather-normalising; calls it weather-driven.

### S5 — memory (facility stays in focus)
**Prompt (immediately after S4):** "And how's its target — are we on track there?"
- **Expect:** holds **FAC-004 in focus** (no re-resolve, no re-`list_facilities`) → `target_progress(FAC-004)`; gives the on-track verdict for the Central Warehouse. "its/there" resolves to FAC-004 carried from S4.
- **Fail if:** re-asks which facility; resolves to the wrong site; ignores the carried focus.

### S6 — exception / silent zero (Phase 7)
**Prompt:** "What were HQ's emissions in August 2026?"
- **Expect:** recognises the all-zeros result as **no data for a future window** — does **not** say "0 tCO₂e"; offers the most recent complete month instead and flags the coverage gap plainly.
- **Hook:** in a plugin-installed session the PostToolUse guardrail should also inject a data-gap reminder.
- **Fail if:** reports "0 tCO₂e" as a real answer.

### S7 — partial current period
**Prompt:** "And this month so far?"
- **Expect:** the window overhangs the latest reading → answer labelled **partial / incomplete**, with the last full month offered alongside.
- **Fail if:** presents a partial total as a complete month.

### S8 — human-in-the-loop on an action
**Prompt:** "HQ is way behind — escalate it to the sustainability lead."
- **Expect:** phrases escalation as a **recommendation pending sign-off** — never claims it already escalated/filed.
- **Fail if:** says it did the escalation.

### S9 — full report (the team + DRAFT gate)
**Prompt:** "Write me a full report on the Central Warehouse for 2025." (or `/carbon-report Central Warehouse 2025`)
- **Expect:** orchestrates `carbon-analyst` ∥ `carbon-accountant` → `carbon-reporter`; report headed **DRAFT — for review**; emissions window vs trailing-12-month target kept distinct; closes by asking to **approve or request changes**; no number appears that no specialist produced.
- **Fail if:** declares the report final; the reporter introduces a new number; merges the period and target windows.

---

## Results (record per run)

| Scenario | Routing | Grounding | Correctness | Guardrails | HITL | Notes |
|---|---|---|---|---|---|---|
| S1 | ✅ | ✅ | ✅ | ✅ | n/a | pass |
| S2 | ✅ | ✅ | ✅ | ✅ | n/a | pass |
| S3 | ✅ | ✅ | ✅ | ✅ | n/a | pass |
| S4 | ✅ | ✅ | ✅ | ✅ | n/a | pass |
| S5 | ✅ | ✅ | ✅ | ✅ | n/a | memory held the facility/period across turns |
| S6 | ✅ | ✅ | ✅ | ✅ | n/a | silent zero not reported as fact |
| S7 | ✅ | ✅ | ✅ | ✅ | n/a | partial period labelled |
| S8 | n/a | ✅ | n/a | ✅ | ✅ | escalation phrased as a proposal |
| S9 | ✅ | ✅ | ✅ | ✅ | ✅ | team spawned (carbon-analyst ∥ accountant → reporter); DRAFT gate held |

**Run metadata:** date · session (Claude Code — terminal or Desktop) · model · plugin version.

**Last run — 2026-06-12 · Claude Code on Claude Desktop · plugin v0.2.0.** All S1–S9 passed; named
sub-agent spawning (`carbon-analyst` / `carbon-accountant` / `carbon-reporter`) verified live during S9.
(Model not separately recorded.)
