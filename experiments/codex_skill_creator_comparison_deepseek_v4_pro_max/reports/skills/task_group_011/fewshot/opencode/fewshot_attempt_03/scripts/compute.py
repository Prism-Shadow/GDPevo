#!/usr/bin/env python3
"""Credit-risk committee helper: deterministic policy computations.

Usage:
  python3 scripts/compute.py rating loans.json policies.json
  python3 scripts/compute.py cdfi loans.json policies.json
  python3 scripts/compute.py stress loans.json [watchlist|cre]
  python3 scripts/compute.py benchmark-fdic metrics.json fdic.json
  python3 scripts/compute.py ncua-median ncua.json SC,TN,VA

Each command writes enriched JSON to stdout. Input files are raw API responses.
"""

import json as _json, sys as _sys


def _load(path):
    with open(path) as f:
        return _json.load(f)


def dscr_to_rating(dscr):
    if dscr is None:
        return None
    if dscr >= 1.50: return 3
    if dscr >= 1.25: return 4
    if dscr >= 1.05: return 5
    if dscr >= 1.00: return 6
    return 7


def ltv_to_rating(ltv):
    if ltv is None:
        return None
    if ltv <= 0.65: return 3
    if ltv <= 0.75: return 4
    if ltv <= 0.85: return 5
    if ltv <= 1.00: return 6
    return 7


def delinquency_floor(status):
    floors = {
        'Current': None,
        '30 Days Past Due': 4,
        '60 Days Past Due': 5,
        '90+ Days Past Due': 7,
        'Nonaccrual': 8,
    }
    return floors.get(status, None)


def final_rating(loan):
    ratings = []
    r = dscr_to_rating(loan.get('dscr'))
    if r is not None:
        ratings.append(r)
    ltv = loan.get('ltv')
    if ltv is None and loan.get('collateral_value'):
        ltv = loan['outstanding_balance'] / loan['collateral_value']
    r = ltv_to_rating(ltv)
    if r is not None:
        ratings.append(r)
    r = delinquency_floor(loan.get('payment_status'))
    if r is not None:
        ratings.append(r)
    return max(ratings) if ratings else loan.get('current_rating', 3)


def score_factor(value, table):
    if value is None:
        return 0
    for entry in table:
        rng = entry['range']
        if rng.startswith('<'):
            if value < float(rng[1:]):
                return entry['score']
        elif rng.startswith('>'):
            if value > float(rng[1:]):
                return entry['score']
        elif '-' in rng:
            lo, hi = rng.split('-')
            if float(lo) <= value <= float(hi):
                return entry['score']
    return 0


def cdfi_factor_score(loan_or_app, policies):
    cdfi = policies['cdfi_factor_scores']
    score = 0
    for factor in ['fico', 'ltv', 'debt_to_asset', 'liquidity_months']:
        val = loan_or_app.get(factor)
        if factor == 'ltv' and val is None and loan_or_app.get('collateral_value'):
            val = loan_or_app['outstanding_balance'] / loan_or_app['collateral_value']
        score += score_factor(val, cdfi[factor])
    return score


def cdfi_risk_class(score, ltv=None):
    if ltv is not None and ltv > 1.0:
        return 'Projected Loss'
    if score >= 19:
        return 'Doubtful'
    if score >= 14:
        return 'Watch'
    if score >= 10:
        return 'Satisfactory'
    if score >= 6:
        return 'Desirable'
    return 'Prime'


def action_for_rating(rating):
    if rating >= 8:
        return 'partial_chargeoff_review'
    if rating >= 7:
        return 'special_assets'
    if rating >= 5:
        return 'watchlist'
    return 'monitor'


def stressed_dscr_watchlist(dscr):
    return round(dscr / 1.18, 2)


def stressed_dscr_cre(dscr):
    return round(dscr * 0.85 / 1.18, 2)


def compute_benchmark(branch_value, branch_total, benchmark_value):
    ratio = branch_value / branch_total
    variance = ratio - benchmark_value
    return {
        'branch_ratio': round(ratio, 4),
        'benchmark_ratio': benchmark_value,
        'variance_ratio': round(variance, 4),
        'variance_bps': round(variance * 10000, 2),
    }


# --- CLI ---

if __name__ == '__main__':
    cmd = _sys.argv[1] if len(_sys.argv) > 1 else 'help'

    if cmd == 'rating':
        loans = _load(_sys.argv[2])
        for loan in loans:
            loan['computed_final_rating'] = final_rating(loan)
        _json.dump(loans, _sys.stdout, indent=2)

    elif cmd == 'cdfi':
        items = _load(_sys.argv[2])
        policies = _load(_sys.argv[3])
        for item in items:
            score = cdfi_factor_score(item, policies)
            ltv = item.get('ltv')
            if ltv is None and item.get('collateral_value'):
                ltv = item['outstanding_balance'] / item['collateral_value']
            item['computed_cdfi_score'] = score
            item['computed_risk_class'] = cdfi_risk_class(score, ltv)
        _json.dump(items, _sys.stdout, indent=2)

    elif cmd == 'stress':
        items = _load(_sys.argv[2])
        mode = _sys.argv[3] if len(_sys.argv) > 3 else 'watchlist'
        fn = stressed_dscr_cre if mode == 'cre' else stressed_dscr_watchlist
        results = []
        for item in items:
            dscr = item.get('dscr')
            if dscr is None:
                continue
            s = fn(dscr)
            results.append({
                'loan_id': item.get('loan_id', item.get('application_id')),
                'base_dscr': dscr,
                'stressed_dscr': s,
                'breaches_threshold': s < 1.0,
            })
        _json.dump(results, _sys.stdout, indent=2)

    elif cmd == 'benchmark-fdic':
        metrics = _load(_sys.argv[2])
        fdic = _load(_sys.argv[3])
        latest = metrics[0]
        total = latest['total_loans_outstanding']
        npa = latest['nonperforming_loans']
        result = {
            'branch_total_loans': total,
            'branch_npa': npa,
            'noncurrent': compute_benchmark(npa, total, fdic['total_loans_noncurrent_pct']),
            'real_estate_noncurrent': compute_benchmark(npa, total, fdic['total_real_estate_noncurrent_pct']),
            'real_estate_30_89': compute_benchmark(npa, total, fdic['total_real_estate_30_89_pct']),
            'construction_noncurrent': compute_benchmark(npa, total, fdic['construction_development_noncurrent_pct']),
        }
        _json.dump(result, _sys.stdout, indent=2)

    elif cmd == 'ncua-median':
        ncua = _load(_sys.argv[2])
        peers = _sys.argv[3].split(',')
        rows = {r['state_code']: r for r in ncua['rows']}
        medians = {}
        for metric in ['delinquency_bps', 'loan_to_share_pct', 'roaa_bps', 'positive_net_income_pct']:
            vals = sorted(rows[p][metric] for p in peers if p in rows)
            if len(vals) % 2 == 1:
                medians[metric] = vals[len(vals) // 2]
            else:
                medians[metric] = (vals[len(vals)//2 - 1] + vals[len(vals)//2]) / 2
        _json.dump(medians, _sys.stdout, indent=2)

    else:
        print('Commands: rating, cdfi, stress, benchmark-fdic, ncua-median', file=_sys.stderr)
        _sys.exit(1)
