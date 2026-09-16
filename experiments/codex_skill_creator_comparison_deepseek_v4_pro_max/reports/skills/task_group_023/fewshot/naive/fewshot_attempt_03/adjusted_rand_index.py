"""
Adjusted Rand Index computation for comparing two cluster labelings.

ARI measures agreement corrected for chance.
"""


def combinations_2(n):
    """C(n, 2) = n*(n-1)/2."""
    return n * (n - 1) // 2


def adjusted_rand_index(labels_a, labels_b):
    """
    Compute Adjusted Rand Index between two labelings.

    Args:
        labels_a: List of integer labels for each item.
        labels_b: List of integer labels for each item.

    Returns:
        ARI value (float). 1.0 = perfect agreement, 0.0 = chance.
    """
    n = len(labels_a)
    if n < 2:
        return 1.0

    # Build contingency table
    unique_a = sorted(set(labels_a))
    unique_b = sorted(set(labels_b))
    map_a = {v: i for i, v in enumerate(unique_a)}
    map_b = {v: i for i, v in enumerate(unique_b)}

    k_a = len(unique_a)
    k_b = len(unique_b)
    table = [[0] * k_b for _ in range(k_a)]

    for la, lb in zip(labels_a, labels_b):
        table[map_a[la]][map_b[lb]] += 1

    # Row sums and column sums
    row_sums = [sum(row) for row in table]
    col_sums = [sum(table[i][j] for i in range(k_a)) for j in range(k_b)]

    # Sum of C(n_ij, 2)
    sum_comb = sum(combinations_2(table[i][j])
                   for i in range(k_a) for j in range(k_b))

    # Expected value
    sum_row_comb = sum(combinations_2(r) for r in row_sums)
    sum_col_comb = sum(combinations_2(c) for c in col_sums)
    expected = sum_row_comb * sum_col_comb / combinations_2(n)

    # ARI
    numerator = sum_comb - expected
    denominator = 0.5 * (sum_row_comb + sum_col_comb) - expected

    if denominator == 0:
        return 1.0 if numerator == 0 else 0.0

    return numerator / denominator


def align_labels(ref_labels, alt_labels):
    """
    Align alt_labels to ref_labels by maximum agreement permutation.

    Returns:
        (aligned_labels, permutation) where permutation maps alt cluster IDs
        to ref cluster IDs. Ties break to lexicographically smallest mapped-ID vector.
    """
    unique_ref = sorted(set(ref_labels))
    unique_alt = sorted(set(alt_labels))
    n_ref = len(unique_ref)
    n_alt = len(unique_alt)

    if n_alt == 0:
        return alt_labels[:], []

    # Pad with empty cluster IDs so ref and alt have same count for matching
    max_k = max(n_ref, n_alt)
    # Build all assignments of alt IDs to ref IDs
    import itertools

    best_matches = -1
    best_perm = None

    # Generate all permutations of ref IDs of length n_alt, padded
    for perm in itertools.permutations(unique_ref * ((n_alt // n_ref) + 1), n_alt):
        mapped = {unique_alt[i]: perm[i] for i in range(n_alt)}
        aligned = [mapped.get(l, -1) for l in alt_labels]
        matches = sum(1 for r, a in zip(ref_labels, aligned) if r == a)
        if matches > best_matches:
            best_matches = matches
            best_perm = perm
        elif matches == best_matches and best_perm is not None:
            # Lexicographic tie-break
            if list(perm) < list(best_perm):
                best_perm = perm

    if best_perm is not None:
        mapped = {unique_alt[i]: best_perm[i] for i in range(n_alt)}
        aligned = [mapped.get(l, -1) for l in alt_labels]
    else:
        aligned = alt_labels[:]

    return aligned
