#!/usr/bin/env python3
"""Small dependency-free helpers for Public Health Observatory audits."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from itertools import permutations
from pathlib import Path
from typing import Any, Callable, Iterable


INVALID_QUALITY_FLAGS = {"INVALID", "INVALID_SCALE", "WITHDRAWN"}


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="") as f:
        return list(csv.DictReader(f))


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return float(value)
    text = str(value).strip()
    if text == "":
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def parse_int(value: Any) -> int | None:
    number = parse_float(value)
    if number is None:
        return None
    return int(number)


def available_value(
    row: dict[str, Any],
    value_field: str = "value",
    invalid_flags: set[str] | None = None,
) -> float | None:
    flags = invalid_flags if invalid_flags is not None else INVALID_QUALITY_FLAGS
    if str(row.get("suppression_flag", "0")).strip() in {"1", "true", "True"}:
        return None
    if str(row.get("quality_flag", "")).strip() in flags:
        return None
    return parse_float(row.get(value_field))


def release_sort_key(
    row: dict[str, Any],
    *,
    id_field: str | None = None,
    id_order: str = "max",
) -> tuple[Any, ...]:
    """Key for selecting latest release. Use max() unless id_order is 'min'."""
    revision = parse_int(row.get("revision")) or 0
    released_at = str(row.get("released_at", ""))
    if id_field is None:
        return (revision, released_at)
    identifier = str(row.get(id_field, ""))
    if id_order == "min":
        inverted = tuple(-ord(ch) for ch in identifier)
        return (revision, released_at, inverted)
    return (revision, released_at, identifier)


def select_one_per_key(
    rows: Iterable[dict[str, Any]],
    key_fields: list[str],
    *,
    id_field: str | None = None,
    id_order: str = "max",
) -> dict[tuple[Any, ...], dict[str, Any]]:
    selected: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key = tuple(row.get(field) for field in key_fields)
        old = selected.get(key)
        if old is None or release_sort_key(row, id_field=id_field, id_order=id_order) > release_sort_key(
            old, id_field=id_field, id_order=id_order
        ):
            selected[key] = row
    return selected


def round_json(value: Any, digits: int) -> Any:
    """Recursively round finite floats while preserving ints, bools, strings, and nulls."""
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        rounded = round(value, digits)
        return 0.0 if rounded == -0.0 else rounded
    if isinstance(value, list):
        return [round_json(item, digits) for item in value]
    if isinstance(value, dict):
        return {key: round_json(item, digits) for key, item in value.items()}
    return value


def dump_json(data: Any, digits: int = 4) -> str:
    return json.dumps(round_json(data, digits), separators=(",", ":"), ensure_ascii=True)


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
    MULTIPLIER = 6364136223846793005
    MASK64 = (1 << 64) - 1

    def __init__(self, seed: int, stream: int):
        self.state = 0
        self.increment = ((stream << 1) | 1) & self.MASK64
        self.next()
        self.state = (self.state + seed) & self.MASK64
        self.next()

    @staticmethod
    def _rotr32(value: int, rot: int) -> int:
        rot &= 31
        return ((value >> rot) | (value << ((-rot) & 31))) & 0xFFFFFFFF

    def next(self) -> int:
        old = self.state
        self.state = (old * self.MULTIPLIER + self.increment) & self.MASK64
        xorshifted = (((old >> 18) ^ old) >> 27) & 0xFFFFFFFF
        rot = old >> 59
        return self._rotr32(xorshifted, rot)

    def webb_index(self) -> int:
        return self.next() % 6

    def webb_weight(self) -> float:
        return [
            -math.sqrt(3.0 / 2.0),
            -1.0,
            -math.sqrt(1.0 / 2.0),
            math.sqrt(1.0 / 2.0),
            1.0,
            math.sqrt(3.0 / 2.0),
        ][self.webb_index()]


def nearest_rank(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = min(len(ordered), math.ceil(probability * len(ordered)))
    return ordered[max(0, rank - 1)]


def type7_quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    h = (len(ordered) - 1) * probability
    j = math.floor(h)
    gamma = h - j
    return (1.0 - gamma) * ordered[j] + gamma * ordered[j + 1]


def conformal_rank_count(m: int, coverage: float) -> int:
    if m <= 0:
        raise ValueError("calibration count must be positive")
    return min(m, math.ceil((m + 1) * coverage))


def adjusted_rand_index(labels_a: list[int], labels_b: list[int]) -> float:
    if len(labels_a) != len(labels_b):
        raise ValueError("label arrays must have the same length")
    n = len(labels_a)
    if n < 2:
        return 1.0
    table: dict[tuple[int, int], int] = defaultdict(int)
    count_a: dict[int, int] = defaultdict(int)
    count_b: dict[int, int] = defaultdict(int)
    for a, b in zip(labels_a, labels_b):
        table[(a, b)] += 1
        count_a[a] += 1
        count_b[b] += 1

    def choose2(x: int) -> float:
        return x * (x - 1) / 2.0

    sum_cells = sum(choose2(v) for v in table.values())
    sum_a = sum(choose2(v) for v in count_a.values())
    sum_b = sum(choose2(v) for v in count_b.values())
    total = choose2(n)
    expected = sum_a * sum_b / total if total else 0.0
    denom = 0.5 * (sum_a + sum_b) - expected
    if denom == 0:
        return 1.0 if labels_a == labels_b else 0.0
    return (sum_cells - expected) / denom


def best_label_alignment(reference: list[int], candidate: list[int]) -> dict[int, int]:
    """Return candidate-label to reference-label mapping with max matches."""
    ref_ids = sorted(set(reference))
    cand_ids = sorted(set(candidate))
    if len(cand_ids) > len(ref_ids):
        ref_ids = ref_ids + [max(ref_ids, default=0) + i + 1 for i in range(len(cand_ids) - len(ref_ids))]
    best_score = -1
    best_pairs: tuple[int, ...] | None = None
    for perm in permutations(ref_ids, len(cand_ids)):
        mapping = dict(zip(cand_ids, perm))
        score = sum(1 for r, c in zip(reference, candidate) if mapping[c] == r)
        if score > best_score or (score == best_score and (best_pairs is None or perm < best_pairs)):
            best_score = score
            best_pairs = perm
    assert best_pairs is not None
    return dict(zip(cand_ids, best_pairs))


def squared_distance(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def farthest_first_kmeans(
    ids: list[str],
    points: list[list[float]],
    k: int,
    *,
    max_iter: int = 100,
    canonicalize: bool = False,
) -> tuple[list[int], list[list[float]], list[str], int]:
    if len(ids) != len(points):
        raise ValueError("ids and points length mismatch")
    if not ids or k <= 0 or k > len(ids):
        raise ValueError("invalid k")
    order = sorted(range(len(ids)), key=lambda i: ids[i])
    centers_idx = [order[0]]
    while len(centers_idx) < k:
        best_i = None
        best_dist = None
        for i in order:
            if i in centers_idx:
                continue
            dist = min(squared_distance(points[i], points[c]) for c in centers_idx)
            if best_dist is None or dist > best_dist or (dist == best_dist and ids[i] < ids[best_i]):
                best_i = i
                best_dist = dist
        centers_idx.append(best_i)  # type: ignore[arg-type]
    centroids = [points[i][:] for i in centers_idx]
    labels = [0] * len(points)
    iterations = 0
    for iterations in range(1, max_iter + 1):
        new_labels = []
        for point in points:
            distances = [squared_distance(point, centroid) for centroid in centroids]
            new_labels.append(min(range(k), key=lambda c: (distances[c], c)))
        if new_labels == labels and iterations > 1:
            break
        labels = new_labels
        for c in range(k):
            members = [points[i] for i, label in enumerate(labels) if label == c]
            if members:
                centroids[c] = [sum(row[j] for row in members) / len(members) for j in range(len(points[0]))]
    if canonicalize:
        ordering = sorted(range(k), key=lambda c: (centroids[c], c))
        remap = {old: new for new, old in enumerate(ordering)}
        centroids = [centroids[old] for old in ordering]
        labels = [remap[label] for label in labels]
    return [label + 1 for label in labels], centroids, [ids[i] for i in centers_idx], iterations
