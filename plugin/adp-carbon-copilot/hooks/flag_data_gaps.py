#!/usr/bin/env python3
"""ADP Phase 7 guardrail — PostToolUse hook (Exception Handling & Recovery / Safety).

The adp MCP tools never raise: a window with no data comes back as an **all-zeros**
emissions struct, an unknown facility as **`{}`**, an empty series as `[]`/`null`, and a
future/partial window as zeros too. A model can mistake any of these for a real answer
("emitted 0 tCO2e", "on track"). This hook reads the PostToolUse payload on stdin and,
on a hit, injects a reminder via `additionalContext` so the silent zero can't pass as
fact. No hit -> silent no-op. It is read-only and NEVER blocks the tool (it already ran).

Deterministic checks:
  1. all-zeros emissions  (total_tco2e == 0 AND electricity_kwh == 0)  -> NO DATA, not 0.
  2. empty result shape   ([[{}]] / [[null]] / [[[]]])                 -> no rows for query.
  3. window past today    (tool_input end_date/start_date > today)     -> future or partial.
Robust to nesting/escaping by normalizing the stringified response (drop \\ " and spaces).
"""
import datetime as dt
import json
import re
import sys


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return  # malformed input is not ours to police — stay silent

    if "adp" not in payload.get("tool_name", ""):
        return

    tool_input = payload.get("tool_input") or {}
    # Normalize the whole response to text, then strip quotes/backslashes/whitespace so the
    # signatures match no matter how deeply the MCP result is wrapped or escaped.
    blob = json.dumps(payload.get("tool_response", ""))
    clean = blob.replace("\\", "").replace('"', "").replace(" ", "")

    notes = []

    zero = r"0(\.0+)?(?![.\d])"  # matches 0 or 0.0 but not 0.123 (a real near-zero value)
    if re.search(r"total_tco2e:" + zero, clean) and re.search(r"electricity_kwh:" + zero, clean):
        notes.append(
            "compute_emissions returned ALL ZEROS — that means NO DATA for this window, "
            "not 0 tCO2e."
        )

    if any(s in clean for s in ("[[{}]]", "[[null]]", "[[[]]]")):
        notes.append(
            "the tool returned an empty/`{}`/null result — no rows for this query "
            "(unknown facility id, or no data in the window)."
        )

    end = tool_input.get("end_date") or tool_input.get("start_date")
    if end:
        try:
            if dt.date.fromisoformat(str(end)) > dt.date.today():
                notes.append(
                    f"the requested window ends {end}, in the future relative to today — "
                    "the period is future or only partially covered."
                )
        except ValueError:
            pass

    if not notes:
        return

    msg = (
        "DATA-QUALITY GUARDRAIL (Phase 7): "
        + " ".join(notes)
        + " Do NOT report a silent zero as fact. Fall back to the most recent complete "
        "window, say which one you used, and flag the gap (cite the data-quality standard)."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        }
    }))


if __name__ == "__main__":
    main()
