# Phase 2 — MCP server (Databricks managed)

**No server code.** The six Unity Catalog functions in
`main.adp` are auto-exposed as MCP tools by Databricks'
**managed MCP server**. Source of the functions: `mcp/adp_uc_functions.sql`.

## Endpoint
```
https://adb-4851152775098961.1.azuredatabricks.net/api/2.0/mcp/functions/main/adp
```
Verified: `initialize` + `tools/list` → **6 tools** (protocol `2025-06-18`,
serverInfo `DatabricksMCPServer`). Was 4 through Phase 3; `query_weather` added in Phase 4;
`search_standards` (RAG) added in Phase 5.

## Tools (as the model sees them)
Tool name = `{catalog}__{schema}__{function}`; description + arg schema come from the
function and parameter `COMMENT`s.

| Tool | Args | Returns (JSON) |
|---|---|---|
| `…__adp__list_facilities` | — | array of facilities |
| `…__adp__query_energy` | facility, start_date, end_date | monthly electricity_kwh / gas_kwh |
| `…__adp__query_weather` | facility, start_date, end_date | monthly avg_temp_c / heating & cooling degree-hours (facility's city) |
| `…__adp__compute_emissions` | facility, start_date, end_date | scope1 / scope2 / total tCO₂e (+ kWh) |
| `…__adp__target_progress` | facility | baseline, current 12-mo, % reduced, on_track |
| `…__adp__search_standards` | query | top-5 policy/standards matches {id,title,category,body,source,score} |

`query_weather` (added Phase 4) powers weather-normalized anomaly diagnosis — compare an
energy spike against degree-hours to tell a fault from a hot/cold spell.

`search_standards` (added Phase 5) is **RAG**: it wraps the `vector_search()` SQL TVF over
the Delta Sync index `main.adp.adp_standards_index` (endpoint `adp_vs`, Databricks-managed
embeddings `databricks-gte-large-en`) so the agent grounds policy answers and action
recommendations in the `adp_standards` corpus. The `adp_vs` endpoint is **billable** while
it exists — delete it when the phase is done.

## Auth
OAuth, with **Unity Catalog permissions enforced** (the agent only sees tools/data
the user may access). Two client paths:
- **Bearer token** (what we tested): `Authorization: Bearer $(databricks auth token -p dexter-umut-databricks)`. Verified working via `curl`.
- **OAuth U2M** (what Claude Code / Cowork use): static OAuth client, redirect
  `http://localhost:8080/callback`. Exercised in **Phase 3** when we connect a client.

## Connect from clients (Phase 3)
- **Claude Code:** `claude mcp add` with the OAuth config (to run/verify in Phase 3).
- **Cowork plugin:** ship the server in the plugin's `.mcp.json` (remote, OAuth). Shape:
  ```json
  { "name": "adp",
    "url": "https://adb-4851152775098961.1.azuredatabricks.net/api/2.0/mcp/functions/main/adp",
    "oauth": true }
  ```
  Exact schema confirmed when we scaffold the plugin.

## Local gotcha (corporate TLS)
A corporate proxy injects a self-signed root into the TLS chain. Python
`urllib`/`requests` fail cert verification unless pointed at the corporate CA bundle;
`curl` and the Databricks CLI use the macOS keychain and work. Relevant if we run a
Python MCP client locally.

## Re-deploy the tools
```bash
# edit mcp/adp_uc_functions.sql, then re-run each CREATE OR REPLACE FUNCTION
# (the functions are picked up by the managed MCP server immediately)
```
