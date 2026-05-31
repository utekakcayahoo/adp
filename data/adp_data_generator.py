# Databricks notebook source
# MAGIC %md
# MAGIC # ADP — Synthetic Data Generator
# MAGIC **Facility Energy & Carbon Co-pilot.** Builds the 5 source tables in `{catalog}.{schema}`.
# MAGIC
# MAGIC - `mode = seed`   → create all tables + full hourly history (run once)
# MAGIC - `mode = append` → append the newest hours since the last reading (scheduled "streaming-ish" feed)
# MAGIC
# MAGIC **Design note:** we never store CO₂ here. Emissions are *computed downstream*
# MAGIC (`kWh × emission factor`) by the MCP tool in Phase 2 — so the agent can only
# MAGIC state emissions it derived from raw activity data + a published factor.

# COMMAND ----------
# MAGIC %md ### Parameters

# COMMAND ----------
dbutils.widgets.dropdown("mode", "seed", ["seed", "append"])
dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "adp")
dbutils.widgets.text("history_start", "2024-01-01")

MODE = dbutils.widgets.get("mode")
CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
EPOCH_STR = dbutils.widgets.get("history_start")
FQ = f"{CATALOG}.{SCHEMA}"
print(f"mode={MODE}  target={FQ}  history_start={EPOCH_STR}")

# COMMAND ----------
import math, random, datetime as dt
from pyspark.sql import functions as F, types as T

random.seed(42)  # reproducible runs
EPOCH = dt.datetime.strptime(EPOCH_STR, "%Y-%m-%d")  # project "day zero" — anchors trends & anomalies

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {FQ}")
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Reference data
# MAGIC Facilities, the grid regions they sit in, and illustrative emission factors
# MAGIC (tagged `source = 'illustrative'` — plausible, not certified).

# COMMAND ----------
# facility_id, name, type, city, grid_region, floor_area_sqm, opened_on
FACILITIES = [
    ("FAC-001", "HQ Office North",   "office",     "Seattle", "US-NW", 12000, "2016-03-01"),
    ("FAC-002", "Downtown Office",    "office",     "Chicago", "US-MW",  8000, "2018-07-15"),
    ("FAC-003", "Riverside Office",   "office",     "Austin",  "US-TX",  6000, "2020-01-10"),
    ("FAC-004", "Central Warehouse",  "warehouse",  "Chicago", "US-MW", 30000, "2015-05-20"),
    ("FAC-005", "West Warehouse",     "warehouse",  "Austin",  "US-TX", 25000, "2019-09-01"),
    ("FAC-006", "Edge Data Center",   "datacenter", "Seattle", "US-NW",  4000, "2017-11-01"),
]

# Illustrative grid electricity factors (kgCO2e/kWh): NW hydro-light, MW coal-heavier.
ELEC_FACTORS = {"US-NW": 0.20, "US-MW": 0.45, "US-TX": 0.38}
GAS_FACTOR = 0.18  # kgCO2e per kWh of natural gas burned on site

CITIES = sorted({f[3] for f in FACILITIES})
FAC_GRID = {f[0]: f[4] for f in FACILITIES}

# COMMAND ----------
# MAGIC %md
# MAGIC ### The model
# MAGIC Hourly usage = base load (type × size) × daily/weekly shape × weather effect
# MAGIC × efficiency trend × anomalies + noise. Gas serves heating; electricity serves
# MAGIC everything + cooling.

# COMMAND ----------
TYPE_PROFILE = {  # base kW per 1000 sqm
    "office":     {"elec":  8.0, "gas": 6.0},
    "warehouse":  {"elec":  4.0, "gas": 8.0},
    "datacenter": {"elec": 60.0, "gas": 1.0},  # power-dense, runs flat 24/7
}

def hourly_temp(city, ts):
    """Seasonal (yearly) + daily cycle + noise, per city."""
    base = {"Seattle": 11, "Chicago": 10, "Austin": 21}.get(city, 14)
    amp  = {"Seattle":  7, "Chicago": 13, "Austin": 10}.get(city, 10)
    doy = ts.timetuple().tm_yday
    seasonal = amp * math.sin(2 * math.pi * (doy - 110) / 365)  # warmest ~ midsummer
    daily = 5 * math.sin(2 * math.pi * (ts.hour - 9) / 24)      # warmest ~ mid-afternoon
    return base + seasonal + daily + random.gauss(0, 1.5)

def degree_hours(temp):
    return max(0.0, 18.0 - temp), max(0.0, temp - 22.0)  # (heating, cooling)

def daily_shape(ftype, hour, is_weekend):
    if ftype == "datacenter":
        return 1.0
    if ftype == "office":
        base = 1.0 if 8 <= hour <= 18 else 0.30
        if is_weekend:
            base *= 0.40
    else:  # warehouse
        base = 1.0 if 7 <= hour <= 19 else 0.35
        if is_weekend:
            base *= 0.70
    return base

def efficiency_factor(ts):
    """Mild ~3%/yr efficiency gains, so 'now' trends below baseline (makes 'on track?' meaningful)."""
    years = (ts - EPOCH).days / 365.0
    return max(0.85, 1.0 - 0.03 * years)

def anomaly_mult(fac_id, ts):
    """Deliberate faults for the Diagnose capability to find later. Electricity only."""
    m = 1.0
    if fac_id == "FAC-004":  # Central Warehouse: stuck HVAC, spring of year 2
        if dt.date(EPOCH.year + 1, 3, 5) <= ts.date() <= dt.date(EPOCH.year + 1, 4, 20):
            m *= 1.8
    if fac_id == "FAC-006":  # Edge Data Center: slow load creep that outruns efficiency
        m *= 1.0 + 0.06 * ((ts - EPOCH).days / 365.0)
    return m

def gen_reading(fac, ts, temp):
    fac_id, _, ftype, _, _, area, _ = fac
    units = area / 1000.0
    hdh, cdh = degree_hours(temp)
    shape = daily_shape(ftype, ts.hour, ts.weekday() >= 5)
    eff = efficiency_factor(ts)
    prof = TYPE_PROFILE[ftype]

    elec = prof["elec"] * units * shape          # base electricity
    elec += 0.15 * units * cdh                    # cooling load
    elec *= eff * anomaly_mult(fac_id, ts) * random.gauss(1.0, 0.08)

    gas = prof["gas"] * units * shape * 0.30       # base (process / hot water)
    gas += 0.50 * units * hdh                       # heating load
    gas *= eff * random.gauss(1.0, 0.08)

    return max(0.0, round(elec, 3)), max(0.0, round(gas, 3))

# COMMAND ----------
# MAGIC %md ### Generation

# COMMAND ----------
def hour_range(start, end):
    cur = start
    while cur < end:
        yield cur
        cur += dt.timedelta(hours=1)

def generate(gen_start, end):
    """Returns (weather_rows, reading_rows) for the half-open window [gen_start, end)."""
    temp_by = {}
    weather_rows = []
    for ts in hour_range(gen_start, end):
        for city in CITIES:
            t = hourly_temp(city, ts)
            hdh, cdh = degree_hours(t)
            temp_by[(city, ts)] = t
            weather_rows.append((ts, city, round(t, 2), round(hdh, 2), round(cdh, 2)))
    reading_rows = []
    for ts in hour_range(gen_start, end):
        for fac in FACILITIES:
            elec, gas = gen_reading(fac, ts, temp_by[(fac[3], ts)])
            reading_rows.append((ts, fac[0], elec, gas, "meter"))
    return weather_rows, reading_rows

# COMMAND ----------
# MAGIC %md ### Schemas

# COMMAND ----------
WEATHER_SCHEMA = T.StructType([
    T.StructField("weather_ts", T.TimestampType()),
    T.StructField("city", T.StringType()),
    T.StructField("temp_c", T.DoubleType()),
    T.StructField("heating_degree_hours", T.DoubleType()),
    T.StructField("cooling_degree_hours", T.DoubleType()),
])
READINGS_SCHEMA = T.StructType([
    T.StructField("reading_ts", T.TimestampType()),
    T.StructField("facility_id", T.StringType()),
    T.StructField("electricity_kwh", T.DoubleType()),
    T.StructField("gas_kwh", T.DoubleType()),
    T.StructField("source", T.StringType()),
])

# COMMAND ----------
# MAGIC %md ### Run — weather + readings

# COMMAND ----------
now = dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)

if MODE == "seed":
    gen_start = EPOCH
elif MODE == "append":
    last = spark.sql(f"SELECT max(reading_ts) AS m FROM {FQ}.adp_energy_readings").collect()[0]["m"]
    gen_start = (last + dt.timedelta(hours=1)) if last else EPOCH
else:
    raise ValueError(f"unknown mode {MODE}")

reading_rows = []
if gen_start >= now:
    print(f"Nothing to generate: gen_start={gen_start} >= now={now}")
else:
    print(f"Generating [{gen_start} .. {now}) ...")
    weather_rows, reading_rows = generate(gen_start, now)
    write_mode = "overwrite" if MODE == "seed" else "append"

    (spark.createDataFrame(weather_rows, WEATHER_SCHEMA)
        .write.mode(write_mode).option("overwriteSchema", "true")
        .saveAsTable(f"{FQ}.adp_weather"))
    (spark.createDataFrame(reading_rows, READINGS_SCHEMA)
        .write.mode(write_mode).option("overwriteSchema", "true")
        .saveAsTable(f"{FQ}.adp_energy_readings"))
    print(f"weather rows={len(weather_rows):,}  reading rows={len(reading_rows):,}")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Dimensions + factors + targets (seed only)
# MAGIC Targets are grounded in real data: each baseline = that facility's actual
# MAGIC emissions in calendar year `EPOCH.year`.

# COMMAND ----------
if MODE == "seed":
    # facilities
    fac_rows = [(f[0], f[1], f[2], f[3], f[4], f[5], dt.datetime.strptime(f[6], "%Y-%m-%d").date())
                for f in FACILITIES]
    fac_schema = T.StructType([
        T.StructField("facility_id", T.StringType()), T.StructField("name", T.StringType()),
        T.StructField("type", T.StringType()), T.StructField("city", T.StringType()),
        T.StructField("grid_region", T.StringType()), T.StructField("floor_area_sqm", T.IntegerType()),
        T.StructField("opened_on", T.DateType()),
    ])
    (spark.createDataFrame(fac_rows, fac_schema)
        .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.adp_facilities"))

    # emission factors
    far = dt.date(2099, 12, 31)
    factor_rows = [(g, "electricity", v, dt.date(2024, 1, 1), far, "illustrative") for g, v in ELEC_FACTORS.items()]
    factor_rows += [(g, "gas", GAS_FACTOR, dt.date(2024, 1, 1), far, "illustrative") for g in ELEC_FACTORS]
    factor_schema = T.StructType([
        T.StructField("grid_region", T.StringType()), T.StructField("fuel", T.StringType()),
        T.StructField("kgco2e_per_kwh", T.DoubleType()), T.StructField("valid_from", T.DateType()),
        T.StructField("valid_to", T.DateType()), T.StructField("source", T.StringType()),
    ])
    (spark.createDataFrame(factor_rows, factor_schema)
        .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.adp_emission_factors"))

    # targets grounded in baseline-year emissions
    from collections import defaultdict
    base_kg = defaultdict(float)
    for (ts, fac_id, elec, gas, _src) in reading_rows:
        if ts.year == EPOCH.year:
            base_kg[fac_id] += elec * ELEC_FACTORS[FAC_GRID[fac_id]] + gas * GAS_FACTOR
    target_rows = []
    for f in FACILITIES:
        target_rows.append(("facility", f[0], EPOCH.year, round(base_kg[f[0]] / 1000.0, 3),
                            2030, round(random.uniform(40, 55), 1)))
    target_rows.append(("org", None, EPOCH.year, round(sum(base_kg.values()) / 1000.0, 3), 2030, 50.0))
    target_schema = T.StructType([
        T.StructField("scope", T.StringType()), T.StructField("facility_id", T.StringType()),
        T.StructField("baseline_year", T.IntegerType()), T.StructField("baseline_tco2e", T.DoubleType()),
        T.StructField("target_year", T.IntegerType()), T.StructField("target_reduction_pct", T.DoubleType()),
    ])
    (spark.createDataFrame(target_rows, target_schema)
        .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{FQ}.adp_targets"))
    print("Wrote facilities, emission_factors, targets.")

# COMMAND ----------
# MAGIC %md ### Summary

# COMMAND ----------
for t in ["adp_facilities", "adp_emission_factors", "adp_targets", "adp_weather", "adp_energy_readings"]:
    try:
        n = spark.table(f"{FQ}.{t}").count()
        print(f"{t:24s} {n:>10,} rows")
    except Exception as e:
        print(f"{t:24s} (not present) {e}")
