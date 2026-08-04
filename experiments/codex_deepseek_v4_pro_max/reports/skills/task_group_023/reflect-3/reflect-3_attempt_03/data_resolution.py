"""
Data resolution and cohort construction helpers for PHO portal data.

Handles revision precedence, quality flag filtering, suppression,
and per-field socioeconomic resolution as described in the portal methodology.
"""

import csv
from typing import Optional


def load_csv(path: str) -> list[dict]:
    """Load a CSV file as a list of dicts."""
    with open(path) as f:
        return list(csv.DictReader(f))


def resolve_health(
    records: list[dict],
    measure_id: str,
    value_type: str,
    source_type: str,
    years: list[int],
    invalid_quality_flags: set = None,
) -> dict:
    """
    Resolve health records to highest-revision FINAL values.

    Returns dict mapping (state_or_county_key, year) -> float value.

    Args:
        records: Raw health CSV rows.
        measure_id: e.g. 'life_expectancy', 'adult_obesity'.
        value_type: 'AGE_ADJUSTED' or 'CRUDE'.
        source_type: 'DIRECT_SURVEY' or 'COUNTY_ROLLUP'.
        years: List of analysis years.
        invalid_quality_flags: Quality flags that invalidate a record
            (default: INVALID_SCALE, INVALID, WITHDRAWN).

    Key field: uses 'state_abbr' for state data, 'county_fips' for county data.
    """
    if invalid_quality_flags is None:
        invalid_quality_flags = {"INVALID_SCALE", "INVALID", "WITHDRAWN"}

    # Determine geography key
    has_state = 'state_abbr' in (records[0] if records else {})
    geo_key = 'state_abbr' if has_state else 'county_fips'

    candidates = {}
    for r in records:
        if r.get('release_status') != 'FINAL':
            continue
        if int(r.get('year', 0)) not in years:
            continue
        if r.get('measure_id') != measure_id:
            continue
        if r.get('value_type') != value_type:
            continue
        if r.get('source_type') != source_type:
            continue
        if r.get('quality_flag', '') in invalid_quality_flags:
            continue
        if r.get('suppression_flag') == '1':
            continue
        v = r.get('value', '')
        if v == '' or v is None:
            continue

        key = (r[geo_key], int(r['year']))
        rev = int(r.get('revision', 0))
        if key not in candidates or rev > candidates[key][1]:
            candidates[key] = (float(v), rev)

    return {k: v[0] for k, v in candidates.items()}


def resolve_socio_field(
    records: list[dict],
    field: str,
    years: list[int],
) -> dict:
    """
    Resolve a single socioeconomic field per (geography, year).

    Scans records in descending revision order and returns the first
    non-empty value for the requested field.  Respects the portal's
    independent-field revision policy.

    Returns dict mapping (state_or_county_key, year) -> float value.
    """
    has_state = 'state_abbr' in (records[0] if records else {})
    geo_key = 'state_abbr' if has_state else 'county_fips'

    candidates = {}
    for r in records:
        if r.get('release_status') != 'FINAL':
            continue
        if int(r.get('year', 0)) not in years:
            continue
        v = r.get(field, '')
        if v == '' or v is None:
            continue
        key = (r[geo_key], int(r['year']))
        rev = int(r.get('revision', 0))
        if key not in candidates or rev > candidates[key][1]:
            candidates[key] = (float(v), rev)

    return {k: v[0] for k, v in candidates.items()}


def build_balanced_cohort(
    state_or_county_list: list[str],
    years: list[int],
    required_sources: list[dict],
) -> list[str]:
    """
    Build a balanced panel: jurisdictions complete in every analysis year.

    Args:
        state_or_county_list: Candidate jurisdiction identifiers.
        years: Analysis years.
        required_sources: List of dicts mapping (jurisdiction, year) -> value.
            Each dict must have a non-None value for a jurisdiction to be
            considered complete.

    Returns:
        Sorted list of jurisdiction identifiers in the balanced cohort.
    """
    cohort = []
    for geo in state_or_county_list:
        complete = True
        for yr in years:
            for src in required_sources:
                if src.get((geo, yr)) is None:
                    complete = False
                    break
            if not complete:
                break
        if complete:
            cohort.append(geo)
    return sorted(cohort)


def cr1_cluster_se(
    X: "np.ndarray",
    y: "np.ndarray",
    beta: "np.ndarray",
    cluster_ids: list,
    unique_clusters: list,
) -> "np.ndarray":
    """
    Compute CR1 cluster-robust standard errors.

    V_cr1 = (G/(G-1)) * (X'X)^(-1) * [sum_g X_g' e_g e_g' X_g] * (X'X)^(-1)

    Args:
        X: Design matrix (N x K).
        y: Outcome vector (N).
        beta: Estimated coefficients (K).
        cluster_ids: Cluster identifier for each observation (N).
        unique_clusters: Unique cluster identifiers.

    Returns:
        Array of standard errors (K).
    """
    import numpy as np

    e = y - X @ beta
    G = len(unique_clusters)
    k = X.shape[1]
    V = np.zeros((k, k))

    for g_idx, g in enumerate(unique_clusters):
        mask = np.array([cid == g for cid in cluster_ids])
        if mask.sum() == 0:
            continue
        X_g = X[mask]
        e_g = e[mask]
        V += X_g.T @ np.outer(e_g, e_g) @ X_g

    V *= G / (G - 1)
    bread = np.linalg.inv(X.T @ X)
    V_robust = bread @ V @ bread
    return np.sqrt(np.maximum(np.diag(V_robust), 1e-12))
