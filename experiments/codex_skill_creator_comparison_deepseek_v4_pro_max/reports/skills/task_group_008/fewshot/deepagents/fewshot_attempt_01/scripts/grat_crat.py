#!/usr/bin/env python3
"""
GRAT and CRAT trust projection engine for private-wealth advisory.

Usage:
  python3 grat_crat.py --asset-value AMOUNT --expected-growth RATE
      --grat-term YEARS --grat-annuity-rate RATE --crat-term YEARS
      --crat-payout-rate RATE --estate-tax-rate RATE
      --charitable-deduction-rate RATE

Output: JSON with grat_remainder, grat_estate_tax_reduction,
        crat_remainder, crat_income_tax_deduction.
"""
import argparse, json, sys


def grat_remainder(asset, growth, term, annuity_rate):
    annuity = asset * annuity_rate
    return asset * ((1 + growth) ** term) - annuity * term


def crat_remainder(asset, growth, term, payout_rate):
    annuity = asset * payout_rate
    return asset * ((1 + growth) ** term) - annuity * term


def main():
    p = argparse.ArgumentParser(description="GRAT/CRAT trust projector")
    p.add_argument("--asset-value", type=float, required=True)
    p.add_argument("--expected-growth", type=float, required=True)
    p.add_argument("--grat-term", type=int, required=True)
    p.add_argument("--grat-annuity-rate", type=float, required=True)
    p.add_argument("--crat-term", type=int, required=True)
    p.add_argument("--crat-payout-rate", type=float, required=True)
    p.add_argument("--estate-tax-rate", type=float, required=True)
    p.add_argument("--charitable-deduction-rate", type=float, required=True)
    args = p.parse_args()

    grat_rem = grat_remainder(args.asset_value, args.expected_growth,
                              args.grat_term, args.grat_annuity_rate)
    grat_reduction = grat_rem * args.estate_tax_rate

    crat_rem = crat_remainder(args.asset_value, args.expected_growth,
                              args.crat_term, args.crat_payout_rate)
    crat_deduction = crat_rem * args.charitable_deduction_rate

    result = {
        "grat_remainder": round(grat_rem, 2),
        "grat_estate_tax_reduction": round(grat_reduction, 2),
        "crat_remainder": round(crat_rem, 2),
        "crat_income_tax_deduction": round(crat_deduction, 2),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

