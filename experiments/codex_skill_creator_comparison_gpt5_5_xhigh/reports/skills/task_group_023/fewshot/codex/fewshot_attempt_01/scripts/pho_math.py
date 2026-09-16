#!/usr/bin/env python3
"""Dependency-free numerical helpers for PHO audit solvers.

The functions here are generic primitives. They contain no task data, no
registered output values, and no protocol-specific default settings.
"""

from __future__ import annotations

import math
from collections import defaultdict
from itertools import combinations


def mean(values, weights=None):
    values = list(values)
    if weights is None:
        return sum(values) / len(values)
    weights = list(weights)
    total = sum(weights)
    return sum(w * x for x, w in zip(values, weights)) / total


def variance(values, weights=None, ddof=0):
    values = list(values)
    if weights is None:
        mu = mean(values)
        denom = len(values) - ddof
        return sum((x - mu) ** 2 for x in values) / denom
    weights = list(weights)
    mu = mean(values, weights)
    denom = sum(weights) - ddof
    return sum(w * (x - mu) ** 2 for x, w in zip(values, weights)) / denom


def sd(values, weights=None, ddof=0):
    v = variance(values, weights=weights, ddof=ddof)
    return math.sqrt(max(v, 0.0))


def transpose(matrix):
    return [list(col) for col in zip(*matrix)]


def matmul(a, b):
    bt = transpose(b)
    return [[sum(x * y for x, y in zip(row, col)) for col in bt] for row in a]


def matvec(a, x):
    return [sum(v * xv for v, xv in zip(row, x)) for row in a]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def outer(a, b):
    return [[x * y for y in b] for x in a]


def add_matrices(a, b):
    return [[x + y for x, y in zip(ar, br)] for ar, br in zip(a, b)]


def scale_matrix(a, c):
    return [[c * x for x in row] for row in a]


def identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def solve(a, b, eps=1e-12):
    """Solve Ax=b with partial-pivot Gauss-Jordan elimination."""
    n = len(a)
    aug = [list(map(float, a[i])) + [float(b[i])] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < eps:
            raise ValueError("singular matrix")
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        div = aug[col][col]
        aug[col] = [v / div for v in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            if factor:
                aug[row] = [v - factor * p for v, p in zip(aug[row], aug[col])]
    return [row[-1] for row in aug]


def inverse(a, eps=1e-12):
    n = len(a)
    cols = []
    eye = identity(n)
    for j in range(n):
        cols.append(solve(a, [eye[i][j] for i in range(n)], eps=eps))
    return transpose(cols)


def weighted_design(x, y, weights=None):
    if weights is None:
        return [list(map(float, row)) for row in x], list(map(float, y))
    out_x = []
    out_y = []
    for row, yi, wi in zip(x, y, weights):
        sw = math.sqrt(wi)
        out_x.append([sw * float(v) for v in row])
        out_y.append(sw * float(yi))
    return out_x, out_y


def linear_fit(x, y, weights=None):
    xw, yw = weighted_design(x, y, weights)
    xt = transpose(xw)
    xtx = matmul(xt, xw)
    xty = matvec(xt, yw)
    beta = solve(xtx, xty)
    fitted = matvec(x, beta)
    residual = [yi - fi for yi, fi in zip(y, fitted)]
    return {"beta": beta, "fitted": fitted, "residual": residual, "xtx_inv": inverse(xtx)}


def hat_diagonal(x, weights=None):
    xw, _ = weighted_design(x, [0.0] * len(x), weights)
    inv_xtx = inverse(matmul(transpose(xw), xw))
    return [dot(row, matvec(inv_xtx, row)) for row in xw]


def hc3_covariance(x, y, beta, weights=None):
    xw, _ = weighted_design(x, [0.0] * len(x), weights)
    sqrt_w = [1.0] * len(x) if weights is None else [math.sqrt(w) for w in weights]
    ew = [sw * (yi - dot(row, beta)) for row, yi, sw in zip(x, y, sqrt_w)]
    xtx_inv = inverse(matmul(transpose(xw), xw))
    h = [dot(row, matvec(xtx_inv, row)) for row in xw]
    k = len(x[0])
    meat = [[0.0] * k for _ in range(k)]
    for row, e, hi in zip(xw, ew, h):
        scale = (e * e) / ((1.0 - hi) ** 2)
        meat = add_matrices(meat, scale_matrix(outer(row, row), scale))
    return matmul(matmul(xtx_inv, meat), xtx_inv)


def cr1_covariance(x, y, beta, clusters, weights=None):
    xw, _ = weighted_design(x, [0.0] * len(x), weights)
    sqrt_w = [1.0] * len(x) if weights is None else [math.sqrt(w) for w in weights]
    ew = [sw * (yi - dot(row, beta)) for row, yi, sw in zip(x, y, sqrt_w)]
    xtx_inv = inverse(matmul(transpose(xw), xw))
    k = len(x[0])
    scores = defaultdict(lambda: [0.0] * k)
    for row, e, g in zip(xw, ew, clusters):
        for j in range(k):
            scores[g][j] += row[j] * e
    meat = [[0.0] * k for _ in range(k)]
    for score in scores.values():
        meat = add_matrices(meat, outer(score, score))
    n = len(x)
    g = len(scores)
    scale = (g / (g - 1)) * ((n - 1) / (n - k))
    return scale_matrix(matmul(matmul(xtx_inv, meat), xtx_inv), scale)


def standardize_columns(rows, weights=None, ddof=0):
    cols = transpose(rows)
    mus = [mean(col, weights) for col in cols]
    sigmas = [sd(col, weights=weights, ddof=ddof) for col in cols]
    sigmas = [s if s > 0 else 1.0 for s in sigmas]
    z = [[(v - mus[j]) / sigmas[j] for j, v in enumerate(row)] for row in rows]
    return z, mus, sigmas


def apply_standardization(rows, mus, sigmas):
    return [[(v - mus[j]) / sigmas[j] for j, v in enumerate(row)] for row in rows]


def soft_threshold(value, penalty):
    if value > penalty:
        return value - penalty
    if value < -penalty:
        return value + penalty
    return 0.0


def ridge_cd(z, y, lam, tol=1e-10, max_iter=10000):
    n = len(y)
    p = len(z[0])
    intercept = mean(y)
    yc = [yi - intercept for yi in y]
    beta = [0.0] * p
    for sweep in range(max_iter):
        max_change = 0.0
        for j in range(p):
            partial = []
            for i in range(n):
                fitted_other = sum(z[i][l] * beta[l] for l in range(p) if l != j)
                partial.append(yc[i] - fitted_other)
            num = sum(z[i][j] * partial[i] for i in range(n))
            den = sum(z[i][j] ** 2 for i in range(n)) + n * lam
            new = num / den
            max_change = max(max_change, abs(new - beta[j]))
            beta[j] = new
        if max_change < tol:
            return intercept, beta, sweep + 1
    return intercept, beta, max_iter


def elastic_net_cd(z, y, alpha, l1_ratio, weights=None, tol=1e-10, max_iter=10000):
    n = len(y)
    p = len(z[0])
    if weights is None:
        weights = [1.0] * n
    wsum = sum(weights)
    intercept = mean(y, weights)
    beta = [0.0] * p
    for sweep in range(max_iter):
        old = [intercept] + beta[:]
        residual = [y[i] - intercept - dot(z[i], beta) for i in range(n)]
        intercept += sum(weights[i] * residual[i] for i in range(n)) / wsum
        for j in range(p):
            partial = [y[i] - intercept - sum(z[i][l] * beta[l] for l in range(p) if l != j) for i in range(n)]
            rho = sum(weights[i] * z[i][j] * partial[i] for i in range(n)) / wsum
            den = sum(weights[i] * z[i][j] ** 2 for i in range(n)) / wsum + alpha * (1.0 - l1_ratio)
            beta[j] = soft_threshold(rho, alpha * l1_ratio) / den
        change = max(abs(a - b) for a, b in zip(old, [intercept] + beta))
        if change < tol:
            return intercept, beta, sweep + 1
    return intercept, beta, max_iter


def rmse(actual, predicted):
    return math.sqrt(mean((a - p) ** 2 for a, p in zip(actual, predicted)))


def mae(actual, predicted):
    return mean(abs(a - p) for a, p in zip(actual, predicted))


def r_squared(actual, predicted):
    mu = mean(actual)
    sse = sum((a - p) ** 2 for a, p in zip(actual, predicted))
    sst = sum((a - mu) ** 2 for a in actual)
    return 1.0 - sse / sst


def nearest_rank_quantile(values, probability):
    values = sorted(values)
    if not values:
        return None
    rank = min(len(values), math.ceil(probability * len(values)))
    return values[rank - 1]


def type7_quantile(values, probability):
    values = sorted(values)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    h = (len(values) - 1) * probability
    j = math.floor(h)
    gamma = h - j
    if j + 1 >= len(values):
        return values[-1]
    return (1.0 - gamma) * values[j] + gamma * values[j + 1]


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
    MULTIPLIER = 6364136223846793005
    MASK64 = (1 << 64) - 1

    def __init__(self, seed, stream):
        self.state = 0
        self.increment = (2 * stream + 1) & self.MASK64
        self.next()
        self.state = (self.state + seed) & self.MASK64
        self.next()

    @staticmethod
    def _rotr32(value, rot):
        rot &= 31
        return ((value >> rot) | (value << ((-rot) & 31))) & 0xFFFFFFFF

    def next(self):
        old = self.state
        self.state = (old * self.MULTIPLIER + self.increment) & self.MASK64
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = old >> 59
        return self._rotr32(xorshifted, rot)

    def webb_index(self):
        return self.next() % 6

    def webb_weight(self):
        weights = [
            -math.sqrt(3.0 / 2.0),
            -1.0,
            -math.sqrt(1.0 / 2.0),
            math.sqrt(1.0 / 2.0),
            1.0,
            math.sqrt(3.0 / 2.0),
        ]
        return weights[self.webb_index()]


def jacobi_eigen_symmetric(matrix, tol=1e-12, max_iter=100000):
    n = len(matrix)
    a = [row[:] for row in matrix]
    v = identity(n)
    for _ in range(max_iter):
        p, q, best = 0, 1, 0.0
        for i in range(n):
            for j in range(i + 1, n):
                cur = abs(a[i][j])
                if cur > best:
                    p, q, best = i, j, cur
        if best < tol:
            break
        tau = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
        sign = 1.0 if tau >= 0 else -1.0
        t = sign / (abs(tau) + math.sqrt(1.0 + tau * tau))
        c = 1.0 / math.sqrt(1.0 + t * t)
        s = t * c
        app, aqq, apq = a[p][p], a[q][q], a[p][q]
        a[p][p] = c * c * app - 2.0 * s * c * apq + s * s * aqq
        a[q][q] = s * s * app + 2.0 * s * c * apq + c * c * aqq
        a[p][q] = a[q][p] = 0.0
        for r in range(n):
            if r in (p, q):
                continue
            arp, arq = a[r][p], a[r][q]
            a[r][p] = a[p][r] = c * arp - s * arq
            a[r][q] = a[q][r] = s * arp + c * arq
        for r in range(n):
            vrp, vrq = v[r][p], v[r][q]
            v[r][p] = c * vrp - s * vrq
            v[r][q] = s * vrp + c * vrq
    values = [a[i][i] for i in range(n)]
    vectors = [[v[i][j] for i in range(n)] for j in range(n)]
    return values, vectors


def pca_scores(rows, ddof=1, components=None):
    z, _, _ = standardize_columns(rows, ddof=ddof)
    n = len(z)
    cov = matmul(transpose(z), z)
    cov = scale_matrix(cov, 1.0 / (n - ddof))
    values, vectors = jacobi_eigen_symmetric(cov)
    order = sorted(range(len(values)), key=lambda i: (-values[i], i))
    if components is not None:
        order = order[:components]
    loadings = []
    for i in order:
        vec = vectors[i]
        max_abs = max(abs(x) for x in vec)
        first = next(j for j, x in enumerate(vec) if abs(x) == max_abs)
        if vec[first] < 0:
            vec = [-x for x in vec]
        loadings.append(vec)
    scores = [[dot(row, vec) for vec in loadings] for row in z]
    return [values[i] for i in order], loadings, scores


def kmeans(points, k, ids=None, max_iter=1000):
    if ids is None:
        ids = list(range(len(points)))
    first = min(range(len(points)), key=lambda i: ids[i])
    centers = [points[first][:]]
    chosen = {first}
    while len(centers) < k:
        def nearest_distance(i):
            return min(sum((points[i][d] - c[d]) ** 2 for d in range(len(points[i]))) for c in centers)
        distances = [(i, nearest_distance(i)) for i in range(len(points)) if i not in chosen]
        best = max(distance for _, distance in distances)
        nxt = min((i for i, distance in distances if distance == best), key=lambda i: str(ids[i]))
        centers.append(points[nxt][:])
        chosen.add(nxt)
    labels = None
    for iteration in range(max_iter):
        new_labels = []
        for point in points:
            distances = [sum((point[d] - c[d]) ** 2 for d in range(len(point))) for c in centers]
            new_labels.append(min(range(k), key=lambda j: (distances[j], j)))
        if new_labels == labels:
            return [x + 1 for x in labels], centers, iteration
        labels = new_labels
        for j in range(k):
            members = [points[i] for i, lab in enumerate(labels) if lab == j]
            if not members:
                continue
            centers[j] = [mean(col) for col in transpose(members)]
    return [x + 1 for x in labels], centers, max_iter


def adjusted_rand_index(labels_a, labels_b):
    n = len(labels_a)
    table = defaultdict(int)
    rows = defaultdict(int)
    cols = defaultdict(int)
    for a, b in zip(labels_a, labels_b):
        table[(a, b)] += 1
        rows[a] += 1
        cols[b] += 1

    def c2(x):
        return x * (x - 1) / 2.0

    total_pairs = c2(n)
    if total_pairs == 0:
        return 1.0
    sum_table = sum(c2(v) for v in table.values())
    sum_rows = sum(c2(v) for v in rows.values())
    sum_cols = sum(c2(v) for v in cols.values())
    expected = sum_rows * sum_cols / total_pairs
    denom = 0.5 * (sum_rows + sum_cols) - expected
    if denom == 0:
        return 1.0
    return (sum_table - expected) / denom


def silhouette(points, labels):
    groups = defaultdict(list)
    for idx, label in enumerate(labels):
        groups[label].append(idx)
    if len(groups) < 2:
        return 0.0

    def dist(i, j):
        return math.sqrt(sum((points[i][d] - points[j][d]) ** 2 for d in range(len(points[i]))))

    scores = []
    for i, label in enumerate(labels):
        own = groups[label]
        if len(own) == 1:
            scores.append(0.0)
            continue
        a = mean(dist(i, j) for j in own if j != i)
        b = min(mean(dist(i, j) for j in members) for lab, members in groups.items() if lab != label)
        scores.append((b - a) / max(a, b))
    return mean(scores)


def _betacf(a, b, x, max_iter=200, eps=3e-14, fpmin=1e-300):
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def regularized_incomplete_beta(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def student_t_cdf(t, df):
    x = df / (df + t * t)
    ib = regularized_incomplete_beta(df / 2.0, 0.5, x)
    if t >= 0:
        return 1.0 - 0.5 * ib
    return 0.5 * ib


def student_t_two_sided_p(t, df):
    cdf = student_t_cdf(t, df)
    return 2.0 * min(cdf, 1.0 - cdf)


def powerset_indices(n):
    for r in range(n + 1):
        for combo in combinations(range(n), r):
            yield combo


def _self_test():
    inv = inverse([[4, 7], [2, 6]])
    assert abs(inv[0][0] - 0.6) < 1e-12
    fit = linear_fit([[1, 0], [1, 1], [1, 2]], [1, 3, 5])
    assert all(abs(a - b) < 1e-10 for a, b in zip(fit["beta"], [1, 2]))
    rng = XorShift32(1)
    assert rng.next() == 270369
    assert abs(nearest_rank_quantile([3, 1, 2], 0.5) - 2) < 1e-12
    assert abs(student_t_two_sided_p(0.0, 10) - 1.0) < 1e-12
    labels, _, _ = kmeans([[0.0], [1.0], [10.0], [11.0]], 2)
    assert len(set(labels)) == 2
    assert abs(adjusted_rand_index([1, 1, 2, 2], [2, 2, 1, 1]) - 1.0) < 1e-12
    print("pho_math self-test passed")


if __name__ == "__main__":
    _self_test()
