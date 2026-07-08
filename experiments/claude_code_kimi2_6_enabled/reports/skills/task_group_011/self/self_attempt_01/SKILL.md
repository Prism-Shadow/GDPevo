# Skill: CRE Competing-Application Committee Decision

## 1. Task Overview
Receive a prompt naming a `branch_id` and two CRE application IDs to compare. Fetch all relevant data from the shared public credit-office API, compute stressed coverage, concentration, FDIC/NCUA variance, and weighted CRE credit scores, then emit a single JSON object matching the task's `answer_template.json`.

## 2. API Workflow
Use the remote base URL from `environment_access.md` (do **not** run `env/setup.sh` or use localhost).

**Required endpoints (call in this order):**
1. `GET /api/manifest` – verify environment version and endpoint list.
2. `GET /api/branches` – map the prompt branch name to the actual `branch_id`.
3. `GET /api/branches/{branch_id}` – branch profile (`cre_policy_limit_pct`, `sector_ceiling_pct`, `lending_capacity_q1`, `institution_type`, `fdic_benchmark_set`).
4. `GET /api/branches/{branch_id}/metrics` – use the **latest quarter** (usually `2025Q1`).
5. `GET /api/branches/{branch_id}/loans` – full loan tape.
6. `GET /api/branches/{branch_id}/sector-exposures` – per-sector limits and grandfathering flags.
7. `GET /api/branches/{branch_id}/applications` – filter to the two target application IDs.
8. `GET /api/policies` – scoring weights, stress formula, rating thresholds, concentration rules.
9. `GET /api/benchmarks/fdic/q4-2024` – for bank branches (`institution_type == "bank"`).
10. `GET /api/benchmarks/ncua/q1-2025` – for credit-union branches (`institution_type == "credit_union"`).

## 3. Key Computations

### 3.1 CRE Dual-Stress DSCR
Formula (from policies):
```
stressed_dscr = dscr * 0.85 / (1 + 0.18)
```
- `coverage_breach_threshold = 1.0`
- `breaches_threshold = true` when `stressed_dscr < 1.0`
- Round `base_dscr` and `stressed_dscr` to **2 decimal places**.

### 3.2 Existing CRE Exposure
```
existing_cre_exposure = sum(outstanding_balance for loan in loans if loan['loan_type'] == 'CRE')
```
- **Do not** include Residential Mortgage, C&I, SBA, Equipment, or Consumer loans.
- Round to **2 decimal places**.

### 3.3 CRE Concentration
```
existing_cre_concentration = existing_cre_exposure / total_loans_outstanding
selected_post_approval_cre_concentration = (existing_cre_exposure + requested_amount) / (total_loans_outstanding + requested_amount)
selected_policy_variance_bps = (selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000
```
- Round concentrations to **4 decimal places**.
- Round `selected_policy_variance_bps` to **2 decimal places**.
- If the selected app is **not** CRE, still add its requested amount to the denominator (it becomes part of the total portfolio) but do **not** add it to the CRE numerator.

### 3.4 Sector Exposure Check
For the **selected application's sector**, look up `sector-exposures`:
```
post_sector_concentration = (current_exposure + requested_amount) / (total_loans_outstanding + requested_amount)
sector_limit = limit_pct from sector-exposures (or sector_ceiling_pct if sector not listed)
```
- If `post_sector_concentration > sector_limit`, the app triggers `sector_breach`.
- Respect `grandfathered` flags: grandfathered sectors may already exceed the default ceiling, but new money still may not worsen the breach without mitigation.

### 3.5 FDIC / NCUA Benchmark Variance (for bank branches)
```
branch_delinquency_ratio = sum(balance for loan in loans
    if loan['loan_type'] in ('CRE', 'Residential Mortgage')
    and 30 <= loan['days_past_due'] <= 89) / sum(balance for loan in loans
    if loan['loan_type'] in ('CRE', 'Residential Mortgage'))
```
- **Do not** use `metrics['delinquency_30_plus_pct']` directly; that metric is portfolio-wide, not real-estate-specific.
- `fdic_benchmark_metric` = `"total_real_estate_30_89_pct"`
- `fdic_benchmark_ratio` = value from FDIC Q4-2024 endpoint.
- `fdic_variance_ratio = branch_delinquency_ratio - fdic_benchmark_ratio`
- `fdic_variance_bps = fdic_variance_ratio * 10000`
- Round ratios to **4 decimal places**, bps to **2 decimal places**.

### 3.6 NCUA Variance (for credit-union branches)
- Use `/api/benchmarks/ncua/q1-2025`.
- Credit unions lack FDIC data (`fdic_benchmark_set == ""`).
- The template may still ask for FDIC fields; if the branch is a credit union, compute the same real-estate delinquency ratio and compare against the relevant NCUA peer metric, or note the institution type mismatch.

### 3.7 Weighted CRE Credit Score (`weighted_cdfi_score`)
The policy defines:
```json
{
  "capacity": 0.45,
  "capital": 0.03,
  "character": 0.05,
  "collateral_exposure": 0.36,
  "conditions": 0.11
}
```
Map application data to component scores (0 = best, higher = worse) using the `cdfi_factor_scores` tables in `/api/policies` as guidance:
- **Capacity** → DSCR (higher is better; score inversely).
- **Capital** → `total_debt / total_assets` (debt_to_asset table: 0/2/4/6).
- **Collateral** → LTV (ltv table: 0/2/4/6).
- **Character** → `prior_delinquencies_12m`, `fico`, `bankruptcy_months_ago` (fico table: 0/1/3/5).
- **Conditions** → `documentation_complete`, `years_in_business`, sector risk, guarantor strength.

Multiply each component score by its weight and sum. Round the final `weighted_cdfi_score` to **1 decimal place**.

**Score class thresholds:**
- `approve_quality` → score ≤ 2.0
- `conditional` → score ≤ 3.0
- `weak` → score > 3.0

## 4. Decision Logic

1. **Select the stronger credit**: compare `weighted_cdfi_score` (lower is better), then stressed DSCR (higher is better), then LTV (lower is better).
2. **Selected application path** (from `recommended_path.path`):
   - If concentration is within policy → `approve` or `conditional_approve` based on score class.
   - If CRE or sector limit is breached → `participation_required`, `conditional_approve`, or `defer`.
   - The policy explicitly lists `participation_required`, `reduced_amount`, and `board_exception` as allowed mitigations.
3. **Unselected application** (`recommended_path.unselected_disposition`):
   - Allowed: `decline` or `defer`.
   - `unselected_reason_codes` must be from the restricted subset: `[sector_breach, weak_dscr, high_ltv, fdic_adverse_variance]`, sorted alphabetically.
4. **Per-application decisions** (`applications_compared[].decision`):
   - The selected app's decision should match `recommended_path.path`.
   - The unselected app's decision should match `unselected_disposition`.
   - `reason_codes` for each app can draw from the full enum; sort alphabetically.

## 5. Output Conventions
- **Ordering**:
  - `applications_compared`: ascending by `application_id`.
  - `stress.results`: ascending by `application_id`.
  - `reason_codes` and `conditions`: ascending alphabetically.
- **Precision**:
  - USD amounts: 2 decimals.
  - Concentration percentages: 4 decimals.
  - BPS values: 2 decimals.
  - DSCR values: 2 decimals.
  - Weighted score: 1 decimal.
- **Required top-level keys**: `branch_id`, `applications_compared`, `recommended_path`, `stress`, `concentration`, `conditions`.
- **No narrative text** outside the JSON.

## 6. Common Pitfalls
- **Missing applications**: The prompt may reference application IDs that do **not** exist in the API (e.g., `CEN-APP-101` when only `CEN-APP-001`–`005` exist). Always verify by scanning `/api/branches/{branch_id}/applications`.
- **Branch name aliases**: Prompts may use shorthand names (`NORTHERN`, `SOUTHERN`, `WESTERN`) that map to different API branch IDs (`NORTHSTAR`, `SOUTHPORT`, etc.). Start with `/api/branches` to resolve the correct ID.
- **Using wrong delinquency metric**: `metrics['delinquency_30_plus_pct']` is portfolio-wide. For FDIC/NCUA comparison, compute the **real-estate-only** 30–89 DPD ratio from loan-level data.
- **CRE vs. total concentration**: Only loans with `loan_type == 'CRE'` count toward CRE exposure. Do not include Residential Mortgage in the CRE numerator.
- **Post-approval denominator**: Always add the requested amount to `total_loans_outstanding` when calculating post-approval concentrations.
- **Credit-union branches**: They have `fdic_benchmark_set == ""` and use NCUA benchmarks instead. Do not blindly apply FDIC Q4-2024 data.
- **Alphabetical sorting**: `reason_codes` and `conditions` must be sorted ascending alphabetically. The evaluator checks ordering.
- **Stressed DSCR rounding**: Round to 2 decimals *before* comparing to the 1.0 threshold (e.g., 0.949 → 0.95, which is still `< 1.0`).
