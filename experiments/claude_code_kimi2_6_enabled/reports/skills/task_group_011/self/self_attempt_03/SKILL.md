# Credit Risk Committee JSON Skill

## Overview
Produce committee-ready JSON answers from a shared credit-office public API.  Tasks include:
- **Branch rating-migration review** (train_001, REDWOOD)
- **Lending-committee allocation package** (train_002, LAKEVIEW)
- **Credit-union segment posture page** (train_003, CIVIC_NC_FIRE_EMS)
- **Watch-list stress & workout review** (train_004, SUMMIT)
- **Competing CRE decision** (train_005, HARBOR)

## Environment
- Base URL is fixed in `environment_access.md` (e.g. `http://34.46.77.124:8011`).
- Do **not** run `env/setup.sh` or use `localhost`.

## API Workflow (transferable across tasks)
1. **Bootstrap**
   - `GET /api/manifest` → list of valid endpoints and record counts.
   - `GET /api/policies` → credit policy, CDFI scoring tables, stress formulas, risk-rating rules.
   - `GET /api/branches` → all branches with `branch_id`, `cre_policy_limit_pct`, `sector_ceiling_pct`, `lending_capacity_q1`, `total_assets`, `fdic_benchmark_set`, `institution_type`.

2. **Branch-level data**
   - `GET /api/branches/{branch_id}` → branch details.
   - `GET /api/branches/{branch_id}/metrics` → quarterly metrics (delinquency_30_plus_pct, total_loans_outstanding, nonperforming_loans, etc.).
   - `GET /api/branches/{branch_id}/loans` → full loan book with `current_rating`, `payment_status`, `days_past_due`, `dscr`, `ltv`, `debt_to_asset`, `liquidity_months`, `outstanding_balance`, `sector`.
   - `GET /api/branches/{branch_id}/sector-exposures` → sector limits, current exposure, grandfathered flags.
   - `GET /api/branches/{branch_id}/applications` → pending applications with `loan_type`, `sector`, `requested_amount`, `dscr`, `ltv`, `documentation_complete`, etc.

3. **Benchmarks**
   - `GET /api/benchmarks/fdic/q4-2024` → FDIC ratios (`total_real_estate_30_89_pct`, `total_loans_noncurrent_pct`, etc.).
   - `GET /api/benchmarks/ncua/q1-2025` → NCUA state-level metrics (delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct).

4. **Credit-union segments**
   - `GET /api/credit-union-segments/{segment_id}` → segment profile, capacity, controls, internal context, peer states.

## Core Business Rules

### Rating Re-derivation (applies to migration & watch-list tasks)
- Use the **dominant-factor rule**: final rating = worst numeric rating from DSCR, LTV/collateral, and delinquency factors.
- DSCR thresholds: ≥1.5→3, ≥1.25→4, ≥1.05→5, ≥1.0→6, <1.0→7.
- LTV thresholds: ≤0.65→3, ≤0.75→4, ≤0.85→5, ≤1.0→6, >1.0→7.
- Delinquency minimums: Current→null, 30 DPD→4, 60 DPD→5, 90+ DPD→7, Nonaccrual→8.
- **Material downgrade** = ≥2 notches. Track only loans whose final rating ≥ target threshold.

### CDFI Factor Scoring (applies to watch-list & CRE tasks)
- Sum scores for: debt_to_asset, fico, liquidity_months, ltv (each from policy tables).
- Classes: Prime 0-5, Desirable 6-9, Satisfactory 10-13, Watch 14-18, Doubtful ≥19, Projected Loss ≥19 **and** ltv>1.0.

### CRE Weighted Score (train_005)
- Weights: capacity 0.45, capital 0.03, character 0.05, collateral_exposure 0.36, conditions 0.11.
- Classes: approve_quality ≤2.0, conditional ≤3.0, weak >3.0.

### Stress Formulas (from policies)
- **CRE dual-stress**: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`
- **Watch-list stress**: `stressed_dscr = dscr / (1 + 0.18)` (the +200bp parallel shock)
- Breach threshold = 1.0 for both.

### Concentration & Capacity (train_002)
- `existing_cre_exposure` = sum of outstanding balances where `loan_type == "CRE"`.
- `existing_cre_concentration` = existing_cre_exposure / branch.total_assets.
- Post-approval concentration = (existing_cre_exposure + approved_amount) / total_assets.
- Policy variance bps = (post_approval_concentration - cre_policy_limit_pct) * 10000.
- Sector post-approval pct = (current_exposure + approved_amount) / total_assets.
- If post-approval pct > limit_pct, flag and apply mitigation (`participation_required`, `reduced_amount`, `board_exception`).
- Grandfathered exposure may not be increased without mitigation.

### NPA / Delinquency Benchmarking
- `branch_npa_ratio` = nonperforming_loans / total_loans_outstanding (from latest metrics quarter).
- `fdic_benchmark_ratio` = choose the matching metric from FDIC data (e.g. `total_loans_noncurrent_pct` for NPA, `total_real_estate_30_89_pct` for delinquency).
- `variance_ratio` = branch_ratio - benchmark_ratio.
- `variance_bps` = variance_ratio * 10000, rounded to 2 decimals.

## Output Conventions
- **Always** write pure JSON matching the task's `answer_template.json`. No markdown, no commentary outside the JSON.
- **Sort orders** (strictly obey template instructions):
  - Lists keyed by `application_id` or `loan_id`: ascending alphanumeric.
  - `conditions`, `reason_codes`: ascending alphabetical.
  - `workout_queue`: descending exposure, then ascending loan_id.
  - `severe_bucket_counts`: ascending current_rating, then payment_status.
  - `concentration_flags`: ascending sector, then application_id.
  - `post_approval_concentrations`: ascending sector.
- **Precision**:
  - Currency (USD): 2 decimals.
  - Percentages as ratios: 4 decimals (e.g. 0.2853).
  - Bps / variance: 2 decimals.
  - DSCR / stressed DSCR: 2 decimals.
  - Weighted CDFI score: 1 decimal.

## Common Pitfalls
1. **Using current_rating instead of re-derived final_rating** for migration and watch-list tasks. Always re-derive per the dominant-factor rule.
2. **Ignoring null DSCR/LTV** — loans without DSCR cannot be stressed; omit from stress results or handle gracefully (do not crash).
3. **Wrong benchmark metric** — match the metric name exactly to the task context (NPA → `total_loans_noncurrent_pct`, CRE delinquency → `total_real_estate_30_89_pct`).
4. **Forgetting grandfathered flags** in sector exposures — grandfathered sectors have a higher limit; new approvals in those sectors still need mitigation if they would increase exposure.
5. **Miscomputing CRE concentration** — use `total_assets` from branch details, not `lending_capacity_q1`.
6. **Wrong stress formula** — watch-list uses `dscr / 1.18`; CRE dual-stress uses `dscr * 0.85 / 1.18`.
7. **Including non-CRE loans in CRE exposure** — filter by `loan_type == "CRE"`.
8. **Missing `documentation_complete == 0`** as a decline/conditional trigger (reason code `documentation_gap`).
9. **Credit-union tasks**: use NCUA benchmarks, not FDIC. Match segment's `state_code` to the NCUA row. Peer comparison uses the segment's `peer_states` list.
10. **Posture page**: `required_checklist_gates` is the intersection of the segment's `minimum_checklist` and the allowed enum; `added_operating_controls` are chosen based on identified risks (e.g. delinquency watch, lien perfection, quarterly monitoring).

## Quick Reference: Decision Enum
- `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`

## Quick Reference: Action Enum (workout / watch-list)
- `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`

## Quick Reference: Reason Codes (decline / conditional)
- `capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`
