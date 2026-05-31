---
description: Rank the whole facility portfolio against its reduction targets and flag anomalies (parallel)
argument-hint: (no args — reviews the entire portfolio)
---

Review the **entire facility portfolio** against its carbon-reduction targets.

Use the `carbon-copilot` skill and the `adp` MCP tools. The point of this command is
**parallelism** — don't walk the facilities one at a time.

## Steps
1. **Enumerate.** `list_facilities` once to get every facility id.
2. **Fan out (parallel).** For **all** facilities, call `target_progress` **together in a
   single step** — issue the calls concurrently, not sequentially.
3. **Rank.** Sort by the **gap** = `required_reduction_by_now_pct − pct_reduction_so_far`.
   A larger positive gap = further behind the linear path to target. `on_track=false`
   sites float to the top.
4. **Spot anomalies.** Note any site whose `current_12mo_tco2e` looks out of line with its
   baseline in a way the others don't. If one clearly stands out, you may drill in with
   `query_energy` + `query_weather` (parallel across just the suspects) to say whether it's
   weather or a likely fault — but keep it brief; `/carbon-report <facility>` is the deep dive.

## Report format
- **Leaderboard** — a table of every facility: name, on-track (✓/✗), % reduced so far,
  % required by now, gap. Sorted worst-gap-first.
- **Worst offenders** — the 1–2 sites furthest behind, with the numbers.
- **Anomaly flags** — any site with a suspicious trend (one line each).
- **Portfolio read** — how many sites are on track, and the overall direction of travel.

Every figure must come from a tool call. Do not estimate.
