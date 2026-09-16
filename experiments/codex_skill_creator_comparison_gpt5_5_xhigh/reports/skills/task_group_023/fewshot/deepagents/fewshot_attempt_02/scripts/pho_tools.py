#!/usr/bin/env python3
"""Portable helpers for Public Health Observatory audit tasks.

The module uses only the Python standard library so it can run in stripped-down
solver environments. It is intentionally generic and contains no task answers.
"""

from __future__ import annotations

import csv
import io
import math
import urllib.parse
import urllib.request
from collections import defaultdict
from itertools import combinations


def download_csv(base_url, dataset, **filters):
    """Return a list of dict rows from /download?dataset=...&format=csv."""
    base = base_url.rstrip("/") + "/download"
    params = {"dataset": dataset, "format": "csv"}
    for k, v in filters.items():
        if v is None or v == "":
            continue
        if isinstance(v, (list, tuple, set)):
            params[k] = ",".join(str(item) for item in v)
        else:
            params[k] = v
    url = base + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as response:
        text = response.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def fnum(value):
    if value is None or value == "":
        return None
    return float(value)


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def transpose(a):
    return [list(col) for col in zip(*a)]


def matmul(a, b):
    bt = transpose(b)
    return [[dot(row, col) for col in bt] for row in a]


def matvec(a, x):
    return [dot(row, x) for row in a]


def eye(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def inverse(a, ridge=0.0):
    """Gauss-Jordan inverse for small dense matrices."""
    n = len(a)
    aug = [list(map(float, row)) + eye(n)[i] for i, row in enumerate(a)]
    if ridge:
        for i in range(n):
            aug[i][i] += ridge
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-14:
            raise ValueError("singular matrix")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [v / scale for v in aug[col]]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor:
                aug[r] = [v - factor * w for v, w in zip(aug[r], aug[col])]
    return [row[n:] for row in aug]


def ols(y, x):
    xt = transpose(x)
    xtx = matmul(xt, x)
    xtx_inv = inverse(xtx)
    beta = matvec(xtx_inv, matvec(xt, y))
    fitted = matvec(x, beta)
    resid = [yi - fi for yi, fi in zip(y, fitted)]
    return beta, fitted, resid, xtx_inv


def wls(y, x, weights):
    sw = [math.sqrt(w) for w in weights]
    xw = [[v * s for v in row] for row, s in zip(x, sw)]
    yw = [v * s for v, s in zip(y, sw)]
    beta, fitted_w, resid_w, xtx_inv = ols(yw, xw)
    fitted = matvec(x, beta)
    resid = [yi - fi for yi, fi in zip(y, fitted)]
    return beta, fitted, resid, xtx_inv, xw, resid_w


def cr1_cov(x, resid, clusters):
    n = len(x)
    k = len(x[0])
    xtx_inv = inverse(matmul(transpose(x), x))
    scores = defaultdict(lambda: [0.0] * k)
    for row, e, g in zip(x, resid, clusters):
        for j, val in enumerate(row):
            scores[g][j] += val * e
    meat = [[0.0] * k for _ in range(k)]
    for s in scores.values():
        for i in range(k):
            for j in range(k):
                meat[i][j] += s[i] * s[j]
    g = len(scores)
    scale = (g / (g - 1)) * ((n - 1) / (n - k))
    return scalar_matmul(scale, matmul(matmul(xtx_inv, meat), xtx_inv))


def hc3_cov(xw, resid_w):
    xtx_inv = inverse(matmul(transpose(xw), xw))
    k = len(xw[0])
    meat = [[0.0] * k for _ in range(k)]
    for row, e in zip(xw, resid_w):
        h = dot(row, matvec(xtx_inv, row))
        adj = (e / (1.0 - h)) ** 2
        for i in range(k):
            for j in range(k):
                meat[i][j] += row[i] * row[j] * adj
    return matmul(matmul(xtx_inv, meat), xtx_inv)


def scalar_matmul(c, a):
    return [[c * v for v in row] for row in a]


def rmse(errors):
    return math.sqrt(sum(e * e for e in errors) / len(errors))


def mae(errors):
    return sum(abs(e) for e in errors) / len(errors)


def r_squared(y, pred):
    ybar = mean(y)
    sse = sum((a - b) ** 2 for a, b in zip(y, pred))
    sst = sum((a - ybar) ** 2 for a in y)
    return 1.0 - sse / sst


def soft_threshold(a, t):
    if a > t:
        return a - t
    if a < -t:
        return a + t
    return 0.0


def nearest_rank(values, p):
    xs = sorted(values)
    idx = min(len(xs), math.ceil(p * len(xs))) - 1
    return xs[idx]


def type7_quantile(values, p):
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    h = (len(xs) - 1) * p
    j = math.floor(h)
    gamma = h - j
    if j + 1 >= len(xs):
        return xs[-1]
    return (1 - gamma) * xs[j] + gamma * xs[j + 1]


class XorShift32:
    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFF

    def next(self):
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x &= 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x &= 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        x &= 0xFFFFFFFF
        self.state = x
        return x

    def sign(self):
        return 1.0 if (self.next() & 1) else -1.0


class PCG32:
    MULT = 6364136223846793005
    MASK64 = (1 << 64) - 1

    def __init__(self, seed, stream):
        self.inc = ((int(stream) << 1) | 1) & self.MASK64
        self.state = 0
        self.next()
        self.state = (self.state + int(seed)) & self.MASK64
        self.next()

    def next(self):
        old = self.state
        self.state = (old * self.MULT + self.inc) & self.MASK64
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = (old >> 59) & 31
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & 0xFFFFFFFF

    def webb_index(self):
        return self.next() % 6

    def webb_weight(self):
        return [
            -math.sqrt(3.0 / 2.0),
            -1.0,
            -math.sqrt(1.0 / 2.0),
            math.sqrt(1.0 / 2.0),
            1.0,
            math.sqrt(3.0 / 2.0),
        ][self.webb_index()]


def standardize_columns(matrix, sample=True):
    n = len(matrix)
    p = len(matrix[0])
    means = [mean([row[j] for row in matrix]) for j in range(p)]
    div = n - 1 if sample else n
    sds = []
    for j in range(p):
        var = sum((row[j] - means[j]) ** 2 for row in matrix) / div
        sd = math.sqrt(var)
        sds.append(sd if sd > 0 else 1.0)
    z = [[(row[j] - means[j]) / sds[j] for j in range(p)] for row in matrix]
    return z, means, sds


def covariance(z, sample=True):
    n = len(z)
    div = n - 1 if sample else n
    return [[dot([r[i] for r in z], [r[j] for r in z]) / div for j in range(len(z[0]))] for i in range(len(z[0]))]


def jacobi_eigen_symmetric(a, tol=1e-12, max_iter=10000):
    n = len(a)
    a = [row[:] for row in a]
    v = eye(n)
    for _ in range(max_iter):
        p, q, m = 0, 1, 0.0
        for i in range(n):
            for j in range(i + 1, n):
                val = abs(a[i][j])
                if val > m:
                    p, q, m = i, j, val
        if m < tol:
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
        a[p][p] = c * c * app - 2 * s * c * apq + s * s * aqq
        a[q][q] = s * s * app + 2 * s * c * apq + c * c * aqq
        a[p][q] = a[q][p] = 0.0
        for k in range(n):
            vkp, vkq = v[k][p], v[k][q]
            v[k][p] = c * vkp - s * vkq
            v[k][q] = s * vkp + c * vkq
    vals = [a[i][i] for i in range(n)]
    vecs = [[v[i][j] for i in range(n)] for j in range(n)]
    order = sorted(range(n), key=lambda i: (-vals[i], i))
    return [vals[i] for i in order], [vecs[i] for i in order]


def orient_loading(vec):
    idx = min(range(len(vec)), key=lambda i: (-abs(vec[i]), i))
    if vec[idx] < 0:
        return [-v for v in vec]
    return vec[:]


def pca(matrix, sample=True):
    z, means, sds = standardize_columns(matrix, sample=sample)
    vals, vecs = jacobi_eigen_symmetric(covariance(z, sample=sample))
    vecs = [orient_loading(v) for v in vecs]
    scores = [[dot(row, vec) for vec in vecs] for row in z]
    total = sum(vals)
    ratios = [v / total if total else 0.0 for v in vals]
    return vals, ratios, vecs, scores, means, sds


def kmeans_farthest(points, ids, k, max_iter=100):
    centers_idx = [0]
    while len(centers_idx) < k:
        best_i = None
        best_d = -1.0
        for i, point in enumerate(points):
            d = min(sqdist(point, points[c]) for c in centers_idx)
            if (
                d > best_d + 1e-15
                or (abs(d - best_d) <= 1e-15 and str(ids[i]) < str(ids[best_i]))
            ):
                best_d = d
                best_i = i
        centers_idx.append(best_i)
    centers = [points[i][:] for i in centers_idx]
    labels = None
    for it in range(max_iter):
        new_labels = []
        for point in points:
            new_labels.append(min(range(k), key=lambda c: (sqdist(point, centers[c]), c)))
        if new_labels == labels:
            return [l + 1 for l in labels], centers, it
        labels = new_labels
        for c in range(k):
            members = [p for p, lab in zip(points, labels) if lab == c]
            if members:
                centers[c] = [mean([m[j] for m in members]) for j in range(len(points[0]))]
    return [l + 1 for l in labels], centers, max_iter


def sqdist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))


def adjusted_rand_index(labels_a, labels_b):
    n = len(labels_a)
    table = defaultdict(int)
    ca = defaultdict(int)
    cb = defaultdict(int)
    for a, b in zip(labels_a, labels_b):
        table[(a, b)] += 1
        ca[a] += 1
        cb[b] += 1
    comb = lambda x: x * (x - 1) / 2.0
    sum_ij = sum(comb(v) for v in table.values())
    sum_a = sum(comb(v) for v in ca.values())
    sum_b = sum(comb(v) for v in cb.values())
    total = comb(n)
    if total == 0:
        return 1.0
    expected = sum_a * sum_b / total
    denom = 0.5 * (sum_a + sum_b) - expected
    return 1.0 if denom == 0 else (sum_ij - expected) / denom


def all_subsets(items):
    for r in range(len(items) + 1):
        for combo in combinations(items, r):
            yield combo


if __name__ == "__main__":
    print("pho_tools import ok")
