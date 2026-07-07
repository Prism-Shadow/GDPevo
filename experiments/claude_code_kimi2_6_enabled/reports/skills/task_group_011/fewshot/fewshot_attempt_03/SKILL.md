# Credit Office Committee JSON Workflow

Generate committee-ready JSON answers from the shared credit office public API. Task prompts map to one of several template shapes; the skill below covers the universal data-gathering workflow, transferable computation rules, and output conventions.

## 1. Environment & Setup

- Base URL is given by the task prompt or `GDPEVO_ENV_BASE_URL` (e.g. `http://34.46.77.124:8011`).
- **Never** read local `env/` source files; use only the public API.
- Start with:
  - `GET /api/manifest` – endpoint index, benchmark versions, record counts.
  - `GET /api/policies` – master policy (rating thresholds, CDFI factor tables, CRE weights, stress formulas, concentration rules).

## 2. Identify Task Type from Prompt

Read the prompt **and** `input/payloads/answer_template.json` before fetching data. Common shapes:

| Task pattern | Key clues | Primary endpoints |
|---|---|---|
| **A. Competing CRE decision** | "Compare … CRE requests", two `application_id`s | `/branches/{id}`, `/branches/{id}/metrics`, `/branches/{id}/loans`, `/branches/{id}/applications`, `/branches/{id}/sector-exposures`, benchmarks |
| **B. Lending allocation package** | "allocation package", "pending applications" | Same as A |
| **C. Rating migration review** | "re-derive risk ratings", "migration", "downgrades" | `/branches/{id}/loans`, `/branches/{id}/metrics`, benchmarks |
| **D. Watch-list stress packet** | "adversely rated", "watch-list", "workout" | `/branches/{id}/loans`, `/branches/{id}/metrics`, policies |
| **E. Credit-union segment posture** | "segment_id", "posture", "NCUA" | `/credit-union-segments/{id}`, `/benchmarks/ncua/q1-2025`, policies |

## 3. Data Fetching Order

1. **Branch / segment details** (`/branches/{branch_id}` or `/credit-union-segments/{segment_id}`)
2. **Metrics** (`/branches/{branch_id}/metrics`) – use the quarter matching the review date (usually most recent).
3. **Loans** (`/branches/{branch_id}/loans`) – full portfolio for rating migrations / watch-list tasks.
4. **Applications** (`/branches/{branch_id}/applications`) – for allocation or competing-CRE tasks.
5. **Sector exposures** (`/branches/{branch_id}/sector-exposures`) – for concentration checks.
6. **Benchmarks** – banks: `/benchmarks/fdic/q4-2024`; credit unions: `/benchmarks/ncua/q1-2025`.

## 4. Transferable Computation Rules

### Stress DSCR (CRE dual-stress)
- **Formula**: `stressed_dscr = dscr * 0.85 / 1.18`
- **Breach threshold**: `1.0`
- Round `base_dscr` and `stressed_dscr` to **2 decimals**.
- `breaches_threshold` is `true` when `stressed_dscr < 1.0`.

### Watch-list stress (+200 bp)
- **Formula**: `stressed_dscr = dscr / 1.18`
- Same threshold and rounding.

### CRE Concentration
- `existing_cre_exposure` = sum of `outstanding_balance` for all loans where `loan_type == "CRE"`.
- `existing_cre_concentration` = `existing_cre_exposure / total_loans_outstanding` (from metrics), round to **4 decimals**.
- `selected_post_approval_cre_concentration` = `(existing_cre_exposure + selected_requested_amount) / (total_loans_outstanding + selected_requested_amount)`, round to **4 decimals**.
- `selected_policy_variance_bps` = `(selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000`, round to **2 decimals**.

### FDIC Benchmark Variance (banks)
- `branch_delinquency_ratio` = `delinquency_30_plus_pct` from branch metrics.
- `fdic_benchmark_ratio` = `total_real_estate_30_89_pct` from FDIC Q4 2024.
- `fdic_variance_ratio` = `branch_delinquency_ratio - fdic_benchmark_ratio`, round to **4 decimals**.
- `fdic_variance_bps` = `fdic_variance_ratio * 10000`, round to **2 decimals** (e.g. `2802.0`).

### NCUA Variance (credit unions)
- `branch_net_worth_ratio` = segment-level net-worth ratio (from segment endpoint or derived from assets/deposits).
- `ncua_benchmark_ratio` = peer `net_worth_ratio` or state-level equivalent.
- `ncua_variance_ratio` = `branch_net_worth_ratio - ncua_benchmark_ratio`.
- `ncua_variance_bps` = `ncua_variance_ratio * 10000`.

### Risk Rating Re-derivation (dominant-factor rule)
1. **DSCR rating**: lookup from policy `dscr_thresholds`.
2. **LTV rating**: lookup from policy `ltv_thresholds`.
3. **Delinquency rating**: lookup from policy `delinquency_minimums`.
4. Final rating = **worst (highest number)** of the available factors.
5. Downgrade notches = `final_rating - current_rating`.

### CDFI Factor Score → Risk Class
- Sum factor scores from policy tables (fico, ltv, debt_to_asset, liquidity_months).
- Map total to class:
  - `0–5` → Prime
  - `6–9` → Desirable
  - `10–13` → Satisfactory
  - `14–18` → Watch
  - `>=19` → Doubtful
  - `>=19` **and** `ltv > 1.0` → Projected Loss

### CRE Weighted Score → Score Class
- `weighted_cdfi_score` is computed from the 5 CDFI factors weighted by policy (`capacity 0.45`, `capital 0.03`, `character 0.05`, `collateral_exposure 0.36`, `conditions 0.11`).
- Map to class:
  - `<= 2.0` → `approve_quality`
  - `<= 3.0` → `conditional`
  - `> 3.0` → `weak`

## 5. Output Field Conventions

- **JSON only** — no markdown, no narrative outside the JSON object.
- **Precision**:
  - Currency / exposure: 2 decimals.
  - Percentages as ratios: 4 decimals.
  - BPS values: 2 decimals.
  - DSCR: 2 decimals.
  - Weighted CDFI score: 1 decimal.
- **Ordering**:
  - Lists of IDs (loan_id, application_id): **ascending** alphanumeric.
  - Reason codes / conditions / enums: **ascending alphabetical**.
  - Concentration flags: by sector, then application_id.
  - Workout queue: descending exposure, then ascending loan_id.
  - Severe bucket counts: ascending current_rating, then payment_status.
- **Enums**: use **exact** allowed values from the template (case-sensitive). Never invent new values.

## 6. Decision & Reason-Code Heuristics

- **Approve quality** (`<=2.0`) → usually `approve`.
- **Conditional** (`2.0–3.0`) → `conditional_approve` or `participation_required` if concentration/sector limits are breached.
- **Weak** (`>3.0`) → `defer` or `decline`.
- Common reason codes:
  - `sector_breach` – post-approval sector % > `sector_ceiling_pct`.
  - `weak_dscr` – stressed DSCR breaches threshold.
  - `high_ltv` – LTV exceeds policy thresholds.
  - `fdic_adverse_variance` – branch delinquency materially exceeds FDIC benchmark.
  - `capacity_limit` – approval would exceed `lending_capacity_q1`.
  - `documentation_gap` – `documentation_complete == 0`.
- Unselected application in a competing-CRE task receives the **disposition of the weaker credit** (`decline` or `defer`) and its reason codes (alphabetically sorted).

## 7. Common Pitfalls

- **Forgetting the template**: Always read `input/payloads/answer_template.json` first; required keys and enum choices differ by task.
- **Wrong benchmark set**: Banks use FDIC Q4 2024 (`total_real_estate_30_89_pct`); credit unions use NCUA Q1 2025 state rows.
- **Wrong denominator**: CRE concentration uses `total_loans_outstanding` from branch metrics, not `total_assets`.
- **Off-by-one in ratings**: Delinquency minimums are *floors* — if a loan is `90+ Days Past Due`, its rating cannot be better than `7` regardless of DSCR/LTV.
- **Missing loans in watch-list / migration**: Include **all** loans that meet the threshold (e.g., `current_rating >= 3` for migration, `current_rating >= 6` for watch-list), not just a subset.
- **NPA calculation**: Non-performing loans are those with `payment_status` of `90+ Days Past Due` or `Nonaccrual`, or `current_rating` in the severe bucket. `branch_npa_ratio` = `npa_exposure / total_loans_outstanding`.
- **Alphabetical sorting**: Python's default string sort works; verify that reason codes like `["fdic_adverse_variance", "sector_breach"]` are correctly ordered.
