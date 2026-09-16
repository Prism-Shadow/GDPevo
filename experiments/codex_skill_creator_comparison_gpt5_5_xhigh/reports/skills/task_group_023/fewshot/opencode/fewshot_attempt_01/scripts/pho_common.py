#!/usr/bin/env python3
"""Stdlib-only helpers for Public Health Observatory audit solvers.

This module intentionally contains reusable primitives, not task-specific
answers. Bind variables, orders, thresholds, and output schemas from the active
request before calling these functions.
"""

from __future__ import annotations

import csv
import io
import json
import math
import urllib.request
from collections import defaultdict
from itertools import combinations
from typing import Any, Callable, Iterable


def read_csv_url(url: str) -> list[dict[str, str]]:
    with urllib.request.urlopen(url) as response:
        text = response.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def dataset_url(base_url: str, dataset: str) -> str:
    return base_url.rstrip("/") + f"/download?dataset={dataset}&format=csv"


def fetch_datasets(base_url: str, names: Iterable[str]) -> dict[str, list[dict[str, str]]]:
    return {name: read_csv_url(dataset_url(base_url, name)) for name in names}


def to_float(value: Any) -> float | None:
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


def to_int(value: Any) -> int | None:
    number = to_float(value)
    if number is None:
        return None
    return int(number)


def unavailable_value(record: dict[str, Any], value_field: str = "value", invalid_flags: set[str] | None = None) -> bool:
    invalid_flags = invalid_flags or {"INVALID", "INVALID_SCALE", "WITHDRAWN"}
    if to_float(record.get(value_field)) is None:
        return True
    if str(record.get("suppression_flag", "")).strip() in {"1", "true", "TRUE", "Y", "YES"}:
        return True
    return str(record.get("quality_flag", "")).strip() in invalid_flags


def group_key(record: dict[str, Any], keys: Iterable[str]) -> tuple[Any, ...]:
    return tuple(record.get(key) for key in keys)


def select_records(
    rows: Iterable[dict[str, Any]],
    key_fields: Iterable[str],
    priority: list[tuple[str, str]],
) -> dict[tuple[Any, ...], dict[str, Any]]:
    """Select one row per key using priority like [('max','revision'), ('max','released_at')].

    Directions are 'max', 'min', or 'lexmax'/'lexmin'. Numeric-looking values are
    compared numerically for max/min; timestamps and ids compare as strings.
    """

    def priority_key(row: dict[str, Any]) -> tuple[Any, ...]:
        out = []
        for direction, field in priority:
            raw = row.get(field)
            num = to_float(raw)
            val: Any = num if num is not None else "" if raw is None else str(raw)
            if direction in {"max", "lexmax"}:
                out.append(val)
            elif direction in {"min", "lexmin"}:
                if isinstance(val, (int, float)):
                    out.append(-val)
                else:
                    out.append("".join(chr(0x10FFFF - ord(ch)) for ch in val))
            else:
                raise ValueError(f"unknown priority direction: {direction}")
        return tuple(out)

    selected: dict[tuple[Any, ...], dict[str, Any]] = {}
    scores: dict[tuple[Any, ...], tuple[Any, ...]] = {}
    for row in rows:
        key = group_key(row, key_fields)
        score = priority_key(row)
        if key not in selected or score > scores[key]:
            selected[key] = row
            scores[key] = score
    return selected


def mean(xs: Iterable[float]) -> float:
    vals = list(xs)
    return sum(vals) / len(vals)


def variance(xs: Iterable[float], ddof: int = 0) -> float:
    vals = list(xs)
    mu = mean(vals)
    den = len(vals) - ddof
    if den <= 0:
        return 0.0
    return sum((x - mu) ** 2 for x in vals) / den


def sd(xs: Iterable[float], ddof: int = 0) -> float:
    return math.sqrt(max(0.0, variance(xs, ddof)))


def transpose(a: list[list[float]]) -> list[list[float]]:
    return [list(col) for col in zip(*a)]


def matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    bt = transpose(b)
    return [[sum(x * y for x, y in zip(row, col)) for col in bt] for row in a]


def matvec(a: list[list[float]], x: list[float]) -> list[float]:
    return [sum(ai * xi for ai, xi in zip(row, x)) for row in a]


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def identity(n: int) -> list[list[float]]:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def solve(a: list[list[float]], b: list[float], ridge: float = 0.0) -> list[float]:
    n = len(a)
    aug = []
    for i, row in enumerate(a):
        aug.append([float(x) + (ridge if i == j else 0.0) for j, x in enumerate(row)] + [float(b[i])])
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-15:
            raise ValueError("singular matrix")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        div = aug[col][col]
        aug[col] = [x / div for x in aug[col]]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor:
                aug[r] = [x - factor * y for x, y in zip(aug[r], aug[col])]
    return [row[-1] for row in aug]


def inverse(a: list[list[float]], ridge: float = 0.0) -> list[list[float]]:
    n = len(a)
    cols = [solve(a, [1.0 if i == j else 0.0 for i in range(n)], ridge=ridge) for j in range(n)]
    return transpose(cols)


def xtx_xty(x: list[list[float]], y: list[float]) -> tuple[list[list[float]], list[float]]:
    p = len(x[0])
    xtx = [[0.0] * p for _ in range(p)]
    xty = [0.0] * p
    for row, yi in zip(x, y):
        for j in range(p):
            xty[j] += row[j] * yi
            for k in range(p):
                xtx[j][k] += row[j] * row[k]
    return xtx, xty


def ols(x: list[list[float]], y: list[float]) -> dict[str, Any]:
    xtx, xty = xtx_xty(x, y)
    beta = solve(xtx, xty)
    fitted = matvec(x, beta)
    resid = [yi - fi for yi, fi in zip(y, fitted)]
    return {"beta": beta, "fitted": fitted, "resid": resid, "xtx": xtx}


def wls(x: list[list[float]], y: list[float], w: list[float]) -> dict[str, Any]:
    sw = [math.sqrt(max(0.0, wi)) for wi in w]
    xw = [[v * s for v in row] for row, s in zip(x, sw)]
    yw = [yi * s for yi, s in zip(y, sw)]
    fit = ols(xw, yw)
    beta = fit["beta"]
    fitted = matvec(x, beta)
    resid = [yi - fi for yi, fi in zip(y, fitted)]
    fit.update({"beta": beta, "fitted": fitted, "resid": resid, "xw": xw, "yw": yw})
    return fit


def covariance_hc3(x: list[list[float]], resid: list[float], xtx_inv: list[list[float]]) -> list[list[float]]:
    p = len(x[0])
    meat = [[0.0] * p for _ in range(p)]
    for row, ei in zip(x, resid):
        h = dot(row, matvec(xtx_inv, row))
        scale = (ei / max(1e-15, 1.0 - h)) ** 2
        for j in range(p):
            for k in range(p):
                meat[j][k] += row[j] * row[k] * scale
    return matmul(matmul(xtx_inv, meat), xtx_inv)


def covariance_cr1(
    x: list[list[float]],
    resid: list[float],
    clusters: list[Any],
    xtx_inv: list[list[float]],
) -> list[list[float]]:
    p = len(x[0])
    scores: dict[Any, list[float]] = defaultdict(lambda: [0.0] * p)
    for row, ei, cluster in zip(x, resid, clusters):
        for j in range(p):
            scores[cluster][j] += row[j] * ei
    meat = [[0.0] * p for _ in range(p)]
    for score in scores.values():
        for j in range(p):
            for k in range(p):
                meat[j][k] += score[j] * score[k]
    n = len(x)
    g = len(scores)
    k = p
    scale = (g / (g - 1)) * ((n - 1) / (n - k)) if g > 1 and n > k else 1.0
    cov = matmul(matmul(xtx_inv, meat), xtx_inv)
    return [[scale * v for v in row] for row in cov]


def standardize_train(
    train_x: list[list[float]],
    other_x: list[list[float]] | None = None,
    ddof: int = 0,
) -> tuple[list[list[float]], list[list[float]] | None, list[float], list[float]]:
    cols = transpose(train_x)
    mus = [mean(col) for col in cols]
    sigmas = [sd(col, ddof=ddof) or 1.0 for col in cols]

    def apply(rows: list[list[float]]) -> list[list[float]]:
        return [[(v - mus[j]) / sigmas[j] for j, v in enumerate(row)] for row in rows]

    return apply(train_x), apply(other_x) if other_x is not None else None, mus, sigmas


def soft_threshold(a: float, t: float) -> float:
    if a > t:
        return a - t
    if a < -t:
        return a + t
    return 0.0


def ridge_cd(
    x: list[list[float]],
    y: list[float],
    lam: float,
    max_iter: int = 10000,
    tol: float = 1e-12,
) -> tuple[float, list[float]]:
    n = len(y)
    p = len(x[0])
    intercept = mean(y)
    beta = [0.0] * p
    for _ in range(max_iter):
        max_delta = 0.0
        residual = [y[i] - intercept - dot(x[i], beta) for i in range(n)]
        intercept += mean(residual)
        for j in range(p):
            num = 0.0
            den = n * lam
            old = beta[j]
            for i in range(n):
                partial = y[i] - intercept - sum(x[i][k] * beta[k] for k in range(p) if k != j)
                num += x[i][j] * partial
                den += x[i][j] ** 2
            beta[j] = num / den if den else 0.0
            max_delta = max(max_delta, abs(beta[j] - old))
        if max_delta < tol:
            break
    return intercept, beta


def elastic_net_cd(
    x: list[list[float]],
    y: list[float],
    lam: float,
    alpha: float,
    weights: list[float] | None = None,
    max_iter: int = 10000,
    tol: float = 1e-12,
) -> tuple[float, list[float], int]:
    n = len(y)
    p = len(x[0])
    w = weights or [1.0] * n
    wsum = sum(w)
    intercept = sum(wi * yi for wi, yi in zip(w, y)) / wsum
    beta = [0.0] * p
    cycles = 0
    for cycles in range(1, max_iter + 1):
        residual = [y[i] - intercept - dot(x[i], beta) for i in range(n)]
        intercept += sum(w[i] * residual[i] for i in range(n)) / wsum
        max_delta = 0.0
        for j in range(p):
            old = beta[j]
            rho = 0.0
            x2 = 0.0
            for i in range(n):
                partial = y[i] - intercept - sum(x[i][k] * beta[k] for k in range(p) if k != j)
                rho += w[i] * x[i][j] * partial
                x2 += w[i] * x[i][j] ** 2
            rho /= wsum
            x2 /= wsum
            beta[j] = soft_threshold(rho, lam * alpha) / (x2 + lam * (1.0 - alpha))
            max_delta = max(max_delta, abs(beta[j] - old))
        if max_delta < tol:
            break
    return intercept, beta, cycles


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
        return ((value >> rot) | ((value << ((-rot) & 31)) & 0xFFFFFFFF)) & 0xFFFFFFFF

    def next(self) -> int:
        old = self.state
        self.state = (old * 6364136223846793005 + self.inc) & 0xFFFFFFFFFFFFFFFF
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = old >> 59
        return self._rotr32(xorshifted, rot)

    def webb_index(self) -> int:
        return self.next() % 6


WEBB_WEIGHTS = [
    -math.sqrt(3.0 / 2.0),
    -1.0,
    -math.sqrt(1.0 / 2.0),
    math.sqrt(1.0 / 2.0),
    1.0,
    math.sqrt(3.0 / 2.0),
]


def rank_quantile(sorted_values: list[float], probability: float, method: str = "nearest") -> float:
    n = len(sorted_values)
    if n == 0:
        raise ValueError("empty quantile input")
    if method == "nearest":
        idx = min(n, math.ceil(probability * n)) - 1
        return sorted_values[idx]
    if method == "type7":
        h = (n - 1) * probability
        j = math.floor(h)
        gamma = h - j
        if j >= n - 1:
            return sorted_values[-1]
        return (1 - gamma) * sorted_values[j] + gamma * sorted_values[j + 1]
    raise ValueError(f"unknown quantile method: {method}")


def jacobi_eigen_symmetric(a: list[list[float]], tol: float = 1e-12, max_steps: int = 100000) -> tuple[list[float], list[list[float]]]:
    n = len(a)
    mat = [row[:] for row in a]
    vec = identity(n)
    for _ in range(max_steps):
        p, q, max_abs = 0, 1, 0.0
        for i in range(n):
            for j in range(i + 1, n):
                val = abs(mat[i][j])
                if val > max_abs:
                    p, q, max_abs = i, j, val
        if max_abs < tol:
            break
        app, aqq, apq = mat[p][p], mat[q][q], mat[p][q]
        tau = (aqq - app) / (2.0 * apq)
        sign = 1.0 if tau >= 0 else -1.0
        t = sign / (abs(tau) + math.sqrt(1.0 + tau * tau))
        c = 1.0 / math.sqrt(1.0 + t * t)
        s = t * c
        for k in range(n):
            if k not in (p, q):
                mkp, mkq = mat[k][p], mat[k][q]
                mat[k][p] = mat[p][k] = c * mkp - s * mkq
                mat[k][q] = mat[q][k] = s * mkp + c * mkq
        mat[p][p] = c * c * app - 2 * s * c * apq + s * s * aqq
        mat[q][q] = s * s * app + 2 * s * c * apq + c * c * aqq
        mat[p][q] = mat[q][p] = 0.0
        for k in range(n):
            vkp, vkq = vec[k][p], vec[k][q]
            vec[k][p] = c * vkp - s * vkq
            vec[k][q] = s * vkp + c * vkq
    vals = [mat[i][i] for i in range(n)]
    return vals, vec


def pca_scores(z: list[list[float]], retained: int | None = None, denominator: str = "sample") -> dict[str, Any]:
    n = len(z)
    p = len(z[0])
    den = n - 1 if denominator == "sample" else n
    cov = [[sum(z[i][j] * z[i][k] for i in range(n)) / den for k in range(p)] for j in range(p)]
    vals, vec_cols = jacobi_eigen_symmetric(cov)
    order = sorted(range(p), key=lambda i: (-vals[i], i))
    vals = [vals[i] for i in order]
    loadings = [[vec_cols[j][i] for j in range(p)] for i in order]
    for comp in loadings:
        pivot = min(range(len(comp)), key=lambda j: (-abs(comp[j]), j))
        if comp[pivot] < 0:
            for j in range(len(comp)):
                comp[j] *= -1.0
    retained = retained or p
    scores = [[dot(row, loadings[c]) for c in range(retained)] for row in z]
    total = sum(vals)
    return {
        "eigenvalues": vals,
        "explained": [v / total if total else 0.0 for v in vals],
        "loadings": loadings,
        "scores": scores,
    }


def squared_distance(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def kmeans_farthest(
    points: list[list[float]],
    ids: list[str],
    k: int,
    max_iter: int = 1000,
) -> dict[str, Any]:
    first = min(range(len(ids)), key=lambda i: ids[i])
    centers = [points[first][:]]
    center_ids = [ids[first]]
    while len(centers) < k:
        idx = max(
            range(len(points)),
            key=lambda i: (min(squared_distance(points[i], c) for c in centers), tuple(-ord(ch) for ch in ids[i])),
        )
        centers.append(points[idx][:])
        center_ids.append(ids[idx])
    labels = [-1] * len(points)
    iterations = 0
    for iterations in range(1, max_iter + 1):
        new_labels = []
        for point in points:
            new_labels.append(min(range(k), key=lambda c: (squared_distance(point, centers[c]), c)))
        if new_labels == labels:
            break
        labels = new_labels
        for c in range(k):
            members = [points[i] for i, lab in enumerate(labels) if lab == c]
            if members:
                centers[c] = [mean(col) for col in transpose(members)]
    return {"labels": [lab + 1 for lab in labels], "centers": centers, "initial_ids": center_ids, "iterations": iterations}


def comb2(n: int) -> float:
    return n * (n - 1) / 2.0


def adjusted_rand_index(labels_a: list[Any], labels_b: list[Any]) -> float:
    n = len(labels_a)
    table: dict[tuple[Any, Any], int] = defaultdict(int)
    rows: dict[Any, int] = defaultdict(int)
    cols: dict[Any, int] = defaultdict(int)
    for a, b in zip(labels_a, labels_b):
        table[(a, b)] += 1
        rows[a] += 1
        cols[b] += 1
    sum_ij = sum(comb2(v) for v in table.values())
    sum_i = sum(comb2(v) for v in rows.values())
    sum_j = sum(comb2(v) for v in cols.values())
    total = comb2(n)
    if total == 0:
        return 1.0
    expected = sum_i * sum_j / total
    denom = 0.5 * (sum_i + sum_j) - expected
    return 1.0 if denom == 0 else (sum_ij - expected) / denom


def silhouette(points: list[list[float]], labels: list[Any]) -> float:
    groups: dict[Any, list[int]] = defaultdict(list)
    for i, label in enumerate(labels):
        groups[label].append(i)
    values = []
    for i, point in enumerate(points):
        own = groups[labels[i]]
        if len(own) == 1:
            values.append(0.0)
            continue
        a = mean(math.sqrt(squared_distance(point, points[j])) for j in own if j != i)
        b = min(
            mean(math.sqrt(squared_distance(point, points[j])) for j in idxs)
            for label, idxs in groups.items()
            if label != labels[i]
        )
        values.append((b - a) / max(a, b) if max(a, b) else 0.0)
    return mean(values)


def round_json(value: Any, digits: int) -> Any:
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return round(value, digits)
    if isinstance(value, list):
        return [round_json(v, digits) for v in value]
    if isinstance(value, dict):
        return {k: round_json(v, digits) for k, v in value.items()}
    return value


def dump_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, separators=(",", ":"))

