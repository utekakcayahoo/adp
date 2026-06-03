# Build Roadmap — mapped to *Agentic Design Patterns*

**Principle:** one use case, grown in thin vertical slices. Each phase ships
something runnable and adds a few patterns. **Skills-first** — behavior lives in
plugin skills (markdown + light tools), not big Python orchestration or DAGs.

**Tooling:** build in **Claude Code** (local) → the agent is a **Claude plugin**
(skills + sub-agents + bundled `.mcp.json`; slash entry points are skills, not
commands) → the end user runs it in **Claude Cowork** → it reaches data through a
**remote MCP server on Databricks**.

Legend: 🧱 build · ✅ verify · 📖 book patterns · 🟢 Databricks resource (`adp` prefix)

---

### Phase 0 — Foundation & architecture  *(done)*
- 🧱 Lock use case; business + agentic architecture diagrams; repo skeleton; data model.
- ✅ You can open both diagrams and explain the system in two minutes.
- 📖 *(framing for)* Tool Use, MCP, Multi-Agent.

### Phase 1 — Data layer (Databricks)  *(done)*
- 🧱 Synthetic data as Databricks **Jobs**: a batch seed (facilities, factors,
  targets, history) + a recurring generator that appends hourly readings (our
  "streaming-ish" feed).
- 🟢 `adp_facilities, adp_energy_readings, adp_emission_factors, adp_targets, adp_weather`; job `adp_data_generator`.
- ✅ Tables query cleanly; new readings keep arriving on schedule.
- 📖 *(sets up)* Tool Use, Knowledge Retrieval.

### Phase 2 — MCP server (Databricks managed)  *(done)*
- 🧱 An **HTTPS MCP server** exposing read tools over the tables: `list_facilities`,
  `query_energy`, `compute_emissions`, `target_progress`. Hosted as a **Databricks
  App** so Cowork can reach it remotely; shipped inside the plugin's `.mcp.json`.
- 🟢 `adp_mcp` (Databricks App).
- ✅ Tools callable from Claude Code **and** Cowork; numbers match raw SQL.
- 📖 **Model Context Protocol, Tool Use**.

### Phase 3 — First plugin (Cowork, skills-first) + tracing  *(done — OAuth proven)*
- 🧱 A Claude **plugin** with one skill that routes a question to the right tool and
  answers with real numbers. Built/tested in Claude Code, installed in Cowork. Log
  tool calls from the MCP server to MLflow.
- 🟢 MLflow experiment `3400437843984105`.
- ✅ "What did Office-1 emit last month?" → tool-backed answer; tool-call trace in MLflow.
- 📖 **Routing, Tool Use, Reflection** (verify numbers), **Guardrails** (no fabrication).

### Phase 4 — Reasoning depth  *(done)*
- 🧱 Added a 5th tool `query_weather`; upgraded `/carbon-report` to a planned multi-step
  chain; weather-normalized **anomaly diagnosis**; new `/portfolio-review` parallel sweep.
- 🟢 `main.adp.query_weather` (UC function, auto-exposed by managed MCP → **5 tools**).
- ✅ Verified on live data vs the planted answer key: FAC-004 spring spike → **equipment
  fault** (electricity +50–64% YoY while degree-hours flat); FAC-006 → **load creep**
  (only site above baseline); portfolio ranked by target gap with parallel tool calls.
- 📝 No occupancy data exists in the model (only weather), so diagnosis is weather-based.
- 📖 **Prompt Chaining, Planning, Reasoning Techniques, Parallelization** (multi-facility).

### Phase 5 — Knowledge + goals + memory  *(done)*
- 🧱 Seeded a 12-policy `adp_standards` corpus; built a Vector Search index and exposed a
  6th tool `search_standards` (RAG). Skill gained a **recommendations** workflow (turn a
  target gap into prioritized, policy-cited actions) and a **memory** rule (hold the
  facility/period in focus across turns).
- 🟢 `adp_standards` (table, CDF on); `adp_vs` (VS endpoint, STANDARD); `adp_standards_index`
  (Delta Sync, managed embeddings `databricks-gte-large-en`).
- ✅ Verified: retrieval is on-target ("Scope 2"→GHG scopes 0.71; "datacenter creeping
  up"→PUE 0.70; "cut emissions at a warehouse"→warehouse+efficiency); managed MCP now
  lists **6 tools**; `search_standards` returns ranked JSON with a no-fabrication
  policy-citation guardrail.
- 📝 The `adp_vs` endpoint is **billable** while it exists — delete it when done
  (`databricks vector-search-endpoints delete-endpoint adp_vs`).
- 📖 **Knowledge Retrieval (RAG), Goal Setting & Monitoring, Memory Management**.

### Phase 6 — Multi-agent  *(done)*
- 🧱 Split the analysis into four specialist sub-agents (plugin `agents/`), each with a
  **minimal tool allowlist** and a structured **findings block**: **carbon-analyst**
  (energy + weather + anomaly), **carbon-accountant** (emissions + target),
  **carbon-advisor** (prioritized, policy-cited actions), **carbon-reporter** (synthesis,
  no new numbers). The **orchestrator is the skill** — a triage rule decides when to
  delegate vs answer solo (the prioritization call). Both slash entry points delegate:
  `/carbon-report` runs the pipeline; `/portfolio-review` fans out the accountant in parallel.
- 🟢 No new Databricks resources — reuses the 6 MCP tools; each specialist just gets a subset.
- ✅ Verified end-to-end on FAC-004 (simulated via general-purpose agents this session):
  analyst ∥ accountant in parallel → advisor with the 12.2 pp gap → reporter composed the
  report with **zero tool calls and no invented numbers**. Analyst reproduced the
  equipment-fault diagnosis (+64%/+49% spring spike, weather ruled out); advisor cited
  STD-EEM-CATALOG / STD-WAREHOUSE / STD-HVAC-SETPOINT and fired the >10 pp escalation rule
  (STD-ESCALATION) while refusing to assert an escalation it wasn't handed.
- 📝 Named sub-agent types are only spawnable in a **fresh session** (same frozen-registry
  rule as skills); this session's test used general-purpose agents carrying each prompt.
  The **reporter** is the most optional of the four — the orchestrator can absorb it.
- 📝 *(2026-06-03)* Plugin **slash commands deprecated → migrated to skills.** `/carbon-report`
  and `/portfolio-review` are now thin slash-invocable skills (`skills/`, each carrying the
  old `argument-hint`); `commands/` was deleted and won't return. A skill can be slash-typed
  *and* auto-invoke on intent, and the method now lives once in `carbon-copilot` + the
  specialists instead of being copied into the entry point.
- 📖 **Multi-Agent Collaboration, Prioritization**.

### Phase 7 — Safety, HITL, robustness
- 🧱 Approval step before a report/action is "final"; graceful handling of
  missing/late data. (Cowork hooks for lifecycle guardrails.)
- 📖 **Human-in-the-Loop, Exception Handling & Recovery, Guardrails / Safety**.

### Phase 8 — Package the Cowork plugin + evaluate
- 🧱 Package skills + sub-agents + `.mcp.json` into the installable
  **plugin**; install in Cowork. Add an evaluation harness (optionally a thin
  Claude Agent SDK harness for full-reasoning traces); watch tool-boundary traces.
- 🟢 plugin `adp-carbon-copilot`; MCP host `adp_mcp` (Databricks App).
- 📖 **Evaluation & Monitoring, Resource-Aware Optimization, Learning & Adaptation**.

---
We don't go chapter-by-chapter — patterns are pulled in when the use case needs them.
