# Phase 1 Deployment — `adp_data_generator` (Azure workspace)

**Job:** `adp_data_generator` · job_id **`359001941947370`**
<https://adb-4851152775098961.1.azuredatabricks.net/jobs/359001941947370>

| | |
|---|---|
| Notebook (workspace) | `/Users/utekakca@yahoo.com/adp_copilot/adp_data_generator` |
| Source of truth | `data/adp_data_generator.py` (re-import after edits) |
| Compute | serverless |
| Schedule | hourly at `:07` UTC, `mode=append`, **UNPAUSED** |
| Target | `main.adp` |
| Verify warehouse | SQL WH, id `8b70493184eb2634` |

**Verified seed (2026-05-31):** 6 facilities · 6 factors · 7 targets · ~63,486 weather rows · 126,972 readings · range 2024-01-01 → 2026-05-31. `compute_emissions(FAC-001, 2024)` = 172.423 tCO₂e (internally consistent with the stored baseline).

> **Reproducibility note:** the generator uses one global random seed, so values are
> deterministic only for a *fixed* end-time. Regenerating on a different day shifts the
> random stream, so the Azure numbers differ slightly from the original AWS run — each
> run is internally consistent, just not identical across runs.

## Runbook (profile `dexter-umut-databricks`)
Re-import the notebook after editing the `.py`:
```bash
databricks workspace import "/Users/utekakca@yahoo.com/adp_copilot/adp_data_generator" \
  --file "data/adp_data_generator.py" --language PYTHON --format SOURCE --overwrite \
  -p dexter-umut-databricks
```
Re-seed (rebuild full history; overwrites tables):
```bash
databricks jobs run-now --json '{"job_id":359001941947370,"notebook_params":{"mode":"seed"}}' \
  -p dexter-umut-databricks
```
Manual append (catch up to now):
```bash
databricks jobs run-now --json '{"job_id":359001941947370,"notebook_params":{"mode":"append"}}' \
  -p dexter-umut-databricks
```
Pause / resume the hourly feed (swap `PAUSED`/`UNPAUSED`):
```bash
databricks jobs update --json '{"job_id":359001941947370,"new_settings":{"schedule":{"quartz_cron_expression":"0 7 * * * ?","timezone_id":"UTC","pause_status":"PAUSED"}}}' \
  -p dexter-umut-databricks
```

> The hourly feed uses a little serverless compute each run. Pause it between
> work sessions if you want to pause spend.
