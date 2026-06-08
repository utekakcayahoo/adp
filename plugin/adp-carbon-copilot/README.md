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

### Option A — OAuth (production path, **proven 2026-05-31**)
A static OAuth client is registered on the Azure Databricks account
(`adp-carbon-copilot-mcp`, client_id `9bbe5bf5-d69c-4e7f-88b9-6b4005f87af8`,
redirect `http://localhost:8080/callback`, scopes `all-apis`+`offline_access`). Its
**secret lives in the gitignored `.env`** — never committed.

```bash
# from this plugin dir
set -a; . ./.env; set +a
export MCP_CLIENT_SECRET="$ADP_OAUTH_CLIENT_SECRET"   # --client-secret is a flag; it reads this env var
claude mcp add-json adp \
  "{\"type\":\"http\",\"url\":\"https://adb-4851152775098961.1.azuredatabricks.net/api/2.0/mcp/functions/main/adp\",\"oauth\":{\"clientId\":\"$ADP_OAUTH_CLIENT_ID\",\"callbackPort\":8080}}" \
  -s user --client-secret
```
Then in a new session: `/mcp` → select `adp` → **Authenticate** → browser login →
`adp` shows **connected, 6 tools** (`list_facilities`, `query_energy`, `query_weather`,
`compute_emissions`, `target_progress`, `search_standards`).

> **Verified:** authenticated via the OAuth browser flow as `umut.tekakca@databricks.com`
> and the agent called `list_facilities` → `compute_emissions` → `target_progress`,
> returning a correct, tool-grounded answer. **Unity Catalog enforces per-user access**,
> so whoever authenticates must have read/execute on `main.adp`.

### Option B — token header (quick local dev)
Simpler for a fast check; the committed `.mcp.json` reads `DATABRICKS_TOKEN` so no
secret is committed:
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
