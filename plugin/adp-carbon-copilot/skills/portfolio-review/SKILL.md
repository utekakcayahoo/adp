---
name: portfolio-review
description: Rank the entire facility portfolio against its carbon-reduction targets and flag anomalies, working all facilities in parallel. Use when the user wants a portfolio-wide leaderboard or "which sites are worst vs target". NOT for a single facility. Invocable as /portfolio-review.
argument-hint: (no args — reviews the entire portfolio)
---

Review the **entire facility portfolio** against its carbon-reduction targets.

Drive this with the **carbon-copilot** skill and the `adp` MCP tools. The point is
**parallelism** — don't walk the facilities one at a time. As orchestrator, fan out
**carbon-accountant** across **all** facilities **in parallel**, rank by the gap
(`required_reduction_by_now_pct − pct_reduction_so_far`), then send only the worst 1–2 to
**carbon-analyst** for a quick weather-normalized read. The mechanics of the sweep live in
the carbon-copilot skill's *Multi-facility analysis* section — don't restate them.

Present it as:
- **Leaderboard** — a table of every facility: name, on-track (✓/✗), % reduced so far,
  % required by now, gap. Sorted worst-gap-first.
- **Worst offenders** — the 1–2 sites furthest behind, with the numbers.
- **Anomaly flags** — any site with a suspicious trend (one line each).
- **Portfolio read** — how many sites are on track, and the overall direction of travel.

Every figure must come from a tool call. Do not estimate.
