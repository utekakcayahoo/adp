# adp-carbon-copilot (Claude plugin)

The Facility Energy & Carbon Co-pilot, packaged as a Claude **plugin** — the same
format Claude Code and Cowork both load. Skills-first: behavior lives in `skills/`,
data access in `.mcp.json` (the Databricks managed MCP server).

```
adp-carbon-copilot/
├── .claude-plugin/plugin.json   # manifest
├── .mcp.json                    # MCP server: Databricks managed UC-functions endpoint
├── skills/carbon-copilot/SKILL.md
├── agents/                      # Phase 6 specialist sub-agents (the "team")
│   ├── carbon-analyst.md        # energy + weather + anomaly diagnosis
│   ├── carbon-accountant.md     # emissions (Scope 1/2) + target progress
│   ├── carbon-advisor.md        # prioritized, policy-cited actions (RAG)
│   └── carbon-reporter.md       # synthesizes the findings into the report
└── commands/
    ├── carbon-report.md         # /carbon-report <facility> [period]  (specialist pipeline)
    └── portfolio-review.md      # /portfolio-review  (parallel multi-facility sweep)
```

The MCP tools come from `mcp/adp_uc_functions.sql` (see `mcp/MCP.md`).

> **Two separate wiring steps — both are needed.** Registering the **MCP server**
> (below) makes the *tools* available. Installing the **skill** makes the *skill*
> drive the behavior (routing, no-fabrication guardrail, report format). With only the
> MCP registered, a capable model will use the tools well on its own — but the skill
> is what *guarantees* that behavior every time, including on weaker models.

## 1. Install the skill + sub-agents + commands
**Claude Code (local):** symlink the skill, the four specialist sub-agents, and both
slash commands into your personal dirs (symlinks, so repo edits propagate), then start a
new session:
```bash
# from this plugin dir
ln -sf "$(pwd)/skills/carbon-copilot"        ~/.claude/skills/carbon-copilot
ln -sf "$(pwd)/commands/carbon-report.md"    ~/.claude/commands/carbon-report.md
ln -sf "$(pwd)/commands/portfolio-review.md" ~/.claude/commands/portfolio-review.md
mkdir -p ~/.claude/agents
for a in carbon-analyst carbon-accountant carbon-advisor carbon-reporter; do
  ln -sf "$(pwd)/agents/$a.md" ~/.claude/agents/$a.md
done
```
This registers the `carbon-copilot` skill, the four **specialist sub-agents** (analyst,
accountant, advisor, reporter — the orchestrated "team"), plus `/carbon-report <facility>
[period]` (planned, weather-aware report) and `/portfolio-review` (parallel sweep). Skills,
agents, and commands are re-scanned per session — **start a new session** before the named
sub-agents can be spawned. **Cowork (production):** the skill + agents + commands ship
*inside* the plugin — installing the plugin registers all of them with `.mcp.json` (Phase 8).

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

For Phase 6 (the **team**), run `/carbon-report Central Warehouse 2025`. The orchestrator
spawns **carbon-analyst** ∥ **carbon-accountant** in parallel, hands the target gap to
**carbon-advisor**, and lets **carbon-reporter** compose the final report — each figure
still traced to a tool call inside a specialist. A simple one-tool question (*"CO₂ at HQ
last month?"*) is answered **solo** — the skill only convenes the team when the depth is
worth it.
