# Build Roadmap — mapped to *Agentic Design Patterns*

**Principle:** one use case, grown in thin vertical slices. Each phase ships
something runnable and adds a few patterns. **Skills-first** — behavior lives in
plugin skills (markdown + light tools), not big Python orchestration or DAGs.

**Tooling:** build in **Claude Code** (local) → the agent is a **Claude plugin**
(skills + sub-agents + commands + bundled `.mcp.json`) → the end user runs it in
**Claude Cowork** → it reaches data through a **remote MCP server on Databricks**.

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

### Phase 5 — Knowledge + goals + memory
- 🧱 RAG over `adp_standards`; track progress vs `adp_targets`; remember the
  facility in focus across turns.
- 🟢 `adp_standards_index` (Vector Search).
- 📖 **Knowledge Retrieval (RAG), Goal Setting & Monitoring, Memory Management**.

### Phase 6 — Multi-agent
- 🧱 Split into specialist skills / sub-agents — Analyst, Carbon Accountant,
  Advisor, Reporter — coordinated by an Orchestrator (Cowork agent teams).
- 📖 **Multi-Agent Collaboration, Prioritization**.

### Phase 7 — Safety, HITL, robustness
- 🧱 Approval step before a report/action is "final"; graceful handling of
  missing/late data. (Cowork hooks for lifecycle guardrails.)
- 📖 **Human-in-the-Loop, Exception Handling & Recovery, Guardrails / Safety**.

### Phase 8 — Package the Cowork plugin + evaluate
- 🧱 Package skills + sub-agents + commands + `.mcp.json` into the installable
  **plugin**; install in Cowork. Add an evaluation harness (optionally a thin
  Claude Agent SDK harness for full-reasoning traces); watch tool-boundary traces.
- 🟢 plugin `adp-carbon-copilot`; MCP host `adp_mcp` (Databricks App).
- 📖 **Evaluation & Monitoring, Resource-Aware Optimization, Learning & Adaptation**.

---
We don't go chapter-by-chapter — patterns are pulled in when the use case needs them.
