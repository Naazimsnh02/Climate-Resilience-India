"""BigQuery-backed allocation tool for the Allocation Agent. Reuses `district_risk_score`
and `district_features_latest` (see data-collection/modeling/build_risk_model.py) - the
same underlying model as the Triage Agent, so the two agents never disagree about which
districts are at risk, only about how to divide resources across them.

Allocation algorithm (deterministic, not LLM-decided, so it's auditable - see PLAN.md
section 5 on explainability):
  1. weight_i = risk_score_i * relief_discount_i
     relief_discount_i = 0.6 if the district already has a real supply-side relief signal
     we have data for (reservoir_pct_full > 40%, or groundwater_trend == 'rising'), else 1.0.
     This is what produces PLAN.md's "deprioritized despite high risk" trade-off narrative,
     grounded only in fields that actually exist in district_features_latest - no fabricated
     upstream-release data.
  2. Proportional allocation: raw_i = total_units * weight_i / sum(weights).
  3. Cap: no single district gets more than 30% of the pool (only enforced when the scope
     has more than one district), redistributing capped excess proportionally among the
     remaining uncapped districts until stable.
  4. Largest-remainder rounding to whole units so allocations sum exactly to total_units.
"""
from google.cloud import bigquery

from agents.common.bq_client import client
from agents.common.config import GCP_PROJECT, BQ_DATASET

T = f"{GCP_PROJECT}.{BQ_DATASET}"

RELIEF_RESERVOIR_PCT_FULL_THRESHOLD = 40.0
RELIEF_DISCOUNT = 0.6
CAP_FRACTION_OF_POOL = 0.30

LATEST_SCORE_CTE = f"""
WITH latest AS (
  SELECT *
  FROM `{T}.district_risk_score`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY district_id ORDER BY date DESC) = 1
)
"""


def _fetch_scope(scope_state: str | None, scope_belt: str | None, district_ids: list[str] | None) -> list[dict]:
    where_clauses = []
    params = []
    if district_ids:
        where_clauses.append("m.district_id IN UNNEST(@district_ids)")
        params.append(bigquery.ArrayQueryParameter("district_ids", "STRING", district_ids))
    if scope_state:
        where_clauses.append("LOWER(m.state) = LOWER(@scope_state)")
        params.append(bigquery.ScalarQueryParameter("scope_state", "STRING", scope_state))
    if scope_belt:
        where_clauses.append("LOWER(m.flagged_belt) = LOWER(@scope_belt)")
        params.append(bigquery.ScalarQueryParameter("scope_belt", "STRING", scope_belt))
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = f"""
        {LATEST_SCORE_CTE}
        SELECT
          m.district_id, m.name, m.state, m.flagged_belt,
          l.risk_score,
          f.reservoir_pct_full, f.groundwater_trend, f.drought_status
        FROM `{T}.district_master` m
        JOIN latest l ON l.district_id = m.district_id
        LEFT JOIN `{T}.district_features_latest` f ON f.district_id = m.district_id
        {where_sql}
        ORDER BY l.risk_score DESC
    """
    job = client().query(
        query,
        job_config=bigquery.QueryJobConfig(query_parameters=params) if params else None,
    )
    return [dict(row) for row in job.result()]


def _largest_remainder_round(raw_values: list[float], total_units: int) -> list[int]:
    floors = [int(v) for v in raw_values]
    remainder = total_units - sum(floors)
    remainders = sorted(range(len(raw_values)), key=lambda i: raw_values[i] - floors[i], reverse=True)
    for i in remainders[:remainder]:
        floors[i] += 1
    return floors


def _cap_and_redistribute(weights: list[float], cap_fraction: float) -> list[float]:
    """Redistributes any weight above cap_fraction of the total proportionally among
    uncapped entries, iterating until stable (or everyone is capped)."""
    n = len(weights)
    total = sum(weights)
    if total <= 0 or n <= 1:
        return weights[:]
    cap = cap_fraction * total
    capped = [False] * n
    shares = weights[:]
    for _ in range(n):
        changed = False
        uncapped_total = sum(shares[i] for i in range(n) if not capped[i])
        for i in range(n):
            if not capped[i] and shares[i] > cap:
                excess = shares[i] - cap
                shares[i] = cap
                capped[i] = True
                remaining_uncapped = [j for j in range(n) if not capped[j]]
                if remaining_uncapped:
                    denom = sum(weights[j] for j in remaining_uncapped)
                    for j in remaining_uncapped:
                        shares[j] += excess * (weights[j] / denom if denom > 0 else 1 / len(remaining_uncapped))
                changed = True
        if not changed:
            break
    return shares


def allocate_resources(
    total_units: int,
    resource_name: str,
    scope_state: str | None = None,
    scope_belt: str | None = None,
    district_ids: list[str] | None = None,
) -> dict:
    """Allocates a limited pool of a resource (e.g. water tankers, relief budget) across
    at-risk districts, proportional to risk but discounted for districts that already have
    a real supply-side relief signal, and capped so no single district takes the whole pool.

    Args:
        total_units: Total quantity of the resource available to allocate (e.g. 50 tankers).
        resource_name: What's being allocated, for labeling the response (e.g. "water tankers",
            "relief budget (INR crore)").
        scope_state: Optional Indian state name to restrict the allocation to (e.g. "Maharashtra").
        scope_belt: Optional flagged_belt name to restrict to (e.g. "Marathwada", "Rajasthan",
            "North Karnataka", "Eastern UP").
        district_ids: Optional explicit list of canonical district_ids to restrict to. If given,
            takes precedence alongside scope_state/scope_belt (all provided filters are ANDed).

    Returns:
        A dict with "resource_name", "total_units", "scope_description", and "allocations": a
        list ordered by allocated units descending, each with district_id, name, state,
        flagged_belt, risk_score, allocated_units, relief_discount_applied (bool + reason if
        true), and capped (bool). Districts with no risk score yet are excluded and listed
        under "excluded_no_score". Returns {"error": ...} if the scope matches zero districts.
    """
    rows = _fetch_scope(scope_state, scope_belt, district_ids)
    if not rows:
        return {"error": "No districts matched the given scope (scope_state/scope_belt/district_ids)."}

    scored = [r for r in rows if r.get("risk_score") is not None]
    excluded = [r["district_id"] for r in rows if r.get("risk_score") is None]
    if not scored:
        return {"error": "Matched districts exist but none have a risk score yet."}

    weights = []
    discount_reasons = []
    for r in scored:
        discount = 1.0
        reason = None
        pct_full = r.get("reservoir_pct_full")
        trend = (r.get("groundwater_trend") or "").lower()
        if (pct_full is not None and pct_full > RELIEF_RESERVOIR_PCT_FULL_THRESHOLD) or trend == "rising":
            discount = RELIEF_DISCOUNT
            if pct_full is not None and pct_full > RELIEF_RESERVOIR_PCT_FULL_THRESHOLD and trend == "rising":
                reason = f"reservoir at {pct_full}% full and groundwater trend rising"
            elif pct_full is not None and pct_full > RELIEF_RESERVOIR_PCT_FULL_THRESHOLD:
                reason = f"reservoir at {pct_full}% full, above the {RELIEF_RESERVOIR_PCT_FULL_THRESHOLD}% relief threshold"
            else:
                reason = "groundwater trend is rising"
        weights.append(r["risk_score"] * discount)
        discount_reasons.append(reason)

    total_weight = sum(weights)
    if total_weight <= 0:
        weights = [1.0] * len(scored)
        total_weight = float(len(scored))

    shares = _cap_and_redistribute(weights, CAP_FRACTION_OF_POOL)
    raw_units = [total_units * (s / sum(shares)) for s in shares]
    allocated = _largest_remainder_round(raw_units, total_units)

    cap_threshold_units = CAP_FRACTION_OF_POOL * total_units
    results = []
    for r, units, discount_reason in zip(scored, allocated, discount_reasons):
        results.append({
            "district_id": r["district_id"],
            "name": r["name"],
            "state": r["state"],
            "flagged_belt": r["flagged_belt"],
            "risk_score": r["risk_score"],
            "allocated_units": units,
            "relief_discount_applied": discount_reason is not None,
            "relief_discount_reason": discount_reason,
            "capped": len(scored) > 1 and units <= cap_threshold_units + 0.5 and units < raw_units[scored.index(r)] - 0.5,
        })
    results.sort(key=lambda x: x["allocated_units"], reverse=True)

    scope_bits = []
    if district_ids:
        scope_bits.append(f"{len(district_ids)} named districts")
    if scope_state:
        scope_bits.append(f"state={scope_state}")
    if scope_belt:
        scope_bits.append(f"belt={scope_belt}")
    scope_description = ", ".join(scope_bits) if scope_bits else "all seeded districts"

    return {
        "resource_name": resource_name,
        "total_units": total_units,
        "scope_description": scope_description,
        "allocations": results,
        "excluded_no_score": excluded,
    }
