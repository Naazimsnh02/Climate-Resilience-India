"""Builds `district_risk_score` via BigQuery ML.

Three steps, each a separate query job so failures are isolated:
  1. `district_features_latest` view - joins the latest snapshot per district across
     ndvi_soil_moisture (GEE, live), reservoir_status/groundwater_level/drought_status
     (Tier 2 seed), weather_current, against district_master.
  2. `district_risk_model` - a BQML linear regression trained to reproduce the NRSC-derived
     drought severity ordinal (`severity_score`, 1-4) from the live/seeded feature signals.
     n=23 districts is too small for a held-out test split to mean anything, so this is a
     calibrated composite index dressed as ML, not a validated predictive model - documented
     here so nobody mistakes it for more than a hackathon-scale baseline. Uses l2_reg to
     control overfitting given the small n.
  3. Populate `district_risk_score` (district_id, date, risk_score, days_to_critical_reservoir,
     rainfall_deficit_rank, model_version, explanation_json) using ML.EXPLAIN_PREDICT so every
     score carries its top feature attributions for the explainability panel (PLAN.md section 5).
     Re-running replaces today's row per district (DELETE + INSERT on CURRENT_DATE) without
     touching prior days, so this can be rerun as new snapshots land.

Run after gee_pull.py and load_tier2_seed.py so the feature view has fresh inputs.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.bq_loader import client
from common.config import GCP_PROJECT, BQ_DATASET

T = f"{GCP_PROJECT}.{BQ_DATASET}"

CREATE_FEATURE_VIEW = f"""
CREATE OR REPLACE VIEW `{T}.district_features_latest` AS
WITH ndvi AS (
  SELECT district_id, precip_mm_30d, precip_asof, ndvi, ndvi_asof,
         soil_moisture_pct, soil_moisture_asof
  FROM `{T}.ndvi_soil_moisture`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY district_id ORDER BY pulled_at DESC) = 1
),
res AS (
  SELECT district_id, pct_full AS reservoir_pct_full, pct_normal AS reservoir_pct_normal,
         asof_date AS reservoir_asof, granularity AS reservoir_granularity
  FROM `{T}.reservoir_status`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY district_id ORDER BY asof_date DESC) = 1
),
gw AS (
  SELECT district_id, trend AS groundwater_trend, level_m_bgl AS groundwater_level_m_bgl,
         asof_date AS groundwater_asof,
         CASE LOWER(trend)
           WHEN 'falling' THEN 1.0
           WHEN 'declining' THEN 1.0
           WHEN 'mixed' THEN 0.0
           WHEN 'stable' THEN 0.0
           WHEN 'rising' THEN -1.0
           ELSE 0.0
         END AS groundwater_stress_score
  FROM `{T}.groundwater_level`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY district_id ORDER BY asof_date DESC) = 1
),
wx AS (
  SELECT district_id, temp_c, feels_like_c, humidity_pct, timestamp AS weather_asof
  FROM `{T}.weather_current`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY district_id ORDER BY timestamp DESC) = 1
),
drought AS (
  SELECT district_id, status AS drought_status, asof_date AS drought_asof,
    CASE
      WHEN LOWER(status) LIKE '%moderate-high%' THEN 2.5
      WHEN LOWER(status) LIKE '%high-risk%' THEN 3.5
      WHEN LOWER(status) LIKE '%severe%' THEN 4.0
      WHEN LOWER(status) LIKE '%high%' THEN 3.0
      WHEN LOWER(status) LIKE '%elevated%' THEN 2.0
      WHEN LOWER(status) LIKE '%moderate%' THEN 1.0
      WHEN LOWER(status) LIKE '%mixed%' THEN 2.0
      ELSE 2.0
    END AS severity_score
  FROM `{T}.drought_status`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY district_id ORDER BY asof_date DESC) = 1
)
SELECT
  m.district_id, m.name, m.state, m.flagged_belt,
  ndvi.precip_mm_30d, ndvi.ndvi, ndvi.soil_moisture_pct,
  ndvi.precip_asof, ndvi.ndvi_asof, ndvi.soil_moisture_asof,
  res.reservoir_pct_full, res.reservoir_pct_normal, res.reservoir_asof, res.reservoir_granularity,
  gw.groundwater_trend, gw.groundwater_level_m_bgl, gw.groundwater_stress_score, gw.groundwater_asof,
  wx.temp_c, wx.feels_like_c, wx.humidity_pct, wx.weather_asof,
  drought.drought_status, drought.severity_score, drought.drought_asof
FROM `{T}.district_master` m
LEFT JOIN ndvi ON ndvi.district_id = m.district_id
LEFT JOIN res ON res.district_id = m.district_id
LEFT JOIN gw ON gw.district_id = m.district_id
LEFT JOIN wx ON wx.district_id = m.district_id
LEFT JOIN drought ON drought.district_id = m.district_id
"""

CREATE_MODEL = f"""
CREATE OR REPLACE MODEL `{T}.district_risk_model`
OPTIONS(
  model_type = 'LINEAR_REG',
  input_label_cols = ['severity_score'],
  l2_reg = 1.0,
  data_split_method = 'NO_SPLIT'
) AS
SELECT
  precip_mm_30d,
  ndvi,
  soil_moisture_pct,
  reservoir_pct_full,
  groundwater_stress_score,
  feels_like_c,
  severity_score
FROM `{T}.district_features_latest`
WHERE severity_score IS NOT NULL
"""

CREATE_SCORE_TABLE = f"""
CREATE TABLE IF NOT EXISTS `{T}.district_risk_score` (
  district_id STRING,
  date DATE,
  risk_score FLOAT64,
  days_to_critical_reservoir FLOAT64,
  rainfall_deficit_rank INT64,
  model_version STRING,
  explanation_json STRING
)
"""

MODEL_VERSION = "bqml_linear_reg_v1"

POPULATE_SCORE_TABLE = f"""
DELETE FROM `{T}.district_risk_score` WHERE date = CURRENT_DATE();

INSERT INTO `{T}.district_risk_score`
WITH preds AS (
  SELECT district_id, predicted_severity_score, top_feature_attributions
  FROM ML.EXPLAIN_PREDICT(
    MODEL `{T}.district_risk_model`,
    (SELECT * FROM `{T}.district_features_latest`),
    STRUCT(4 AS top_k_features)
  )
),
ranked AS (
  SELECT district_id, reservoir_pct_full,
         RANK() OVER (ORDER BY precip_mm_30d ASC) AS rainfall_deficit_rank
  FROM `{T}.district_features_latest`
)
SELECT
  p.district_id,
  CURRENT_DATE() AS date,
  -- severity_score is a 1-4 ordinal; rescale predicted value onto a 0-100 risk score
  ROUND(LEAST(GREATEST(p.predicted_severity_score, 0), 4) / 4 * 100, 1) AS risk_score,
  -- heuristic: assumes a flat 0.3pp/day summer drawdown from CWC bulletin patterns,
  -- critical threshold at 10% live storage. Documented assumption, not a fitted rate -
  -- no per-district time series exists yet to fit one.
  CASE WHEN r.reservoir_pct_full IS NULL THEN NULL
       ELSE GREATEST(r.reservoir_pct_full - 10, 0) / 0.3
  END AS days_to_critical_reservoir,
  r.rainfall_deficit_rank,
  '{MODEL_VERSION}' AS model_version,
  TO_JSON_STRING(p.top_feature_attributions) AS explanation_json
FROM preds p
JOIN ranked r USING (district_id)
"""


def main():
    bq = client()

    print("Creating district_features_latest view...")
    bq.query(CREATE_FEATURE_VIEW).result()

    print("Training district_risk_model (BQML linear_reg)...")
    bq.query(CREATE_MODEL).result()

    print("Ensuring district_risk_score table exists...")
    bq.query(CREATE_SCORE_TABLE).result()

    print("Scoring districts via ML.EXPLAIN_PREDICT and writing district_risk_score...")
    bq.query(POPULATE_SCORE_TABLE).result()

    rows = list(
        bq.query(
            f"SELECT district_id, risk_score, days_to_critical_reservoir, rainfall_deficit_rank "
            f"FROM `{T}.district_risk_score` WHERE date = CURRENT_DATE() ORDER BY risk_score DESC"
        ).result()
    )
    print(f"\nWrote {len(rows)} district_risk_score rows for today:")
    for r in rows:
        print(f"  {r.district_id:20s} risk={r.risk_score:5.1f}  "
              f"days_to_critical_reservoir={r.days_to_critical_reservoir}  "
              f"rainfall_deficit_rank={r.rainfall_deficit_rank}")


if __name__ == "__main__":
    main()
