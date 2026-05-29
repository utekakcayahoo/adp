# Build Roadmap — mapped to *Agentic Design Patterns*

**Principle:** one use case, grown in thin vertical slices. Each phase ships
something runnable and adds a few patterns. **Skills-first** — behavior lives in
agent skills (markdown + light tools), not big Python orchestration or DAGs.

Legend: 🧱 build · ✅ verify · 📖 book patterns · 🟢 Databricks resource (`adp` prefix)

---

### Phase 0 — Foundation & architecture  *(this phase)*
- 🧱 Lock use case; business + agentic architecture diagrams; repo skeleton; data model.
- ✅ You can open both diagrams and explain the system in two minutes.
- 📖 *(framing for)* Tool Use, MCP, Multi-Agent.

### Phase 1 — Data layer (Databricks)
- 🧱 Synthetic data as Databricks **Jobs**: a batch seed (facilities, factors,
  targets, history) + a recurring generator that appends hourly readings (our
  "streaming-ish" feed).
- 🟢 `adp_facilities, adp_energy_readings, adp_emission_factors, adp_targets, adp_weather`; job `adp_data_generator`.
- ✅ Tables query cleanly; new readings keep arriving on schedule.
- 📖 *(sets up)* Tool Use, Knowledge Retrieval.

### Phase 2 — MCP tool server (Databricks)
- 🧱 MCP server exposing read tools over the tables: `list_facilities`,
  `query_energy`, `compute_emissions`, `target_progress`. Hosted on Databricks.
- 🟢 `adp_mcp`.
- ✅ Tools callable from Claude Code; numbers match raw SQL.
- 📖 **Model Context Protocol, Tool Use**.

### Phase 3 — First agent (Claude Agent SDK, skills-first) + tracing
- 🧱 A single agent that chats, routes a question to the right tool, answers with
  real numbers. Wire MLflow tracing.
- 🟢 MLflow experiment `4115298422633092`.
- ✅ "What did Office-1 emit last month?" → tool-backed answer; trace in MLflow.
- 📖 **Routing, Tool Use, Reflection** (verify numbers), **Guardrails** (no fabrication).

### Phase 4 — Reasoning depth
- 🧱 Multi-step report generation; explain anomalies using weather/occupancy.
- ✅ "Generate Q1 report" runs end-to-end from one instruction.
- 📖 **Prompt Chaining, Planning, Reasoning Techniques, Parallelization** (multi-facility).

### Phase 5 — Knowledge + goals + memory
- 🧱 RAG over `adp_standards`; track progress vs `adp_targets`; remember the
  facility in focus across turns.
- 🟢 `adp_standards_index` (Vector Search).
- 📖 **Knowledge Retrieval (RAG), Goal Setting & Monitoring, Memory Management**.

### Phase 6 — Multi-agent
- 🧱 Split into specialist skills/agents — Analyst, Carbon Accountant, Advisor,
  Reporter — coordinated by an Orchestrator.
- 📖 **Multi-Agent Collaboration, Prioritization**.

### Phase 7 — Safety, HITL, robustness
- 🧱 Approval step before a report/action is "final"; graceful handling of
  missing/late data.
- 📖 **Human-in-the-Loop, Exception Handling & Recovery, Guardrails / Safety**.

### Phase 8 — Deploy as a Databricks App + evaluate
- 🧱 Package agent + MCP as a **Databricks App** (chat UI). Add an evaluation
  harness; watch traces in production.
- 🟢 `adp_app`.
- 📖 **Evaluation & Monitoring, Resource-Aware Optimization, Learning & Adaptation**.

---
We don't go chapter-by-chapter — patterns are pulled in when the use case needs them.
