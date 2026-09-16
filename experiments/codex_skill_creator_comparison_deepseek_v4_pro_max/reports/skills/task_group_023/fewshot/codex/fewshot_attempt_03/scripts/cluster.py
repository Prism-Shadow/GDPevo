#!/usr/bin/env python3
"""K-means clustering (Lloyd) and silhouette scoring as used in PHO audits.

- Deterministic initialization: first center = ASCII-first entity;
  each subsequent = entity maximizing distance to its nearest center,
  tie-broken by entity code.
- Assignment: nearest center, ties to lower working id.
- Update to member means; stop when assignments unchanged or at cap.
- Canonicalize final cluster ids by centroid coordinates then working id.
- Adjusted Rand Index for stability comparison.

Also: silhouette score for selecting cluster count.
"""

import math
from collections import Counter


def euclidean_sq(a, b):
    return sum((ai - bi) ** 2 for ai, bi in zip(a, b))


def kmeans_deterministic(points, entity_ids, k, max_iters=100):
    """Deterministic k-means as used in PHO audits.

    Args:
        points: list of coordinate vectors (list of floats)
        entity_ids: list of string identifiers (for tie-breaking)
        k: number of clusters
        max_iters: maximum Lloyd iterations

    Returns:
        (assignments, centroids, n_iters)
        assignments: list of cluster ids (0..k-1)
        centroids: list of centroid vectors
    """
    n = len(points)
    if k >= n:
        return list(range(n)), [list(p) for p in points], 0

    # Initialization
    # First center: ASCII-first entity
    first_idx = sorted(range(n), key=lambda i: entity_ids[i])[0]
    centroids = [list(points[first_idx])]
    centroid_indices = [first_idx]

    for _ in range(k - 1):
        # Each point's distance to nearest existing centroid
        dists = []
        for i in range(n):
            min_d = float('inf')
            for c in centroids:
                d = euclidean_sq(points[i], c)
                if d < min_d:
                    min_d = d
            dists.append(min_d)
        # Select point with max min-distance, tie to lower entity code
        best_idx = max(range(n), key=lambda i: (dists[i], -ord(entity_ids[i][0]) if entity_ids[i] else 0, entity_ids[i]))
        centroids.append(list(points[best_idx]))
        centroid_indices.append(best_idx)

    # Lloyd iterations
    assignments = [0] * n
    for iteration in range(max_iters):
        # Assignment
        new_assignments = [0] * n
        for i in range(n):
            best_c = 0
            best_d = float('inf')
            for c_idx, c in enumerate(centroids):
                d = euclidean_sq(points[i], c)
                if d < best_d - 1e-12:
                    best_c = c_idx
                    best_d = d
                elif abs(d - best_d) < 1e-12 and c_idx < best_c:
                    best_c = c_idx
            new_assignments[i] = best_c

        if new_assignments == assignments:
            break
        assignments = new_assignments

        # Update centroids
        sums = [[0.0] * len(points[0]) for _ in range(k)]
        counts = [0] * k
        for i in range(n):
            c = assignments[i]
            counts[c] += 1
            for j in range(len(points[i])):
                sums[c][j] += points[i][j]
        for c in range(k):
            if counts[c] > 0:
                centroids[c] = [s / counts[c] for s in sums[c]]
            else:
                centroids[c] = [0.0] * len(points[0])

    # Canonicalize: sort cluster ids by centroid coordinates, then working id
    # Map old ids to new ordering
    centroid_with_id = [(tuple(centroids[c]), c) for c in range(k)]
    centroid_with_id.sort()
    id_map = {old: new for new, (_, old) in enumerate(centroid_with_id)}

    canonical_assignments = [id_map[a] for a in assignments]
    canonical_centroids = [centroids[centroid_with_id[new][1]] for new in range(k)]

    return canonical_assignments, canonical_centroids, iteration + 1


def silhouette_score(points, assignments, k):
    """Average silhouette score for k clusters."""
    n = len(points)
    if k <= 1 or k >= n:
        return 1.0 if k == n else 0.0

    # Precompute clusters
    clusters = {c: [] for c in range(k)}
    for i, c in enumerate(assignments):
        clusters[c].append(i)

    # a_i: mean intra-cluster distance
    a = [0.0] * n
    for i in range(n):
        c = assignments[i]
        if len(clusters[c]) <= 1:
            a[i] = 0.0
        else:
            total = sum(math.sqrt(euclidean_sq(points[i], points[j])) for j in clusters[c] if j != i)
            a[i] = total / (len(clusters[c]) - 1)

    # b_i: min mean inter-cluster distance
    b = [float('inf')] * n
    for i in range(n):
        ci = assignments[i]
        for c in range(k):
            if c != ci:
                total = sum(math.sqrt(euclidean_sq(points[i], points[j])) for j in clusters[c])
                mean_d = total / len(clusters[c])
                if mean_d < b[i]:
                    b[i] = mean_d

    # Silhouette for each point
    s = [0.0] * n
    for i in range(n):
        if a[i] > 0 and b[i] > 0:
            s[i] = (b[i] - a[i]) / max(a[i], b[i])
        elif a[i] == 0 and b[i] == 0:
            s[i] = 0.0
        elif a[i] == 0:
            s[i] = 1.0

    return sum(s) / n


def adjusted_rand_index(labels1, labels2):
    """Adjusted Rand Index between two label vectors."""
    n = len(labels1)
    # Contingency table
    from collections import defaultdict
    table = Counter()
    for a, b in zip(labels1, labels2):
        table[(a, b)] += 1

    # Row and column sums
    row_sum = Counter()
    col_sum = Counter()
    for (a, b), cnt in table.items():
        row_sum[a] += cnt
        col_sum[b] += cnt

    # n_ij choose 2 sums
    sum_nij_choose2 = sum(cnt * (cnt - 1) // 2 for cnt in table.values())
    sum_a_choose2 = sum(cnt * (cnt - 1) // 2 for cnt in row_sum.values())
    sum_b_choose2 = sum(cnt * (cnt - 1) // 2 for cnt in col_sum.values())

    expected = (sum_a_choose2 * sum_b_choose2) / (n * (n - 1) // 2) if n > 1 else 0.0

    index = sum_nij_choose2
    max_index = 0.5 * (sum_a_choose2 + sum_b_choose2)

    if max_index == 0:
        return 1.0

    return (index - expected) / (max_index - expected)
