# Evaluation — Facility Energy & Carbon Co-pilot

Phase 8 evaluation, in two layers. The book pattern is **Evaluation & Monitoring**:
test the deterministic substrate cheaply and continuously, and the agent's judgement
against a fixed rubric.

```
eval/
├── run_regression.py    # Layer 1 — data/tool-layer regression (deterministic, runnable in CI)
└── golden_scenarios.md  # Layer 2 — agent-behaviour eval spec + scoring rubric (run in a live session)
```

## Layer 1 — data-layer regression  (`run_regression.py`)
Calls the six UC functions behind the MCP tools and asserts the planted answer key
(`docs/data-model.md`) still holds: facility list, the FAC-001 2024 baseline, the FAC-004
March-2025 figure, the **FAC-004 HVAC spike** (electricity up YoY while degree-hours flat →
equipment fault), the **FAC-006 load creep** (only site above baseline / worst gap), the
**Phase-7 silent-zero substrate** (future window → all zeros; unknown id → `{}`), and **RAG
retrieval** (HVAC / data-quality / warehouse queries hit the right standard).

```bash
python3 eval/run_regression.py            # exits 0 if all checks pass, 1 otherwise
```
- **No model calls** — pure tool/data assertions, so it's cheap and repeatable (regression gate).
- **Transport:** the Databricks CLI Statement Execution API (same as `data/run_sql.py`) — the
  corporate TLS proxy breaks urllib; the CLI trusts the macOS keychain. Needs a valid
  `dexter-umut-databricks` profile and warehouse `8b70493184eb2634`.
- **Dependency:** the three RAG checks need the `adp_vs` endpoint + `main.adp.adp_standards_index`
  online. If `adp_vs` is torn down for cost, those three checks fail with a `vector_search`
  error and the other nine still pass.

## Layer 2 — golden scenarios  (`golden_scenarios.md`)
Ten prompts (S1–S10) that exercise routing, grounding, the anomaly chain, recommendations +
citation, memory, the silent-zero exception, partial periods, the HITL gates, and the full
report pipeline. Run them in a **fresh session** with the plugin installed and `adp`
authenticated, and score each against the rubric. This is the only path to behaviour-level
eval while Cowork (no model hook) is the runtime — see `docs/observability.md`.

## What this layer does NOT do (honest scope)
- **No model-in-the-loop auto-runner.** The chosen scope is *regression + rubric*. A thin
  `claude_agent_sdk` harness that fires S1–S10 and auto-scores with full MLflow agent traces
  remains the documented future lever, not built here.
- **Live tool-call monitoring** (which tool ran, args, as whom) is the Databricks query-history /
  audit story in `docs/observability.md`, not this harness.
