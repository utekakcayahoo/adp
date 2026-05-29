# Locked Use Case — ADP Facility Energy & Carbon Co-pilot

> Single source of truth for **what** we build. The use case and data **do not
> change** for the life of the project. Patterns, agents, and deployment are
> layered on top of this.

## One-liner
An AI co-pilot that helps a sustainability team **understand, track, diagnose,
and act on** the energy use and carbon emissions of a portfolio of facilities —
and produce audit-ready reports.

## Why this use case
It exercises every pattern in the book with the simplest possible data:

| Need in the use case | Pattern it forces |
|---|---|
| Numbers must come from tools (never invented) | Tool Use, Guardrails, Reflection |
| "Produce the quarterly report" (multi-step) | Planning, Prompt Chaining |
| Different question types (lookup vs diagnose vs report) | Routing |
| Several facilities at once | Parallelization |
| Methodology / standards lookups | Knowledge Retrieval (RAG) |
| Reduction targets | Goal Setting & Monitoring |
| Approve an action/report before it's "final" | Human-in-the-Loop |
| Specialists: analyst / accountant / advisor / reporter | Multi-Agent + A2A |
| Remember the facility in focus | Memory Management |
| Missing / late data | Exception Handling & Recovery |
| Traces + scoring | Evaluation & Monitoring |

## Personas
| Persona | Cares about | Example ask |
|---|---|---|
| **Sustainability Manager** (primary) | Portfolio emissions, target progress, reporting | "Are we on track for our 2030 target?" |
| **Facility Manager** | One site's performance & actions | "Why did Warehouse-2 spike in March?" |
| **Executive / ESG reporting** | Summary + audit trail | "Generate the Q1 ESG summary." |

## Carbon accounting (the only domain knowledge you need)
- **Scope 1** = direct emissions from on-site fuel combustion → here, **natural gas**.
- **Scope 2** = indirect emissions from **purchased electricity**.
- `emissions = activity (kWh) × emission factor (kgCO₂e/kWh)`. Factors differ by
  fuel and by electricity grid region.
- We report in **tCO₂e** (tonnes of CO₂-equivalent).

## Scope (in / out)
**In:** Scope 1 (gas) + Scope 2 (electricity); hourly→monthly granularity; a
handful of facilities; reduction targets; simple anomaly explanation; an
ESG-style narrative report.

**Out (for now):** Scope 3, market- vs location-based nuance, real billing,
real-time equipment control, financial accounting.

## Synthetic data model (Databricks Unity Catalog, all `adp_`)
Catalog/schema finalized in the data phase; table names are fixed now:

1. **`adp_facilities`** — `facility_id, name, type{office|warehouse|datacenter}, city, grid_region, floor_area_sqm, opened_on`
2. **`adp_energy_readings`** — `reading_ts, facility_id, electricity_kwh, gas_kwh, source{meter|estimate}` *(hourly; batch + streaming generators)*
3. **`adp_emission_factors`** — `grid_region, fuel{electricity|gas}, kgco2e_per_kwh, valid_from, valid_to, source`
4. **`adp_targets`** — `scope{org|facility}, facility_id?, baseline_year, baseline_tco2e, target_year, target_reduction_pct`
5. **`adp_weather`** — `weather_ts, city, temp_c, heating_degree_hours, cooling_degree_hours` *(explains consumption swings)*

**Knowledge base for RAG (`adp_standards`):** short, plain-language docs — GHG
Protocol scope definitions, our emission-factor methodology, an ESG report
template, an anomaly-investigation playbook. Indexed in Databricks Vector Search
as **`adp_standards_index`**.

## Success criteria (how we know each step works)
- Every emissions number the agent states is traceable to a tool call — **no fabrication**.
- "On track?" answers cite the target and the current trajectory.
- A full report is generated from a single instruction, end-to-end.
- Every run produces an **MLflow trace** in the configured experiment.
