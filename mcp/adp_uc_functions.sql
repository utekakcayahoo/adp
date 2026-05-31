-- ADP MCP tools as Unity Catalog functions.
-- Auto-exposed at: /api/2.0/mcp/functions/main/adp
-- Each function RETURNS STRING (compact JSON) -- the documented, reliable shape for
-- agent tools. Function + parameter COMMENTs become the MCP tool/arg descriptions.
-- (The deploy runner splits this file on a fixed delimiter line between statements.)
--
-- Note: a UC function body is a scalar subquery; because it references the function
-- parameter it is "correlated", so Spark requires the body to be an AGGREGATING
-- query (guaranteed <= 1 row). That's why each body aggregates (sum/collect_list/max).

CREATE OR REPLACE FUNCTION main.adp.list_facilities()
RETURNS STRING
COMMENT 'List every facility in the portfolio with its type, city, electricity grid region, and floor area. Returns a JSON array. Call this first to discover valid facility ids (e.g. FAC-001) before using the other tools.'
RETURN (
  SELECT to_json(sort_array(collect_list(struct(
    facility_id, name, type, city, grid_region, floor_area_sqm))))
  FROM main.adp.adp_facilities
)
-- @@STATEMENT@@
CREATE OR REPLACE FUNCTION main.adp.query_energy(
  facility STRING COMMENT 'Facility id, e.g. FAC-001. Use list_facilities to find valid ids.',
  start_date DATE COMMENT 'Inclusive start date, YYYY-MM-DD.',
  end_date DATE COMMENT 'Inclusive end date, YYYY-MM-DD.')
RETURNS STRING
COMMENT 'Monthly electricity (kWh) and natural gas (kWh) consumption for one facility between two dates. Returns a JSON array of {month, electricity_kwh, gas_kwh} sorted by month. Raw energy only; does NOT compute emissions -- use compute_emissions for CO2e.'
RETURN (
  SELECT to_json(sort_array(collect_list(struct(month, electricity_kwh, gas_kwh))))
  FROM (
    SELECT CAST(date_trunc('MONTH', reading_ts) AS DATE) AS month,
           round(sum(electricity_kwh), 1) AS electricity_kwh,
           round(sum(gas_kwh), 1) AS gas_kwh
    FROM main.adp.adp_energy_readings
    WHERE facility_id = facility
      AND reading_ts >= start_date
      AND reading_ts < end_date + INTERVAL 1 DAY
    GROUP BY 1
  )
)
-- @@STATEMENT@@
CREATE OR REPLACE FUNCTION main.adp.compute_emissions(
  facility STRING COMMENT 'Facility id, e.g. FAC-001.',
  start_date DATE COMMENT 'Inclusive start date, YYYY-MM-DD.',
  end_date DATE COMMENT 'Inclusive end date, YYYY-MM-DD.')
RETURNS STRING
COMMENT 'Compute carbon emissions (tonnes CO2e) for one facility between two dates by multiplying measured kWh by the published grid/fuel emission factors. Returns JSON: scope1_tco2e (on-site gas), scope2_tco2e (purchased electricity), total_tco2e, plus the underlying electricity_kwh and gas_kwh. Always use this for emissions -- never estimate CO2e yourself.'
RETURN (
  SELECT to_json(struct(
    round(coalesce(sum(r.gas_kwh * fg.kgco2e_per_kwh), 0) / 1000.0, 3) AS scope1_tco2e,
    round(coalesce(sum(r.electricity_kwh * fe.kgco2e_per_kwh), 0) / 1000.0, 3) AS scope2_tco2e,
    round(coalesce(sum(r.gas_kwh * fg.kgco2e_per_kwh + r.electricity_kwh * fe.kgco2e_per_kwh), 0) / 1000.0, 3) AS total_tco2e,
    round(coalesce(sum(r.electricity_kwh), 0), 1) AS electricity_kwh,
    round(coalesce(sum(r.gas_kwh), 0), 1) AS gas_kwh))
  FROM main.adp.adp_energy_readings r
  JOIN main.adp.adp_facilities f ON f.facility_id = r.facility_id
  JOIN main.adp.adp_emission_factors fe ON fe.grid_region = f.grid_region AND fe.fuel = 'electricity'
  JOIN main.adp.adp_emission_factors fg ON fg.grid_region = f.grid_region AND fg.fuel = 'gas'
  WHERE r.facility_id = facility
    AND r.reading_ts >= start_date AND r.reading_ts < end_date + INTERVAL 1 DAY
)
-- @@STATEMENT@@
CREATE OR REPLACE FUNCTION main.adp.target_progress(
  facility STRING COMMENT 'Facility id, e.g. FAC-001.')
RETURNS STRING
COMMENT 'Assess a facility''s progress toward its emissions-reduction target. Compares trailing-12-month emissions against the baseline-year emissions and the linear path to the target year. Returns JSON: baseline_year, baseline_tco2e, target_year, target_reduction_pct, current_12mo_tco2e, pct_reduction_so_far, required_reduction_by_now_pct, on_track (boolean). On_track is true when reduction so far meets the linear path.'
RETURN (
  WITH bounds AS (
    SELECT max(reading_ts) AS now_ts
    FROM main.adp.adp_energy_readings WHERE facility_id = facility
  )
  SELECT to_json(struct(
    max(tg.baseline_year) AS baseline_year,
    max(tg.baseline_tco2e) AS baseline_tco2e,
    max(tg.target_year) AS target_year,
    max(tg.target_reduction_pct) AS target_reduction_pct,
    round(sum(r.gas_kwh * fg.kgco2e_per_kwh + r.electricity_kwh * fe.kgco2e_per_kwh) / 1000.0, 3) AS current_12mo_tco2e,
    round((max(tg.baseline_tco2e) - sum(r.gas_kwh * fg.kgco2e_per_kwh + r.electricity_kwh * fe.kgco2e_per_kwh) / 1000.0) / max(tg.baseline_tco2e) * 100, 1) AS pct_reduction_so_far,
    round(max(tg.target_reduction_pct) * (year(max(b.now_ts)) - max(tg.baseline_year)) / (max(tg.target_year) - max(tg.baseline_year)), 1) AS required_reduction_by_now_pct,
    ((max(tg.baseline_tco2e) - sum(r.gas_kwh * fg.kgco2e_per_kwh + r.electricity_kwh * fe.kgco2e_per_kwh) / 1000.0) / max(tg.baseline_tco2e) * 100)
      >= (max(tg.target_reduction_pct) * (year(max(b.now_ts)) - max(tg.baseline_year)) / (max(tg.target_year) - max(tg.baseline_year))) AS on_track))
  FROM main.adp.adp_energy_readings r
  JOIN main.adp.adp_facilities f ON f.facility_id = r.facility_id
  JOIN main.adp.adp_emission_factors fe ON fe.grid_region = f.grid_region AND fe.fuel = 'electricity'
  JOIN main.adp.adp_emission_factors fg ON fg.grid_region = f.grid_region AND fg.fuel = 'gas'
  JOIN main.adp.adp_targets tg ON tg.scope = 'facility' AND tg.facility_id = r.facility_id
  CROSS JOIN bounds b
  WHERE r.facility_id = facility
    AND r.reading_ts > b.now_ts - INTERVAL 365 DAY
)
-- @@STATEMENT@@
CREATE OR REPLACE FUNCTION main.adp.query_weather(
  facility STRING COMMENT 'Facility id, e.g. FAC-001. Weather is resolved to this facility''s city. Use list_facilities to find valid ids.',
  start_date DATE COMMENT 'Inclusive start date, YYYY-MM-DD.',
  end_date DATE COMMENT 'Inclusive end date, YYYY-MM-DD.')
RETURNS STRING
COMMENT 'Monthly weather for one facility''s city between two dates: average temperature (C), total heating degree-hours, and total cooling degree-hours. Returns a JSON array of {month, avg_temp_c, heating_degree_hours, cooling_degree_hours} sorted by month. Use this to weather-normalize an energy spike: if electricity jumps but cooling/heating degree-hours are flat versus the same months a year earlier, the spike is NOT explained by weather (likely an equipment fault).'
RETURN (
  SELECT to_json(sort_array(collect_list(struct(month, avg_temp_c, heating_degree_hours, cooling_degree_hours))))
  FROM (
    SELECT CAST(date_trunc('MONTH', w.weather_ts) AS DATE) AS month,
           round(avg(w.temp_c), 1) AS avg_temp_c,
           round(sum(w.heating_degree_hours), 1) AS heating_degree_hours,
           round(sum(w.cooling_degree_hours), 1) AS cooling_degree_hours
    FROM main.adp.adp_weather w
    JOIN main.adp.adp_facilities f ON f.city = w.city
    WHERE f.facility_id = facility
      AND w.weather_ts >= start_date
      AND w.weather_ts < end_date + INTERVAL 1 DAY
    GROUP BY 1
  )
)
