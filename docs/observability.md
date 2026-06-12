# Observability — how we trace the agent

Goal: agent traces in MLflow experiment `3400437843984105`. The **Claude Code on Desktop + managed-MCP**
architecture constrains how much of that is achievable. Here is the honest picture.

## What we CAN see
- **Tool calls, Databricks side.** Every tool the agent calls executes as a Unity
  Catalog function query in Databricks, so it is auditable via UC audit logs / query
  history (`system.access.audit`, query history) — *which tool ran, with what args,
  as whom*. Solid tool-level observability. *(Mechanism confirmed in principle; exact
  capture not yet verified — TODO.)*
- **Tool I/O at the client.** A client wrapper (a Claude Code session, or the dev
  harness below) can log each tool request/response.

## What we CANNOT easily get
- **Model-reasoning traces in MLflow.** Claude Code on Desktop runs the model, and managed MCP runs
  the tools — both are managed services with **no code hook** for us to call
  `mlflow.log_trace()` / `mlflow.<framework>.autolog()`. So chain-of-thought / step
  traces can't be exported the way the Claude Agent SDK would.

## Plan
- **Now (Phase 3):** tool-call observability via Databricks query history.
- **Phase 8 (eval, done):** a two-layer eval harness in `eval/` — a deterministic
  **data-layer regression** (`run_regression.py`) that gates the tool answers against the
  planted answer key (baseline, the FAC-004 fault, the FAC-006 creep, the silent-zero
  substrate), plus a **golden-scenario behavioural rubric**
  (`golden_scenarios.md`) run in a live session. **Live tool-call monitoring** stays the
  Databricks query-history path above (which tool ran, with what args, as whom).
- **Future lever (not built):** a thin **Claude Agent SDK** harness that replays the same
  skill + MCP tools with MLflow tracing **on**, producing full *agent-reasoning* traces in
  experiment `3400437843984105`. This is the only clean path to MLflow agent traces while
  Claude Code on Desktop (no model hook) remains the runtime — deferred, since the chosen Phase-8 scope was
  regression + rubric.

## Consequence of the managed-MCP choice (be explicit)
We traded the easy "log inside the MCP server" hook — which a custom FastAPI MCP
server would have given us — for near-zero server code. Net: **much less code, but
MLflow agent tracing now lives in a separate harness, not the live path.** If
first-class live MLflow tracing later becomes a hard requirement, the lever is to
swap the managed MCP for a custom MCP server (Databricks App) that instruments each
tool call. We are deliberately not doing that yet.
