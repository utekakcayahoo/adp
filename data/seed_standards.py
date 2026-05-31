#!/usr/bin/env python3
"""Generate data/adp_standards_seed.sql — the adp_standards knowledge corpus.

The corpus is the RAG source for Phase 5: short, self-contained policy chunks a
facility energy/carbon co-pilot should cite. Each chunk maps to existing tools and
to the planted anomalies (e.g. the HVAC/runbook/warehouse chunks back the FAC-004
fault diagnosis; the PUE chunk backs the FAC-006 load-creep call).

Kept as a generator so single-quote escaping for SQL is automatic. Run:
    python3 data/seed_standards.py        # writes the .sql
    python3 data/run_sql.py data/adp_standards_seed.sql
"""
import os

# (id, category, title, body, source)
STANDARDS = [
    ("STD-HVAC-SETPOINT", "hvac", "HVAC temperature setpoint policy",
     "Occupied-hours setpoints: heating no higher than 20 C, cooling no lower than 24 C, "
     "with a minimum 4 C deadband so heating and cooling never run at once. Unoccupied "
     "setback: 16 C heating / 28 C cooling. Each 1 C of setpoint tightening saves roughly "
     "3-5% of HVAC energy. Setpoints are reviewed seasonally. Manual overrides require "
     "facilities-manager approval and must auto-expire within 72 hours.",
     "ADP Facilities Standards v1 (illustrative)"),

    ("STD-ANOMALY-RUNBOOK", "operations", "Energy anomaly investigation runbook",
     "When a facility's monthly electricity or gas use rises materially versus the same "
     "month a year earlier, weather-normalize before acting: compare heating and cooling "
     "degree-hours year over year. If consumption is up but degree-hours are flat (within "
     "~10%), weather does not explain it - open a maintenance investigation. A sharp, "
     "bounded spike that returns to normal points to an equipment fault (for example an "
     "HVAC unit stuck on). A slow, persistent year-over-year climb points to load growth "
     "or degrading efficiency. Open a ticket when an unexplained deviation exceeds 15% for "
     "two or more weeks.",
     "ADP Operations Runbook (illustrative)"),

    ("STD-GHG-SCOPES", "accounting", "GHG Protocol emission scopes",
     "Emissions follow the GHG Protocol. Scope 1 is direct emissions from on-site "
     "combustion - here, natural gas burned for heating. Scope 2 is indirect emissions "
     "from purchased electricity, computed with the location-based method using "
     "grid-region emission factors. Scope 3 (value-chain emissions) is not modeled or "
     "reported. Always report Scope 1 and Scope 2 separately; never net them against each "
     "other or against offsets.",
     "GHG Protocol Corporate Standard (illustrative summary)"),

    ("STD-EMISSION-FACTORS", "accounting", "Emission factor sourcing and method",
     "Carbon is computed as energy (kWh) times an emission factor (kgCO2e/kWh), never "
     "measured directly. Electricity factors are grid-region specific and reflect the "
     "local generation mix; natural gas uses a single combustion factor. Factors here are "
     "illustrative, not certified, and each carries a validity window. Use the "
     "location-based method, and when a factor changes mid-period apply each factor only "
     "within its valid dates. Report the factor source and vintage with any emissions "
     "figure.",
     "ADP Carbon Accounting Method (illustrative)"),

    ("STD-TARGET-METHOD", "targets", "Reduction target methodology",
     "Each facility and the organization carry a baseline-year (2024) emissions figure and "
     "a percent reduction target for a target year (2030). Progress is judged against a "
     "straight linear path: required reduction by now = target percent times (years "
     "elapsed / total years). A facility is on track when its trailing-12-month reduction "
     "versus baseline meets or exceeds that linear requirement. A trailing-12-month window "
     "can lag a recent event, so a site may read on track even with a recent spike inside "
     "the calendar year - call this out when it happens.",
     "ADP Target Framework (illustrative)"),

    ("STD-EEM-CATALOG", "efficiency", "Energy efficiency measures catalog",
     "Standard measures and typical savings: LED lighting retrofit (10-15% of electricity "
     "in lit areas); HVAC scheduling and occupancy-based control (5-12% of HVAC); setpoint "
     "optimization and wider deadbands (3-8%); economizer / free-cooling repair (variable, "
     "often large after a fault); envelope sealing (2-6% of heating). Prioritize by payback "
     "period and by the size of the gap to the facility's target, and verify savings "
     "against metered data after the work.",
     "ADP Efficiency Playbook (illustrative)"),

    ("STD-DATACENTER-PUE", "datacenter", "Data center efficiency (PUE) standard",
     "Data centers are measured by Power Usage Effectiveness (PUE = total facility power / "
     "IT equipment power). Target PUE for edge sites is 1.5 or lower. IT load may grow with "
     "demand, but total electricity rising faster than IT load - or rising while weather is "
     "flat - signals cooling inefficiency or load creep and warrants review. A persistent "
     "year-over-year electricity climb above ~5% that outpaces the efficiency trend should "
     "be investigated even without a single obvious spike.",
     "ADP Data Center Standard (illustrative)"),

    ("STD-DATA-QUALITY", "operations", "Meter data quality rules",
     "Readings are hourly per facility. Reject negative consumption and impossible spikes "
     "(for example above 5x the facility's rolling median) pending review. Flag gaps where "
     "expected hourly readings are missing; do not silently interpolate across gaps longer "
     "than 6 hours. Late-arriving data can revise recent totals, so treat the most recent "
     "few days as provisional. Never fabricate a value to fill a gap - report the gap "
     "instead.",
     "ADP Data Quality Standard (illustrative)"),

    ("STD-REPORTING-CADENCE", "reporting", "Reporting and disclosure cadence",
     "Operational reviews run monthly: consumption, emissions, anomalies, and target "
     "progress per facility. A consolidated ESG report is produced annually covering Scope "
     "1 and Scope 2 emissions, year-over-year change, progress against the 2030 target, and "
     "material anomalies with their resolution. Every figure must be traceable to source "
     "data; label estimates as estimates. Reports are reviewed and approved before external "
     "disclosure.",
     "ADP Disclosure Policy (illustrative)"),

    ("STD-ESCALATION", "operations", "Escalation thresholds",
     "Escalate to the facilities manager when an unexplained energy deviation exceeds 15% "
     "for two or more weeks, when a facility falls behind its linear target path by more "
     "than 10 percentage points, or when a data gap exceeds 24 hours. Escalate to "
     "sustainability leadership when a facility is projected to miss its annual target or "
     "when a portfolio-wide trend threatens the organization target. Every escalation "
     "records the evidence: metered deviation, weather normalization, and the affected "
     "period.",
     "ADP Operations Runbook (illustrative)"),

    ("STD-WAREHOUSE", "warehouse", "Warehouse energy guidance",
     "Warehouses are dominated by conditioning of large volumes and by lighting. High-bay "
     "LED with occupancy sensors and daylight harvesting is the first-priority measure. "
     "Dock-door discipline (minimizing open time) cuts heating and cooling load in extreme "
     "weather. Because occupancy density is low, aggressive unoccupied setbacks are usually "
     "safe. A warehouse showing an electricity spike with flat degree-hours most often has "
     "an HVAC or refrigeration fault rather than a weather cause.",
     "ADP Facilities Standards v1 (illustrative)"),

    ("STD-RENEWABLE", "procurement", "Renewable electricity and RECs",
     "Pursue reductions first through efficiency (fewer kWh), then through cleaner supply. "
     "Renewable Energy Certificates (RECs) and power purchase agreements reduce "
     "market-based Scope 2 but do not change the location-based figure this system reports. "
     "Do not claim a reduction from RECs in location-based reporting. Track procurement "
     "separately and disclose the method (location-based vs market-based) explicitly to "
     "avoid double counting.",
     "ADP Procurement Policy (illustrative)"),
]

DELIM = "-- @@STATEMENT@@"


def sq(s):
    """Escape a string for a single-quoted Spark SQL literal.

    Spark's default parser uses BACKSLASH escaping inside string literals (\\' for a
    quote), NOT ANSI quote-doubling. Through the Statement Execution API, '' silently
    drops the apostrophe (verified). Escape backslash first, then the single quote.
    """
    return s.replace("\\", "\\\\").replace("'", "\\'")


def main():
    # IF NOT EXISTS + TRUNCATE (not CREATE OR REPLACE) so re-runs keep the same table
    # object and don't disrupt the Vector Search index that syncs from it.
    create = (
        "CREATE TABLE IF NOT EXISTS main.adp.adp_standards (\n"
        "  id STRING NOT NULL,\n"
        "  title STRING,\n"
        "  category STRING,\n"
        "  body STRING,\n"
        "  source STRING,\n"
        "  CONSTRAINT adp_standards_pk PRIMARY KEY (id)\n"
        ")\n"
        "TBLPROPERTIES (delta.enableChangeDataFeed = true)"
    )
    truncate = "TRUNCATE TABLE main.adp.adp_standards"

    rows = ",\n".join(
        "  ('{}', '{}', '{}', '{}', '{}')".format(
            sq(i), sq(title), sq(cat), sq(body), sq(src))
        for (i, cat, title, body, src) in STANDARDS
    )
    insert = (
        "INSERT INTO main.adp.adp_standards (id, title, category, body, source) VALUES\n"
        + rows
    )

    out = (f"-- Generated by data/seed_standards.py -- do not edit by hand.\n"
           f"{create}\n{DELIM}\n{truncate}\n{DELIM}\n{insert}\n")
    path = os.path.join(os.path.dirname(__file__), "adp_standards_seed.sql")
    with open(path, "w") as f:
        f.write(out)
    print(f"wrote {path} ({len(STANDARDS)} standards)")


if __name__ == "__main__":
    main()
