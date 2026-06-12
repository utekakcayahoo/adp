# ADP — Agentic Design Patterns, Applied

A hands-on, end-to-end build of an agentic AI system, using the *Agentic Design
Patterns* book as the curriculum. **One use case, carried from start to finish:**
a **Facility Energy & Carbon Co-pilot** for a sustainability team.

## Stack
- **Claude Code** (terminal) — the build/dev cockpit.
- **Claude Code on Claude Desktop** — where the *end user* runs the agent. The
  agent ships as a **Claude plugin** (skills + sub-agents + a bundled
  MCP connector), kept **skills-first**: behavior lives in *skills* (markdown +
  light tools), not heavy Python or DAGs. Same plugin format across both, so we
  build/test it in the Claude Code terminal and install it in Claude Code on Claude Desktop.
- **Databricks** — synthetic data + the **remote MCP server** (hosted as a
  Databricks App, HTTPS) that the plugin connects to.
- **MLflow** — tracing & evaluation, captured at the **MCP/tool boundary**
  (Claude Code on Desktop doesn't natively export agent reasoning).

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
