---
description: Generate a carbon & energy report for a facility over a period
argument-hint: <facility name or id> [period, e.g. "Q1 2025" or "2025"]
---

Produce a concise carbon & energy report for: **$ARGUMENTS**

Use the carbon-copilot skill and the `adp` MCP tools. Steps:
1. Resolve the facility to its id with `list_facilities` if a name/city was given.
2. Determine the period from the request (default: the most recent full calendar
   year, and say which year you used).
3. Call `compute_emissions` for the period and `query_energy` for the monthly trend.
4. Call `target_progress` to state whether the facility is on track.
5. Write a short report: total tCO₂e (Scope 1 vs Scope 2), the monthly trend in one
   or two sentences (flag any obvious spike), and target status with the numbers.

Every figure must come from a tool call. Do not estimate.
