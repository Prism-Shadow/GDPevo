#!/usr/bin/env python3
"""Shared helpers for credit-office committee JSON tasks.

Keep this module dependency-free so it can run in the staged workspace.
"""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable
from urllib.request import Request, urlopen


def fetch_json(base_url: str, path: str) -> Any:
    """Fetch a JSON payload from the public task environment."""
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request) as response:  # nosec: staged task environment only
        return json.load(response)


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def round_decimal(value: Any, places: int) -> float:
    quant = Decimal("1").scaleb(-places)
    return float(_decimal(value).quantize(quant, rounding=ROUND_HALF_UP))


def ratio(numerator: Any, denominator: Any, places: int = 4) -> float:
    return round_decimal(_decimal(numerator) / _decimal(denominator), places)


def bps_from_ratio(value: Any, places: int = 2) -> float:
    return round_decimal(_decimal(value) * Decimal("10000"), places)


def quarter_key(quarter: str) -> tuple[int, int]:
    year, q = quarter.split("Q")
    return int(year), int(q)


def latest_row(rows: list[dict[str, Any]], quarter_field: str = "quarter") -> dict[str, Any]:
    return max(rows, key=lambda row: quarter_key(str(row[quarter_field])))


def sort_ids(values: Iterable[str]) -> list[str]:
    return sorted(values)


def group_sum(rows: Iterable[dict[str, Any]], key_field: str, value_field: str) -> dict[str, float]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for row in rows:
        totals[str(row[key_field])] += _decimal(row[value_field])
    return {key: float(value) for key, value in totals.items()}


def dscr_rating(dscr: Any) -> int | None:
    if dscr is None:
        return None
    value = _decimal(dscr)
    if value >= Decimal("1.5"):
        return 3
    if value >= Decimal("1.25"):
        return 4
    if value >= Decimal("1.05"):
        return 5
    if value >= Decimal("1.0"):
        return 6
    return 7


def ltv_rating(ltv: Any) -> int | None:
    if ltv is None:
        return None
    value = _decimal(ltv)
    if value <= Decimal("0.65"):
        return 3
    if value <= Decimal("0.75"):
        return 4
    if value <= Decimal("0.85"):
        return 5
    if value <= Decimal("1.0"):
        return 6
    return 7


def delinquency_rating(payment_status: str | None) -> int | None:
    if payment_status is None or payment_status == "Current":
        return None
    mapping = {
        "30 Days Past Due": 4,
        "60 Days Past Due": 5,
        "90+ Days Past Due": 7,
        "Nonaccrual": 8,
    }
    return mapping.get(payment_status)


def rederived_rating(
    *,
    current_rating: int | None = None,
    dscr: Any = None,
    ltv: Any = None,
    payment_status: str | None = None,
) -> int | None:
    ratings = [rating for rating in (dscr_rating(dscr), ltv_rating(ltv), delinquency_rating(payment_status)) if rating is not None]
    if ratings:
        return max(ratings)
    return current_rating


def stress_dscr(base_dscr: Any, shock_multiplier: str = "1.18", downside_multiplier: str = "1.0") -> float:
    base = _decimal(base_dscr)
    return round_decimal(base * _decimal(downside_multiplier) / _decimal(shock_multiplier), 2)


def cre_dual_stress_dscr(base_dscr: Any) -> float:
    return round_decimal(_decimal(base_dscr) * Decimal("0.85") / Decimal("1.18"), 2)


def cdfi_factor_score(kind: str, value: Any) -> int | None:
    if value is None:
        return None
    x = _decimal(value)
    if kind in {"debt_to_asset", "ltv"}:
        if x < Decimal("0.40"):
            return 0
        if x <= Decimal("0.60"):
            return 2
        if x <= Decimal("0.80"):
            return 4
        return 6
    if kind == "fico":
        if x > Decimal("720"):
            return 0
        if x >= Decimal("680"):
            return 1
        if x >= Decimal("580"):
            return 3
        return 5
    if kind == "liquidity_months":
        if x > Decimal("12"):
            return 0
        if x >= Decimal("6"):
            return 1
        if x >= Decimal("3"):
            return 3
        return 5
    raise ValueError(f"Unsupported factor kind: {kind}")


def cdfi_class(total_score: int, projected_loss: bool = False) -> str:
    if projected_loss:
        return "Projected Loss"
    if total_score <= 5:
        return "Prime"
    if total_score <= 9:
        return "Desirable"
    if total_score <= 13:
        return "Satisfactory"
    if total_score <= 18:
        return "Watch"
    return "Doubtful"


def branch_npa_variance(branch_ratio: Any, benchmark_ratio: Any) -> tuple[float, float]:
    variance_ratio = round_decimal(_decimal(branch_ratio) - _decimal(benchmark_ratio), 4)
    variance_bps = bps_from_ratio(variance_ratio, 2)
    return variance_ratio, variance_bps


if __name__ == "__main__":
    raise SystemExit(
        "Import this module from a solver or run targeted helper calls from a Python shell."
    )
