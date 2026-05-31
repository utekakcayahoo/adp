---
description: Generate a carbon & energy report for a facility over a period (multi-step, weather-aware)
argument-hint: <facility name or id> [period, e.g. "Q1 2025" or "2025"]
---

Produce a carbon & energy report for: **$ARGUMENTS**

Use the `carbon-copilot` skill and the `adp` MCP tools. This is a **planned, multi-step**
job — state a one-line plan, then run the chain. Every figure must come from a tool
call; never estimate.

## Plan, then chain
1. **Resolve the facility.** If a name/city was given, `list_facilities` → map to its id.
2. **Fix the period.** Convert the request to explicit dates. If none was given, use the
   most recent full calendar year and **say which year you used**.
3. **Headline emissions.** `compute_emissions(facility, start, end)` → total tCO₂e and the
   Scope 1 (gas) / Scope 2 (electricity) split.
4. **Trend + anomaly scan.** `query_energy` over the period **plus the 12 months before it**
   (so you can compare year-on-year). Identify the monthly shape and flag any month that
   breaks from the prior year — note whether it's a **bounded spike** or a **persistent drift**.
5. **Diagnose if warranted.** If step 4 flagged anything, run the skill's *Diagnosing an
   anomaly* routine: `query_weather` for the flagged months and the same months a year
   earlier, then decide **weather-driven vs likely fault/load-growth** from the
   degree-hours comparison. Skip this step (and say "no anomalies") if the trend is clean.
6. **Target status.** `target_progress(facility)` → on track or not, with
   `pct_reduction_so_far` vs `required_reduction_by_now_pct`.

## Report format
Write it as:
- **Facility & period** — name, id, the exact dates used.
- **Emissions** — total tCO₂e; Scope 1 vs Scope 2; and the kWh behind them.
- **Trend** — one or two sentences on the monthly shape; explicitly flag spikes/drift.
- **Diagnosis** — only if an anomaly was found: the deviation (%, vs prior year), the
  weather comparison that rules weather in or out, the likely explanation + a suggested
  check. State your confidence.
- **Target** — on-track verdict with the two percentages and the gap.
- **One-line takeaway.**
