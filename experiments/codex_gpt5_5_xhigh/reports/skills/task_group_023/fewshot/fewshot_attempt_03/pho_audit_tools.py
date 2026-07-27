"""Reusable helpers for Public Health Observatory audit tasks.

This module intentionally contains method primitives only. Bind measures,
years, filters, thresholds, seeds, grids, output names, and decision labels from
the active task's analysis_request.json and answer_template.json.
"""

from __future__ import annotations

import csv
import io
import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from itertools import combinations, permutations
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np

try:
    from scipy import stats
except Exception:  # pragma: no cover - scipy is expected in task envs.
    stats = None


DATASETS = {
    "states": "states",
    "counties": "counties",
    "countries": "countries",
    "state_health": "state_health",
    "state_socioeconomic": "state_socioeconomic",
    "county_health": "county_health",
    "county_socioeconomic": "county_socioeconomic",
    "country_indicators": "country_indicators",
    "revisions": "revisions",
}

INVALID_QUALITY_FLAGS = {"INVALID_SCALE", "INVALID", "WITHDRAWN"}
COUNTRY_ANOMALY_FLAGS = {"SCALE_REVIEW", "INVALID_SCALE"}


def read_env_base_url(path: str = "/work/environment_access.md") -> str:
    """Read the allowed portal base URL from environment_access.md."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("GDPEVO_ENV_BASE_URL="):
                return line.split("=", 1)[1].strip().rstrip("/") + "/"
    raise ValueError(f"GDPEVO_ENV_BASE_URL not found in {path}")


def fetch_csv_dataset(
    dataset: str,
    base_url: str | None = None,
    params: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Fetch a portal dataset through /download as CSV."""
    if dataset not in DATASETS:
        raise ValueError(f"unknown dataset {dataset!r}")
    base = base_url or read_env_base_url()
    query = {"dataset": DATASETS[dataset], "format": "csv"}
    if params:
        query.update({k: v for k, v in params.items() if v is not None})
    url = urllib.parse.urljoin(base, "download") + "?" + urllib.parse.urlencode(query)
    with urllib.request.urlopen(url) as resp:
        text = resp.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def fetch_all_portal_tables(base_url: str | None = None) -> dict[str, list[dict[str, str]]]:
    """Fetch every PHO table exposed by the catalog."""
    base = base_url or read_env_base_url()
    return {name: fetch_csv_dataset(name, base) for name in DATASETS}


def coerce_number(value: Any) -> float | None:
    """Convert portal cells to float, preserving missing strings as None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = str(value).strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def is_unavailable_value(
    row: Mapping[str, Any],
    value_col: str = "value",
    invalid_flags: set[str] | None = None,
) -> bool:
    """Return True for suppressed, invalid, blank, or null analytic values."""
    flags = invalid_flags or INVALID_QUALITY_FLAGS
    qflag = str(row.get("quality_flag") or "").strip().upper()
    suppressed = str(row.get("suppression_flag") or "0").strip() in {"1", "true", "TRUE"}
    return suppressed or qflag in flags or coerce_number(row.get(value_col)) is None


def is_country_anomaly(row: Mapping[str, Any]) -> bool:
    """Return True for unresolved country scale-review/anomaly cells."""
    return str(row.get("quality_flag") or "").strip().upper() in COUNTRY_ANOMALY_FLAGS


def filter_rows(rows: Iterable[Mapping[str, Any]], **filters: Any) -> list[dict[str, Any]]:
    """Filter dictionaries by exact string-equivalent field matches."""
    out: list[dict[str, Any]] = []
    for row in rows:
        keep = True
        for key, expected in filters.items():
            if expected is None:
                continue
            if isinstance(expected, (set, list, tuple)):
                allowed = {str(x) for x in expected}
                keep = str(row.get(key)) in allowed
            else:
                keep = str(row.get(key)) == str(expected)
            if not keep:
                break
        if keep:
            out.append(dict(row))
    return out


def select_publication_records(
    rows: Iterable[Mapping[str, Any]],
    key_cols: Sequence[str],
    filters: Mapping[str, Any] | None = None,
    id_col: str | None = None,
    id_order: str = "asc",
    revision_col: str = "revision",
    released_at_col: str = "released_at",
) -> list[dict[str, Any]]:
    """Resolve one publication row per key.

    The common PHO rule is highest revision, then latest released_at. The final
    identifier tie-break differs by protocol, so pass id_order="asc" or "desc"
    from the active request/profile.
    """
    selected: dict[tuple[Any, ...], dict[str, Any]] = {}
    candidates = filter_rows(rows, **(filters or {}))
    if id_order not in {"asc", "desc"}:
        raise ValueError("id_order must be 'asc' or 'desc'")

    def score(row: Mapping[str, Any]) -> tuple[Any, ...]:
        rev = int(coerce_number(row.get(revision_col)) or 0)
        released = str(row.get(released_at_col) or "")
        ident = str(row.get(id_col) or "") if id_col else ""
        if id_order == "asc":
            ident_score = tuple(-ord(c) for c in ident)
        else:
            ident_score = tuple(ord(c) for c in ident)
        return (rev, released, ident_score)

    for row in candidates:
        key = tuple(row.get(col) for col in key_cols)
        old = selected.get(key)
        if old is None or score(row) > score(old):
            selected[key] = dict(row)
    return list(selected.values())


def complete_case_mask(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> np.ndarray:
    """True where all requested columns have nonmissing numeric values."""
    mask = []
    for row in rows:
        mask.append(all(coerce_number(row.get(col)) is not None for col in columns))
    return np.array(mask, dtype=bool)


def resolve_country_labels(
    countries: Iterable[Mapping[str, Any]],
    requested_labels: Sequence[str],
) -> list[dict[str, Any]]:
    """Resolve labels against canonical, portal, and pipe-separated alternates."""
    lookup: dict[str, dict[str, Any]] = {}
    for row in countries:
        labels = [row.get("canonical_name"), row.get("portal_label")]
        labels.extend(str(row.get("alternate_labels") or "").split("|"))
        for label in labels:
            if label:
                lookup[str(label)] = dict(row)
    resolved = []
    for label in requested_labels:
        if label not in lookup:
            raise KeyError(f"unresolved country label {label!r}")
        item = dict(lookup[label])
        item["_requested_label"] = label
        resolved.append(item)
    return resolved


def median_impute_columns(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Replace NaNs by column medians computed from nonmissing entries."""
    arr = np.asarray(x, dtype=float).copy()
    fills = np.nanmedian(arr, axis=0)
    rows, cols = np.where(np.isnan(arr))
    for r, c in zip(rows, cols):
        arr[r, c] = fills[c]
    return arr, fills


def round_json(value: Any, digits: int) -> Any:
    """Recursively round noninteger floats for JSON output."""
    if isinstance(value, dict):
        return {k: round_json(v, digits) for k, v in value.items()}
    if isinstance(value, list):
        return [round_json(v, digits) for v in value]
    if isinstance(value, tuple):
        return [round_json(v, digits) for v in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        if abs(value - round(value)) < 1e-12:
            return int(round(value))
        return round(value, digits)
    if isinstance(value, np.floating):
        return round_json(float(value), digits)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.ndarray):
        return round_json(value.tolist(), digits)
    return value


def dump_answer(obj: Mapping[str, Any], digits: int = 4) -> str:
    """Serialize an answer object after applying PHO rounding/null rules."""
    return json.dumps(round_json(dict(obj), digits), separators=(",", ":"), ensure_ascii=True)


def matrix_rank_safe_inverse(a: np.ndarray, rcond: float = 1e-12) -> np.ndarray:
    """Moore-Penrose inverse with explicit relative singular cutoff."""
    u, s, vt = np.linalg.svd(np.asarray(a, dtype=float), full_matrices=False)
    if s.size == 0:
        return vt.T @ u.T
    cutoff = rcond * s[0]
    inv_s = np.array([1.0 / x if x > cutoff else 0.0 for x in s])
    return (vt.T * inv_s) @ u.T


def add_intercept(x: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(np.asarray(x).shape[0]), np.asarray(x, dtype=float)])


def ols_fit(x: np.ndarray, y: np.ndarray, add_const: bool = False) -> dict[str, np.ndarray | float]:
    x = add_intercept(x) if add_const else np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    xtx_inv = matrix_rank_safe_inverse(x.T @ x)
    beta = xtx_inv @ x.T @ y
    resid = y - x @ beta
    n, k = x.shape
    return {"beta": beta, "resid": resid, "fitted": x @ beta, "xtx_inv": xtx_inv, "n": n, "k": k}


def wls_fit(
    x: np.ndarray,
    y: np.ndarray,
    weights: np.ndarray,
    add_const: bool = False,
) -> dict[str, np.ndarray | float]:
    x = add_intercept(x) if add_const else np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    w = np.asarray(weights, dtype=float)
    sw = np.sqrt(w)
    xw = x * sw[:, None]
    yw = y * sw
    xtx_inv = matrix_rank_safe_inverse(xw.T @ xw)
    beta = xtx_inv @ xw.T @ yw
    resid = y - x @ beta
    weighted_resid = yw - xw @ beta
    n, k = x.shape
    return {
        "beta": beta,
        "resid": resid,
        "weighted_resid": weighted_resid,
        "fitted": x @ beta,
        "x": x,
        "xw": xw,
        "weights": w,
        "xtx_inv": xtx_inv,
        "n": n,
        "k": k,
    }


def hc3_cov_from_fit(fit: Mapping[str, Any]) -> np.ndarray:
    """HC3 covariance for an OLS/WLS fit using weighted design residuals."""
    xw = np.asarray(fit.get("xw", fit.get("x")), dtype=float)
    xtx_inv = np.asarray(fit["xtx_inv"], dtype=float)
    ew = np.asarray(fit.get("weighted_resid", fit["resid"]), dtype=float)
    h = np.sum((xw @ xtx_inv) * xw, axis=1)
    scale = (ew / np.maximum(1.0 - h, 1e-15)) ** 2
    meat = xw.T @ (xw * scale[:, None])
    return xtx_inv @ meat @ xtx_inv


def cluster_cr1_cov_from_fit(fit: Mapping[str, Any], clusters: Sequence[Any]) -> np.ndarray:
    """CR1 cluster sandwich covariance for OLS/WLS fits."""
    xw = np.asarray(fit.get("xw", fit.get("x")), dtype=float)
    ew = np.asarray(fit.get("weighted_resid", fit["resid"]), dtype=float)
    xtx_inv = np.asarray(fit["xtx_inv"], dtype=float)
    n = int(fit["n"])
    k = int(fit["k"])
    groups = list(dict.fromkeys(clusters))
    meat = np.zeros((k, k), dtype=float)
    clusters_arr = np.asarray(clusters)
    for group in groups:
        idx = clusters_arr == group
        score = xw[idx].T @ ew[idx]
        meat += np.outer(score, score)
    g = len(groups)
    factor = (g / (g - 1)) * ((n - 1) / (n - k)) if g > 1 and n > k else 1.0
    return factor * xtx_inv @ meat @ xtx_inv


def t_p_value(t_stat: float, df: int | float) -> float:
    """Two-sided Student-t p-value; falls back to normal if scipy is absent."""
    if stats is not None:
        return float(2.0 * stats.t.sf(abs(t_stat), df))
    return float(math.erfc(abs(t_stat) / math.sqrt(2.0)))


def coefficient_summary(beta: float, se: float, df: int | float, level: float = 0.95) -> dict[str, Any]:
    t_stat = beta / se if se != 0 else math.copysign(math.inf, beta)
    alpha = 1.0 - level
    crit = float(stats.t.ppf(1 - alpha / 2, df)) if stats is not None else 1.959963984540054
    return {
        "coefficient": beta,
        "standard_error": se,
        "t_statistic": t_stat,
        "p_value": t_p_value(t_stat, df),
        "confidence_interval": [beta - crit * se, beta + crit * se],
    }


def two_way_demean(values: Sequence[float], entity: Sequence[Any], time: Sequence[Any]) -> np.ndarray:
    """Apply z_it - entity_mean - time_mean + grand_mean."""
    z = np.asarray(values, dtype=float)
    ent = np.asarray(entity)
    tim = np.asarray(time)
    out = z.copy()
    grand = float(np.mean(z))
    for e in np.unique(ent):
        out[ent == e] -= np.mean(z[ent == e])
    for t in np.unique(tim):
        out[tim == t] -= np.mean(z[tim == t])
    out += grand
    return out


def fit_two_way_fe(
    y: Sequence[float],
    x: np.ndarray,
    entity: Sequence[Any],
    time: Sequence[Any],
) -> dict[str, Any]:
    y_dm = two_way_demean(y, entity, time)
    x_dm = np.column_stack([two_way_demean(x[:, j], entity, time) for j in range(x.shape[1])])
    fit = ols_fit(x_dm, y_dm, add_const=False)
    fit["x"] = x_dm
    return fit


def jackknife(
    full_estimate: float,
    delete_estimates: Sequence[float],
    df: int | None = None,
    test_estimate: str = "full",
) -> dict[str, float]:
    """Delete-cluster jackknife mean, SE, bias correction, t, and p."""
    vals = np.asarray(delete_estimates, dtype=float)
    g = vals.size
    mean_delete = float(np.mean(vals))
    se = math.sqrt(((g - 1) / g) * float(np.sum((vals - mean_delete) ** 2)))
    bias_corrected = g * full_estimate - (g - 1) * mean_delete
    numerator = bias_corrected if test_estimate == "bias_corrected" else full_estimate
    t_stat = numerator / se if se != 0 else math.copysign(math.inf, numerator)
    return {
        "delete_mean": mean_delete,
        "standard_error": se,
        "bias_corrected": bias_corrected,
        "t_statistic": t_stat,
        "p_value": t_p_value(t_stat, df if df is not None else g - 1),
    }


def rmse(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    return float(math.sqrt(np.mean((y - p) ** 2)))


def mae(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y - p)))


def r_squared_oof(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    sse = float(np.sum((y - p) ** 2))
    sst = float(np.sum((y - np.mean(y)) ** 2))
    return 1.0 - sse / sst if sst > 0 else 0.0


def standardize_train(
    x_train: np.ndarray,
    x_apply: np.ndarray | None = None,
    ddof: int = 0,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray, np.ndarray]:
    """Standardize from training moments; zero-variance columns use divisor 1."""
    x_train = np.asarray(x_train, dtype=float)
    mu = np.mean(x_train, axis=0)
    sigma = np.std(x_train, axis=0, ddof=ddof)
    sigma = np.where(sigma == 0, 1.0, sigma)
    z_train = (x_train - mu) / sigma
    z_apply = None if x_apply is None else (np.asarray(x_apply, dtype=float) - mu) / sigma
    return z_train, z_apply, mu, sigma


def weighted_standardize_train(
    x_train: np.ndarray,
    weights: Sequence[float],
    x_apply: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray, np.ndarray]:
    x_train = np.asarray(x_train, dtype=float)
    w = np.asarray(weights, dtype=float)
    mu = np.average(x_train, axis=0, weights=w)
    var = np.average((x_train - mu) ** 2, axis=0, weights=w)
    sigma = np.sqrt(var)
    sigma = np.where(sigma == 0, 1.0, sigma)
    z_train = (x_train - mu) / sigma
    z_apply = None if x_apply is None else (np.asarray(x_apply, dtype=float) - mu) / sigma
    return z_train, z_apply, mu, sigma


@dataclass
class RidgeModel:
    intercept: float
    coef: np.ndarray
    x_mean: np.ndarray
    x_scale: np.ndarray
    y_mean: float


def fit_ridge(
    x: np.ndarray,
    y: Sequence[float],
    lam: float,
    ddof: int = 0,
    penalty_scale: str = "n",
) -> RidgeModel:
    """Fit ridge with training-only standardization and unpenalized intercept."""
    y_arr = np.asarray(y, dtype=float)
    z, _, mu, sigma = standardize_train(x, ddof=ddof)
    y_mean = float(np.mean(y_arr))
    yc = y_arr - y_mean
    p = z.shape[1]
    scale = len(y_arr) if penalty_scale == "n" else 1.0
    coef = np.linalg.solve(z.T @ z + lam * scale * np.eye(p), z.T @ yc)
    return RidgeModel(y_mean, coef, mu, sigma, y_mean)


def predict_ridge(model: RidgeModel, x: np.ndarray) -> np.ndarray:
    z = (np.asarray(x, dtype=float) - model.x_mean) / model.x_scale
    return model.intercept + z @ model.coef


@dataclass
class ElasticNetModel:
    intercept: float
    coef: np.ndarray
    x_mean: np.ndarray
    x_scale: np.ndarray
    cycles: int


def soft_threshold(value: float, threshold: float) -> float:
    if value > threshold:
        return value - threshold
    if value < -threshold:
        return value + threshold
    return 0.0


def fit_elastic_net_cd(
    x: np.ndarray,
    y: Sequence[float],
    penalty: float,
    l1_ratio: float,
    weights: Sequence[float] | None = None,
    standardize: str = "population",
    indicators: Sequence[int] | None = None,
    max_cycles: int = 10000,
    tol: float = 1e-10,
    update_intercept: bool = True,
) -> ElasticNetModel:
    """Cold-start cyclic coordinate descent for PHO elastic-net modules.

    `standardize` is "population", "weighted", or "none". Indicator columns can
    be supplied to leave them unstandardized for county panel tasks.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    n, p = x_arr.shape
    w = np.ones(n, dtype=float) if weights is None else np.asarray(weights, dtype=float)
    indicators_set = set(indicators or [])

    if standardize == "weighted":
        z, _, mu, sigma = weighted_standardize_train(x_arr, w)
    elif standardize == "population":
        z, _, mu, sigma = standardize_train(x_arr, ddof=0)
    elif standardize == "none":
        z, mu, sigma = x_arr.copy(), np.zeros(p), np.ones(p)
    else:
        raise ValueError("standardize must be population, weighted, or none")
    for j in indicators_set:
        z[:, j] = x_arr[:, j]
        mu[j] = 0.0
        sigma[j] = 1.0

    w_sum = float(np.sum(w))
    intercept = float(np.sum(w * y_arr) / w_sum)
    beta = np.zeros(p, dtype=float)
    for cycle in range(1, max_cycles + 1):
        old_intercept = intercept
        old_beta = beta.copy()
        if update_intercept:
            intercept = float(np.sum(w * (y_arr - z @ beta)) / w_sum)
        for j in range(p):
            partial = y_arr - intercept - z @ beta + z[:, j] * beta[j]
            rho = float(np.sum(w * z[:, j] * partial) / w_sum)
            denom = float(np.sum(w * z[:, j] ** 2) / w_sum + penalty * (1.0 - l1_ratio))
            beta[j] = soft_threshold(rho, penalty * l1_ratio) / denom if denom != 0 else 0.0
        max_delta = max(float(np.max(np.abs(beta - old_beta))), abs(intercept - old_intercept))
        if max_delta < tol:
            return ElasticNetModel(intercept, beta, mu, sigma, cycle)
    return ElasticNetModel(intercept, beta, mu, sigma, max_cycles)


def predict_elastic_net(model: ElasticNetModel, x: np.ndarray) -> np.ndarray:
    z = (np.asarray(x, dtype=float) - model.x_mean) / model.x_scale
    return model.intercept + z @ model.coef


def group_order(values: Sequence[Any]) -> list[Any]:
    """Stable first-seen group order."""
    return list(dict.fromkeys(values))


def leave_one_group_indices(groups: Sequence[Any], ordered_groups: Sequence[Any] | None = None):
    arr = np.asarray(groups)
    order = list(ordered_groups) if ordered_groups is not None else group_order(groups)
    for group in order:
        test = arr == group
        yield group, ~test, test


def allocate_balanced_group_folds(
    group_counts: Mapping[Any, int],
    fold_count: int,
) -> list[list[Any]]:
    """Greedy descending-count group allocation for state-blocked folds."""
    folds: list[list[Any]] = [[] for _ in range(fold_count)]
    loads = [0] * fold_count
    for group, count in sorted(group_counts.items(), key=lambda kv: (-kv[1], str(kv[0]))):
        target = min(range(fold_count), key=lambda i: (loads[i], i))
        folds[target].append(group)
        loads[target] += int(count)
    return [sorted(fold, key=str) for fold in folds]


class XorShift32:
    """Unsigned xorshift32 with PHO's 13,17,5 shifts."""

    def __init__(self, seed: int):
        self.state = seed & 0xFFFFFFFF

    def next_u32(self) -> int:
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x &= 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x &= 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        x &= 0xFFFFFFFF
        self.state = x
        return x

    def sign(self) -> int:
        return 1 if (self.next_u32() & 1) else -1


class PCG32:
    """PCG32 stream used by PHO Webb wild bootstrap modules."""

    MULT = 6364136223846793005

    def __init__(self, seed: int, stream: int):
        self.state = 0
        self.inc = ((stream << 1) | 1) & 0xFFFFFFFFFFFFFFFF
        self.next_u32()
        self.state = (self.state + seed) & 0xFFFFFFFFFFFFFFFF
        self.next_u32()

    @staticmethod
    def rotr32(value: int, rot: int) -> int:
        rot &= 31
        return ((value >> rot) | (value << ((-rot) & 31))) & 0xFFFFFFFF

    def next_u32(self) -> int:
        old = self.state
        self.state = (old * self.MULT + self.inc) & 0xFFFFFFFFFFFFFFFF
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = old >> 59
        return self.rotr32(xorshifted, rot)

    def webb_weight(self) -> float:
        weights = [-math.sqrt(1.5), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(1.5)]
        return weights[self.next_u32() % 6]


def nearest_rank(values: Sequence[float], probability: float) -> float:
    arr = np.sort(np.asarray(values, dtype=float))
    if arr.size == 0:
        return math.nan
    idx = min(arr.size, math.ceil(probability * arr.size)) - 1
    return float(arr[idx])


def quantile_type7(values: Sequence[float], probability: float) -> float:
    arr = np.sort(np.asarray(values, dtype=float))
    if arr.size == 0:
        return math.nan
    h = (arr.size - 1) * probability
    j = int(math.floor(h))
    gamma = h - j
    if j + 1 >= arr.size:
        return float(arr[j])
    return float((1.0 - gamma) * arr[j] + gamma * arr[j + 1])


def conformal_radius(
    scores: Sequence[float],
    *,
    coverage: float | None = None,
    alpha: float | None = None,
) -> tuple[float, int]:
    """Finite-sample split-conformal radius and one-based rank."""
    if coverage is None:
        if alpha is None:
            raise ValueError("provide coverage or alpha")
        coverage = 1.0 - alpha
    arr = np.sort(np.asarray(scores, dtype=float))
    if arr.size == 0:
        return math.nan, 0
    rank = min(arr.size, math.ceil((arr.size + 1) * coverage))
    return float(arr[rank - 1]), rank


def pca_covariance(
    x: np.ndarray,
    *,
    ddof: int = 1,
    population_standardize: bool = False,
    orient: bool = True,
) -> dict[str, np.ndarray]:
    """Standardize columns, eigendecompose covariance, and orient loadings."""
    x_arr = np.asarray(x, dtype=float)
    z, _, mu, sigma = standardize_train(x_arr, ddof=0 if population_standardize else 1)
    cov = z.T @ z / (z.shape[0] - ddof)
    vals, vecs = np.linalg.eigh(cov)
    order = np.argsort(-vals)
    vals = vals[order]
    vecs = vecs[:, order]
    if orient:
        for j in range(vecs.shape[1]):
            idx = int(np.argmax(np.abs(vecs[:, j])))
            if vecs[idx, j] < 0:
                vecs[:, j] *= -1
    scores = z @ vecs
    ratios = vals / np.sum(vals) if np.sum(vals) else np.zeros_like(vals)
    return {
        "z": z,
        "mean": mu,
        "scale": sigma,
        "eigenvalues": vals,
        "loadings": vecs,
        "scores": scores,
        "explained_ratios": ratios,
    }


def deterministic_kmeans(
    points: np.ndarray,
    labels: Sequence[Any],
    k: int,
    max_iter: int = 1000,
    canonicalize: bool = True,
) -> dict[str, Any]:
    """Farthest-first deterministic Lloyd k-means."""
    pts = np.asarray(points, dtype=float)
    ids = list(labels)
    if len(ids) != pts.shape[0]:
        raise ValueError("labels length must equal point count")
    first = min(range(len(ids)), key=lambda i: str(ids[i]))
    centers_idx = [first]
    while len(centers_idx) < k:
        best = None
        for i in range(pts.shape[0]):
            nearest = min(float(np.sum((pts[i] - pts[j]) ** 2)) for j in centers_idx)
            key = (nearest, tuple(-ord(c) for c in str(ids[i])))
            if best is None or key > best[0]:
                best = (key, i)
        centers_idx.append(best[1])
    centers = pts[centers_idx].copy()
    assign = np.full(pts.shape[0], -1, dtype=int)
    for iteration in range(1, max_iter + 1):
        d = ((pts[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_assign = np.argmin(d, axis=1)
        if np.array_equal(assign, new_assign):
            break
        assign = new_assign
        for j in range(k):
            mask = assign == j
            if np.any(mask):
                centers[j] = pts[mask].mean(axis=0)
    if canonicalize:
        order = sorted(range(k), key=lambda j: tuple(centers[j].tolist()) + (j,))
        remap = {old: new for new, old in enumerate(order)}
        centers = centers[order]
        assign = np.array([remap[int(a)] for a in assign], dtype=int)
    return {"centers": centers, "assignments": assign, "iterations": iteration, "initial_indices": centers_idx}


def adjusted_rand_index(labels_a: Sequence[Any], labels_b: Sequence[Any]) -> float:
    a = np.asarray(labels_a)
    b = np.asarray(labels_b)
    if a.size != b.size:
        raise ValueError("label arrays must have equal length")
    n = a.size
    if n < 2:
        return 1.0
    a_vals = list(dict.fromkeys(a.tolist()))
    b_vals = list(dict.fromkeys(b.tolist()))
    table = np.zeros((len(a_vals), len(b_vals)), dtype=int)
    for i, av in enumerate(a_vals):
        for j, bv in enumerate(b_vals):
            table[i, j] = int(np.sum((a == av) & (b == bv)))

    def comb2(x: np.ndarray | int) -> np.ndarray | float:
        return x * (x - 1) / 2

    sum_ij = float(np.sum(comb2(table)))
    sum_a = float(np.sum(comb2(table.sum(axis=1))))
    sum_b = float(np.sum(comb2(table.sum(axis=0))))
    total = float(comb2(n))
    expected = sum_a * sum_b / total if total else 0.0
    denom = 0.5 * (sum_a + sum_b) - expected
    return (sum_ij - expected) / denom if denom else 0.0


def best_label_alignment(reference: Sequence[int], candidate: Sequence[int]) -> tuple[list[int], int]:
    """Return lexicographically tied best permutation and number changed."""
    ref = list(reference)
    cand = list(candidate)
    classes = sorted(set(ref) | set(cand))
    best_perm = None
    best_matches = -1
    best_mapped: list[int] | None = None
    for perm in permutations(classes):
        mapping = dict(zip(classes, perm))
        mapped = [mapping[x] for x in cand]
        matches = sum(1 for a, b in zip(ref, mapped) if a == b)
        key = tuple(mapped)
        if matches > best_matches or (matches == best_matches and (best_mapped is None or key < tuple(best_mapped))):
            best_matches = matches
            best_perm = list(perm)
            best_mapped = mapped
    return best_perm or [], len(ref) - best_matches


def silhouette_score(points: np.ndarray, assignments: Sequence[int]) -> float:
    pts = np.asarray(points, dtype=float)
    labs = np.asarray(assignments)
    scores = []
    for i in range(pts.shape[0]):
        same = labs == labs[i]
        if np.sum(same) <= 1:
            scores.append(0.0)
            continue
        a = float(np.mean(np.linalg.norm(pts[i] - pts[same & (np.arange(pts.shape[0]) != i)], axis=1)))
        b = math.inf
        for lab in set(labs.tolist()):
            if lab == labs[i]:
                continue
            other = labs == lab
            b = min(b, float(np.mean(np.linalg.norm(pts[i] - pts[other], axis=1))))
        scores.append((b - a) / max(a, b) if math.isfinite(b) and max(a, b) > 0 else 0.0)
    return float(np.mean(scores))


def residualize_against(x: np.ndarray, controls: np.ndarray) -> np.ndarray:
    """Residualize each column of x against controls."""
    x_arr = np.asarray(x, dtype=float)
    c = np.asarray(controls, dtype=float)
    c_inv = matrix_rank_safe_inverse(c.T @ c)
    hat = c @ c_inv @ c.T
    return x_arr - hat @ x_arr


def two_step_linear_gmm(
    y: Sequence[float],
    d: np.ndarray,
    z: np.ndarray,
    clusters: Sequence[Any] | None = None,
    rcond: float = 1e-12,
) -> dict[str, Any]:
    """Two-step linear GMM for y = D theta + u with moment Z'u = 0."""
    y_arr = np.asarray(y, dtype=float)
    d_arr = np.asarray(d, dtype=float)
    z_arr = np.asarray(z, dtype=float)
    n = y_arr.size
    theta1 = matrix_rank_safe_inverse(d_arr.T @ z_arr @ z_arr.T @ d_arr, rcond) @ d_arr.T @ z_arr @ z_arr.T @ y_arr
    u1 = y_arr - d_arr @ theta1
    if clusters is None:
        s = (z_arr * u1[:, None]).T @ (z_arr * u1[:, None]) / n
    else:
        s = np.zeros((z_arr.shape[1], z_arr.shape[1]), dtype=float)
        carr = np.asarray(clusters)
        for g in group_order(clusters):
            idx = carr == g
            score = z_arr[idx].T @ u1[idx]
            s += np.outer(score, score) / n
    w = matrix_rank_safe_inverse(s, rcond)
    theta2 = matrix_rank_safe_inverse(d_arr.T @ z_arr @ w @ z_arr.T @ d_arr, rcond) @ d_arr.T @ z_arr @ w @ z_arr.T @ y_arr
    u2 = y_arr - d_arr @ theta2
    gbar = z_arr.T @ u2 / n
    hansen_j = float(n * gbar.T @ w @ gbar)
    return {"theta": theta2, "resid": u2, "weight": w, "hansen_j": hansen_j}


def enumerate_year_subsets(years: Sequence[int], subset_sizes: Sequence[int]) -> list[tuple[int, ...]]:
    out: list[tuple[int, ...]] = []
    for size in subset_sizes:
        out.extend(tuple(c) for c in combinations(years, size))
    return out


def shapley_effects_from_mask_values(values: Mapping[int, float], item_count: int) -> list[float]:
    """Exact signed Shapley effects from mask -> coefficient/value mapping."""
    facts = [math.factorial(i) for i in range(item_count + 1)]
    denom = facts[item_count]
    effects = []
    for j in range(item_count):
        phi = 0.0
        for mask, value in values.items():
            if mask & (1 << j):
                continue
            size = int(mask.bit_count())
            weight = facts[size] * facts[item_count - size - 1] / denom
            phi += weight * (values[mask | (1 << j)] - value)
        effects.append(phi)
    return effects


def evaluate_gates(gates: Sequence[tuple[str, bool]]) -> dict[str, Any]:
    """Count gates and identify the first failed gate in declared order."""
    passed = [bool(v) for _, v in gates]
    first_failed = next((name for name, ok in gates if not ok), "NONE")
    return {"passed_count": sum(passed), "first_failed": first_failed}
