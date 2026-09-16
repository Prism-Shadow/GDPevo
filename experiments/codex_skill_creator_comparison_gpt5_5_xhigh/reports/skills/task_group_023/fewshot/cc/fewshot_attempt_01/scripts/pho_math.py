"""Reusable standard-library helpers for Public Health Observatory audits.

The helpers are intentionally method primitives, not task-specific answers.
They avoid third-party dependencies so a clean Codex solver can run them in the
task workspace.
"""

from __future__ import annotations

import csv
import io
import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


MISSING_STRINGS = {"", "NA", "NaN", "nan", "NULL", "None"}


def download_portal_csvs(base_url: str, datasets: Sequence[str]) -> dict[str, list[dict[str, str]]]:
    """Download portal datasets through /download?dataset=...&format=csv."""
    out: dict[str, list[dict[str, str]]] = {}
    root = base_url.rstrip("/")
    for dataset in datasets:
        query = urllib.parse.urlencode({"dataset": dataset, "format": "csv"})
        url = f"{root}/download?{query}"
        with urllib.request.urlopen(url) as resp:
            text = resp.read().decode("utf-8")
        out[dataset] = list(csv.DictReader(io.StringIO(text)))
    return out


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else None
    text = str(value).strip()
    if text in MISSING_STRINGS:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def to_int(value: Any) -> int | None:
    number = to_float(value)
    return None if number is None else int(number)


def is_available(
    row: Mapping[str, Any],
    value_field: str = "value",
    invalid_quality_flags: Iterable[str] = ("INVALID_SCALE", "INVALID", "WITHDRAWN"),
) -> bool:
    """Return whether a selected publication row contributes an analytic value."""
    if to_float(row.get(value_field)) is None:
        return False
    if str(row.get("suppression_flag", "0")).strip() not in {"", "0", "0.0"}:
        return False
    if str(row.get("release_status", "")).upper() == "WITHDRAWN":
        return False
    invalid = {x.upper() for x in invalid_quality_flags}
    return str(row.get("quality_flag", "")).upper() not in invalid


def select_latest(
    rows: Iterable[Mapping[str, Any]],
    key_fields: Sequence[str],
    *,
    revision_field: str = "revision",
    released_at_field: str = "released_at",
    id_field: str,
    id_tie: str = "asc",
) -> dict[tuple[Any, ...], Mapping[str, Any]]:
    """Select one record per key by revision, release timestamp, and id.

    Revision and release timestamp are descending. `id_tie` is "asc" for lowest
    identifier or "desc" for greatest identifier.
    """
    if id_tie not in {"asc", "desc"}:
        raise ValueError("id_tie must be 'asc' or 'desc'")
    selected: dict[tuple[Any, ...], Mapping[str, Any]] = {}

    def better(row: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
        rev_row = to_int(row.get(revision_field)) or -10**18
        rev_cur = to_int(current.get(revision_field)) or -10**18
        if rev_row != rev_cur:
            return rev_row > rev_cur
        rel_row = str(row.get(released_at_field, ""))
        rel_cur = str(current.get(released_at_field, ""))
        if rel_row != rel_cur:
            return rel_row > rel_cur
        id_row = str(row.get(id_field, ""))
        id_cur = str(current.get(id_field, ""))
        return id_row < id_cur if id_tie == "asc" else id_row > id_cur

    for row in rows:
        key = tuple(row.get(field) for field in key_fields)
        if key not in selected or better(row, selected[key]):
            selected[key] = row
    return selected


def deep_merge(base: Any, override: Any) -> Any:
    """Deep-merge exact object keys; arrays and scalars replace."""
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = deep_merge(merged[key], value) if key in merged else value
        return merged
    return override


def finite_json(value: Any, decimals: int = 4) -> Any:
    """Round floats recursively and convert non-finite values to None."""
    if isinstance(value, dict):
        return {k: finite_json(v, decimals) for k, v in value.items()}
    if isinstance(value, list):
        return [finite_json(v, decimals) for v in value]
    if isinstance(value, tuple):
        return [finite_json(v, decimals) for v in value]
    if isinstance(value, (bool, int)) or value is None:
        return value
    if isinstance(value, float):
        return round(value, decimals) if math.isfinite(value) else None
    return value


def dump_json(obj: Any, decimals: int = 4) -> str:
    return json.dumps(finite_json(obj, decimals), separators=(",", ":"), allow_nan=False)


def transpose(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    return [list(col) for col in zip(*matrix)]


def matmul(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> list[list[float]]:
    bt = transpose(b)
    return [[sum(x * y for x, y in zip(row, col)) for col in bt] for row in a]


def matvec(a: Sequence[Sequence[float]], x: Sequence[float]) -> list[float]:
    return [sum(ai * xi for ai, xi in zip(row, x)) for row in a]


def outer(a: Sequence[float], b: Sequence[float]) -> list[list[float]]:
    return [[x * y for y in b] for x in a]


def add_matrix(a: list[list[float]], b: Sequence[Sequence[float]]) -> list[list[float]]:
    for i in range(len(a)):
        for j in range(len(a[i])):
            a[i][j] += b[i][j]
    return a


def identity(n: int) -> list[list[float]]:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def add_intercept(x: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[1.0, *map(float, row)] for row in x]


def xtx(x: Sequence[Sequence[float]]) -> list[list[float]]:
    return matmul(transpose(x), x)


def xty(x: Sequence[Sequence[float]], y: Sequence[float]) -> list[float]:
    return matvec(transpose(x), y)


def jacobi_eigen_symmetric(
    matrix: Sequence[Sequence[float]],
    *,
    tol: float = 1e-12,
    max_iter: int = 10000,
) -> tuple[list[float], list[list[float]]]:
    """Eigen-decompose a real symmetric matrix by deterministic Jacobi rotation."""
    n = len(matrix)
    a = [list(map(float, row)) for row in matrix]
    v = identity(n)
    if n == 0:
        return [], []
    for _ in range(max_iter):
        p, q = 0, 1 if n > 1 else 0
        max_abs = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                val = abs(a[i][j])
                if val > max_abs:
                    max_abs = val
                    p, q = i, j
        if max_abs < tol or n == 1:
            break
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        tau = (aqq - app) / (2.0 * apq)
        sign = 1.0 if tau >= 0 else -1.0
        t = sign / (abs(tau) + math.sqrt(1.0 + tau * tau))
        c = 1.0 / math.sqrt(1.0 + t * t)
        s = t * c
        for k in range(n):
            if k not in (p, q):
                akp, akq = a[k][p], a[k][q]
                a[k][p] = a[p][k] = c * akp - s * akq
                a[k][q] = a[q][k] = s * akp + c * akq
        a[p][p] = c * c * app - 2.0 * s * c * apq + s * s * aqq
        a[q][q] = s * s * app + 2.0 * s * c * apq + c * c * aqq
        a[p][q] = a[q][p] = 0.0
        for k in range(n):
            vkp, vkq = v[k][p], v[k][q]
            v[k][p] = c * vkp - s * vkq
            v[k][q] = s * vkp + c * vkq
    return [a[i][i] for i in range(n)], v


def pinv_symmetric(matrix: Sequence[Sequence[float]], rel_cutoff: float = 1e-12) -> list[list[float]]:
    vals, vecs = jacobi_eigen_symmetric(matrix)
    n = len(vals)
    scale = max([abs(x) for x in vals] or [0.0])
    cutoff = scale * rel_cutoff
    out = [[0.0 for _ in range(n)] for _ in range(n)]
    for col, val in enumerate(vals):
        if abs(val) <= cutoff:
            continue
        inv = 1.0 / val
        for i in range(n):
            for j in range(n):
                out[i][j] += vecs[i][col] * inv * vecs[j][col]
    return out


@dataclass
class Fit:
    beta: list[float]
    fitted: list[float]
    resid: list[float]
    xtx_inv: list[list[float]]
    design: list[list[float]]


def ols(y: Sequence[float], x: Sequence[Sequence[float]], intercept: bool = True) -> Fit:
    yy = list(map(float, y))
    design = add_intercept(x) if intercept else [list(map(float, row)) for row in x]
    inv = pinv_symmetric(xtx(design))
    beta = matvec(inv, xty(design, yy))
    fitted = matvec(design, beta)
    resid = [a - b for a, b in zip(yy, fitted)]
    return Fit(beta=beta, fitted=fitted, resid=resid, xtx_inv=inv, design=design)


def wls(y: Sequence[float], x: Sequence[Sequence[float]], weights: Sequence[float], intercept: bool = True) -> Fit:
    yy = list(map(float, y))
    design_raw = add_intercept(x) if intercept else [list(map(float, row)) for row in x]
    sw = [math.sqrt(float(w)) for w in weights]
    design = [[value * sw[i] for value in row] for i, row in enumerate(design_raw)]
    yw = [yy[i] * sw[i] for i in range(len(yy))]
    inv = pinv_symmetric(xtx(design))
    beta = matvec(inv, xty(design, yw))
    fitted = matvec(design_raw, beta)
    resid = [a - b for a, b in zip(yy, fitted)]
    return Fit(beta=beta, fitted=fitted, resid=resid, xtx_inv=inv, design=design_raw)


def hc3_cov(
    design: Sequence[Sequence[float]],
    resid: Sequence[float],
    *,
    weights: Sequence[float] | None = None,
) -> list[list[float]]:
    if weights is None:
        xw = [list(map(float, row)) for row in design]
        ew = list(map(float, resid))
    else:
        sw = [math.sqrt(float(w)) for w in weights]
        xw = [[value * sw[i] for value in row] for i, row in enumerate(design)]
        ew = [float(resid[i]) * sw[i] for i in range(len(resid))]
    inv = pinv_symmetric(xtx(xw))
    p = len(xw[0])
    meat = [[0.0 for _ in range(p)] for _ in range(p)]
    for row, e in zip(xw, ew):
        h = sum(row[i] * sum(inv[i][j] * row[j] for j in range(p)) for i in range(p))
        scale = e * e / max((1.0 - h) ** 2, 1e-30)
        add_matrix(meat, [[scale * cell for cell in line] for line in outer(row, row)])
    return matmul(matmul(inv, meat), inv)


def cr1_cov(
    design: Sequence[Sequence[float]],
    resid: Sequence[float],
    clusters: Sequence[Any],
    *,
    weights: Sequence[float] | None = None,
) -> list[list[float]]:
    if weights is None:
        xw = [list(map(float, row)) for row in design]
        ew = list(map(float, resid))
    else:
        sw = [math.sqrt(float(w)) for w in weights]
        xw = [[value * sw[i] for value in row] for i, row in enumerate(design)]
        ew = [float(resid[i]) * sw[i] for i in range(len(resid))]
    n, p = len(xw), len(xw[0])
    order = list(dict.fromkeys(clusters))
    inv = pinv_symmetric(xtx(xw))
    meat = [[0.0 for _ in range(p)] for _ in range(p)]
    for cluster in order:
        score = [0.0 for _ in range(p)]
        for row, e, g in zip(xw, ew, clusters):
            if g == cluster:
                for j in range(p):
                    score[j] += row[j] * e
        add_matrix(meat, outer(score, score))
    g = len(order)
    factor = (g / (g - 1)) * ((n - 1) / (n - p)) if g > 1 and n > p else 1.0
    cov = matmul(matmul(inv, meat), inv)
    return [[factor * cell for cell in row] for row in cov]


def double_demean(values: Sequence[float], entities: Sequence[Any], times: Sequence[Any]) -> list[float]:
    vals = list(map(float, values))
    grand = sum(vals) / len(vals)
    entity_means = {
        e: sum(v for v, ee in zip(vals, entities) if ee == e) / sum(1 for ee in entities if ee == e)
        for e in dict.fromkeys(entities)
    }
    time_means = {
        t: sum(v for v, tt in zip(vals, times) if tt == t) / sum(1 for tt in times if tt == t)
        for t in dict.fromkeys(times)
    }
    return [v - entity_means[e] - time_means[t] + grand for v, e, t in zip(vals, entities, times)]


def column_means(matrix: Sequence[Sequence[float]], weights: Sequence[float] | None = None) -> list[float]:
    x = [list(map(float, row)) for row in matrix]
    if not x:
        return []
    p = len(x[0])
    if weights is None:
        return [sum(row[j] for row in x) / len(x) for j in range(p)]
    w = list(map(float, weights))
    total = sum(w)
    return [sum(w[i] * x[i][j] for i in range(len(x))) / total for j in range(p)]


def standardize(
    train: Sequence[Sequence[float]],
    apply: Sequence[Sequence[float]],
    *,
    ddof: int = 0,
    weights: Sequence[float] | None = None,
) -> tuple[list[list[float]], list[list[float]], list[float], list[float]]:
    x_train = [list(map(float, row)) for row in train]
    x_apply = [list(map(float, row)) for row in apply]
    mu = column_means(x_train, weights)
    if weights is None:
        denom = max(1, len(x_train) - ddof)
        sd = [math.sqrt(sum((row[j] - mu[j]) ** 2 for row in x_train) / denom) for j in range(len(mu))]
    else:
        w = list(map(float, weights))
        total = sum(w)
        sd = [math.sqrt(sum(w[i] * (x_train[i][j] - mu[j]) ** 2 for i in range(len(x_train))) / total) for j in range(len(mu))]
    sd = [s if s != 0 else 1.0 for s in sd]
    train_z = [[(row[j] - mu[j]) / sd[j] for j in range(len(mu))] for row in x_train]
    apply_z = [[(row[j] - mu[j]) / sd[j] for j in range(len(mu))] for row in x_apply]
    return train_z, apply_z, mu, sd


def ridge_cd(
    y: Sequence[float],
    x: Sequence[Sequence[float]],
    lam: float,
    *,
    weights: Sequence[float] | None = None,
    max_sweeps: int = 10000,
    tol: float = 1e-10,
) -> tuple[float, list[float], int]:
    yy = list(map(float, y))
    xx = [list(map(float, row)) for row in x]
    n, p = len(xx), len(xx[0])
    w = [1.0] * n if weights is None else list(map(float, weights))
    wsum = sum(w)
    intercept = sum(w[i] * yy[i] for i in range(n)) / wsum
    beta = [0.0 for _ in range(p)]
    for sweep in range(1, max_sweeps + 1):
        old = beta[:]
        for j in range(p):
            rho_num = 0.0
            denom_num = 0.0
            for i in range(n):
                pred_without_j = intercept + sum(xx[i][k] * beta[k] for k in range(p) if k != j)
                rho_num += w[i] * xx[i][j] * (yy[i] - pred_without_j)
                denom_num += w[i] * xx[i][j] * xx[i][j]
            beta[j] = (rho_num / wsum) / ((denom_num / wsum) + lam)
        if max(abs(beta[j] - old[j]) for j in range(p)) < tol:
            return intercept, beta, sweep
    return intercept, beta, max_sweeps


def soft_threshold(value: float, threshold: float) -> float:
    if value > threshold:
        return value - threshold
    if value < -threshold:
        return value + threshold
    return 0.0


def elastic_net_cd(
    y: Sequence[float],
    x: Sequence[Sequence[float]],
    lam: float,
    l1_ratio: float,
    *,
    weights: Sequence[float] | None = None,
    update_intercept: bool = False,
    max_sweeps: int = 10000,
    tol: float = 1e-10,
) -> tuple[float, list[float], int]:
    yy = list(map(float, y))
    xx = [list(map(float, row)) for row in x]
    n, p = len(xx), len(xx[0])
    w = [1.0] * n if weights is None else list(map(float, weights))
    wsum = sum(w)
    intercept = sum(w[i] * yy[i] for i in range(n)) / wsum
    beta = [0.0 for _ in range(p)]
    for sweep in range(1, max_sweeps + 1):
        old_intercept = intercept
        old = beta[:]
        if update_intercept:
            residual_sum = sum(w[i] * (yy[i] - intercept - sum(xx[i][k] * beta[k] for k in range(p))) for i in range(n))
            intercept += residual_sum / wsum
        for j in range(p):
            rho_num = 0.0
            denom_num = 0.0
            for i in range(n):
                pred_without_j = intercept + sum(xx[i][k] * beta[k] for k in range(p) if k != j)
                rho_num += w[i] * xx[i][j] * (yy[i] - pred_without_j)
                denom_num += w[i] * xx[i][j] * xx[i][j]
            rho = rho_num / wsum
            denom = denom_num / wsum + lam * (1.0 - l1_ratio)
            beta[j] = soft_threshold(rho, lam * l1_ratio) / denom if denom else 0.0
        max_change = max(abs(intercept - old_intercept), max(abs(beta[j] - old[j]) for j in range(p)))
        if max_change < tol:
            return intercept, beta, sweep
    return intercept, beta, max_sweeps


class XorShift32:
    def __init__(self, seed: int):
        self.state = seed & 0xFFFFFFFF

    def next(self) -> int:
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x &= 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x &= 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x & 0xFFFFFFFF
        return self.state


class PCG32:
    def __init__(self, initstate: int, stream: int):
        self.state = 0
        self.inc = ((stream & 0xFFFFFFFFFFFFFFFF) << 1) | 1
        self.next()
        self.state = (self.state + initstate) & 0xFFFFFFFFFFFFFFFF
        self.next()

    def next(self) -> int:
        old = self.state
        self.state = (old * 6364136223846793005 + self.inc) & 0xFFFFFFFFFFFFFFFF
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = (old >> 59) & 31
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & 0xFFFFFFFF


def webb_weight_from_index(index: int) -> float:
    weights = [-math.sqrt(1.5), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(1.5)]
    return weights[index]


def nearest_rank(sorted_values: Sequence[float], probability: float) -> float:
    vals = list(map(float, sorted_values))
    if not vals:
        return float("nan")
    rank = min(len(vals), max(1, math.ceil(probability * len(vals))))
    return vals[rank - 1]


def type7_quantile(sorted_values: Sequence[float], probability: float) -> float:
    vals = list(map(float, sorted_values))
    if not vals:
        return float("nan")
    if len(vals) == 1:
        return vals[0]
    h = (len(vals) - 1) * probability
    j = int(math.floor(h))
    gamma = h - j
    if j >= len(vals) - 1:
        return vals[-1]
    return (1.0 - gamma) * vals[j] + gamma * vals[j + 1]


def covariance_pca(
    matrix: Sequence[Sequence[float]],
    *,
    ddof_scale: int = 1,
    covariance_divisor: str = "n-1",
) -> tuple[list[float], list[list[float]], list[list[float]], list[list[float]]]:
    x = [list(map(float, row)) for row in matrix]
    z, _, _, _ = standardize(x, x, ddof=ddof_scale)
    denom = len(z) - 1 if covariance_divisor == "n-1" else len(z)
    cov = [[sum(row[i] * row[j] for row in z) / denom for j in range(len(z[0]))] for i in range(len(z[0]))]
    vals, vecs = jacobi_eigen_symmetric(cov)
    order = sorted(range(len(vals)), key=lambda i: (-vals[i], i))
    vals = [vals[i] for i in order]
    vecs = [[row[i] for i in order] for row in vecs]
    for col in range(len(vals)):
        abs_col = [abs(vecs[row][col]) for row in range(len(vecs))]
        idx = abs_col.index(max(abs_col))
        if vecs[idx][col] < 0:
            for row in range(len(vecs)):
                vecs[row][col] *= -1.0
    scores = matmul(z, vecs)
    return vals, vecs, scores, z


def squared_distance(a: Sequence[float], b: Sequence[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def euclidean(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(squared_distance(a, b))


def kmeans_farthest_first(
    points: Sequence[Sequence[float]],
    ids: Sequence[Any],
    k: int,
    *,
    max_iter: int = 1000,
) -> tuple[list[int], list[list[float]], int, list[Any]]:
    pts = [list(map(float, row)) for row in points]
    order = sorted(range(len(ids)), key=lambda i: str(ids[i]))
    center_idx = [order[0]]
    while len(center_idx) < k:
        best_idx = None
        best_dist = -1.0
        for i in order:
            if i in center_idx:
                continue
            dist = min(squared_distance(pts[i], pts[c]) for c in center_idx)
            if best_idx is None or dist > best_dist or (dist == best_dist and str(ids[i]) < str(ids[best_idx])):
                best_idx = i
                best_dist = dist
        center_idx.append(int(best_idx))
    centers = [pts[i][:] for i in center_idx]
    labels = [0 for _ in pts]
    for iteration in range(1, max_iter + 1):
        old = labels[:]
        for i, point in enumerate(pts):
            distances = [squared_distance(point, center) for center in centers]
            labels[i] = min(range(k), key=lambda c: (distances[c], c))
        for c in range(k):
            members = [pts[i] for i, lab in enumerate(labels) if lab == c]
            if members:
                centers[c] = [sum(row[j] for row in members) / len(members) for j in range(len(pts[0]))]
        if labels == old:
            return [lab + 1 for lab in labels], centers, iteration, [ids[i] for i in center_idx]
    return [lab + 1 for lab in labels], centers, max_iter, [ids[i] for i in center_idx]


def adjusted_rand_index(labels_a: Sequence[Any], labels_b: Sequence[Any]) -> float:
    a, b = list(labels_a), list(labels_b)
    if len(a) != len(b):
        raise ValueError("label arrays must have equal length")
    n = len(a)
    if n < 2:
        return 1.0
    avals = list(dict.fromkeys(a))
    bvals = list(dict.fromkeys(b))
    table = [[0 for _ in bvals] for _ in avals]
    ai = {v: i for i, v in enumerate(avals)}
    bi = {v: i for i, v in enumerate(bvals)}
    for x, y in zip(a, b):
        table[ai[x]][bi[y]] += 1

    def comb2(value: int) -> float:
        return value * (value - 1) / 2.0

    sum_ij = sum(comb2(cell) for row in table for cell in row)
    row_sums = [sum(row) for row in table]
    col_sums = [sum(table[i][j] for i in range(len(table))) for j in range(len(bvals))]
    sum_a = sum(comb2(x) for x in row_sums)
    sum_b = sum(comb2(x) for x in col_sums)
    total = comb2(n)
    expected = sum_a * sum_b / total if total else 0.0
    denom = 0.5 * (sum_a + sum_b) - expected
    return 1.0 if denom == 0 else (sum_ij - expected) / denom


def silhouette(points: Sequence[Sequence[float]], labels: Sequence[Any]) -> float:
    pts = [list(map(float, row)) for row in points]
    labs = list(labels)
    unique = list(dict.fromkeys(labs))
    scores = []
    for i, point in enumerate(pts):
        same = [j for j, lab in enumerate(labs) if lab == labs[i] and j != i]
        if not same:
            scores.append(0.0)
            continue
        a = sum(euclidean(point, pts[j]) for j in same) / len(same)
        b = math.inf
        for lab in unique:
            if lab == labs[i]:
                continue
            other = [j for j, other_lab in enumerate(labs) if other_lab == lab]
            if other:
                b = min(b, sum(euclidean(point, pts[j]) for j in other) / len(other))
        scores.append((b - a) / max(a, b) if math.isfinite(b) and max(a, b) > 0 else 0.0)
    return sum(scores) / len(scores) if scores else float("nan")


def rmse(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    errors = [(float(a) - float(b)) ** 2 for a, b in zip(y_true, y_pred)]
    return math.sqrt(sum(errors) / len(errors))


def mae(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    errors = [abs(float(a) - float(b)) for a, b in zip(y_true, y_pred)]
    return sum(errors) / len(errors)


def r_squared(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    y = list(map(float, y_true))
    mean_y = sum(y) / len(y)
    denom = sum((value - mean_y) ** 2 for value in y)
    if denom == 0:
        return float("nan")
    return 1.0 - sum((float(a) - float(b)) ** 2 for a, b in zip(y_true, y_pred)) / denom

