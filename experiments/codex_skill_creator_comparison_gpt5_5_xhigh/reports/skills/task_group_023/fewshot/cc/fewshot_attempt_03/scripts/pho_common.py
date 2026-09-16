#!/usr/bin/env python3
"""Standard-library helpers for Public Health Observatory audit solvers.

The module is intentionally generic: it contains no task-specific rows,
coefficients, dates, geography lists, decisions, or answer values.
"""

from __future__ import annotations

import csv
import io
import math
import urllib.parse
import urllib.request
from collections import Counter
from typing import Any, Iterable


WEBB_WEIGHTS = [
    -math.sqrt(3 / 2),
    -1.0,
    -math.sqrt(1 / 2),
    math.sqrt(1 / 2),
    1.0,
    math.sqrt(3 / 2),
]


def fetch_csv(base_url: str, dataset: str) -> list[dict[str, str]]:
    url = urllib.parse.urljoin(
        base_url.rstrip("/") + "/",
        "download?" + urllib.parse.urlencode({"dataset": dataset, "format": "csv"}),
    )
    with urllib.request.urlopen(url) as response:
        text = response.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def parse_number(value: Any) -> float | None:
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


def is_unavailable(row: dict[str, Any], value_field: str = "value", invalid_flags: Iterable[str] = ()) -> bool:
    value = parse_number(row.get(value_field))
    if value is None:
        return True
    if str(row.get("suppression_flag", "0")).strip() in {"1", "true", "TRUE"}:
        return True
    flag = str(row.get("quality_flag", "")).strip()
    return bool(flag and flag in set(invalid_flags))


def select_latest(
    rows: Iterable[dict[str, Any]],
    key_fields: list[str],
    filters: dict[str, Any] | None = None,
    id_field: str | None = None,
    id_tie: str = "min",
) -> dict[tuple[Any, ...], dict[str, Any]]:
    """Select one release row per key by revision, release timestamp, and id."""
    filters = filters or {}
    selected: dict[tuple[Any, ...], dict[str, Any]] = {}

    def id_rank(text: str) -> str:
        if id_tie == "max":
            return text
        return "".join(chr(255 - ord(ch)) for ch in text)

    def rank(row: dict[str, Any]) -> tuple[Any, ...]:
        revision = parse_number(row.get("revision"))
        return (
            -math.inf if revision is None else revision,
            str(row.get("released_at", "")),
            id_rank(str(row.get(id_field, ""))) if id_field else "",
        )

    for row in rows:
        if any(str(row.get(k)) != str(v) for k, v in filters.items()):
            continue
        key = tuple(row.get(k) for k in key_fields)
        if key not in selected or rank(row) > rank(selected[key]):
            selected[key] = row
    return selected


def transpose(a: list[list[float]]) -> list[list[float]]:
    return [list(col) for col in zip(*a)]


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    bt = transpose(b)
    return [[dot(row, col) for col in bt] for row in a]


def matvec(a: list[list[float]], x: list[float]) -> list[float]:
    return [dot(row, x) for row in a]


def outer(a: list[float], b: list[float]) -> list[list[float]]:
    return [[x * y for y in b] for x in a]


def add_matrix(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[x + y for x, y in zip(ar, br)] for ar, br in zip(a, b)]


def solve_linear(a: list[list[float]], b: list[float], ridge: float = 0.0) -> list[float]:
    n = len(a)
    aug = []
    for i, row in enumerate(a):
        aug.append([float(v) + (ridge if i == j else 0.0) for j, v in enumerate(row)] + [float(b[i])])
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-14:
            if ridge == 0.0:
                return solve_linear(a, b, ridge=1e-10)
            raise ValueError("singular matrix")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [v / scale for v in aug[col]]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor:
                aug[r] = [v - factor * p for v, p in zip(aug[r], aug[col])]
    return [row[-1] for row in aug]


def inverse(a: list[list[float]]) -> list[list[float]]:
    n = len(a)
    cols = []
    for j in range(n):
        e = [0.0] * n
        e[j] = 1.0
        cols.append(solve_linear(a, e))
    return transpose(cols)


def add_intercept(x: list[list[float]]) -> list[list[float]]:
    return [[1.0] + list(row) for row in x]


def ols_fit(x: list[list[float]], y: list[float]) -> tuple[list[float], list[float], list[float]]:
    xt = transpose(x)
    beta = solve_linear(matmul(xt, x), matvec(xt, y))
    fitted = matvec(x, beta)
    resid = [yi - fi for yi, fi in zip(y, fitted)]
    return beta, fitted, resid


def wls_fit(
    x: list[list[float]], y: list[float], weights: list[float]
) -> tuple[list[float], list[float], list[float]]:
    sw = [math.sqrt(w) for w in weights]
    xw = [[v * s for v in row] for row, s in zip(x, sw)]
    yw = [yi * s for yi, s in zip(y, sw)]
    beta = solve_linear(matmul(transpose(xw), xw), matvec(transpose(xw), yw))
    fitted = matvec(x, beta)
    resid = [yi - fi for yi, fi in zip(y, fitted)]
    return beta, fitted, resid


def hc3_cov(x: list[list[float]], resid: list[float], weights: list[float] | None = None) -> list[list[float]]:
    if weights is None:
        xw = [list(row) for row in x]
        ew = list(resid)
    else:
        sw = [math.sqrt(w) for w in weights]
        xw = [[v * s for v in row] for row, s in zip(x, sw)]
        ew = [e * s for e, s in zip(resid, sw)]
    inv = inverse(matmul(transpose(xw), xw))
    meat = [[0.0 for _ in inv] for _ in inv]
    for row, err in zip(xw, ew):
        h = dot(row, matvec(inv, row))
        scale = err * err / max((1 - h) ** 2, 1e-30)
        meat = add_matrix(meat, [[scale * v for v in r] for r in outer(row, row)])
    return matmul(matmul(inv, meat), inv)


def cr1_cov(
    x: list[list[float]], resid: list[float], clusters: list[Any], weights: list[float] | None = None
) -> list[list[float]]:
    if weights is None:
        xw = [list(row) for row in x]
        ew = list(resid)
    else:
        sw = [math.sqrt(w) for w in weights]
        xw = [[v * s for v in row] for row, s in zip(x, sw)]
        ew = [e * s for e, s in zip(resid, sw)]
    inv = inverse(matmul(transpose(xw), xw))
    groups = list(dict.fromkeys(clusters))
    meat = [[0.0 for _ in inv] for _ in inv]
    for group in groups:
        score = [0.0] * len(xw[0])
        for row, err, cluster in zip(xw, ew, clusters):
            if cluster == group:
                score = [s + v * err for s, v in zip(score, row)]
        meat = add_matrix(meat, outer(score, score))
    n, k, g = len(x), len(x[0]), len(groups)
    factor = (g / max(g - 1, 1)) * ((n - 1) / max(n - k, 1))
    return [[factor * v for v in row] for row in matmul(matmul(inv, meat), inv)]


def double_demean(values: list[list[float]], entities: list[Any], times: list[Any]) -> list[list[float]]:
    cols = len(values[0])
    grand = [sum(row[j] for row in values) / len(values) for j in range(cols)]
    out = []
    for i, row in enumerate(values):
        ent_rows = [r for r, e in zip(values, entities) if e == entities[i]]
        time_rows = [r for r, t in zip(values, times) if t == times[i]]
        ent_mean = [sum(r[j] for r in ent_rows) / len(ent_rows) for j in range(cols)]
        time_mean = [sum(r[j] for r in time_rows) / len(time_rows) for j in range(cols)]
        out.append([row[j] - ent_mean[j] - time_mean[j] + grand[j] for j in range(cols)])
    return out


def training_standardize(
    x_train: list[list[float]],
    x_other: list[list[float]] | None = None,
    *,
    ddof: int = 0,
    weights: list[float] | None = None,
) -> tuple[list[list[float]], list[list[float]] | None, list[float], list[float]]:
    cols = len(x_train[0])
    if weights is None:
        mu = [sum(row[j] for row in x_train) / len(x_train) for j in range(cols)]
        denom = max(len(x_train) - ddof, 1)
        sigma = [
            math.sqrt(sum((row[j] - mu[j]) ** 2 for row in x_train) / denom) or 1.0 for j in range(cols)
        ]
    else:
        wsum = sum(weights)
        mu = [sum(w * row[j] for row, w in zip(x_train, weights)) / wsum for j in range(cols)]
        sigma = [
            math.sqrt(sum(w * (row[j] - mu[j]) ** 2 for row, w in zip(x_train, weights)) / wsum) or 1.0
            for j in range(cols)
        ]

    def scale(rows: list[list[float]]) -> list[list[float]]:
        return [[(row[j] - mu[j]) / sigma[j] for j in range(cols)] for row in rows]

    return scale(x_train), None if x_other is None else scale(x_other), mu, sigma


def ridge_cd(x: list[list[float]], y: list[float], lam: float, max_sweeps: int = 10000, tol: float = 1e-10) -> tuple[float, list[float]]:
    n, p = len(x), len(x[0])
    intercept = sum(y) / n
    yc = [v - intercept for v in y]
    beta = [0.0] * p
    for _ in range(max_sweeps):
        old = beta[:]
        fitted = matvec(x, beta)
        for j in range(p):
            numerator = sum(row[j] * (yc[i] - fitted[i] + row[j] * beta[j]) for i, row in enumerate(x))
            denominator = sum(row[j] ** 2 for row in x) + n * lam
            beta[j] = numerator / max(denominator, 1e-30)
            fitted = matvec(x, beta)
        if max(abs(a - b) for a, b in zip(beta, old)) < tol:
            break
    return intercept, beta


def soft_threshold(value: float, threshold: float) -> float:
    if value > threshold:
        return value - threshold
    if value < -threshold:
        return value + threshold
    return 0.0


def elastic_net_cd(
    x: list[list[float]],
    y: list[float],
    alpha: float,
    l1_ratio: float,
    weights: list[float] | None = None,
    max_sweeps: int = 20000,
    tol: float = 1e-10,
) -> tuple[float, list[float], int]:
    n, p = len(x), len(x[0])
    weights = [1.0] * n if weights is None else list(weights)
    wsum = sum(weights)
    intercept = sum(w * yi for w, yi in zip(weights, y)) / wsum
    beta = [0.0] * p
    for sweep in range(1, max_sweeps + 1):
        old = beta[:]
        fitted = matvec(x, beta)
        residual = [y[i] - intercept - fitted[i] for i in range(n)]
        intercept += sum(w * r for w, r in zip(weights, residual)) / wsum
        for j in range(p):
            fitted = matvec(x, beta)
            partial = [y[i] - intercept - fitted[i] + x[i][j] * beta[j] for i in range(n)]
            rho = sum(weights[i] * x[i][j] * partial[i] for i in range(n)) / wsum
            denom = sum(weights[i] * x[i][j] ** 2 for i in range(n)) / wsum + alpha * (1 - l1_ratio)
            beta[j] = soft_threshold(rho, alpha * l1_ratio) / max(denom, 1e-30)
        if max(abs(a - b) for a, b in zip(beta, old)) < tol:
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
        x &= 0xFFFFFFFF
        self.state = x
        return x

    def sign(self) -> int:
        return 1 if (self.next() & 1) else -1


class PCG32:
    def __init__(self, seed: int, stream: int):
        self.state = 0
        self.inc = ((stream << 1) | 1) & 0xFFFFFFFFFFFFFFFF
        self.next()
        self.state = (self.state + seed) & 0xFFFFFFFFFFFFFFFF
        self.next()

    @staticmethod
    def _rotr32(value: int, rot: int) -> int:
        rot &= 31
        return ((value >> rot) | (value << ((-rot) & 31))) & 0xFFFFFFFF

    def next(self) -> int:
        old = self.state
        self.state = (old * 6364136223846793005 + self.inc) & 0xFFFFFFFFFFFFFFFF
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = old >> 59
        return self._rotr32(xorshifted, rot)

    def webb_index(self) -> int:
        return self.next() % 6


def nearest_rank(values: Iterable[float], p: float) -> float:
    xs = sorted(values)
    if not xs:
        raise ValueError("empty values")
    rank = min(len(xs), math.ceil(p * len(xs)))
    return float(xs[rank - 1])


def type7_quantile(values: Iterable[float], p: float) -> float:
    xs = sorted(values)
    if not xs:
        raise ValueError("empty values")
    if len(xs) == 1:
        return float(xs[0])
    h = (len(xs) - 1) * p
    j = math.floor(h)
    gamma = h - j
    return float((1 - gamma) * xs[j] + gamma * xs[min(j + 1, len(xs) - 1)])


def jacobi_eigh(a: list[list[float]], tol: float = 1e-12, max_iter: int = 10000) -> tuple[list[float], list[list[float]]]:
    n = len(a)
    mat = [row[:] for row in a]
    vec = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(max_iter):
        p, q, max_abs = 0, 1, 0.0
        for i in range(n):
            for j in range(i + 1, n):
                v = abs(mat[i][j])
                if v > max_abs:
                    p, q, max_abs = i, j, v
        if max_abs < tol:
            break
        if mat[p][q] == 0:
            continue
        tau = (mat[q][q] - mat[p][p]) / (2 * mat[p][q])
        sign = 1.0 if tau >= 0 else -1.0
        t = sign / (abs(tau) + math.sqrt(1 + tau * tau))
        c = 1 / math.sqrt(1 + t * t)
        s = t * c
        app, aqq, apq = mat[p][p], mat[q][q], mat[p][q]
        mat[p][p] = c * c * app - 2 * s * c * apq + s * s * aqq
        mat[q][q] = s * s * app + 2 * s * c * apq + c * c * aqq
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
    return values, vectors


def covariance_pca(
    z: list[list[float]], components: int | None = None, ddof: int = 1
) -> tuple[list[float], list[list[float]], list[list[float]]]:
    n, p = len(z), len(z[0])
    cov = [[sum(row[i] * row[j] for row in z) / max(n - ddof, 1) for j in range(p)] for i in range(p)]
    values, vectors = jacobi_eigh(cov)
    order = sorted(range(p), key=lambda i: (-values[i], i))
    if components is not None:
        order = order[:components]
    values = [values[i] for i in order]
    loadings = [vectors[i][:] for i in order]
    for loading in loadings:
        idx = max(range(len(loading)), key=lambda i: (abs(loading[i]), -i))
        if loading[idx] < 0:
            for j in range(len(loading)):
                loading[j] *= -1
    scores = [[dot(row, loading) for loading in loadings] for row in z]
    return values, loadings, scores


def squared_distance(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def farthest_first_kmeans(
    x: list[list[float]], labels_for_ties: list[Any], k: int, max_iter: int = 1000
) -> tuple[list[list[float]], list[int], int]:
    first = min(range(len(x)), key=lambda i: str(labels_for_ties[i]))
    centers = [x[first][:]]
    while len(centers) < k:
        best = max(
            range(len(x)),
            key=lambda i: (min(squared_distance(x[i], c) for c in centers), tuple(-ord(ch) for ch in str(labels_for_ties[i]))),
        )
        centers.append(x[best][:])
    labels = [-1] * len(x)
    for iteration in range(1, max_iter + 1):
        new_labels = [
            min(range(k), key=lambda j: (squared_distance(row, centers[j]), j))
            for row in x
        ]
        if new_labels == labels:
            return centers, labels, iteration - 1
        labels = new_labels
        for j in range(k):
            members = [row for row, label in zip(x, labels) if label == j]
            if members:
                centers[j] = [sum(row[col] for row in members) / len(members) for col in range(len(x[0]))]
    return centers, labels, max_iter


def adjusted_rand_index(labels_a: Iterable[Any], labels_b: Iterable[Any]) -> float:
    pairs = list(zip(labels_a, labels_b))
    n = len(pairs)
    if n < 2:
        return 1.0
    contingency = Counter(pairs)
    count_a = Counter(a for a, _ in pairs)
    count_b = Counter(b for _, b in pairs)

    def comb2(v: int) -> float:
        return v * (v - 1) / 2

    sum_ij = sum(comb2(v) for v in contingency.values())
    sum_a = sum(comb2(v) for v in count_a.values())
    sum_b = sum(comb2(v) for v in count_b.values())
    total = comb2(n)
    expected = sum_a * sum_b / total if total else 0.0
    denom = 0.5 * (sum_a + sum_b) - expected
    if denom == 0:
        return 1.0
    return (sum_ij - expected) / denom


def rmse(y_true: list[float], y_pred: list[float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(y_true, y_pred)) / len(y_true))


def mae(y_true: list[float], y_pred: list[float]) -> float:
    return sum(abs(a - b) for a, b in zip(y_true, y_pred)) / len(y_true)


def r_squared(y_true: list[float], y_pred: list[float]) -> float:
    mean = sum(y_true) / len(y_true)
    sse = sum((a - b) ** 2 for a, b in zip(y_true, y_pred))
    sst = sum((a - mean) ** 2 for a in y_true)
    return 1 - sse / sst if sst else 0.0
