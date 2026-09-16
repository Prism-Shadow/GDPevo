"""Reusable helpers for Public Health Observatory registered audits.

The functions are generic utilities, not task solvers. They intentionally do not
contain solved values from any training task.
"""

from __future__ import annotations

import csv
import io
import itertools
import json
import math
from typing import Any, Callable, Iterable
from urllib.parse import urlencode
from urllib.request import urlopen


def download_csv(base_url: str, dataset: str, **filters: Any) -> list[dict[str, str]]:
    """Download a portal CSV dataset, optionally with exact-match filters."""
    base = base_url.rstrip("/")
    query = {"dataset": dataset, "format": "csv"}
    query.update({k: v for k, v in filters.items() if v is not None})
    url = f"{base}/download?{urlencode(query, doseq=True)}"
    with urlopen(url) as response:
        text = response.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null", "--"}:
        return None
    return float(text)


def to_int(value: Any) -> int | None:
    number = to_float(value)
    if number is None:
        return None
    return int(number)


def is_available_value(
    row: dict[str, Any],
    value_field: str = "value",
    invalid_flags: Iterable[str] = ("INVALID", "INVALID_SCALE", "WITHDRAWN", "SCALE_REVIEW"),
) -> bool:
    if to_float(row.get(value_field)) is None:
        return False
    if str(row.get("suppression_flag", "0")).strip() in {"1", "true", "TRUE"}:
        return False
    flag = str(row.get("quality_flag", "")).strip()
    return flag not in set(invalid_flags)


def select_latest(
    rows: Iterable[dict[str, Any]],
    key_fields: Iterable[str],
    priority: Iterable[tuple[str, str]] = (
        ("revision", "desc"),
        ("released_at", "desc"),
        ("observation_id", "asc"),
        ("record_id", "asc"),
    ),
) -> dict[tuple[Any, ...], dict[str, Any]]:
    """Select one row per key according to ordered priority.

    Direction is "asc" or "desc". Missing priority fields are ignored for that
    row, which lets one priority work across health and socioeconomic tables.
    """
    key_fields = tuple(key_fields)
    priority = tuple(priority)
    selected: dict[tuple[Any, ...], dict[str, Any]] = {}

    def normalize(value: Any) -> Any:
        if value is None:
            return ""
        text = str(value)
        number = to_float(text)
        return number if number is not None and text.replace(".", "", 1).isdigit() else text

    def better(candidate: dict[str, Any], incumbent: dict[str, Any]) -> bool:
        for field, direction in priority:
            if field not in candidate and field not in incumbent:
                continue
            left = normalize(candidate.get(field))
            right = normalize(incumbent.get(field))
            if left == right:
                continue
            return left > right if direction == "desc" else left < right
        return False

    for row in rows:
        key = tuple(row.get(field) for field in key_fields)
        if key not in selected or better(row, selected[key]):
            selected[key] = row
    return selected


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(base))
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def round_json(value: Any, digits: int) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return round(value, digits)
    if isinstance(value, list):
        return [round_json(item, digits) for item in value]
    if isinstance(value, dict):
        return {key: round_json(item, digits) for key, item in value.items()}
    return value


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def transpose(a: list[list[float]]) -> list[list[float]]:
    return [list(col) for col in zip(*a)]


def matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    bt = transpose(b)
    return [[dot(row, col) for col in bt] for row in a]


def matvec(a: list[list[float]], x: list[float]) -> list[float]:
    return [dot(row, x) for row in a]


def outer(a: list[float], b: list[float]) -> list[list[float]]:
    return [[x * y for y in b] for x in a]


def eye(n: int) -> list[list[float]]:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def inverse(a: list[list[float]], ridge: float = 0.0) -> list[list[float]]:
    n = len(a)
    aug = []
    for i, row in enumerate(a):
        left = [float(x) for x in row]
        if ridge:
            left[i] += ridge
        aug.append(left + eye(n)[i])
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-14:
            raise ValueError("matrix is singular")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [x / scale for x in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            if factor:
                aug[row] = [x - factor * y for x, y in zip(aug[row], aug[col])]
    return [row[n:] for row in aug]


def solve(a: list[list[float]], b: list[float], ridge: float = 0.0) -> list[float]:
    return matvec(inverse(a, ridge=ridge), b)


def xtx_xty(
    x: list[list[float]], y: list[float], weights: list[float] | None = None
) -> tuple[list[list[float]], list[float]]:
    p = len(x[0])
    xtx = [[0.0] * p for _ in range(p)]
    xty = [0.0] * p
    for i, row in enumerate(x):
        w = 1.0 if weights is None else weights[i]
        for j in range(p):
            xty[j] += w * row[j] * y[i]
            for k in range(p):
                xtx[j][k] += w * row[j] * row[k]
    return xtx, xty


def ols_beta(x: list[list[float]], y: list[float], weights: list[float] | None = None) -> list[float]:
    xtx, xty = xtx_xty(x, y, weights)
    try:
        return solve(xtx, xty)
    except ValueError:
        return matvec(pinv_symmetric(xtx), xty)


def residuals(x: list[list[float]], y: list[float], beta: list[float]) -> list[float]:
    fitted = matvec(x, beta)
    return [yi - fi for yi, fi in zip(y, fitted)]


def weighted_design(
    x: list[list[float]], y: list[float], weights: list[float] | None
) -> tuple[list[list[float]], list[float], list[float]]:
    if weights is None:
        return x, y, [1.0] * len(y)
    roots = [math.sqrt(w) for w in weights]
    return (
        [[roots[i] * value for value in row] for i, row in enumerate(x)],
        [roots[i] * value for i, value in enumerate(y)],
        roots,
    )


def hc3_covariance(
    x: list[list[float]], y: list[float], beta: list[float], weights: list[float] | None = None
) -> list[list[float]]:
    xw, _, roots = weighted_design(x, y, weights)
    xtx, _ = xtx_xty(xw, [0.0] * len(xw))
    xtx_inv = inverse(xtx)
    raw_resid = residuals(x, y, beta)
    p = len(beta)
    meat = [[0.0] * p for _ in range(p)]
    for i, row in enumerate(xw):
        h = dot(row, matvec(xtx_inv, row))
        denom = max((1.0 - h) ** 2, 1e-30)
        scale = (roots[i] * raw_resid[i]) ** 2 / denom
        for j in range(p):
            for k in range(p):
                meat[j][k] += row[j] * scale * row[k]
    return matmul(matmul(xtx_inv, meat), xtx_inv)


def cr1_covariance(
    x: list[list[float]],
    y: list[float],
    beta: list[float],
    clusters: list[Any],
    weights: list[float] | None = None,
) -> list[list[float]]:
    xw, _, roots = weighted_design(x, y, weights)
    xtx, _ = xtx_xty(xw, [0.0] * len(xw))
    xtx_inv = inverse(xtx)
    raw_resid = residuals(x, y, beta)
    p = len(beta)
    order = []
    scores: dict[Any, list[float]] = {}
    for i, cluster in enumerate(clusters):
        if cluster not in scores:
            scores[cluster] = [0.0] * p
            order.append(cluster)
        ew = roots[i] * raw_resid[i]
        for j in range(p):
            scores[cluster][j] += xw[i][j] * ew
    meat = [[0.0] * p for _ in range(p)]
    for cluster in order:
        s = scores[cluster]
        for j in range(p):
            for k in range(p):
                meat[j][k] += s[j] * s[k]
    n = len(y)
    g = len(order)
    k = p
    factor = (g / (g - 1)) * ((n - 1) / (n - k)) if g > 1 and n > k else 1.0
    cov = matmul(matmul(xtx_inv, meat), xtx_inv)
    return [[factor * value for value in row] for row in cov]


def double_demean(values: list[list[float]], entities: list[Any], times: list[Any]) -> list[list[float]]:
    n = len(values)
    p = len(values[0])
    entity_groups: dict[Any, list[int]] = {}
    time_groups: dict[Any, list[int]] = {}
    for i, entity in enumerate(entities):
        entity_groups.setdefault(entity, []).append(i)
        time_groups.setdefault(times[i], []).append(i)
    grand = [sum(row[j] for row in values) / n for j in range(p)]
    entity_mean = {
        key: [sum(values[i][j] for i in idxs) / len(idxs) for j in range(p)]
        for key, idxs in entity_groups.items()
    }
    time_mean = {
        key: [sum(values[i][j] for i in idxs) / len(idxs) for j in range(p)]
        for key, idxs in time_groups.items()
    }
    return [
        [values[i][j] - entity_mean[entities[i]][j] - time_mean[times[i]][j] + grand[j] for j in range(p)]
        for i in range(n)
    ]


def _betacf(a: float, b: float, x: float) -> float:
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, 200):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-14:
            break
    return h


def regularized_beta(a: float, b: float, x: float) -> float:
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
    ib = regularized_beta(df / 2.0, 0.5, x)
    return 1.0 - 0.5 * ib if t >= 0 else 0.5 * ib


def two_sided_t_p(t: float, df: float) -> float:
    return max(0.0, min(1.0, 2.0 * (1.0 - student_t_cdf(abs(t), df))))


def rmse(y: list[float], pred: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(y, pred)) / len(y))


def mae(y: list[float], pred: list[float]) -> float:
    return sum(abs(a - b) for a, b in zip(y, pred)) / len(y)


def r_squared(y: list[float], pred: list[float]) -> float:
    mean_y = sum(y) / len(y)
    sse = sum((a - b) ** 2 for a, b in zip(y, pred))
    sst = sum((a - mean_y) ** 2 for a in y)
    return 1.0 - sse / sst if sst else 0.0


def nearest_rank(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("empty values")
    rank = min(len(ordered), max(1, math.ceil(probability * len(ordered))))
    return ordered[rank - 1]


def type7_quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        raise ValueError("empty values")
    if n == 1:
        return ordered[0]
    h = (n - 1) * probability
    j = math.floor(h)
    gamma = h - j
    if j >= n - 1:
        return ordered[-1]
    return (1.0 - gamma) * ordered[j] + gamma * ordered[j + 1]


def conformal_rank(m: int, coverage: float) -> int:
    return min(m, max(1, math.ceil((m + 1) * coverage)))


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

    def sign(self) -> int:
        return 1 if self.next() & 1 else -1


def _rotr32(value: int, rot: int) -> int:
    rot &= 31
    return ((value >> rot) | ((value << ((-rot) & 31)) & 0xFFFFFFFF)) & 0xFFFFFFFF


class PCG32:
    def __init__(self, seed: int, stream: int):
        self.state = 0
        self.inc = ((stream << 1) | 1) & 0xFFFFFFFFFFFFFFFF
        self.next()
        self.state = (self.state + seed) & 0xFFFFFFFFFFFFFFFF
        self.next()

    def next(self) -> int:
        old = self.state
        self.state = (old * 6364136223846793005 + self.inc) & 0xFFFFFFFFFFFFFFFF
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = (old >> 59) & 0x1F
        return _rotr32(xorshifted, rot)

    def webb_index(self) -> int:
        return self.next() % 6

    def webb_weight(self) -> float:
        weights = [-math.sqrt(1.5), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(1.5)]
        return weights[self.webb_index()]


def standardize(
    x: list[list[float]],
    weights: list[float] | None = None,
    ddof: int = 0,
) -> tuple[list[list[float]], list[float], list[float]]:
    n = len(x)
    p = len(x[0])
    if weights is None:
        weights = [1.0] * n
    total_w = sum(weights)
    means = [sum(weights[i] * x[i][j] for i in range(n)) / total_w for j in range(p)]
    denom = total_w - ddof if total_w > ddof else total_w
    scales = []
    for j in range(p):
        var = sum(weights[i] * (x[i][j] - means[j]) ** 2 for i in range(n)) / denom
        scale = math.sqrt(max(var, 0.0))
        scales.append(scale if scale > 0 else 1.0)
    z = [[(row[j] - means[j]) / scales[j] for j in range(p)] for row in x]
    return z, means, scales


def apply_standardization(x: list[list[float]], means: list[float], scales: list[float]) -> list[list[float]]:
    return [[(row[j] - means[j]) / scales[j] for j in range(len(means))] for row in x]


def soft_threshold(value: float, threshold: float) -> float:
    if value > threshold:
        return value - threshold
    if value < -threshold:
        return value + threshold
    return 0.0


def elastic_net_cd(
    x: list[list[float]],
    y: list[float],
    penalty: float,
    l1_ratio: float,
    weights: list[float] | None = None,
    max_iter: int = 10000,
    tol: float = 1e-10,
) -> tuple[float, list[float], int]:
    n = len(y)
    p = len(x[0]) if p_len(x) else 0
    if weights is None:
        weights = [1.0] * n
    sum_w = sum(weights)
    intercept = sum(weights[i] * y[i] for i in range(n)) / sum_w
    beta = [0.0] * p
    for iteration in range(1, max_iter + 1):
        old = [intercept] + beta[:]
        pred_without_intercept = [dot(x[i], beta) for i in range(n)]
        intercept = sum(weights[i] * (y[i] - pred_without_intercept[i]) for i in range(n)) / sum_w
        for j in range(p):
            numerator = 0.0
            denom = 0.0
            for i in range(n):
                partial = y[i] - intercept - sum(x[i][k] * beta[k] for k in range(p) if k != j)
                numerator += weights[i] * x[i][j] * partial
                denom += weights[i] * x[i][j] * x[i][j]
            rho = numerator / sum_w
            z = denom / sum_w
            beta[j] = soft_threshold(rho, penalty * l1_ratio) / (z + penalty * (1.0 - l1_ratio))
        change = max(abs(a - b) for a, b in zip(old, [intercept] + beta))
        if change < tol:
            return intercept, beta, iteration
    return intercept, beta, max_iter


def p_len(x: list[list[float]]) -> int:
    return len(x[0]) if x else 0


def predict_linear(x: list[list[float]], intercept: float, beta: list[float]) -> list[float]:
    return [intercept + dot(row, beta) for row in x]


def jacobi_symmetric(
    a: list[list[float]], tol: float = 1e-12, max_iter: int = 100000
) -> tuple[list[float], list[list[float]]]:
    n = len(a)
    mat = [[float(a[i][j]) for j in range(n)] for i in range(n)]
    vec = eye(n)
    for _ in range(max_iter):
        p, q = 0, 1
        best = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                value = abs(mat[i][j])
                if value > best:
                    best = value
                    p, q = i, j
        if best < tol:
            break
        if mat[p][q] == 0:
            continue
        tau = (mat[q][q] - mat[p][p]) / (2.0 * mat[p][q])
        sign = 1.0 if tau >= 0 else -1.0
        t = sign / (abs(tau) + math.sqrt(1.0 + tau * tau))
        c = 1.0 / math.sqrt(1.0 + t * t)
        s = t * c
        app = mat[p][p]
        aqq = mat[q][q]
        apq = mat[p][q]
        mat[p][p] = c * c * app - 2.0 * s * c * apq + s * s * aqq
        mat[q][q] = s * s * app + 2.0 * s * c * apq + c * c * aqq
        mat[p][q] = mat[q][p] = 0.0
        for r in range(n):
            if r in (p, q):
                continue
            arp = mat[r][p]
            arq = mat[r][q]
            mat[r][p] = mat[p][r] = c * arp - s * arq
            mat[r][q] = mat[q][r] = s * arp + c * arq
        for r in range(n):
            vrp = vec[r][p]
            vrq = vec[r][q]
            vec[r][p] = c * vrp - s * vrq
            vec[r][q] = s * vrp + c * vrq
    return [mat[i][i] for i in range(n)], vec


def pinv_symmetric(a: list[list[float]], relative_cutoff: float = 1e-12) -> list[list[float]]:
    values, vectors = jacobi_symmetric(a)
    max_abs = max((abs(v) for v in values), default=0.0)
    n = len(values)
    result = [[0.0] * n for _ in range(n)]
    for j, value in enumerate(values):
        if max_abs == 0.0 or abs(value) <= relative_cutoff * max_abs:
            continue
        inv_value = 1.0 / value
        col = [vectors[i][j] for i in range(n)]
        for r in range(n):
            for c in range(n):
                result[r][c] += inv_value * col[r] * col[c]
    return result


def pca(
    x: list[list[float]], ddof: int = 1, covariance_divisor: float | None = None
) -> dict[str, Any]:
    z, means, scales = standardize(x, ddof=ddof)
    n = len(z)
    p = len(z[0])
    divisor = covariance_divisor if covariance_divisor is not None else n - ddof
    cov = [[sum(z[i][j] * z[i][k] for i in range(n)) / divisor for k in range(p)] for j in range(p)]
    values, vectors = jacobi_symmetric(cov)
    order = sorted(range(p), key=lambda i: (-values[i], i))
    eigenvalues = [values[i] for i in order]
    loadings = [[vectors[r][i] for i in order] for r in range(p)]
    for comp in range(p):
        col = [loadings[r][comp] for r in range(p)]
        max_abs = max(abs(v) for v in col)
        first = next(i for i, v in enumerate(col) if abs(v) == max_abs)
        if col[first] < 0:
            for r in range(p):
                loadings[r][comp] *= -1.0
    scores = matmul(z, loadings)
    total = sum(eigenvalues)
    ratios = [value / total if total else 0.0 for value in eigenvalues]
    return {
        "means": means,
        "scales": scales,
        "standardized": z,
        "eigenvalues": eigenvalues,
        "explained_ratios": ratios,
        "loadings": loadings,
        "scores": scores,
    }


def squared_distance(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def kmeans_farthest_first(
    points: list[list[float]], k: int, ids: list[str] | None = None, max_iter: int = 1000
) -> dict[str, Any]:
    if ids is None:
        ids = [str(i) for i in range(len(points))]
    centers_idx = [0]
    while len(centers_idx) < k:
        best_i = None
        best_dist = -1.0
        for i, point in enumerate(points):
            if i in centers_idx:
                continue
            dist = min(squared_distance(point, points[c]) for c in centers_idx)
            if dist > best_dist or (dist == best_dist and ids[i] < ids[best_i]):
                best_i = i
                best_dist = dist
        centers_idx.append(best_i)
    centers = [points[i][:] for i in centers_idx]
    labels = [0] * len(points)
    for iteration in range(1, max_iter + 1):
        old = labels[:]
        for i, point in enumerate(points):
            labels[i] = min(range(k), key=lambda c: (squared_distance(point, centers[c]), c))
        for c in range(k):
            members = [points[i] for i, label in enumerate(labels) if label == c]
            if not members:
                farthest = max(
                    range(len(points)),
                    key=lambda i: (squared_distance(points[i], centers[labels[i]]), -i),
                )
                labels[farthest] = c
                members = [points[farthest]]
            centers[c] = [sum(row[j] for row in members) / len(members) for j in range(len(points[0]))]
        if labels == old:
            return {"labels": [x + 1 for x in labels], "centers": centers, "iterations": iteration}
    return {"labels": [x + 1 for x in labels], "centers": centers, "iterations": max_iter}


def adjusted_rand_index(labels_a: list[Any], labels_b: list[Any]) -> float:
    n = len(labels_a)
    if n != len(labels_b):
        raise ValueError("label lengths differ")
    if n < 2:
        return 1.0
    table: dict[tuple[Any, Any], int] = {}
    a_count: dict[Any, int] = {}
    b_count: dict[Any, int] = {}
    for a, b in zip(labels_a, labels_b):
        table[(a, b)] = table.get((a, b), 0) + 1
        a_count[a] = a_count.get(a, 0) + 1
        b_count[b] = b_count.get(b, 0) + 1

    def comb2(x: int) -> float:
        return x * (x - 1) / 2.0

    sum_table = sum(comb2(v) for v in table.values())
    sum_a = sum(comb2(v) for v in a_count.values())
    sum_b = sum(comb2(v) for v in b_count.values())
    total = comb2(n)
    expected = sum_a * sum_b / total if total else 0.0
    denom = 0.5 * (sum_a + sum_b) - expected
    return (sum_table - expected) / denom if denom else 1.0


def silhouette(points: list[list[float]], labels: list[Any]) -> float:
    clusters: dict[Any, list[int]] = {}
    for i, label in enumerate(labels):
        clusters.setdefault(label, []).append(i)
    values = []
    for i, point in enumerate(points):
        own = clusters[labels[i]]
        if len(own) == 1:
            values.append(0.0)
            continue
        a = sum(math.sqrt(squared_distance(point, points[j])) for j in own if j != i) / (len(own) - 1)
        b = min(
            sum(math.sqrt(squared_distance(point, points[j])) for j in idxs) / len(idxs)
            for label, idxs in clusters.items()
            if label != labels[i]
        )
        values.append((b - a) / max(a, b) if max(a, b) else 0.0)
    return sum(values) / len(values)


def shapley_values(effects_by_mask: dict[int, float], m: int) -> list[float]:
    factorial = math.factorial
    denom = factorial(m)
    values = []
    for j in range(m):
        phi = 0.0
        bit = 1 << j
        for mask, base in effects_by_mask.items():
            if mask & bit:
                continue
            size = mask.bit_count()
            weight = factorial(size) * factorial(m - size - 1) / denom
            phi += weight * (effects_by_mask[mask | bit] - base)
        values.append(phi)
    return values


def powerset_masks(m: int) -> Iterable[int]:
    return range(1 << m)


def combinations_in_declared_order(values: list[Any], sizes: Iterable[int]) -> list[tuple[Any, ...]]:
    result = []
    for size in sizes:
        result.extend(itertools.combinations(values, size))
    return result
