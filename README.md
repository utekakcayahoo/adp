# ADP — Agentic Design Patterns, Applied

A hands-on, end-to-end build of an agentic AI system, using the *Agentic Design
Patterns* book as the curriculum. **One use case, carried from start to finish:**
a **Facility Energy & Carbon Co-pilot** for a sustainability team.

## Stack
- **Claude Code** (terminal) — the build/dev cockpit.
- **Claude Agent SDK** — the agent runtime, kept **skills-first**: behavior lives
  in *agent skills* (markdown + light tools), not heavy Python or DAGs.
- **Databricks** — synthetic data, MCP data tools, and final deployment as a
  **Databricks App**.
- **MLflow** — agent tracing & evaluation.

All Databricks resources use the prefix **`adp`**.

## Repo layout
| Path | What |
|---|---|
| `docs/use-case.md` | The **locked** use case — never changes. |
| `docs/architecture/business-architecture.html` | Business view (who, what, value). |
| `docs/architecture/agentic-architecture.html` | Agentic AI system view, annotated with book patterns. |
| `docs/roadmap.md` | Phased build plan, mapped to the book. |

## View the diagrams
They're self-contained (no internet needed). From the repo root:
```bash
open "docs/architecture/business-architecture.html"
open "docs/architecture/agentic-architecture.html"
```
