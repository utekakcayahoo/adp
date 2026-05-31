#!/usr/bin/env python3
"""Run SQL against Databricks via the Statement Execution API.

Transport is the Databricks CLI (`databricks api post ...`), NOT a Python HTTP
client: the corporate TLS proxy injects a self-signed root that breaks
urllib/requests, while the CLI trusts the macOS keychain and works.

Splits the input file on a fixed delimiter line and runs each statement in order
(the Statement Execution API runs one statement per call). Exits non-zero on the
first failure.

Usage:
    python3 data/run_sql.py <file.sql> [--profile P] [--warehouse W]
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

DELIM = "-- @@STATEMENT@@"


def _api(method, path, payload=None, profile="dexter-umut-databricks"):
    cmd = ["databricks", "api", method, path, "-p", profile]
    tmp = None
    if payload is not None:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(payload, tmp)
        tmp.close()
        cmd += ["--json", "@" + tmp.name]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        if tmp:
            os.unlink(tmp.name)
    if out.returncode != 0:
        return {"_cli_error": (out.stderr or out.stdout).strip()}
    return json.loads(out.stdout)


def run_one(stmt, profile, warehouse):
    resp = _api("post", "/api/2.0/sql/statements", {
        "warehouse_id": warehouse,
        "statement": stmt,
        "wait_timeout": "50s",
        "on_wait_timeout": "CONTINUE",
    }, profile)
    if "_cli_error" in resp:
        return resp
    stmt_id = resp.get("statement_id")
    state = resp.get("status", {}).get("state")
    while state in ("PENDING", "RUNNING"):
        time.sleep(2)
        resp = _api("get", f"/api/2.0/sql/statements/{stmt_id}", profile=profile)
        if "_cli_error" in resp:
            return resp
        state = resp.get("status", {}).get("state")
    return resp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--profile", default="dexter-umut-databricks")
    ap.add_argument("--warehouse", default="8b70493184eb2634")
    a = ap.parse_args()

    with open(a.file) as f:
        statements = [s.strip() for s in f.read().split(DELIM) if s.strip()]

    for i, stmt in enumerate(statements, 1):
        r = run_one(stmt, a.profile, a.warehouse)
        if "_cli_error" in r:
            print(f"[{i}/{len(statements)}] CLI ERROR\n{r['_cli_error']}")
            sys.exit(1)
        state = r.get("status", {}).get("state")
        print(f"[{i}/{len(statements)}] state={state}")
        if state != "SUCCEEDED":
            print(json.dumps(r.get("status", {}), indent=2)[:2000])
            sys.exit(1)
        data = r.get("result", {}).get("data_array")
        if data:
            for row in data[:10]:
                print("   ", row)
    print("OK")


if __name__ == "__main__":
    main()
