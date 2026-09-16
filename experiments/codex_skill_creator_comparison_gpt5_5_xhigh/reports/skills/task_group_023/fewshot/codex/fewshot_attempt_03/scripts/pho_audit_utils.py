#!/usr/bin/env python3
"""Portable helpers for Public Health Observatory audit solvers.

This module intentionally uses only the Python standard library. It is a helper
library, not a complete solver for every registered audit.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Sequence, Tuple


MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF


def read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: str, rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str] | None = None) -> None:
    if fieldnames is None:
        keys: List[str] = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    keys.append(key)
                    seen.add(key)
        fieldnames = keys
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def download_dataset(base_url: str, dataset: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", "download")
    url = url + "?" + urllib.parse.urlencode({"dataset": dataset, "format": "csv"})
    out_path = os.path.join(out_dir, f"{dataset}.csv")
    with urllib.request.urlopen(url) as response, open(out_path, "wb") as f:
        f.write(response.read())
    return out_path


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def to_int(value: Any) -> int | None:
    f = to_float(value)
    if f is None:
        return None
    return int(f)


def unavailable(
    row: Dict[str, Any],
    value_field: str = "value",
    suppression_field: str = "suppression_flag",
    quality_field: str = "quality_flag",
    invalid_quality_flags: Iterable[str] = ("INVALID", "INVALID_SCALE", "WITHDRAWN"),
) -> bool:
    value = row.get(value_field)
    if to_float(value) is None:
        return True
    suppression = str(row.get(suppression_field, "")).strip().lower()
    if suppression in {"1", "true", "yes", "y"}:
        return True
    quality = str(row.get(quality_field, "")).strip().upper()
    return quality in {flag.upper() for flag in invalid_quality_flags}


def _priority_value(row: Dict[str, Any], field: str, kind: str) -> Any:
    value = row.get(field, "")
    if kind == "number":
        parsed = to_float(value)
        return -math.inf if parsed is None else parsed
    return str(value)


def select_latest_records(
    rows: Sequence[Dict[str, Any]],
    group_keys: Sequence[str],
    filters: Dict[str, Any] | None = None,
    priority: Sequence[Tuple[str, str, str]] = (),
) -> List[Dict[str, Any]]:
    """Filter and select one record per key.

    priority items are (field, direction, kind), where direction is "asc" or
    "desc" and kind is "number" or "string". Later records win only by this
    declared priority order.
    """

    filters = filters or {}
    grouped: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        ok = True
        for key, expected in filters.items():
            if isinstance(expected, (list, tuple, set)):
                ok = str(row.get(key, "")) in {str(item) for item in expected}
            else:
                ok = str(row.get(key, "")) == str(expected)
            if not ok:
                break
        if ok:
            grouped[tuple(row.get(key, "") for key in group_keys)].append(row)

    selected = []
    for key in sorted(grouped):
        candidates = grouped[key]

        def sort_key(row: Dict[str, Any]) -> Tuple[Any, ...]:
            parts = []
            for field, direction, kind in priority:
                value = _priority_value(row, field, kind)
                if direction == "desc":
                    if isinstance(value, (int, float)):
                        value = -value
                    else:
                        value = "".join(chr(0x10FFFF - ord(ch)) for ch in value)
                parts.append(value)
            return tuple(parts)

        selected.append(sorted(candidates, key=sort_key)[0])
    return selected


def transpose(matrix: Sequence[Sequence[float]]) -> List[List[float]]:
    return [list(col) for col in zip(*matrix)]


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def matmul(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> List[List[float]]:
    bt = transpose(b)
    return [[dot(row, col) for col in bt] for row in a]


def matvec(a: Sequence[Sequence[float]], x: Sequence[float]) -> List[float]:
    return [dot(row, x) for row in a]


def identity(n: int) -> List[List[float]]:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def inverse(matrix: Sequence[Sequence[float]], tol: float = 1e-12) -> List[List[float]]:
    n = len(matrix)
    aug = [list(map(float, matrix[i])) + identity(n)[i] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) <= tol:
            raise ValueError("singular matrix")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [v / scale for v in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            if factor:
                aug[row] = [v - factor * p for v, p in zip(aug[row], aug[col])]
    return [row[n:] for row in aug]


def solve(matrix: Sequence[Sequence[float]], rhs: Sequence[float], tol: float = 1e-12) -> List[float]:
    inv = inverse(matrix, tol=tol)
    return matvec(inv, rhs)


def weighted_rows(x: Sequence[Sequence[float]], y: Sequence[float], weights: Sequence[float] | None = None) -> Tuple[List[List[float]], List[float]]:
    if weights is None:
        return [list(row) for row in x], list(y)
    xw: List[List[float]] = []
    yw: List[float] = []
    for row, yi, wi in zip(x, y, weights):
        s = math.sqrt(float(wi))
        xw.append([s * v for v in row])
        yw.append(s * yi)
    return xw, yw


def ols_coefficients(x: Sequence[Sequence[float]], y: Sequence[float], weights: Sequence[float] | None = None) -> List[float]:
    xw, yw = weighted_rows(x, y, weights)
    xt = transpose(xw)
    return solve(matmul(xt, xw), matvec(xt, yw))


def residuals(x: Sequence[Sequence[float]], y: Sequence[float], beta: Sequence[float]) -> List[float]:
    return [yi - dot(row, beta) for row, yi in zip(x, y)]


def rmse(errors: Sequence[float]) -> float:
    return math.sqrt(sum(e * e for e in errors) / len(errors))


def mae(errors: Sequence[float]) -> float:
    return sum(abs(e) for e in errors) / len(errors)


def hc3_covariance(
    x: Sequence[Sequence[float]],
    y: Sequence[float],
    beta: Sequence[float],
    weights: Sequence[float] | None = None,
) -> List[List[float]]:
    xw, _ = weighted_rows(x, y, weights)
    weighted_y = [math.sqrt(w) * yi for yi, w in zip(y, weights)] if weights is not None else list(y)
    xt = transpose(xw)
    bread = inverse(matmul(xt, xw))
    fitted_w = matvec(xw, beta)
    meat = [[0.0 for _ in beta] for _ in beta]
    for row, yi, fit in zip(xw, weighted_y, fitted_w):
        h = dot(row, matvec(bread, row))
        denom = max((1.0 - h) ** 2, 1e-30)
        scale = (yi - fit) ** 2 / denom
        for i in range(len(beta)):
            for j in range(len(beta)):
                meat[i][j] += row[i] * row[j] * scale
    return matmul(matmul(bread, meat), bread)


def cr1_covariance(
    x: Sequence[Sequence[float]],
    y: Sequence[float],
    beta: Sequence[float],
    clusters: Sequence[Any],
    weights: Sequence[float] | None = None,
) -> List[List[float]]:
    xw, _ = weighted_rows(x, y, weights)
    ew = []
    for row, yi, wi in zip(x, y, weights or [1.0] * len(y)):
        ew.append(math.sqrt(wi) * (yi - dot(row, beta)))
    xt = transpose(xw)
    bread = inverse(matmul(xt, xw))
    k = len(beta)
    scores: Dict[Any, List[float]] = {}
    for row, err, cluster in zip(xw, ew, clusters):
        score = scores.setdefault(cluster, [0.0] * k)
        for j in range(k):
            score[j] += row[j] * err
    meat = [[0.0 for _ in range(k)] for _ in range(k)]
    for score in scores.values():
        for i in range(k):
            for j in range(k):
                meat[i][j] += score[i] * score[j]
    n = len(y)
    g = len(scores)
    factor = (g / (g - 1)) * ((n - 1) / (n - k))
    meat = [[factor * v for v in row] for row in meat]
    return matmul(matmul(bread, meat), bread)


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


def regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def student_t_cdf(t: float, df: float) -> float:
    x = df / (df + t * t)
    ib = regularized_incomplete_beta(df / 2.0, 0.5, x)
    return 1.0 - 0.5 * ib if t >= 0 else 0.5 * ib


def two_sided_t_pvalue(t: float, df: float) -> float:
    cdf = student_t_cdf(abs(t), df)
    return max(0.0, min(1.0, 2.0 * (1.0 - cdf)))


def quantile_nearest_rank(values: Sequence[float], p: float) -> float:
    xs = sorted(values)
    if not xs:
        raise ValueError("empty quantile input")
    index = min(len(xs), math.ceil(p * len(xs))) - 1
    return xs[index]


def quantile_type7(values: Sequence[float], p: float) -> float:
    xs = sorted(values)
    if not xs:
        raise ValueError("empty quantile input")
    if len(xs) == 1:
        return xs[0]
    h = (len(xs) - 1) * p
    j = math.floor(h)
    gamma = h - j
    if j >= len(xs) - 1:
        return xs[-1]
    return (1.0 - gamma) * xs[j] + gamma * xs[j + 1]


def xorshift32_next(state: int) -> int:
    state &= MASK32
    state ^= (state << 13) & MASK32
    state &= MASK32
    state ^= (state >> 17) & MASK32
    state &= MASK32
    state ^= (state << 5) & MASK32
    return state & MASK32


def xorshift32_signs(seed: int, cluster_count: int, replicates: int) -> Tuple[List[List[int]], int]:
    state = seed & MASK32
    rows: List[List[int]] = []
    for _ in range(replicates):
        signs = []
        for _ in range(cluster_count):
            state = xorshift32_next(state)
            signs.append(1 if state & 1 else -1)
        rows.append(signs)
    return rows, state


class PCG32:
    def __init__(self, seed: int, stream: int):
        self.state = 0
        self.inc = ((stream << 1) | 1) & MASK64
        self.next()
        self.state = (self.state + seed) & MASK64
        self.next()

    def next(self) -> int:
        old = self.state
        self.state = (old * 6364136223846793005 + self.inc) & MASK64
        xorshifted = (((old >> 18) ^ old) >> 27) & MASK32
        rot = (old >> 59) & 31
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & MASK32


def pcg32_webb_indices(seed: int, stream: int, cluster_count: int, replicates: int) -> Tuple[List[List[int]], int]:
    rng = PCG32(seed, stream)
    rows: List[List[int]] = []
    for _ in range(replicates):
        rows.append([rng.next() % 6 for _ in range(cluster_count)])
    return rows, rng.state


def standardize_columns(x: Sequence[Sequence[float]], ddof: int = 1) -> Tuple[List[List[float]], List[float], List[float]]:
    n = len(x)
    p = len(x[0]) if n else 0
    means = [sum(row[j] for row in x) / n for j in range(p)]
    denom = max(1, n - ddof)
    sds = []
    for j in range(p):
        var = sum((row[j] - means[j]) ** 2 for row in x) / denom
        sd = math.sqrt(max(var, 0.0))
        sds.append(sd if sd > 0 else 1.0)
    z = [[(row[j] - means[j]) / sds[j] for j in range(p)] for row in x]
    return z, means, sds


def jacobi_eigen_symmetric(matrix: Sequence[Sequence[float]], tol: float = 1e-12, max_steps: int = 100000) -> Tuple[List[float], List[List[float]]]:
    n = len(matrix)
    a = [list(map(float, row)) for row in matrix]
    v = identity(n)
    for _ in range(max_steps):
        p, q = 0, 1
        best = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                val = abs(a[i][j])
                if val > best:
                    best, p, q = val, i, j
        if best < tol:
            break
        if abs(a[p][q]) < tol:
            continue
        tau = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
        sign = 1.0 if tau >= 0 else -1.0
        t = sign / (abs(tau) + math.sqrt(1.0 + tau * tau))
        c = 1.0 / math.sqrt(1.0 + t * t)
        s = t * c
        app = a[p][p]
        aqq = a[q][q]
        apq = a[p][q]
        a[p][p] = c * c * app - 2 * s * c * apq + s * s * aqq
        a[q][q] = s * s * app + 2 * s * c * apq + c * c * aqq
        a[p][q] = a[q][p] = 0.0
        for r in range(n):
            if r in (p, q):
                continue
            arp = a[r][p]
            arq = a[r][q]
            a[r][p] = a[p][r] = c * arp - s * arq
            a[r][q] = a[q][r] = s * arp + c * arq
        for r in range(n):
            vrp = v[r][p]
            vrq = v[r][q]
            v[r][p] = c * vrp - s * vrq
            v[r][q] = s * vrp + c * vrq
    eigenvalues = [a[i][i] for i in range(n)]
    eigenvectors = [[v[i][j] for i in range(n)] for j in range(n)]
    return eigenvalues, eigenvectors


def pca(
    x: Sequence[Sequence[float]],
    ddof: int = 1,
    retained: int | None = None,
) -> Tuple[List[float], List[float], List[List[float]], List[List[float]]]:
    z, _, _ = standardize_columns(x, ddof=ddof)
    n = len(z)
    denom = max(1, n - ddof)
    cov = [[dot([row[i] for row in z], [row[j] for row in z]) / denom for j in range(len(z[0]))] for i in range(len(z[0]))]
    vals, vecs = jacobi_eigen_symmetric(cov)
    order = sorted(range(len(vals)), key=lambda i: (-vals[i], i))
    total = sum(vals) if sum(vals) else 1.0
    if retained is None:
        retained = len(vals)
    eigenvalues = [vals[i] for i in order[:retained]]
    loadings = []
    for i in order[:retained]:
        vec = vecs[i]
        max_abs = max(abs(v) for v in vec)
        first = next(j for j, v in enumerate(vec) if abs(v) == max_abs)
        if vec[first] < 0:
            vec = [-v for v in vec]
        loadings.append(vec)
    scores = [[dot(row, vec) for vec in loadings] for row in z]
    ratios = [value / total for value in eigenvalues]
    return eigenvalues, ratios, loadings, scores


def kmeans_farthest(points: Sequence[Sequence[float]], ids: Sequence[str], k: int, max_iter: int = 1000) -> Tuple[List[int], List[List[float]], int]:
    if k <= 0 or k > len(points):
        raise ValueError("invalid k")
    first = min(range(len(ids)), key=lambda i: ids[i])
    centers = [list(points[first])]
    chosen = {first}
    while len(centers) < k:
        best_index = None
        best_dist = -1.0
        for i, point in enumerate(points):
            if i in chosen:
                continue
            dist = min(sum((a - b) ** 2 for a, b in zip(point, center)) for center in centers)
            if dist > best_dist or (dist == best_dist and ids[i] < ids[best_index]):  # type: ignore[index]
                best_dist = dist
                best_index = i
        chosen.add(best_index)  # type: ignore[arg-type]
        centers.append(list(points[best_index]))  # type: ignore[index]
    labels = [0] * len(points)
    iterations = 0
    for iterations in range(1, max_iter + 1):
        changed = False
        for i, point in enumerate(points):
            distances = [sum((a - b) ** 2 for a, b in zip(point, center)) for center in centers]
            label = min(range(k), key=lambda c: (distances[c], c))
            if label != labels[i]:
                changed = True
                labels[i] = label
        new_centers = [[0.0 for _ in points[0]] for _ in range(k)]
        counts = [0] * k
        for label, point in zip(labels, points):
            counts[label] += 1
            for j, value in enumerate(point):
                new_centers[label][j] += value
        for c in range(k):
            if counts[c]:
                new_centers[c] = [v / counts[c] for v in new_centers[c]]
            else:
                new_centers[c] = centers[c]
        centers = new_centers
        if not changed:
            break
    return [label + 1 for label in labels], centers, iterations


def comb2(n: int) -> float:
    return n * (n - 1) / 2.0


def adjusted_rand_index(a: Sequence[Any], b: Sequence[Any]) -> float:
    if len(a) != len(b):
        raise ValueError("label vectors must have the same length")
    n = len(a)
    if n < 2:
        return 1.0
    table: Dict[Tuple[Any, Any], int] = defaultdict(int)
    rows: Dict[Any, int] = defaultdict(int)
    cols: Dict[Any, int] = defaultdict(int)
    for x, y in zip(a, b):
        table[(x, y)] += 1
        rows[x] += 1
        cols[y] += 1
    sum_ij = sum(comb2(v) for v in table.values())
    sum_i = sum(comb2(v) for v in rows.values())
    sum_j = sum(comb2(v) for v in cols.values())
    total = comb2(n)
    expected = sum_i * sum_j / total if total else 0.0
    denom = 0.5 * (sum_i + sum_j) - expected
    if abs(denom) < 1e-30:
        return 1.0 if list(a) == list(b) else 0.0
    return (sum_ij - expected) / denom


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
    max_iter: int = 10000,
    tol: float = 1e-10,
) -> Tuple[float, List[float], int]:
    n = len(y)
    p = len(x[0]) if n else 0
    w = list(weights) if weights is not None else [1.0] * n
    wsum = sum(w)
    intercept = sum(wi * yi for wi, yi in zip(w, y)) / wsum
    beta = [0.0] * p
    for iteration in range(1, max_iter + 1):
        old_intercept = intercept
        old_beta = beta[:]
        residual = [y[i] - (intercept + dot(x[i], beta)) for i in range(n)]
        intercept += sum(w[i] * residual[i] for i in range(n)) / wsum
        for j in range(p):
            rho = 0.0
            denom = 0.0
            for i in range(n):
                partial = y[i] - intercept - sum(x[i][l] * beta[l] for l in range(p) if l != j)
                rho += w[i] * x[i][j] * partial
                denom += w[i] * x[i][j] * x[i][j]
            rho /= wsum
            denom = denom / wsum + alpha * (1.0 - l1_ratio)
            beta[j] = soft_threshold(rho, alpha * l1_ratio) / denom if denom else 0.0
        max_change = max([abs(intercept - old_intercept)] + [abs(a - b) for a, b in zip(beta, old_beta)])
        if max_change < tol:
            return intercept, beta, iteration
    return intercept, beta, max_iter


def round_json(value: Any, places: int) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return round(value, places)
    if isinstance(value, list):
        return [round_json(item, places) for item in value]
    if isinstance(value, dict):
        return {key: round_json(item, places) for key, item in value.items()}
    return value


def _self_test() -> None:
    beta = ols_coefficients([[1, 0], [1, 1], [1, 2]], [1, 3, 5])
    assert all(abs(a - b) < 1e-10 for a, b in zip(beta, [1.0, 2.0]))
    assert xorshift32_next(1) == 270369
    rows, state = xorshift32_signs(1, 2, 2)
    assert rows == [[1, 1], [1, 1]]
    assert state == 307599695
    assert abs(two_sided_t_pvalue(0.0, 10) - 1.0) < 1e-12
    assert quantile_nearest_rank([3, 1, 2], 0.5) == 2
    labels, _, _ = kmeans_farthest([[0.0], [1.0], [10.0], [11.0]], ["a", "b", "c", "d"], 2)
    assert len(set(labels)) == 2
    assert abs(adjusted_rand_index([1, 1, 2, 2], [1, 1, 2, 2]) - 1.0) < 1e-12


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PHO audit helper utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    download = sub.add_parser("download", help="download portal CSV datasets")
    download.add_argument("base_url")
    download.add_argument("out_dir")
    download.add_argument("datasets", nargs="+")

    xs = sub.add_parser("xorshift32", help="print xorshift32 sign rows as JSON")
    xs.add_argument("seed", type=int)
    xs.add_argument("cluster_count", type=int)
    xs.add_argument("replicates", type=int)

    pcg = sub.add_parser("pcg32-webb", help="print PCG32 Webb weight indices as JSON")
    pcg.add_argument("seed", type=int)
    pcg.add_argument("stream", type=int)
    pcg.add_argument("cluster_count", type=int)
    pcg.add_argument("replicates", type=int)

    sub.add_parser("self-test", help="run internal checks")

    args = parser.parse_args(argv)
    if args.command == "download":
        outputs = [download_dataset(args.base_url, dataset, args.out_dir) for dataset in args.datasets]
        print(json.dumps(outputs, indent=2))
    elif args.command == "xorshift32":
        rows, state = xorshift32_signs(args.seed, args.cluster_count, args.replicates)
        print(json.dumps({"rows": rows, "final_state": state}, indent=2))
    elif args.command == "pcg32-webb":
        rows, state = pcg32_webb_indices(args.seed, args.stream, args.cluster_count, args.replicates)
        print(json.dumps({"rows": rows, "final_state": state}, indent=2))
    elif args.command == "self-test":
        _self_test()
        print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
