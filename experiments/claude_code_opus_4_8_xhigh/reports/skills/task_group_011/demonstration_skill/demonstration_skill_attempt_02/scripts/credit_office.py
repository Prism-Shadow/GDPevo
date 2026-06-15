#!/usr/bin/env python3
"""
Helper for the Credit Office / lending-committee task family.

API client + policy-driven computations. The policy endpoint is the source of truth, so the
threshold functions read the live policy object you pass in rather than hardcoding numbers.

Usage:
    from credit_office import API, Policy
    api = API()                      # http://127.0.0.1:8003
    pol = Policy(api.policies())
    loans = api.loans("REDWOOD")
    final = pol.rederive_rating(loans[0])

Run `python credit_office.py smoke REDWOOD` for a quick sanity print.

All currency rounding is 2 dp, ratios 4 dp, bps from UNROUNDED ratios then 2 dp. Use r2/r4/bps.
"""
import json
import sys
import urllib.request
import urllib.parse

BASE = "http://127.0.0.1:8003"


# ---------- rounding helpers ----------
def r2(x):  # currency / dscr
    return round(float(x), 2)


def r4(x):  # ratios / percentages-as-ratios
    return round(float(x), 4)


def bps(branch_ratio, bench_ratio):
    """Variance in bps from UNROUNDED ratios, then round 2 dp. Do not feed pre-rounded ratios."""
    return round((float(branch_ratio) - float(bench_ratio)) * 10000.0, 2)


# ---------- API client ----------
class API:
    def __init__(self, base=BASE):
        self.base = base

    def _get(self, path, **params):
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        with urllib.request.urlopen(url) as r:
            return json.load(r)

    def health(self):            return self._get("/api/health")
    def manifest(self):          return self._get("/api/manifest")
    def policies(self):          return self._get("/api/policies")
    def branches(self, institution_type=None):
        return self._get("/api/branches", institution_type=institution_type)
    def branch(self, bid):       return self._get(f"/api/branches/{bid}")
    def metrics(self, bid, quarter=None):
        return self._get(f"/api/branches/{bid}/metrics", quarter=quarter)
    def loans(self, bid, loan_type=None, payment_status=None, min_current_rating=None):
        return self._get(f"/api/branches/{bid}/loans", loan_type=loan_type,
                         payment_status=payment_status, min_current_rating=min_current_rating)
    def sector_exposures(self, bid):
        return self._get(f"/api/branches/{bid}/sector-exposures")
    def applications(self, bid, loan_type=None):
        return self._get(f"/api/branches/{bid}/applications", loan_type=loan_type)
    def fdic(self):              return self._get("/api/benchmarks/fdic/q4-2024")
    def ncua(self, state_code=None):
        return self._get("/api/benchmarks/ncua/q1-2025", state_code=state_code)
    def segment(self, sid):      return self._get(f"/api/credit-union-segments/{sid}")

    def metrics_for(self, bid, quarter="2025Q1"):
        """Return the single metrics row for the given quarter (default the as-of quarter)."""
        rows = self.metrics(bid, quarter)
        if isinstance(rows, list):
            for row in rows:
                if row.get("quarter") == quarter:
                    return row
            return rows[0] if rows else None
        return rows


# ---------- policy-driven math ----------
class Policy:
    def __init__(self, pol):
        self.pol = pol
        self.rr = pol["risk_rating"]
        self.cdfi = pol["cdfi_factor_scores"]
        self.cre = pol["cre_weighted_score"]
        self.stress = pol["stress"]

    # --- risk rating re-derivation (dominant-factor: worst available) ---
    def dscr_rating(self, dscr):
        if dscr is None:
            return None
        for t in self.rr["dscr_thresholds"]:
            if "min" in t and dscr >= t["min"]:
                return t["rating"]
        for t in self.rr["dscr_thresholds"]:
            if "max_below" in t:   # below the lowest min
                return t["rating"]
        return None

    def ltv_rating(self, ltv):
        if ltv is None:
            return None
        for t in self.rr["ltv_thresholds"]:
            if "max" in t and ltv <= t["max"]:
                return t["rating"]
        for t in self.rr["ltv_thresholds"]:
            if "min_above" in t:   # above the highest max
                return t["rating"]
        return None

    def delinquency_floor(self, payment_status):
        return self.rr["delinquency_minimums"].get(payment_status)

    def rederive_rating(self, loan):
        cands = [c for c in (self.dscr_rating(loan.get("dscr")),
                             self.ltv_rating(loan.get("ltv")),
                             self.delinquency_floor(loan.get("payment_status")))
                 if c is not None]
        if cands:
            return max(cands)
        return loan.get("current_rating")  # no objective factor -> keep current rating

    def is_material_downgrade(self, current_rating, final_rating):
        return (final_rating - current_rating) >= self.rr["material_downgrade_notches"]

    # --- CDFI factor scoring (additive, lower better; missing factor -> 0) ---
    def _fico_score(self, f):
        if f is None: return 0
        if f > 720: return 0
        if f >= 680: return 1
        if f >= 580: return 3
        return 5

    def _band_score(self, v, key):
        """0.40-0.60 style bands, upper-inclusive; used for ltv and debt_to_asset."""
        if v is None: return 0
        if v < 0.40: return 0
        if v <= 0.60: return 2
        if v <= 0.80: return 4
        return 6

    def _liq_score(self, v):
        if v is None: return 0
        if v > 12: return 0
        if v >= 6: return 1
        if v >= 3: return 3
        return 5

    def factor_score(self, obj, ltv=None, dta=None):
        ltv = obj.get("ltv") if ltv is None else ltv
        if dta is None:
            dta = obj.get("debt_to_asset")
            if dta is None and obj.get("total_assets"):
                dta = obj["total_debt"] / obj["total_assets"]
        return (self._fico_score(obj.get("fico"))
                + self._band_score(ltv, "ltv")
                + self._band_score(dta, "dta")
                + self._liq_score(obj.get("liquidity_months")))

    def risk_class(self, score, ltv):
        # Projected Loss override: Watch-band-or-worse + underwater collateral (ltv > 1.0).
        if score >= 14 and ltv is not None and ltv > 1.0:
            return "Projected Loss"
        if score >= 19:
            return "Doubtful"
        if score >= 14:
            return "Watch"
        if score >= 10:
            return "Satisfactory"
        if score >= 6:
            return "Desirable"
        return "Prime"

    # --- stress ---
    def watch_list_stress(self, dscr):
        if dscr is None: return None
        return dscr / (1 + 0.18)

    def cre_dual_stress(self, dscr):
        if dscr is None: return None
        return dscr * 0.85 / (1 + 0.18)

    @property
    def breach_threshold(self):
        return self.stress["coverage_breach_threshold"]

    # --- action mapping by effective severity rating ---
    @staticmethod
    def recommended_action(rating, payment_status=None, risk_class=None):
        if rating is not None and rating >= 8 or payment_status == "Nonaccrual" \
                or risk_class == "Projected Loss":
            return "partial_chargeoff_review"
        if rating == 7 or payment_status == "90+ Days Past Due":
            return "special_assets"
        if rating == 6:
            return "watchlist"
        return "monitor"

    # --- CRE weighted score ---
    def cre_weighted_score(self, capacity_s, collateral_s, conditions_s, character_s, capital_s):
        w = self.cre["weights"]
        return (w["capacity"] * capacity_s + w["collateral_exposure"] * collateral_s
                + w["conditions"] * conditions_s + w["character"] * character_s
                + w["capital"] * capital_s)

    def cre_score_class(self, score):
        for c in self.cre["classes"]:
            if "max" in c and score <= c["max"]:
                return c["class"]
        return "weak"


def smoke(bid="REDWOOD"):
    api = API()
    pol = Policy(api.policies())
    loans = api.loans(bid)
    m = api.metrics_for(bid)
    print(f"{bid}: {len(loans)} loans; metrics quarter {m.get('quarter')}")
    for ln in loans[:5]:
        print(f"  {ln['loan_id']} cur={ln['current_rating']} -> final={pol.rederive_rating(ln)} "
              f"(dscr={ln.get('dscr')} ltv={ln.get('ltv')} ps={ln.get('payment_status')})")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "smoke":
        smoke(sys.argv[2] if len(sys.argv) > 2 else "REDWOOD")
    else:
        print(__doc__)
