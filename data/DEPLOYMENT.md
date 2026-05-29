# Phase 1 Deployment — `adp_data_generator`

**Job:** `adp_data_generator` · job_id **`1063767712826398`**
<https://fevm-umut-aws-classic-stable.cloud.databricks.com/jobs/1063767712826398>

| | |
|---|---|
| Notebook (workspace) | `/Users/umut.tekakca@databricks.com/adp/adp_data_generator` |
| Source of truth | `data/adp_data_generator.py` (re-import after edits) |
| Compute | serverless |
| Schedule | hourly at `:07` UTC, `mode=append`, **UNPAUSED** |
| Target | `umut_aws_classic_stable_catalog.adp` |
| Verify warehouse | Serverless Starter, id `0a6c807a63217e54` |

**Verified seed (2026-05-29):** 6 facilities · 6 factors · 7 targets · 63,321 weather rows · 126,642 readings · range 2024-01-01 → 2026-05-29.

## Runbook
Re-import the notebook after editing the `.py`:
```bash
databricks workspace import "/Users/umut.tekakca@databricks.com/adp/adp_data_generator" \
  --file "data/adp_data_generator.py" --language PYTHON --format SOURCE --overwrite \
  -p fevm-umut-aws-classic-stable
```
Re-seed (rebuild full history; overwrites tables):
```bash
databricks jobs run-now --json '{"job_id":1063767712826398,"notebook_params":{"mode":"seed"}}' \
  -p fevm-umut-aws-classic-stable
```
Manual append (catch up to now):
```bash
databricks jobs run-now --json '{"job_id":1063767712826398,"notebook_params":{"mode":"append"}}' \
  -p fevm-umut-aws-classic-stable
```
Pause / resume the hourly feed (swap `PAUSED`/`UNPAUSED`):
```bash
databricks jobs update --json '{"job_id":1063767712826398,"new_settings":{"schedule":{"quartz_cron_expression":"0 7 * * * ?","timezone_id":"UTC","pause_status":"PAUSED"}}}' \
  -p fevm-umut-aws-classic-stable
```

> The hourly feed uses a little serverless compute each run. Pause it between
> work sessions if you want to pause spend.
