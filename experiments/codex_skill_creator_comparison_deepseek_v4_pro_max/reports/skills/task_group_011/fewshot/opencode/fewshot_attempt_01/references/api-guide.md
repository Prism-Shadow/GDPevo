# API Guide

The shared credit office exposes a public REST API at the base URL provided as
`<TASK_ENV_BASE_URL>` in the prompt. All endpoints are GET requests. No
authentication is required.

## Endpoint Catalog

### Discovery

**GET /api/manifest**
Returns available endpoints and response field descriptions. Always fetch this
first to understand what data each endpoint exposes and to confirm field names
before writing extraction logic.

Example usage:
```
curl -s <TASK_ENV_BASE_URL>/api/manifest | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d,indent=2))"
```

### Policies

**GET /api/policies**
Returns the institution's credit policies: rating thresholds, concentration
limits, capacity formulas, DSCR/LTV/FICO floors, benchmark selection guidance,
and action-mapping rules.

This endpoint is authoritative for all threshold values. When it provides
explicit numbers or rules, those override the standard conventions in
`references/formulas.md` and `references/rating-guide.md`.

Typical policy fields include:
- `rating_thresholds` — DSCR, LTV, FICO bands for rating assignment
- `concentration_limits` — per-sector maximum exposure percentages
- `capacity_formula` — how lending capacity is computed from branch metrics
- `dscr_floor` — minimum acceptable DSCR
- `ltv_ceiling` — maximum acceptable LTV
- `fico_minimum` — minimum credit score
- `benchmark_guidance` — which benchmark metric to use for given review types
- `cdfi_factor_weights` — weights for factor score computation (if applicable)

### Branch Data

**GET /api/branches/{branch_id}**
Branch metadata: name, region, total assets, branch type.

**GET /api/branches/{branch_id}/metrics**
Key financial metrics for the branch:
- `total_loans` — gross loan portfolio size (USD)
- `lending_capacity` — available lending headroom (USD)
- `npa_exposure` — non-performing asset exposure (USD)
- `npa_ratio` — may be precomputed; recompute from npa_exposure / total_loans anyway
- `delinquency_ratios` — by aging bucket (30, 60, 90+ days, nonaccrual)
- `roaa` — return on average assets if applicable

**GET /api/branches/{branch_id}/loans**
The branch loan portfolio. Each loan object typically has:
- `loan_id` — unique identifier (string, e.g. "BRANCH-LN-001")
- `borrower_name` — borrower or entity name
- `current_rating` — risk rating 1-8 as currently booked
- `exposure` — outstanding balance (USD)
- `dscr` — debt service coverage ratio (may be null for some loan types)
- `ltv` — loan-to-value ratio (may be null)
- `fico` — borrower credit score (may be null)
- `payment_status` — one of: Current, 30 Days Past Due, 60 Days Past Due, 90+ Days Past Due, Nonaccrual
- `sector` — industry sector classification
- `origination_date` — loan origination date
- `maturity_date` — loan maturity date
- `collateral_type` — type of collateral securing the loan
- `guarantor` — SBA or other guarantee flag

**GET /api/branches/{branch_id}/sector-exposures**
Per-sector breakdown of the branch's loan portfolio:
- `sector` — sector name
- `exposure` — total USD exposure in that sector
- `limit_pct` — policy concentration limit for that sector (as a ratio, e.g. 0.19)
- `current_concentration_pct` — current concentration percentage

**GET /api/branches/{branch_id}/applications**
Pending loan applications for the branch. Each application typically has:
- `application_id` — unique identifier (string, e.g. "BRANCH-APP-001")
- `borrower_name` — applicant name
- `requested_amount` — amount requested (USD)
- `sector` — industry sector
- `dscr` — projected DSCR
- `ltv` — projected LTV
- `fico` — applicant credit score
- `business_age_years` — years in business
- `startup_flag` — boolean for startup businesses
- `bankruptcy_flag` — boolean for recent bankruptcy history
- `collateral_value` — appraised collateral value
- `participation_available` — whether a participation partner is available
- `sba_eligible` — whether SBA guaranty is available
- `cdfi_factors` — factor scores for CDFI scoring (if applicable)

### Credit Union Segments

**GET /api/credit-union-segments/{segment_id}**
Segment details for credit union posture analysis:
- `segment_id` — segment identifier
- `segment_name` — human-readable name
- `state_code` — two-letter state code
- `lending_capacity` — segment capacity
- `current_utilization` — capacity currently in use
- `state_metrics` — delinquency, loan-to-share, ROAA, positive net income %
- `peer_states` — list of peer state codes for comparison

### Benchmarks

**GET /api/benchmarks/fdic/q4-2024**
FDIC Quarterly Banking Profile Q4 2024. National aggregate ratios for insured
institutions. Key fields:
- `total_loans_noncurrent_pct` — noncurrent loans as % of total loans
- `total_real_estate_noncurrent_pct` — noncurrent RE loans as % of total RE loans
- `total_real_estate_30_89_pct` — 30-89 day past due RE loans as % of total RE loans
- `construction_development_noncurrent_pct` — noncurrent C&D loans as % of C&D loans
- Various other aggregate ratios

Use the decimal form of these percentages (0.0098 = 0.98%, not 98).

**GET /api/benchmarks/ncua/q1-2025**
NCUA Q1 2025 credit union call report aggregates. National and state-level
metrics for credit unions. Key fields:
- National-level delinquency, loan-to-share, ROAA, positive net income percentages
- State-level breakdowns of the same metrics

---

## Parsing Patterns

### Extracting Branch Total Loans

Look for `total_loans` or `total_loan_portfolio` in the branch metrics response.
This is the denominator for all concentration and NPA ratio calculations.

### Extracting NPA Exposure

Look for `npa_exposure`, `nonperforming_loans`, or `nonaccrual_exposure` in the
branch metrics or loans response. When not directly available, sum the exposure
of all loans with `payment_status == "Nonaccrual"` from the loans endpoint.

### Extracting Sector Exposure and Limits

From the sector-exposures endpoint, map each sector to its `exposure` (USD) and
`limit_pct` (ratio). The `limit_pct` is the policy maximum for that sector.

### Handling Missing Fields

When a loan or application is missing a DSCR, LTV, or FICO value, do not
fabricate data. For regrades, rate using the available factors only. For stress
tests, skip loans without DSCR. For reason codes, missing data may itself be a
reason to flag (use `documentation_gap` or `policy_floor_missing`).

### Parallel Fetching

Use shell backgrounding or separate curl calls. Example pattern:

```bash
curl -s "$BASE/api/manifest" > /tmp/manifest.json &
curl -s "$BASE/api/policies" > /tmp/policies.json &
curl -s "$BASE/api/branches/$BID" > /tmp/branch.json &
curl -s "$BASE/api/branches/$BID/metrics" > /tmp/metrics.json &
curl -s "$BASE/api/branches/$BID/loans" > /tmp/loans.json &
curl -s "$BASE/api/branches/$BID/sector-exposures" > /tmp/sectors.json &
curl -s "$BASE/api/benchmarks/fdic/q4-2024" > /tmp/fdic.json &
wait
```

Then parse each file with Python or jq. Use Python when computations are
needed; use jq for quick field extraction.
