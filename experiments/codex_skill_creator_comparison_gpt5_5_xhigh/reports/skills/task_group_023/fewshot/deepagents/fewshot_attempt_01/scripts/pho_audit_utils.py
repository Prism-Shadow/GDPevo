#!/usr/bin/env python3
"""Reusable helpers for Public Health Observatory audit tasks.

The module is intentionally pure standard-library Python so it can run in the
task workspace without extra packages. It supplies deterministic primitives, not
a complete task solver. Bind all schemas, fields, orders, and thresholds from
the active analysis_request.json and answer_template.json.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence


PORTAL_ENDPOINTS = [
    "/catalog",
    "/geographies/states",
    "/geographies/counties",
    "/geographies/countries",
    "/data/state-health",
    "/data/state-socioeconomic",
    "/data/county-health",
    "/data/county-socioeconomic",
    "/data/country-indicators",
    "/data/revisions",
    "/methodology",
]


def fetch_json(base_url: str, endpoint: str, timeout: int = 30) -> Any:
    """Fetch one JSON endpoint from the Observatory portal."""
    url = base_url.rstrip("/") + "/" + endpoint.lstrip("/")
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_portal(base_url: str, endpoints: Sequence[str] = PORTAL_ENDPOINTS) -> dict[str, Any]:
    """Fetch allowed Observatory endpoints into a dictionary keyed by endpoint."""
    return {endpoint: fetch_json(base_url, endpoint) for endpoint in endpoints}


def write_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def rows_from_payload(payload: Any) -> list[dict[str, Any]]:
    """Return the most likely list of row dictionaries from an endpoint payload."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("rows", "data", "records", "items", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    raise TypeError("Could not find row list in payload")


def unavailable(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        return stripped == "" or stripped.upper() in {"NA", "N/A", "NULL", "NAN", "SUPPRESSED"}
    return isinstance(value, float) and math.isnan(value)


def analytic_value(row: dict[str, Any], fields: Sequence[str] = ("value", "estimate", "rate")) -> float | None:
    for field in fields:
        if field in row and not unavailable(row[field]):
            return float(row[field])
    return None


def quality_ok(row: dict[str, Any], invalid_flags: set[str] | None = None) -> bool:
    invalid = invalid_flags or {"INVALID", "INVALID_SCALE", "WITHDRAWN"}
    for key in ("quality_flag", "quality", "status_flag", "validity_flag"):
        value = row.get(key)
        if isinstance(value, str) and value.upper() in invalid:
            return False
    for key in ("suppressed", "is_suppressed"):
        if row.get(key) is True:
            return False
    return True


def filter_rows(rows: Iterable[dict[str, Any]], filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Filter rows by exact field values. Iterable filter values are treated as membership sets."""
    out = []
    for row in rows:
        keep = True
        for key, expected in filters.items():
            actual = row.get(key)
            if isinstance(expected, (list, tuple, set)):
                if actual not in expected:
                    keep = False
                    break
            elif actual != expected:
                keep = False
                break
        if keep:
            out.append(row)
    return out


def _record_id_value(value: Any, prefer: str) -> Any:
    if value is None:
        return "" if prefer == "lowest" else -math.inf
    if isinstance(value, (int, float)):
        return value if prefer == "greatest" else -value
    text = str(value)
    return text if prefer == "greatest" else "".join(chr(255 - ord(ch)) for ch in text)


def select_latest(
    rows: Iterable[dict[str, Any]],
    key_fields: Sequence[str],
    revision_field: str = "revision",
    released_field: str = "released_at",
    id_field: str = "observation_id",
    id_preference: str = "lowest",
) -> dict[tuple[Any, ...], dict[str, Any]]:
    """Select one row per key by revision, release timestamp, and record id priority."""
    selected: dict[tuple[Any, ...], dict[str, Any]] = {}

    def priority(row: dict[str, Any]) -> tuple[Any, Any, Any]:
        revision = row.get(revision_field)
        if revision is None:
            revision = row.get("revision_number", 0)
        released = row.get(released_field, "")
        rid = row.get(id_field)
        if rid is None:
            rid = row.get("record_id", row.get("id"))
        return (revision, released, _record_id_value(rid, id_preference))

    for row in rows:
        key = tuple(row.get(field) for field in key_fields)
        if key not in selected or priority(row) > priority(selected[key]):
            selected[key] = row
    return selected


def transpose(a: Sequence[Sequence[float]]) -> list[list[float]]:
    return [list(col) for col in zip(*a)]


def matmul(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> list[list[float]]:
    bt = transpose(b)
    return [[sum(x * y for x, y in zip(row, col)) for col in bt] for row in a]


def matvec(a: Sequence[Sequence[float]], x: Sequence[float]) -> list[float]:
    return [sum(v * xv for v, xv in zip(row, x)) for row in a]


def eye(n: int) -> list[list[float]]:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def inverse(a: Sequence[Sequence[float]], ridge: float = 0.0) -> list[list[float]]:
    n = len(a)
    aug = []
    for i, row in enumerate(a):
        left = [float(v) for v in row]
        if ridge:
            left[i] += ridge
        aug.append(left + eye(n)[i])
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-14:
            raise ValueError("singular matrix")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        div = aug[col][col]
        aug[col] = [v / div for v in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            if factor:
                aug[row] = [v - factor * p for v, p in zip(aug[row], aug[col])]
    return [row[n:] for row in aug]


def solve(a: Sequence[Sequence[float]], b: Sequence[float], ridge: float = 0.0) -> list[float]:
    return matvec(inverse(a, ridge=ridge), b)


@dataclass
class LinearFit:
    beta: list[float]
    fitted: list[float]
    residuals: list[float]
    xtx_inv: list[list[float]]
    x_weighted: list[list[float]]
    weighted_residuals: list[float]
    n: int
    k: int


def wls_fit(x: Sequence[Sequence[float]], y: Sequence[float], weights: Sequence[float] | None = None) -> LinearFit:
    n = len(x)
    k = len(x[0]) if x else 0
    if weights is None:
        weights = [1.0] * n
    xw = []
    yw = []
    for row, yi, wi in zip(x, y, weights):
        root = math.sqrt(float(wi))
        xw.append([root * float(v) for v in row])
        yw.append(root * float(yi))
    xt = transpose(xw)
    xtx = matmul(xt, xw)
    xty = matvec(xt, yw)
    xtx_inv = inverse(xtx)
    beta = matvec(xtx_inv, xty)
    fitted = matvec(x, beta)
    residuals = [float(yi) - fi for yi, fi in zip(y, fitted)]
    weighted_residuals = [math.sqrt(float(wi)) * ri for wi, ri in zip(weights, residuals)]
    return LinearFit(beta, fitted, residuals, xtx_inv, xw, weighted_residuals, n, k)


def ols_fit(x: Sequence[Sequence[float]], y: Sequence[float]) -> LinearFit:
    return wls_fit(x, y, None)


def hc3_cov(fit: LinearFit) -> list[list[float]]:
    meat = [[0.0 for _ in range(fit.k)] for _ in range(fit.k)]
    for row, ew in zip(fit.x_weighted, fit.weighted_residuals):
        h = sum(row[j] * sum(fit.xtx_inv[j][l] * row[l] for l in range(fit.k)) for j in range(fit.k))
        scale = (ew / max(1e-12, 1.0 - h)) ** 2
        for j in range(fit.k):
            for l in range(fit.k):
                meat[j][l] += row[j] * row[l] * scale
    return matmul(matmul(fit.xtx_inv, meat), fit.xtx_inv)


def cr1_cov(fit: LinearFit, clusters: Sequence[Any]) -> list[list[float]]:
    grouped: dict[Any, list[int]] = {}
    for idx, cluster in enumerate(clusters):
        grouped.setdefault(cluster, []).append(idx)
    g = len(grouped)
    factor = (g / (g - 1)) * ((fit.n - 1) / (fit.n - fit.k)) if g > 1 and fit.n > fit.k else 1.0
    meat = [[0.0 for _ in range(fit.k)] for _ in range(fit.k)]
    for indices in grouped.values():
        score = [0.0] * fit.k
        for i in indices:
            for j in range(fit.k):
                score[j] += fit.x_weighted[i][j] * fit.weighted_residuals[i]
        for j in range(fit.k):
            for l in range(fit.k):
                meat[j][l] += score[j] * score[l]
    cov = matmul(matmul(fit.xtx_inv, meat), fit.xtx_inv)
    return [[factor * v for v in row] for row in cov]


def se_from_cov(cov: Sequence[Sequence[float]]) -> list[float]:
    return [math.sqrt(max(0.0, cov[i][i])) for i in range(len(cov))]


def _betacf(a: float, b: float, x: float) -> float:
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-300:
        d = 1e-300
    d = 1.0 / d
    h = d
    for m in range(1, 201):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-300:
            d = 1e-300
        c = 1.0 + aa / c
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-14:
            break
    return h


def regularized_beta(x: float, a: float, b: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def student_t_cdf(t: float, df: float) -> float:
    if df <= 0:
        raise ValueError("df must be positive")
    x = df / (df + t * t)
    ib = regularized_beta(x, df / 2.0, 0.5)
    return 1.0 - 0.5 * ib if t >= 0 else 0.5 * ib


def student_t_two_sided_p(t: float, df: float) -> float:
    return 2.0 * (1.0 - student_t_cdf(abs(t), df))


def rmse(errors: Sequence[float]) -> float:
    return math.sqrt(sum(e * e for e in errors) / len(errors))


def mae(errors: Sequence[float]) -> float:
    return sum(abs(e) for e in errors) / len(errors)


def r_squared(y: Sequence[float], pred: Sequence[float]) -> float:
    mean_y = sum(y) / len(y)
    sse = sum((yi - pi) ** 2 for yi, pi in zip(y, pred))
    sst = sum((yi - mean_y) ** 2 for yi in y)
    return 1.0 - sse / sst if sst else 0.0


def standardize_train_apply(
    train: Sequence[Sequence[float]],
    other: Sequence[Sequence[float]],
    ddof: int = 0,
    weights: Sequence[float] | None = None,
) -> tuple[list[list[float]], list[list[float]], list[float], list[float]]:
    p = len(train[0])
    weighted = weights is not None
    if weights is None:
        weights = [1.0] * len(train)
    wsum = sum(weights)
    means = [sum(w * row[j] for w, row in zip(weights, train)) / wsum for j in range(p)]
    sigmas = []
    for j in range(p):
        var_num = sum(w * (row[j] - means[j]) ** 2 for w, row in zip(weights, train))
        denom = wsum if weighted else (len(train) - ddof)
        sigma = math.sqrt(var_num / denom) if denom > 0 else 0.0
        sigmas.append(sigma if sigma > 0 else 1.0)

    def transform(rows: Sequence[Sequence[float]]) -> list[list[float]]:
        return [[(row[j] - means[j]) / sigmas[j] for j in range(p)] for row in rows]

    return transform(train), transform(other), means, sigmas


def ridge_cd(x: Sequence[Sequence[float]], y: Sequence[float], lam: float, tol: float = 1e-10, max_cycles: int = 10000) -> tuple[float, list[float], int]:
    n = len(y)
    p = len(x[0])
    y_mean = sum(y) / n
    yc = [v - y_mean for v in y]
    beta = [0.0] * p
    for cycle in range(1, max_cycles + 1):
        max_change = 0.0
        for j in range(p):
            numerator = 0.0
            denom = n * lam
            for i in range(n):
                partial = yc[i] - sum(x[i][l] * beta[l] for l in range(p) if l != j)
                numerator += x[i][j] * partial
                denom += x[i][j] ** 2
            new_b = numerator / denom if denom else 0.0
            max_change = max(max_change, abs(new_b - beta[j]))
            beta[j] = new_b
        if max_change < tol:
            return y_mean, beta, cycle
    return y_mean, beta, max_cycles


def soft_threshold(value: float, threshold: float) -> float:
    if value > threshold:
        return value - threshold
    if value < -threshold:
        return value + threshold
    return 0.0


def elastic_net_cd(
    x: Sequence[Sequence[float]],
    y: Sequence[float],
    alpha: float,
    l1_ratio: float,
    weights: Sequence[float] | None = None,
    tol: float = 1e-10,
    max_cycles: int = 10000,
) -> tuple[float, list[float], int]:
    n = len(y)
    p = len(x[0])
    if weights is None:
        weights = [1.0] * n
    wsum = sum(weights)
    intercept = sum(w * yi for w, yi in zip(weights, y)) / wsum
    beta = [0.0] * p
    for cycle in range(1, max_cycles + 1):
        old_intercept = intercept
        pred_no_intercept = [sum(row[j] * beta[j] for j in range(p)) for row in x]
        intercept = sum(w * (yi - pi) for w, yi, pi in zip(weights, y, pred_no_intercept)) / wsum
        max_change = abs(intercept - old_intercept)
        for j in range(p):
            rho = 0.0
            x2 = 0.0
            for i in range(n):
                partial = y[i] - intercept - sum(x[i][l] * beta[l] for l in range(p) if l != j)
                rho += weights[i] * x[i][j] * partial
                x2 += weights[i] * x[i][j] ** 2
            rho /= wsum
            denom = x2 / wsum + alpha * (1.0 - l1_ratio)
            new_b = soft_threshold(rho, alpha * l1_ratio) / (denom if denom else 1.0)
            max_change = max(max_change, abs(new_b - beta[j]))
            beta[j] = new_b
        if max_change < tol:
            return intercept, beta, cycle
    return intercept, beta, max_cycles


def xorshift32_next(state: int) -> int:
    state &= 0xFFFFFFFF
    state ^= (state << 13) & 0xFFFFFFFF
    state ^= (state >> 17) & 0xFFFFFFFF
    state ^= (state << 5) & 0xFFFFFFFF
    return state & 0xFFFFFFFF


def xorshift32_sign(state: int) -> tuple[int, int]:
    state = xorshift32_next(state)
    return state, (1 if state & 1 else -1)


class PCG32:
    def __init__(self, seed: int, stream: int):
        self.state = 0
        self.inc = ((int(stream) << 1) | 1) & 0xFFFFFFFFFFFFFFFF
        self.next()
        self.state = (self.state + int(seed)) & 0xFFFFFFFFFFFFFFFF
        self.next()

    def next(self) -> int:
        old = self.state
        self.state = (old * 6364136223846793005 + self.inc) & 0xFFFFFFFFFFFFFFFF
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = (old >> 59) & 31
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & 0xFFFFFFFF


WEBB_WEIGHTS = [-math.sqrt(1.5), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(1.5)]


def webb_index_and_weight(output: int) -> tuple[int, float]:
    idx = output % 6
    return idx, WEBB_WEIGHTS[idx]


def nearest_rank(values: Sequence[float], p: float) -> float:
    ordered = sorted(values)
    rank = min(len(ordered), math.ceil(p * len(ordered)))
    return ordered[rank - 1]


def type7_quantile(values: Sequence[float], p: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    h = (len(ordered) - 1) * p
    j = math.floor(h)
    gamma = h - j
    if j + 1 >= len(ordered):
        return ordered[-1]
    return (1.0 - gamma) * ordered[j] + gamma * ordered[j + 1]


def covariance_matrix(z: Sequence[Sequence[float]], denom: float) -> list[list[float]]:
    p = len(z[0])
    cov = [[0.0 for _ in range(p)] for _ in range(p)]
    for row in z:
        for i in range(p):
            for j in range(i, p):
                cov[i][j] += row[i] * row[j] / denom
                cov[j][i] = cov[i][j]
    return cov


def jacobi_eigen_symmetric(a: Sequence[Sequence[float]], tol: float = 1e-12, max_steps: int = 100000) -> tuple[list[float], list[list[float]]]:
    n = len(a)
    mat = [[float(v) for v in row] for row in a]
    vec = eye(n)
    for _ in range(max_steps):
        p, q, best = 0, 1, 0.0
        for i in range(n):
            for j in range(i + 1, n):
                val = abs(mat[i][j])
                if val > best:
                    p, q, best = i, j, val
        if best < tol:
            break
        if mat[p][q] == 0.0:
            continue
        tau = (mat[q][q] - mat[p][p]) / (2.0 * mat[p][q])
        sign = 1.0 if tau >= 0 else -1.0
        t = sign / (abs(tau) + math.sqrt(1.0 + tau * tau))
        c = 1.0 / math.sqrt(1.0 + t * t)
        s = t * c
        app, aqq, apq = mat[p][p], mat[q][q], mat[p][q]
        mat[p][p] = app - t * apq
        mat[q][q] = aqq + t * apq
        mat[p][q] = mat[q][p] = 0.0
        for r in range(n):
            if r in (p, q):
                continue
            arp, arq = mat[r][p], mat[r][q]
            mat[r][p] = mat[p][r] = c * arp - s * arq
            mat[r][q] = mat[q][r] = s * arp + c * arq
        for r in range(n):
            vrp, vrq = vec[r][p], vec[r][q]
            vec[r][p] = c * vrp - s * vrq
            vec[r][q] = s * vrp + c * vrq
    values = [mat[i][i] for i in range(n)]
    vectors = [[vec[i][j] for i in range(n)] for j in range(n)]
    order = sorted(range(n), key=lambda i: (-values[i], i))
    return [values[i] for i in order], [orient_loading(vectors[i]) for i in order]


def orient_loading(vector: Sequence[float]) -> list[float]:
    max_abs = max(abs(v) for v in vector)
    idx = next(i for i, v in enumerate(vector) if abs(v) == max_abs)
    sign = 1.0 if vector[idx] >= 0 else -1.0
    return [sign * v for v in vector]


def project_scores(z: Sequence[Sequence[float]], loadings: Sequence[Sequence[float]], count: int) -> list[list[float]]:
    return [[sum(row[j] * loadings[c][j] for j in range(len(row))) for c in range(count)] for row in z]


def squared_distance(a: Sequence[float], b: Sequence[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def kmeans_farthest_first(ids: Sequence[str], points: Sequence[Sequence[float]], k: int, max_iter: int = 1000) -> tuple[list[int], list[list[float]], list[str], int]:
    n = len(points)
    centers_idx = [min(range(n), key=lambda i: ids[i])]
    while len(centers_idx) < k:
        centers_idx.append(
            max(
                (i for i in range(n) if i not in centers_idx),
                key=lambda i: (min(squared_distance(points[i], points[c]) for c in centers_idx), tuple(-ord(ch) for ch in ids[i])),
            )
        )
    centers = [[float(v) for v in points[i]] for i in centers_idx]
    labels = [0] * n
    for iteration in range(1, max_iter + 1):
        new_labels = []
        for point in points:
            new_labels.append(min(range(k), key=lambda c: (squared_distance(point, centers[c]), c)))
        if new_labels == labels and iteration > 1:
            break
        labels = new_labels
        for c in range(k):
            members = [points[i] for i, label in enumerate(labels) if label == c]
            if members:
                centers[c] = [sum(row[j] for row in members) / len(members) for j in range(len(points[0]))]
    return [label + 1 for label in labels], centers, [ids[i] for i in centers_idx], iteration


def adjusted_rand_index(labels_a: Sequence[int], labels_b: Sequence[int]) -> float:
    n = len(labels_a)
    if n != len(labels_b):
        raise ValueError("label lengths differ")

    def comb2(x: int) -> float:
        return x * (x - 1) / 2.0

    table: dict[tuple[int, int], int] = {}
    a_counts: dict[int, int] = {}
    b_counts: dict[int, int] = {}
    for a, b in zip(labels_a, labels_b):
        table[(a, b)] = table.get((a, b), 0) + 1
        a_counts[a] = a_counts.get(a, 0) + 1
        b_counts[b] = b_counts.get(b, 0) + 1
    sum_table = sum(comb2(v) for v in table.values())
    sum_a = sum(comb2(v) for v in a_counts.values())
    sum_b = sum(comb2(v) for v in b_counts.values())
    total = comb2(n)
    if total == 0:
        return 1.0
    expected = sum_a * sum_b / total
    denom = 0.5 * (sum_a + sum_b) - expected
    return (sum_table - expected) / denom if denom else 1.0


def rounded_json(value: Any, places: int) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return round(value, places)
    if isinstance(value, list):
        return [rounded_json(item, places) for item in value]
    if isinstance(value, dict):
        return {key: rounded_json(item, places) for key, item in value.items()}
    return value


def _self_test() -> None:
    fit = ols_fit([[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]], [1.0, 3.0, 5.0])
    assert all(abs(a - b) < 1e-9 for a, b in zip(fit.beta, [1.0, 2.0]))
    assert xorshift32_next(1) == 270369
    assert abs(nearest_rank([3, 1, 2], 0.5) - 2) < 1e-12
    assert abs(type7_quantile([0, 10], 0.25) - 2.5) < 1e-12
    assert abs(adjusted_rand_index([1, 1, 2, 2], [1, 1, 2, 2]) - 1.0) < 1e-12
    print("pho_audit_utils self-test passed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Observatory portal JSON or run helper self-test.")
    parser.add_argument("--base-url", help="Portal base URL.")
    parser.add_argument("--output-dir", help="Directory for fetched endpoint JSON files.")
    parser.add_argument("--self-test", action="store_true", help="Run deterministic helper checks.")
    args = parser.parse_args()
    if args.self_test:
        _self_test()
        return
    if not args.base_url or not args.output_dir:
        parser.error("--base-url and --output-dir are required unless --self-test is used")
    os.makedirs(args.output_dir, exist_ok=True)
    payloads = fetch_portal(args.base_url)
    for endpoint, payload in payloads.items():
        filename = endpoint.strip("/").replace("/", "_") + ".json"
        write_json(os.path.join(args.output_dir, filename), payload)


if __name__ == "__main__":
    main()
