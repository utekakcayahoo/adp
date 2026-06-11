#!/usr/bin/env python3
"""ADP Phase 8 — data-layer regression for the carbon co-pilot's tools.

Calls the five Unity Catalog functions that back the MCP tools and asserts the
planted answer key still holds (see docs/data-model.md). This tests the *data /
tool layer* the agent depends on — NOT the agent's behaviour (that's the
golden-scenario rubric in eval/golden_scenarios.md, run in a live session).

Transport is the Databricks CLI (`databricks api post ...`), same as
data/run_sql.py: the corporate TLS proxy breaks urllib/requests, but the CLI
trusts the macOS keychain.

Usage:
    python3 eval/run_regression.py [--profile P] [--warehouse W]

Exit code 0 = all checks passed; 1 = at least one failed.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import os

PROFILE = "dexter-umut-databricks"
WAREHOUSE = "8b70493184eb2634"


def sql(stmt):
    """Run one SQL statement, return the parsed JSON in result.data_array[0][0]."""
    payload = {"warehouse_id": WAREHOUSE, "statement": stmt,
               "wait_timeout": "50s", "on_wait_timeout": "CONTINUE"}
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(payload, tmp)
    tmp.close()
    try:
        out = subprocess.run(
            ["databricks", "api", "post", "/api/2.0/sql/statements",
             "-p", PROFILE, "--json", "@" + tmp.name],
            capture_output=True, text=True)
    finally:
        os.unlink(tmp.name)
    if out.returncode != 0:
        raise RuntimeError((out.stderr or out.stdout).strip())
    resp = json.loads(out.stdout)
    # poll if still running
    sid = resp.get("statement_id")
    while resp.get("status", {}).get("state") in ("PENDING", "RUNNING"):
        import time
        time.sleep(2)
        g = subprocess.run(["databricks", "api", "get",
                            f"/api/2.0/sql/statements/{sid}", "-p", PROFILE],
                           capture_output=True, text=True)
        resp = json.loads(g.stdout)
    state = resp.get("status", {}).get("state")
    if state != "SUCCEEDED":
        raise RuntimeError(json.dumps(resp.get("status", {}))[:500])
    cell = resp["result"]["data_array"][0][0]
    return json.loads(cell)


def tool(fn, *args):
    """Call a UC function tool: tool('compute_emissions','FAC-001','2024-01-01','2024-12-31')."""
    arglist = ", ".join("'" + str(a) + "'" for a in args)
    return sql(f"SELECT main.adp.{fn}({arglist}) AS output")


# --- checks: each returns (name, passed: bool, detail: str) ---
CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


@check("facilities: 6 sites, FAC-001..FAC-006")
def c_facilities():
    facs = tool("list_facilities")
    ids = sorted(f["facility_id"] for f in facs)
    exp = [f"FAC-00{i}" for i in range(1, 7)]
    return ids == exp, f"got {ids}"


@check("baseline: FAC-001 2024 total ~ 172.4 tCO2e")
def c_baseline():
    e = tool("compute_emissions", "FAC-001", "2024-01-01", "2024-12-31")
    t = e["total_tco2e"]
    return abs(t - 172.4) < 1.5, f"total={t} (scope1={e['scope1_tco2e']}, scope2={e['scope2_tco2e']})"


@check("FAC-004 Mar-2025 total ~ 77.5, both scopes > 0")
def c_march():
    e = tool("compute_emissions", "FAC-004", "2025-03-01", "2025-03-31")
    ok = abs(e["total_tco2e"] - 77.5) < 1.5 and e["scope1_tco2e"] > 0 and e["scope2_tco2e"] > 0
    return ok, f"total={e['total_tco2e']} s1={e['scope1_tco2e']} s2={e['scope2_tco2e']}"


@check("FAC-004 HVAC fault: Mar-2025 elec >= 1.3x Mar-2024 (planted x1.8 spike)")
def c_spike():
    e = tool("query_energy", "FAC-004", "2024-01-01", "2025-12-31")
    by = {r["month"]: r["electricity_kwh"] for r in e}
    m24, m25 = by.get("2024-03-01"), by.get("2025-03-01")
    ratio = m25 / m24 if m24 else 0
    return ratio >= 1.3, f"Mar2024={m24} Mar2025={m25} ratio={ratio:.2f}"


@check("FAC-004 weather flat: Mar heating-degree-hrs ~flat YoY, cooling ~0 (rules out weather)")
def c_weather():
    w = tool("query_weather", "FAC-004", "2024-01-01", "2025-12-31")
    by = {r["month"]: r for r in w}
    h24 = by["2024-03-01"]["heating_degree_hours"]
    h25 = by["2025-03-01"]["heating_degree_hours"]
    c25 = by["2025-03-01"]["cooling_degree_hours"]
    ratio = h25 / h24 if h24 else 0
    ok = 0.8 <= ratio <= 1.2 and c25 < 50
    return ok, f"heating Mar24={h24} Mar25={h25} ratio={ratio:.2f}, cooling Mar25={c25}"


@check("FAC-006 load creep: only site with negative reduction & the worst gap")
def c_creep():
    rows = {}
    for i in range(1, 7):
        fid = f"FAC-00{i}"
        tp = tool("target_progress", fid)
        gap = tp["required_reduction_by_now_pct"] - tp["pct_reduction_so_far"]
        rows[fid] = (tp["pct_reduction_so_far"], gap)
    worst = max(rows, key=lambda k: rows[k][1])
    f6_neg = rows["FAC-006"][0] < 0
    negs = [k for k, v in rows.items() if v[0] < 0]
    ok = worst == "FAC-006" and f6_neg and negs == ["FAC-006"]
    detail = "; ".join(f"{k}: red={v[0]} gap={v[1]:.1f}" for k, v in sorted(rows.items()))
    return ok, f"worst={worst}, negatives={negs} | {detail}"


@check("silent zero: future window returns total=0 & 0 kWh (Phase-7 substrate)")
def c_silent_zero():
    e = tool("compute_emissions", "FAC-001", "2026-08-01", "2026-08-31")
    ok = e["total_tco2e"] == 0 and e["electricity_kwh"] == 0 and e["gas_kwh"] == 0
    return ok, f"{e}"


@check("unknown facility: target_progress('FAC-999') is empty {}")
def c_unknown():
    tp = tool("target_progress", "FAC-999")
    return tp == {} or "baseline_year" not in tp, f"{tp}"


def main():
    global PROFILE, WAREHOUSE
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default=PROFILE)
    ap.add_argument("--warehouse", default=WAREHOUSE)
    a = ap.parse_args()
    PROFILE, WAREHOUSE = a.profile, a.warehouse

    print(f"ADP data-layer regression — {len(CHECKS)} checks\n" + "=" * 70)
    passed = 0
    for name, fn in CHECKS:
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"ERROR: {e}"
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}\n       {detail}")
    print("=" * 70)
    print(f"{passed}/{len(CHECKS)} passed")
    sys.exit(0 if passed == len(CHECKS) else 1)


if __name__ == "__main__":
    main()
