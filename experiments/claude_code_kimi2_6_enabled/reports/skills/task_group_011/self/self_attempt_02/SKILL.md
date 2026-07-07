# Credit Risk Committee JSON Skill

## API Workflow

1. **Read environment**: Get `GDPEVO_ENV_BASE_URL` from `environment_access.md`.
2. **Discover data**:
   - `GET /api/manifest` — lists all endpoints and record counts.
   - `GET /api/branches` — resolve the target branch; prompts may use aliases (e.g., "Eastfield" → `EASTGATE`), so match by application prefix or branch state.
   - `GET /api/branches/{branch_id}` — branch profile (`total_assets`, `lending_capacity_q1`, `cre_policy_limit_pct`, `sector_ceiling_pct`, `institution_type`, `state_code`).
   - `GET /api/branches/{branch_id}/metrics` — latest quarter metrics (use `2025Q1`); note `delinquency_30_plus_pct` and `total_loans_outstanding`.
   - `GET /api/branches/{branch_id}/loans` — outstanding balances, loan types, sectors, payment status, days past due, DSCR, LTV, FICO, debt-to-asset, liquidity months.
   - `GET /api/branches/{branch_id}/sector-exposures` — current exposure per sector with limit.
   - `GET /api/branches/{branch_id}/applications` — filter for the target application IDs.
   - `GET /api/policies` — scoring rules, thresholds, weights.
   - `GET /api/benchmarks/fdic/q4-2024` — benchmark ratios.
   - `GET /api/benchmarks/ncua/q1-2025` — for credit unions, match by `state_code`.
3. **Compute scores** using the policy definitions below.
4. **Emit JSON** exactly matching the task `answer_template.json`; no narrative outside JSON.

---

## Scoring & Business Rules

### 1. CDFI Factor Scoring (train_001 style)
From `/api/policies` → `cdfi_factor_scores`, sum applicable factor scores (0 = best):

| Factor | Score 0 | Score 1 | Score 2 | Score 3 | Score 4 | Score 5 | Score 6 |
|--------|---------|---------|---------|---------|---------|---------|---------|
| **fico** | >720 | 680–720 | — | 580–679 | — | <580 | — |
| **ltv** | <0.40 | — | 0.40–0.60 | — | 0.60–0.80 | — | >0.80 |
| **debt_to_asset** | <0.40 | — | 0.40–0.60 | — | 0.60–0.80 | — | >0.80 |
| **liquidity_months** | >12 | 6–12 | — | 3–6 | — | <3 | — |

- **weighted_cdfi_score** = sum of all *available* factor scores (precision 1). Missing fields contribute 0.
- **score_class** mapping:
  - `prime`: 0–5
  - `desirable`: 6–9
  - `satisfactory`: 10–13
  - `watch`: 14–18
  - `doubtful`: ≥19 (use `projected_loss` only if ≥19 **and** `ltv > 1.0`)
- **Decision logic**: Lower score is better. Rank ascending. The best may still be `decline`/`defer` if capacity or sector limits are breached.

### 2. CRE Weighted Score (train_005 style)
From `/api/policies` → `cre_weighted_score`:

| Component | Weight |
|-----------|--------|
| capacity | 0.45 |
| capital | 0.03 |
| character | 0.05 |
| collateral_exposure | 0.36 |
| conditions | 0.11 |

- Each component is rated on a scale where **lower is better** (e.g., 1 = best, 5 = worst).
- **score_class**:
  - `approve_quality`: weighted score ≤ 2.0
  - `conditional`: weighted score ≤ 3.0
  - `weak`: weighted score > 3.0
- **Capacity**: use DSCR thresholds from risk rating (1.5+ → best, 1.25+ → next, etc.).
- **Collateral_exposure**: use LTV thresholds (≤0.65 best, ≤0.75 next, etc.).
- **Capital**: judge from `total_assets` vs `total_debt` (equity position) or `debt_to_asset`.
- **Character**: relationship length, prior delinquencies, bankruptcy, guarantor strength.
- **Conditions**: documentation completeness, market/sector notes, SBA guaranty.

### 3. Risk Rating (dominant factor rule)
From `/api/policies` → `risk_rating`:
- DSCR rating, LTV rating, delinquency rating — final rating is the **worst** available.
- Delinquency minimums: Current → none; 30 DPD → 4; 60 DPD → 5; 90+ DPD → 7; Nonaccrual → 8.

### 4. Stress Testing (CRE)
From `/api/policies` → `stress`:
- **CRE dual-stress formula**: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`
- **Coverage breach threshold**: 1.00
- `breaches_threshold`: `true` if `stressed_dscr < 1.00`

### 5. Capacity & Concentration
- **Lending capacity**: `branches.lending_capacity_q1`. Requested amount must not exceed residual capacity.
- **Sector ceiling**: `branches.sector_ceiling_pct` (default) or `sector_exposures.limit_pct` (per-sector override). Compute post-approval exposure vs limit.
- **CRE concentration**: `existing_cre_exposure` = sum of `outstanding_balance` for all loans where `loan_type == "CRE"`.
  - `existing_cre_concentration` = `existing_cre_exposure / total_assets`
  - `selected_post_approval_cre_concentration` = `(existing_cre_exposure + selected_requested_amount) / total_assets`
  - `selected_policy_variance_bps` = (`selected_post_approval_cre_concentration` − `cre_policy_limit_pct`) × 10,000
- **FDIC benchmark** (bank branches):
  - Metric: `total_real_estate_30_89_pct` = 0.0051
  - `branch_delinquency_ratio` = latest `delinquency_30_plus_pct`
  - `fdic_variance_ratio` = `branch_delinquency_ratio` − `fdic_benchmark_ratio`
  - `fdic_variance_bps` = `fdic_variance_ratio` × 10,000
- **NCUA benchmark** (credit unions):
  - Match branch `state_code` to NCUA state row; use `delinquency_bps`.

---

## Output Conventions (Pitfall Prevention)

1. **Precision**: Respect the decimal precision in the answer template (e.g., `precision: 4` → four decimal places, `precision: 2` → two, `precision: 1` → one). Do not truncate incorrectly; round half-up.
2. **Alphabetical ordering**:
   - `reason_codes` arrays must be sorted ascending alphabetically.
   - `conditions` arrays must be sorted ascending alphabetically.
3. **Application ordering**:
   - `applications_compared` and nested `results` lists must be ascending by `application_id`.
4. **Required keys**: Do not omit any key marked `required` or `required_keys` in the template.
5. **Enums**: Use only the exact allowed values from the template (e.g., `score_class` values, `decision` values).
6. **JSON only**: Do not wrap output in markdown code fences or add narrative text.

---

## Branch Name Resolution

Prompts may use fictional aliases. Resolve by:
- Searching `/api/branches` for the branch whose applications contain the IDs referenced in the prompt (e.g., `HAR-APP-901` → `HARBOR`).
- If the prompt’s `branch_id` does not match any API `branch_id`, fall back to matching by `application_id` prefix or by `state_code` when the prompt mentions a location.

## Common Pitfalls

- **Using 2024Q4 instead of 2025Q1 metrics** — always pick the latest quarter.
- **Confusing `sector_ceiling_pct` with `cre_policy_limit_pct`** — CRE sectors (Multifamily, Hospitality, Retail CRE, Office, Industrial CRE, Construction) often use the CRE limit; non-CRE sectors use the general sector ceiling.
- **Forgetting to include the requested amount in post-approval concentration** — add the selected application’s `requested_amount` to `existing_cre_exposure` before dividing by `total_assets`.
- **Wrong stress formula** — use the exact `dscr * 0.85 / (1 + 0.18)` from the policy; do not approximate.
- **Ignoring grandfathering** — the policy states existing over-ceiling exposure may be grandfathered, but new approvals may not worsen that sector without mitigation. If post-approval exposure increases the breach, flag it.
- **Omitting `documentation_gap` or `policy_floor_missing`** — if `documentation_complete == 0` or if a required policy floor (e.g., minimum DSCR covenant) is absent, add the corresponding reason code.
