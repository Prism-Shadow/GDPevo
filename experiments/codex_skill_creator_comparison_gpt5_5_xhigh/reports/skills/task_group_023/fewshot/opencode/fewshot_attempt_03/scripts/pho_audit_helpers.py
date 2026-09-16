#!/usr/bin/env python3
"""Reusable helpers for Public Health Observatory audit tasks.

This module intentionally contains no task-specific solved values.
"""

from __future__ import annotations

import csv
import io
import json
import math
import urllib.parse
import urllib.request
from collections import Counter
from typing import Any, Iterable, Mapping, Sequence

try:
    import numpy as _NUMPY
except ModuleNotFoundError:
    _NUMPY = None


U32_MASK = 0xFFFFFFFF
U64_MASK = 0xFFFFFFFFFFFFFFFF


def _np():
    if _NUMPY is None:
        raise RuntimeError(
            "This helper routine requires numpy. Use the pure-Python helpers "
            "in this module or implement the linear algebra directly."
        )
    return _NUMPY


def fetch_csv(base_url: str, dataset: str, **params: Any) -> list[dict[str, str]]:
    query = {"dataset": dataset, "format": "csv"}
    query.update({k: v for k, v in params.items() if v is not None})
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", "download")
    url = url + "?" + urllib.parse.urlencode(query, doseq=True)
    with urllib.request.urlopen(url) as response:
        text = response.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def coerce_value(value: str | None) -> Any:
    if value is None or value == "":
        return None
    try:
        if value.strip().isdigit() or (value.startswith("-") and value[1:].isdigit()):
            return int(value)
        return float(value)
    except ValueError:
        return value


def coerce_rows(rows: Iterable[Mapping[str, str]]) -> list[dict[str, Any]]:
    return [{k: coerce_value(v) for k, v in row.items()} for row in rows]


def is_available(
    value: Any,
    suppression_flag: Any = 0,
    quality_flag: Any = None,
    invalid_flags: Iterable[str] = (),
) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    if suppression_flag not in (None, "", 0, "0", False):
        return False
    invalid = set(invalid_flags)
    if quality_flag in invalid:
        return False
    return True


def select_one_per_key(
    rows: Iterable[Mapping[str, Any]],
    key_fields: Sequence[str],
    priority: Sequence[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Select one row per key.

    priority items are (field, direction), where direction is "asc" or "desc".
    The best row is max by the transformed priority tuple.
    """
    grouped: dict[tuple[Any, ...], list[Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(tuple(row.get(k) for k in key_fields), []).append(row)

    def rank(row: Mapping[str, Any]) -> tuple[Any, ...]:
        out = []
        for field, direction in priority:
            value = row.get(field)
            if value is None:
                value = ""
            if direction == "desc":
                if isinstance(value, (int, float)):
                    out.append(value)
                else:
                    out.append(str(value))
            elif direction == "asc":
                if isinstance(value, (int, float)):
                    out.append(-value)
                else:
                    out.append(_invert_string(str(value)))
            else:
                raise ValueError(f"unknown priority direction {direction!r}")
        return tuple(out)

    return [dict(max(items, key=rank)) for items in grouped.values()]


def _invert_string(text: str) -> tuple[int, ...]:
    return tuple(0x10FFFF - ord(ch) for ch in text)


def add_intercept(x: np.ndarray) -> np.ndarray:
    np = _np()
    return np.column_stack([np.ones(x.shape[0]), x])


def ols_fit(x: np.ndarray, y: np.ndarray, rcond: float | None = None) -> np.ndarray:
    np = _np()
    return np.linalg.lstsq(np.asarray(x, float), np.asarray(y, float), rcond=rcond)[0]


def wls_fit(x: np.ndarray, y: np.ndarray, w: np.ndarray, rcond: float | None = None) -> np.ndarray:
    np = _np()
    sw = np.sqrt(np.asarray(w, float))
    return ols_fit(np.asarray(x, float) * sw[:, None], np.asarray(y, float) * sw, rcond=rcond)


def residuals(x: np.ndarray, y: np.ndarray, beta: np.ndarray) -> np.ndarray:
    np = _np()
    return np.asarray(y, float) - np.asarray(x, float) @ np.asarray(beta, float)


def hc3_cov(x: np.ndarray, y: np.ndarray, beta: np.ndarray, w: np.ndarray | None = None) -> np.ndarray:
    np = _np()
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    if w is None:
        xw = x
        ew = y - x @ beta
    else:
        sw = np.sqrt(np.asarray(w, float))
        xw = x * sw[:, None]
        ew = sw * (y - x @ beta)
    xtx_inv = np.linalg.pinv(xw.T @ xw)
    h = np.einsum("ij,jk,ik->i", xw, xtx_inv, xw)
    scale = (ew / np.maximum(1.0 - h, 1e-15)) ** 2
    return xtx_inv @ (xw.T @ (scale[:, None] * xw)) @ xtx_inv


def cr1_cov(x: np.ndarray, y: np.ndarray, beta: np.ndarray, groups: Sequence[Any], w: np.ndarray | None = None) -> np.ndarray:
    np = _np()
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n, k = x.shape
    if w is None:
        xw = x
        ew = y - x @ beta
    else:
        sw = np.sqrt(np.asarray(w, float))
        xw = x * sw[:, None]
        ew = sw * (y - x @ beta)
    xtx_inv = np.linalg.pinv(xw.T @ xw)
    meat = np.zeros((k, k), float)
    ordered = list(dict.fromkeys(groups))
    for group in ordered:
        idx = np.array([g == group for g in groups])
        score = xw[idx].T @ ew[idx]
        meat += np.outer(score, score)
    g_count = len(ordered)
    factor = (g_count / (g_count - 1)) * ((n - 1) / (n - k))
    return factor * xtx_inv @ meat @ xtx_inv


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    np = _np()
    err = np.asarray(y_true, float) - np.asarray(y_pred, float)
    return float(np.sqrt(np.mean(err * err)))


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    np = _np()
    return float(np.mean(np.abs(np.asarray(y_true, float) - np.asarray(y_pred, float))))


def r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    np = _np()
    y = np.asarray(y_true, float)
    sse = float(np.sum((y - np.asarray(y_pred, float)) ** 2))
    sst = float(np.sum((y - np.mean(y)) ** 2))
    return float(1.0 - sse / sst) if sst else math.nan


def xorshift32_stream(seed: int) -> Iterable[int]:
    x = seed & U32_MASK
    while True:
        x ^= (x << 13) & U32_MASK
        x &= U32_MASK
        x ^= (x >> 17) & U32_MASK
        x &= U32_MASK
        x ^= (x << 5) & U32_MASK
        x &= U32_MASK
        yield x


class PCG32:
    def __init__(self, seed: int, stream: int):
        self.state = 0
        self.inc = ((stream << 1) | 1) & U64_MASK
        self.random_u32()
        self.state = (self.state + seed) & U64_MASK
        self.random_u32()

    def random_u32(self) -> int:
        old = self.state
        self.state = (old * 6364136223846793005 + self.inc) & U64_MASK
        xorshifted = (((old >> 18) ^ old) >> 27) & U32_MASK
        rot = (old >> 59) & 31
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & U32_MASK


def nearest_rank(values: Sequence[float], probability: float) -> float:
    vals = sorted(float(v) for v in values)
    if not vals:
        return math.nan
    rank = min(len(vals), math.ceil(probability * len(vals)))
    return vals[max(0, rank - 1)]


def type7_quantile(values: Sequence[float], probability: float) -> float:
    vals = sorted(float(v) for v in values)
    if not vals:
        return math.nan
    if len(vals) == 1:
        return vals[0]
    h = (len(vals) - 1) * probability
    j = int(math.floor(h))
    gamma = h - j
    if j + 1 >= len(vals):
        return vals[-1]
    return (1.0 - gamma) * vals[j] + gamma * vals[j + 1]


def standardize(x: np.ndarray, ddof: int = 1) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    np = _np()
    x = np.asarray(x, float)
    mu = np.mean(x, axis=0)
    sd = np.std(x, axis=0, ddof=ddof)
    sd = np.where(sd == 0, 1.0, sd)
    return (x - mu) / sd, mu, sd


def pca_from_standardized(z: np.ndarray, denominator: int | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    np = _np()
    z = np.asarray(z, float)
    denom = denominator if denominator is not None else z.shape[0] - 1
    cov = z.T @ z / denom
    vals, vecs = np.linalg.eigh(cov)
    order = np.argsort(vals)[::-1]
    vals = vals[order]
    vecs = vecs[:, order]
    for j in range(vecs.shape[1]):
        col = vecs[:, j]
        idx = int(np.flatnonzero(np.abs(col) == np.max(np.abs(col)))[0])
        if col[idx] < 0:
            vecs[:, j] = -col
    scores = z @ vecs
    return vals, vecs, scores


def kmeans_farthest_first(points: np.ndarray, labels_for_tie: Sequence[Any], k: int, max_iter: int = 1000) -> tuple[np.ndarray, np.ndarray, int]:
    np = _np()
    pts = np.asarray(points, float)
    n = pts.shape[0]
    if k <= 0 or k > n:
        raise ValueError("k must be between 1 and number of points")
    tie_order = list(labels_for_tie)
    centers_idx = [0]
    while len(centers_idx) < k:
        d2 = np.min(((pts[:, None, :] - pts[centers_idx][None, :, :]) ** 2).sum(axis=2), axis=1)
        for idx in centers_idx:
            d2[idx] = -1
        max_d = np.max(d2)
        candidates = [i for i, d in enumerate(d2) if d == max_d]
        centers_idx.append(min(candidates, key=lambda i: tie_order[i]))
    centers = pts[centers_idx].copy()
    labels = np.full(n, -1, int)
    iterations = 0
    for iterations in range(1, max_iter + 1):
        d2 = ((pts[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = np.argmin(d2, axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for j in range(k):
            members = pts[labels == j]
            if len(members):
                centers[j] = members.mean(axis=0)
    return labels + 1, centers, iterations


def adjusted_rand_index(labels_a: Sequence[Any], labels_b: Sequence[Any]) -> float:
    a = list(labels_a)
    b = list(labels_b)
    if len(a) != len(b):
        raise ValueError("label arrays must have equal length")
    n = len(a)
    if n < 2:
        return 1.0
    contingency = Counter(zip(a, b))
    count_a = Counter(a)
    count_b = Counter(b)

    def choose2(x: int) -> float:
        return x * (x - 1) / 2.0

    sum_ij = sum(choose2(v) for v in contingency.values())
    sum_a = sum(choose2(v) for v in count_a.values())
    sum_b = sum(choose2(v) for v in count_b.values())
    total = choose2(n)
    expected = sum_a * sum_b / total if total else 0.0
    denom = 0.5 * (sum_a + sum_b) - expected
    return float((sum_ij - expected) / denom) if denom else 1.0


def silhouette_mean(points: np.ndarray, labels: Sequence[Any]) -> float:
    np = _np()
    pts = np.asarray(points, float)
    labels = list(labels)
    n = len(labels)
    if n <= 1:
        return 0.0
    dist = np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(axis=2))
    values = []
    for i, label in enumerate(labels):
        same = [j for j, x in enumerate(labels) if x == label and j != i]
        if not same:
            values.append(0.0)
            continue
        a = float(np.mean(dist[i, same]))
        b = math.inf
        for other in sorted(set(labels)):
            if other == label:
                continue
            idx = [j for j, x in enumerate(labels) if x == other]
            b = min(b, float(np.mean(dist[i, idx])))
        values.append((b - a) / max(a, b) if max(a, b) else 0.0)
    return float(np.mean(values))


def json_ready(value: Any, digits: int | None = None) -> Any:
    if isinstance(value, Mapping):
        return {str(k): json_ready(v, digits) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(v, digits) for v in value]
    if _NUMPY is not None and isinstance(value, _NUMPY.ndarray):
        return json_ready(value.tolist(), digits)
    if _NUMPY is not None and isinstance(value, (_NUMPY.integer,)):
        return int(value)
    if isinstance(value, float) or (_NUMPY is not None and isinstance(value, (_NUMPY.floating,))):
        x = float(value)
        if not math.isfinite(x):
            return None
        return round(x, digits) if digits is not None else x
    return value


def assert_finite_json(value: Any) -> None:
    if isinstance(value, Mapping):
        for item in value.values():
            assert_finite_json(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            assert_finite_json(item)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite float in JSON output")


def dump_json(value: Any, path: str, digits: int | None = None) -> None:
    cleaned = json_ready(value, digits)
    assert_finite_json(cleaned)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cleaned, fh, indent=2, sort_keys=False)
        fh.write("\n")
