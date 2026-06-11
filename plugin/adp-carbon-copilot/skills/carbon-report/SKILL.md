---
name: carbon-report
description: Generate a full, multi-section carbon & energy report for ONE facility over a period — weather-aware, with anomaly diagnosis. Use when the user wants a written report / write-up on a facility. NOT for a single-number lookup. Invocable as /carbon-report <facility> [period].
argument-hint: <facility name or id> [period, e.g. "Q1 2025" or "2025"]
---

Produce a carbon & energy report for: **$ARGUMENTS**

This is the **full-report** entry point. Drive it with the **carbon-copilot** skill and
the `adp` MCP tools, and run the **specialist pipeline** exactly as that skill's
*Working as a team* section defines it:

1. Spawn **carbon-analyst** and **carbon-accountant** on the facility **in parallel**.
2. Give both findings blocks to **carbon-reporter**, which composes the report in its own format.

Pass each findings block **forward verbatim** — every figure must trace to a tool call
made inside a specialist; never estimate. The *how* for each step (facility resolution,
the anomaly routine, the report layout) already lives in the carbon-copilot skill and the
specialists' own files — don't restate it here.

If $ARGUMENTS omits the period, default to the most recent full calendar year (a report
wants a year, not a month) and say which year you used. If the data doesn't cover the whole
period (a partial/stale feed), report the **complete** window you can and flag the gap — don't
present a silent zero as the answer (see carbon-copilot's *When the data is missing…* section).

Present the result as a **DRAFT for review** and ask the user to approve it as final or request
changes — it isn't final until they sign off (carbon-copilot's *Approve before it's final*).
