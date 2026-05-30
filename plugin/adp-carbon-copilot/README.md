# adp-carbon-copilot (Claude plugin)

The Facility Energy & Carbon Co-pilot, packaged as a Claude **plugin** — the same
format Claude Code and Cowork both load. It's skills-first: the behavior lives in
`skills/`, the data access in `.mcp.json` (the Databricks managed MCP server).

```
adp-carbon-copilot/
├── .claude-plugin/plugin.json   # manifest
├── .mcp.json                    # MCP server: Databricks managed UC-functions endpoint
├── skills/carbon-copilot/SKILL.md
└── commands/carbon-report.md    # /carbon-report <facility> [period]
```

The MCP tools come from `mcp/adp_uc_functions.sql` (see `mcp/MCP.md`).

## Connect for local testing (Claude Code)
The committed `.mcp.json` reads the token from an env var, so **no secret is committed**.

1. Get a token (short-lived OAuth token, or create a PAT for a longer life):
   ```bash
   export DATABRICKS_TOKEN=$(databricks auth token -p fevm-umut-aws-classic-stable \
     | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
   ```
2. Point Claude Code at this plugin's MCP server, e.g.:
   ```bash
   claude mcp add adp --transport http \
     "https://fevm-umut-aws-classic-stable.cloud.databricks.com/api/2.0/mcp/functions/umut_aws_classic_stable_catalog/adp" \
     --header "Authorization: Bearer $DATABRICKS_TOKEN"
   ```
3. In a new Claude Code session: `/mcp` should list `adp` as connected with 4 tools.
   Ask: *"How much CO₂ did the Central Warehouse emit in March 2025?"*

> Verified at the protocol level: `initialize` + `tools/list` + `tools/call` all
> succeed against this endpoint with bearer-token auth. The interactive OAuth login
> flow (below) has not yet been exercised from a Claude client.

## Connect in Cowork (production)
Cowork can't take a raw token from end users; it uses OAuth. Create a **static OAuth
client** (Databricks doesn't support dynamic registration) and reference it:

```bash
databricks account custom-app-integration create --json '{
  "name":"adp-carbon-copilot-mcp",
  "redirect_urls":["http://localhost:8080/callback"],
  "confidential":true,
  "scopes":["unity-catalog","offline_access"]
}'
```
Then the plugin's `.mcp.json` uses the OAuth client id instead of the token header.
(Exact Cowork install flow is exercised in Phase 8.)
