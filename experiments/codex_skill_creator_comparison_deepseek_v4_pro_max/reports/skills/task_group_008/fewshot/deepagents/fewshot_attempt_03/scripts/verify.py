#!/usr/bin/env python3
import json, sys
def main():
    if len(sys.argv) < 2:
        print('Usage: verify.py <answer.json>')
        sys.exit(1)
    with open(sys.argv[1]) as f:
        a = json.load(f)
    ok = True
    cp, rp = a.get('conversion_plan',{}), a.get('rmd_projection',{})
    if cp:
        if cp.get('conversion_years') != cp.get('conversion_years_positive'):
            print('FAIL: conversion_years != conversion_years_positive'); ok = False
        tc = cp.get('annual_conversion_amount',0) * cp.get('conversion_years',0)
        if abs(tc - cp.get('total_converted',0)) > 0.02:
            print('FAIL: total_converted mismatch'); ok = False
    if rp:
        s = rp.get('baseline_rmd_tax_through_horizon',0) - rp.get('conversion_rmd_tax_through_horizon',0)
        if abs(s - rp.get('rmd_tax_savings_through_horizon',0)) > 0.02:
            print('FAIL: rmd_tax_savings mismatch'); ok = False
    if ok:
        print('Internal consistency OK')
    sys.exit(0 if ok else 1)
if __name__ == '__main__':
    main()
