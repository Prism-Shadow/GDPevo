#!/usr/bin/env python3
"""
Roth conversion and RMD projection engine for private-wealth advisory.

Usage:
  python3 roth_projection.py --traditional BALANCE --roth BALANCE --return RATE
      --rmd-start-age AGE --client-age AGE --horizon YEAR --planning-year YEAR
      --marginal-rate RATE --annual-income AMOUNT --bracket-target AMOUNT
      --conversion-years N

Output: JSON with baseline_rmd_tax, conversion_rmd_tax, rmd_savings,
        projected_roth, projected_traditional, annual_conversion,
        total_converted, total_conversion_tax.
"""
import argparse, json, sys

RMD_FACTORS = {
    73: 26.5, 74: 25.5, 75: 24.6, 76: 23.7, 77: 22.9, 78: 22.0, 79: 21.1,
    80: 20.2, 81: 19.4, 82: 18.5, 83: 17.7, 84: 16.8, 85: 16.0, 86: 15.2,
    87: 14.4, 88: 13.7, 89: 12.9, 90: 12.2, 91: 11.5, 92: 10.8, 93: 10.1,
    94: 9.5,  95: 8.9,  96: 8.4,  97: 7.8,  98: 7.3,  99: 6.8,
}


def compute_baseline(traditional_balance, expected_return, rmd_start_age,
                     client_age, planning_year, horizon_year, marginal_rate):
    trad = traditional_balance
    tax = 0.0
    for yr in range(planning_year, horizon_year + 1):
        age = client_age + (yr - planning_year)
        if age >= rmd_start_age:
            rmd = trad / RMD_FACTORS[age]
            trad -= rmd
            tax += rmd * marginal_rate
        trad *= (1.0 + expected_return)
    return round(tax, 2)


def compute_conversion(traditional_balance, roth_balance, expected_return,
                       rmd_start_age, client_age, planning_year, horizon_year,
                       marginal_rate, annual_conversion, conversion_years):
    trad = traditional_balance
    roth = roth_balance
    rmd_tax = 0.0
    for yr in range(planning_year, horizon_year + 1):
        age = client_age + (yr - planning_year)
        if (yr - planning_year) < conversion_years:
            trad -= annual_conversion
            roth += annual_conversion
        if age >= rmd_start_age:
            rmd = trad / RMD_FACTORS[age]
            trad -= rmd
            rmd_tax += rmd * marginal_rate
        trad *= (1.0 + expected_return)
        roth *= (1.0 + expected_return)
    return round(trad, 2), round(roth, 2), round(rmd_tax, 2)


def main():
    p = argparse.ArgumentParser(description="Roth conversion RMD projector")
    p.add_argument("--traditional", type=float, required=True)
    p.add_argument("--roth", type=float, default=0.0)
    p.add_argument("--return", dest="ereturn", type=float, required=True)
    p.add_argument("--rmd-start-age", type=int, required=True)
    p.add_argument("--client-age", type=int, required=True)
    p.add_argument("--horizon", type=int, required=True, help="horizon year")
    p.add_argument("--planning-year", type=int, required=True)
    p.add_argument("--marginal-rate", type=float, required=True)
    p.add_argument("--annual-income", type=float, required=True)
    p.add_argument("--bracket-target", type=float, required=True)
    p.add_argument("--conversion-years", type=int, required=True)
    args = p.parse_args()

    annual_conv = max(0.0, args.bracket_target - args.annual_income)
    total_converted = round(annual_conv * args.conversion_years, 2)
    total_conv_tax = round(annual_conv * args.marginal_rate * args.conversion_years, 2)

    baseline_tax = compute_baseline(args.traditional, args.ereturn,
                                    args.rmd_start_age, args.client_age,
                                    args.planning_year, args.horizon,
                                    args.marginal_rate)
    trad_end, roth_end, conv_rmd_tax = compute_conversion(
        args.traditional, args.roth, args.ereturn, args.rmd_start_age,
        args.client_age, args.planning_year, args.horizon,
        args.marginal_rate, annual_conv, args.conversion_years)

    result = {
        "annual_conversion": round(annual_conv, 2),
        "total_converted": total_converted,
        "total_conversion_tax": total_conv_tax,
        "baseline_rmd_tax": baseline_tax,
        "conversion_rmd_tax": conv_rmd_tax,
        "rmd_tax_savings": round(baseline_tax - conv_rmd_tax, 2),
        "projected_roth": roth_end,
        "projected_traditional": trad_end,
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

