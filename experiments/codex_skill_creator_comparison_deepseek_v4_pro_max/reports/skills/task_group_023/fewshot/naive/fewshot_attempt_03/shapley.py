"""
Exact Shapley value enumeration for source perturbation.

Computes Shapley values by enumerating all 2^m subsets for m replaceable
entities and computing coefficient differences.
"""

import math


def exact_shapley(coefficient_fn, m):
    """
    Compute exact Shapley values for m players by enumerating all subsets.

    Args:
        coefficient_fn: Function taking an integer mask (0..2^m-1) and
            returning the coefficient for that subset.
        m: Number of players.

    Returns:
        List of m Shapley values (phi_j for j=0..m-1).
        Also returns (baseline, all_replaced) for validation.
    """
    # Precompute coefficient for every mask
    coeffs = [coefficient_fn(mask) for mask in range(1 << m)]

    # Precompute factorials
    fact = [math.factorial(i) for i in range(m + 1)]

    phi = [0.0] * m
    for j in range(m):
        bit = 1 << j
        for mask in range(1 << m):
            if mask & bit:
                continue  # j not in S
            S_size = popcount(mask)
            weight = fact[S_size] * fact[m - S_size - 1] / fact[m]
            phi[j] += weight * (coeffs[mask | bit] - coeffs[mask])

    return phi, coeffs[0], coeffs[(1 << m) - 1]


def popcount(x):
    """Count set bits in integer."""
    return x.bit_count() if hasattr(x, 'bit_count') else bin(x).count('1')


def verify_shapley(phi, baseline, all_replaced, tol=1e-6):
    """
    Verify that sum of Shapley values equals the full difference.

    Returns True if the equality holds within tolerance.
    """
    total = sum(phi)
    expected = all_replaced - baseline
    return abs(total - expected) < tol
