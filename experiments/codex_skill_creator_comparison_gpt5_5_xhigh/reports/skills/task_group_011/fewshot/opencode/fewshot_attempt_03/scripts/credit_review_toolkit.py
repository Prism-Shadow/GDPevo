#!/usr/bin/env python3
"""Utilities for credit-office API committee JSON tasks.

The script embeds no branch, segment, loan, application, or answer data. It is a
portable helper for fetching public API JSON, applying common policy math, and
checking final answer shape against the provided task template.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def normalize_base_url(base_url: str) -> str:
    if not base_url:
        raise ValueError("base URL is empty")
    return base_url.rstrip("/") + "/"


def fetch_json(base_url: str, path: str) -> Any:
    url = urllib.parse.urljoin(normalize_base_url(base_url), path.lstrip("/"))
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"HTTP {exc.code} fetching {url}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Error fetching {url}: {exc.reason}") from exc


def money(value: float | int | None) -> float | None:
    return None if value is None else round(float(value) + 0.0, 2)


def ratio(numerator: float | int | None, denominator: float | int | None, digits: int = 4) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return round(float(numerator) / float(denominator), digits)


def variance(branch_ratio: float, benchmark_ratio: float) -> dict[str, float]:
    diff = float(branch_ratio) - float(benchmark_ratio)
    return {
        "variance_ratio": round(diff, 4),
        "variance_bps": round(diff * 10000, 2),
    }


def median(values: list[float | int]) -> float:
    return float(statistics.median(float(v) for v in values))


def direction(value: float | int, comparator: float | int) -> str:
    if float(value) > float(comparator):
        return "higher"
    if float(value) < float(comparator):
        return "lower"
    return "equal"


def risk_rating_from_factors(record: dict[str, Any], policies: dict[str, Any]) -> int | None:
    risk_policy = policies.get("risk_rating", {})
    ratings: list[int] = []

    dscr = record.get("dscr")
    if dscr is not None:
        dscr = float(dscr)
        if dscr >= 1.50:
            ratings.append(3)
        elif dscr >= 1.25:
            ratings.append(4)
        elif dscr >= 1.05:
            ratings.append(5)
        elif dscr >= 1.00:
            ratings.append(6)
        else:
            ratings.append(7)

    ltv = record.get("ltv")
    if ltv is not None:
        ltv = float(ltv)
        if ltv <= 0.65:
            ratings.append(3)
        elif ltv <= 0.75:
            ratings.append(4)
        elif ltv <= 0.85:
            ratings.append(5)
        elif ltv <= 1.00:
            ratings.append(6)
        else:
            ratings.append(7)

    payment_status = record.get("payment_status")
    delinquency_minimums = risk_policy.get("delinquency_minimums", {})
    payment_rating = delinquency_minimums.get(payment_status)
    if payment_rating is not None:
        ratings.append(int(payment_rating))

    current = record.get("current_rating")
    if current is not None:
        ratings.append(int(current))
    return max(ratings) if ratings else None


def factor_score(record: dict[str, Any]) -> int:
    score = 0

    ltv = record.get("ltv")
    if ltv is not None:
        ltv = float(ltv)
        if ltv < 0.40:
            score += 0
        elif ltv <= 0.60:
            score += 2
        elif ltv <= 0.80:
            score += 4
        else:
            score += 6

    debt_to_asset = record.get("debt_to_asset")
    if debt_to_asset is not None:
        debt_to_asset = float(debt_to_asset)
        if debt_to_asset < 0.40:
            score += 0
        elif debt_to_asset <= 0.60:
            score += 2
        elif debt_to_asset <= 0.80:
            score += 4
        else:
            score += 6

    fico = record.get("fico")
    if fico is not None:
        fico = float(fico)
        if fico > 720:
            score += 0
        elif fico >= 680:
            score += 1
        elif fico >= 580:
            score += 3
        else:
            score += 5

    liquidity = record.get("liquidity_months")
    if liquidity is not None:
        liquidity = float(liquidity)
        if liquidity > 12:
            score += 0
        elif liquidity >= 6:
            score += 1
        elif liquidity >= 3:
            score += 3
        else:
            score += 5

    return score


def cdfi_class(score: int, record: dict[str, Any] | None = None) -> str:
    ltv = None if record is None else record.get("ltv")
    payment_status = None if record is None else record.get("payment_status")
    if ltv is not None and float(ltv) > 1.0 and (score >= 19 or payment_status == "Nonaccrual"):
        return "Projected Loss"
    if score <= 5:
        return "Prime"
    if score <= 9:
        return "Desirable"
    if score <= 13:
        return "Satisfactory"
    if score <= 18:
        return "Watch"
    return "Doubtful"


def recommended_action(rating: int | None, payment_status: str | None = None, projected_loss: bool = False) -> str:
    if projected_loss or rating is not None and rating >= 8 or payment_status == "Nonaccrual":
        return "partial_chargeoff_review"
    if rating is not None and rating >= 7:
        return "special_assets"
    if rating is not None and rating >= 6:
        return "watchlist"
    return "monitor"


def stressed_dscr(base_dscr: float | int | None, mode: str) -> float | None:
    if base_dscr is None:
        return None
    value = float(base_dscr)
    if mode == "watch_list":
        return round(value / 1.18, 2)
    if mode == "cre_dual":
        return round(value * 0.85 / 1.18, 2)
    raise ValueError("mode must be watch_list or cre_dual")


def current_metrics(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    if not metrics:
        return {}
    return sorted(metrics, key=lambda row: str(row.get("quarter", "")), reverse=True)[0]


def collect_command(args: argparse.Namespace) -> int:
    base_url = normalize_base_url(args.base_url)
    data: dict[str, Any] = {
        "manifest": fetch_json(base_url, "/api/manifest"),
        "policies": fetch_json(base_url, "/api/policies"),
    }
    if args.include_fdic:
        data["fdic_q4_2024"] = fetch_json(base_url, "/api/benchmarks/fdic/q4-2024")
    if args.include_ncua:
        data["ncua_q1_2025"] = fetch_json(base_url, "/api/benchmarks/ncua/q1-2025")
    if args.branch_id:
        branch = args.branch_id
        data["branch"] = fetch_json(base_url, f"/api/branches/{branch}")
        data["branch_metrics"] = fetch_json(base_url, f"/api/branches/{branch}/metrics")
        data["loans"] = fetch_json(base_url, f"/api/branches/{branch}/loans")
        data["sector_exposures"] = fetch_json(base_url, f"/api/branches/{branch}/sector-exposures")
        data["applications"] = fetch_json(base_url, f"/api/branches/{branch}/applications")
    if args.segment_id:
        data["credit_union_segment"] = fetch_json(base_url, f"/api/credit-union-segments/{args.segment_id}")

    text = json.dumps(data, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


def formulas_command(args: argparse.Namespace) -> int:
    formulas = {
        "benchmark_variance": "variance_ratio = branch_ratio - benchmark_ratio; variance_bps = variance_ratio * 10000",
        "watch_list_stress": "stressed_dscr = dscr / 1.18",
        "cre_dual_stress": "stressed_dscr = dscr * 0.85 / 1.18",
        "risk_rating": "final_rating = worst numeric rating from available DSCR, LTV, delinquency, and current-rating floor",
        "post_approval_pct": "post_sector_exposure / post_total_exposure",
        "remaining_capacity": "lending_capacity - sum(bank_capacity_used)",
    }
    print(json.dumps(formulas, indent=2, sort_keys=True))
    return 0


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_command(args: argparse.Namespace) -> int:
    template = load_json(args.template)
    answer_text = Path(args.answer).read_text(encoding="utf-8")
    try:
        answer = json.loads(answer_text)
    except json.JSONDecodeError as exc:
        print(f"FAIL: answer is not valid JSON: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    required_top = template.get("required_top_level_keys", [])
    for key in required_top:
        if key not in answer:
            errors.append(f"missing top-level key: {key}")

    fields = template.get("fields") or template.get("field_rules") or {}
    validate_fields(answer, fields, "$", errors)

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: JSON is valid against required keys, basic types, and enums")
    return 0


def validate_fields(value: Any, field_specs: dict[str, Any], path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path} should be an object")
        return
    for field_name, spec in field_specs.items():
        if not isinstance(spec, dict):
            continue
        required = spec.get("required") is True or field_name in spec.get("required_keys", [])
        if required and field_name not in value:
            errors.append(f"missing required key: {path}.{field_name}")
        if field_name in value:
            validate_value(value[field_name], spec, f"{path}.{field_name}", errors)


def validate_value(value: Any, spec: dict[str, Any], path: str, errors: list[str]) -> None:
    expected_type = spec.get("type")
    if expected_type == "object":
        nested = spec.get("fields") or {}
        if not isinstance(value, dict):
            errors.append(f"{path} should be object")
            return
        for key in spec.get("required_keys", []):
            if key not in value:
                errors.append(f"missing required key: {path}.{key}")
        validate_fields(value, nested, path, errors)
    elif expected_type in {"list", "set"}:
        if not isinstance(value, list):
            errors.append(f"{path} should be list")
            return
        item_fields = spec.get("item_fields")
        for idx, item in enumerate(value):
            item_path = f"{path}[{idx}]"
            if item_fields:
                if not isinstance(item, dict):
                    errors.append(f"{item_path} should be object")
                else:
                    for key in spec.get("item_required_keys", []):
                        if key not in item:
                            errors.append(f"missing required key: {item_path}.{key}")
                    validate_fields(item, item_fields, item_path, errors)
            else:
                allowed = spec.get("allowed_values") or spec.get("choices")
                if allowed and item not in allowed:
                    errors.append(f"{item_path} has enum value {item!r}, allowed {allowed}")
    elif expected_type == "string":
        if not isinstance(value, str):
            errors.append(f"{path} should be string")
    elif expected_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{path} should be integer")
    elif expected_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
            errors.append(f"{path} should be finite number")
        precision = spec.get("precision")
        if isinstance(precision, int) and round(float(value), precision) != float(value):
            errors.append(f"{path} should be rounded to {precision} decimals")
    elif expected_type == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{path} should be boolean")
    elif expected_type == "enum":
        allowed = spec.get("allowed_values") or spec.get("choices") or []
        if value not in allowed:
            errors.append(f"{path} has enum value {value!r}, allowed {allowed}")

    allowed = spec.get("allowed_values") or spec.get("choices")
    if allowed and expected_type != "list" and value not in allowed:
        errors.append(f"{path} has enum value {value!r}, allowed {allowed}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Credit office committee JSON helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="Fetch public API records into one JSON snapshot")
    collect.add_argument("--base-url", required=True)
    collect.add_argument("--branch-id")
    collect.add_argument("--segment-id")
    collect.add_argument("--out")
    collect.add_argument("--include-fdic", action=argparse.BooleanOptionalAction, default=True)
    collect.add_argument("--include-ncua", action=argparse.BooleanOptionalAction, default=True)
    collect.set_defaults(func=collect_command)

    formulas = subparsers.add_parser("formulas", help="Print common formulas")
    formulas.set_defaults(func=formulas_command)

    validate = subparsers.add_parser("validate", help="Check final answer against task template")
    validate.add_argument("--template", required=True)
    validate.add_argument("--answer", required=True)
    validate.set_defaults(func=validate_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
