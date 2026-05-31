# adp-carbon-copilot (Claude plugin)

The Facility Energy & Carbon Co-pilot, packaged as a Claude **plugin** — the same
format Claude Code and Cowork both load. Skills-first: behavior lives in `skills/`,
data access in `.mcp.json` (the Databricks managed MCP server).

```
adp-carbon-copilot/
├── .claude-plugin/plugin.json   # manifest
├── .mcp.json                    # MCP server: Databricks managed UC-functions endpoint
├── skills/carbon-copilot/SKILL.md
└── commands/carbon-report.md    # /carbon-report <facility> [period]
```

The MCP tools come from `mcp/adp_uc_functions.sql` (see `mcp/MCP.md`).

> **Two separate wiring steps — both are needed.** Registering the **MCP server**
> (below) makes the *tools* available. Installing the **skill** makes the *skill*
> drive the behavior (routing, no-fabrication guardrail, report format). With only the
> MCP registered, a capable model will use the tools well on its own — but the skill
> is what *guarantees* that behavior every time, including on weaker models.

## 1. Install the skill
**Claude Code (local):** symlink the skill into your personal skills dir, then start a
new session:
```bash
ln -s "$(pwd)/skills/carbon-copilot" ~/.claude/skills/carbon-copilot
```
**Cowork (production):** the skill ships *inside* the plugin — installing the plugin
registers the skill, `.mcp.json`, and `/carbon-report` together (Phase 8).

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
`adp` shows **connected, 4 tools**.

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
