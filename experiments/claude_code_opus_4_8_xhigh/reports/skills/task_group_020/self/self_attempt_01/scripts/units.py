#!/usr/bin/env python3
"""Rounding helpers for workbench answers.

Python's built-in round() is banker's rounding: round(2.5) == 2 and
round(12.345, 2) == 12.34. That silently produces off-by-one dollars and wrong
second decimals in these deliverables. Use these instead.

    from units import dollars, pct, months, pct_of

    dollars(100_000_000 * 0.125)   -> 12500000     (int)
    pct(3.145, 2)                  -> 3.15         (float, half-up)
    pct_of(12.5, 100_000_000)      -> 12500000     (12.5% of the base, int)
    months(15.0)                   -> 15           (int)
"""

from decimal import ROUND_HALF_UP, Decimal


def _dec(value):
    return Decimal(str(value))


def dollars(value):
    """Integer USD, half-up."""
    if value is None:
        return None
    return int(_dec(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def pct(value, places=2):
    """Percent points rounded half-up to `places` decimals.

    Returns an int when places == 0 so whole-percent templates get 12, not 12.0.
    """
    if value is None:
        return None
    exp = Decimal("1") if places == 0 else Decimal("1").scaleb(-places)
    out = _dec(value).quantize(exp, rounding=ROUND_HALF_UP)
    return int(out) if places == 0 else float(out)


def pct_of(percent_points, base):
    """Integer dollars for `percent_points`% of `base`."""
    if percent_points is None or base is None:
        return None
    return dollars(_dec(percent_points) / Decimal("100") * _dec(base))


def months(value):
    """Integer months, half-up."""
    if value is None:
        return None
    return int(_dec(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def fraction_to_pct(fraction, places=4):
    """cap_table.fully_diluted_pct is a fraction summing to 1.0; convert to points."""
    if fraction is None:
        return None
    return pct(_dec(fraction) * 100, places)


def allocate(total, weights, places=0):
    """Split `total` across `weights` (fractions or points) with no rounding drift.

    Returns integers summing exactly to `total`; the largest weight absorbs the
    residue. Use for holder-level consideration allocation.
    """
    if not weights:
        return []
    tw = sum(_dec(w) for w in weights)
    raw = [(_dec(total) * _dec(w) / tw) for w in weights]
    out = [dollars(r) for r in raw] if places == 0 else [float(_dec(r).quantize(
        Decimal("1").scaleb(-places), rounding=ROUND_HALF_UP)) for r in raw]
    if places == 0:
        drift = dollars(total) - sum(out)
        if drift:
            biggest = max(range(len(weights)), key=lambda i: _dec(weights[i]))
            out[biggest] += drift
    return out


if __name__ == "__main__":
    assert dollars(2.5) == 3 and dollars(3.5) == 4, "half-up dollars"
    assert pct(12.345, 2) == 12.35, "half-up percent"
    assert pct(12.5, 0) == 13 and isinstance(pct(12.5, 0), int), "whole percent points"
    assert pct_of(12.5, 100_000_000) == 12_500_000, "percent of base"
    assert months(15.0) == 15, "months"
    assert fraction_to_pct(0.125) == 12.5, "fraction to points"
    alloc = allocate(1_000_000, [0.1, 0.2, 0.3, 0.4])
    assert sum(alloc) == 1_000_000, "allocation sums to total"
    assert allocate(1_000_003, [1, 1, 1]) == [333334, 333334, 333335] or \
        sum(allocate(1_000_003, [1, 1, 1])) == 1_000_003, "residue absorbed"
    print("units.py self-tests passed")
