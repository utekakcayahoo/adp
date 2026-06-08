# adp-carbon-copilot (Claude plugin)

The Facility Energy & Carbon Co-pilot, packaged as a Claude **plugin** — the same
format Claude Code and Cowork both load. Skills-first: behavior lives in `skills/`,
data access in `.mcp.json` (the Databricks managed MCP server).

```
adp-carbon-copilot/
├── .claude-plugin/plugin.json   # manifest
├── .mcp.json                    # MCP server: Databricks managed UC-functions endpoint
├── skills/                      # behavior — skills-first
│   ├── carbon-copilot/SKILL.md  # core: routing, memory, diagnosis, guardrails (auto-invoked)
│   ├── carbon-report/SKILL.md   # /carbon-report <facility> [period]  (specialist pipeline)
│   └── portfolio-review/SKILL.md  # /portfolio-review  (parallel multi-facility sweep)
├── agents/                      # Phase 6 specialist sub-agents (the "team")
│   ├── carbon-analyst.md        # energy + weather + anomaly diagnosis
│   ├── carbon-accountant.md     # emissions (Scope 1/2) + target progress
│   ├── carbon-advisor.md        # prioritized, policy-cited actions (RAG)
│   └── carbon-reporter.md       # synthesizes the findings into the report
└── hooks/                       # Phase 7 safety guardrail (PostToolUse)
    ├── hooks.json               # matches the 3 numeric tools
    └── flag_data_gaps.py        # flags silent-zero / empty / future-window results
```

> **No `commands/`.** Plugin slash *commands* are deprecated in favour of **skills**
> (a skill can carry an `argument-hint` and be invoked as `/name`, *and* auto-invoke when
> its description matches). `carbon-report` and `portfolio-review` are now thin
> slash-invocable skills that orchestrate the team; the method lives once in
> `carbon-copilot` + the specialists, not copied into the entry point.

The MCP tools come from `mcp/adp_uc_functions.sql` (see `mcp/MCP.md`).

> **Two separate wiring steps — both are needed.** Registering the **MCP server**
> (below) makes the *tools* available. Installing the **skill** makes the *skill*
> drive the behavior (routing, no-fabrication guardrail, report format). With only the
> MCP registered, a capable model will use the tools well on its own — but the skill
> is what *guarantees* that behavior every time, including on weaker models.

## 1. Install the skills + sub-agents

> **Phase 8 — install as a plugin (recommended).** The whole thing ships as an installable
> plugin via a repo-root marketplace (`.claude-plugin/marketplace.json`). From the repo root:
> ```bash
> claude plugin marketplace add "$(pwd)"
> claude plugin install adp-carbon-copilot@adp-carbon-copilot-marketplace
> ```
> `claude plugin details adp-carbon-copilot` shows the inventory: **3 skills, 4 agents, the
> PostToolUse hook, and the `adp` MCP**. Installing as a plugin is what **registers the hook** —
> the symlink method below does not. Start a new session after installing. (The marketplace is a
> directory snapshot — after editing the repo, run `claude plugin marketplace update
> adp-carbon-copilot-marketplace`.) **Cowork:** add the marketplace / install the plugin from the
> Desktop app; skills, agents, hook, and `.mcp.json` all ship inside it.

**Claude Code (local, live-edit dev):** symlink the three skills and the four specialist sub-agents into
your personal dirs (symlinks, so repo edits propagate), then start a new session:
```bash
# from this plugin dir
mkdir -p ~/.claude/skills ~/.claude/agents
for s in carbon-copilot carbon-report portfolio-review; do
  ln -sf "$(pwd)/skills/$s" ~/.claude/skills/$s
done
for a in carbon-analyst carbon-accountant carbon-advisor carbon-reporter; do
  ln -sf "$(pwd)/agents/$a.md" ~/.claude/agents/$a.md
done
```
This registers `carbon-copilot` (the core skill) plus two **slash-invocable skills** —
`/carbon-report <facility> [period]` (planned, weather-aware report) and `/portfolio-review`
(parallel sweep) — and the four **specialist sub-agents** (analyst, accountant, advisor,
reporter — the orchestrated "team"). Skills and agents are re-scanned per session —
**start a new session** before the named sub-agents can be spawned. **Cowork (production):**
the skills + agents ship *inside* the plugin — installing the plugin registers all of them
with `.mcp.json` (Phase 8).

## 2. Connect the MCP server

### OAuth — baked into the plugin (Phase 8, the shipped path)
The bundled `.mcp.json` ships a **public/PKCE OAuth client** (no secret):
`adp-carbon-copilot-public`, client_id `fa2a1992-0304-4783-8e8e-5c5a104bac8a`, redirect
`http://localhost:8080/callback`, scopes `all-apis`+`offline_access`. So once the plugin is
installed there is **nothing to register** — in a new session run `/mcp` → select `adp` →
**Authenticate** → browser login → `adp` shows **connected, 6 tools** (`list_facilities`,
`query_energy`, `query_weather`, `compute_emissions`, `target_progress`, `search_standards`).
Each user authenticates as themselves and **Unity Catalog enforces per-user access**, so whoever
logs in needs read/execute on `main.adp`. PKCE means no client secret ships in the plugin.

> The earlier **confidential** client (`adp-carbon-copilot-mcp`, `9bbe5bf5-…`, secret in the
> gitignored **repo-root** `.env` — kept out of the plugin dir so installs never copy it) was the
> path proven 2026-05-31 via `claude mcp add-json … --client-secret`. It still works for manual CLI
> registration, but a plugin can only ship a *public* client — so the bundled `.mcp.json` uses the
> public one above. *(Public-client browser flow **proven live 2026-06-09**: install → `/mcp` →
> Authenticate → 6 tools connect.)*

### Alternative — token header (quick local dev, no OAuth)
For a fast check without OAuth, register the server manually with a bearer token (the shipped
`.mcp.json` now uses OAuth, so this is a separate manual registration; nothing secret is committed):
```bash
export DATABRICKS_TOKEN=$(databricks auth token -p dexter-umut-databricks \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
claude mcp add adp --transport http \
  "https://adb-4851152775098961.1.azuredatabricks.net/api/2.0/mcp/functions/main/adp" \
  --header "Authorization: Bearer $DATABRICKS_TOKEN"
```

## 3. Try it
Ask: *"How much CO₂ did the Central Warehouse emit in March 2025, and are we on track there?"*
The skill should route `list_facilities` → `compute_emissions` → `target_progress` and
answer only with tool-derived numbers.

Then follow up — *"so what should we do about it?"* — to exercise Phase 5: the skill keeps
the **same facility in focus** (memory), calls `search_standards` for relevant policy, and
returns **prioritized actions that cite the standard** (e.g. STD-EEM-CATALOG). Pure policy
questions (*"what counts as Scope 2?"*) are answered from `search_standards` only.

For Phase 6 (the **team**), run `/carbon-report Central Warehouse 2025` — now a
slash-invocable **skill** (it also auto-invokes on a plain *"write me a full report on the
Central Warehouse for 2025"*). The orchestrator spawns **carbon-analyst** ∥
**carbon-accountant** in parallel, hands the target gap to **carbon-advisor**, and lets
**carbon-reporter** compose the final report — each figure still traced to a tool call
inside a specialist. A simple one-tool question (*"CO₂ at HQ last month?"*) is answered
**solo** — the skill only convenes the team when the depth is worth it.

For Phase 7 (**safety, HITL, robustness**):
- **Exception handling** — ask *"What were HQ's emissions in August 2026?"* The tools return a
  silent all-zeros struct (no data exists yet — the feed ends mid-2026), so the agent must
  **not** answer "0 tCO₂e": it says there's no data for that window and offers the most recent
  complete period instead. *"…this month so far?"* should come back labelled **partial**.
- **Human-in-the-loop** — a full report is presented as a **DRAFT for review**; the agent asks
  you to approve it as final or request changes, and any escalation is phrased as a
  recommendation pending sign-off — never as a done action.
- **Guardrail hook** — `hooks/hooks.json` registers a **PostToolUse** hook
  (`flag_data_gaps.py`) that fires on an all-zeros/empty/future-window result and injects a
  data-quality reminder, as a deterministic backstop under the skill instruction. It ships with
  the plugin (auto-loaded when the plugin is installed). **Hooks load at session start**, so
  start a new session after install before it can fire. *Cowork plugin-hook support is
  unverified — the skill instruction is the portable safety net.*
