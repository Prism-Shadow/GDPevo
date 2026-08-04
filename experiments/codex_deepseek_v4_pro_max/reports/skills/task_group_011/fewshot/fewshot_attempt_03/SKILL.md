## Overview

This skill equips you to interact with the **Shared Credit Office API**, a simulated financial institution back-end that serves branch loan portfolios, branch metrics, credit policies, pending applications, sector exposures, credit-union segment data, and regulatory benchmarks (FDIC, NCUA). You will receive a committee-level task — such as a rating migration review, a lending allocation package, a segment posture assessment, a watch-list stress packet, or a competing CRE decision — and must produce a committee-ready JSON answer that strictly conforms to the provided answer-template schema.

## Environment

- The API base URL is always injected by the runner as `<TASK_ENV_BASE_URL>`.
- No authentication is required; all endpoints are publicly accessible over HTTP GET.
- Never use health-check, reset, evaluator, or judge endpoints.
- Replace path placeholders (`{branch_id}`, `{segment_id}`) with the identifier named in the task input.

## API Endpoint Reference

| Endpoint | Returns |
|---|---|
| `GET /api/manifest` | Full manifest of available branches, segments, and benchmark versions. |
| `GET /api/policies` | Credit policy rules, concentration limits, rating definitions, LTV/DSCR minima, and CDFI factor weights. |
| `GET /api/benchmarks/fdic/q4-2024` | FDIC Q4 2024 industry benchmark ratios (noncurrent, 30-89 day, etc.). |
| `GET /api/benchmarks/ncua/q1-2025` | NCUA Q1 2025 state-level and national credit-union metrics. |
| `GET /api/branches` | List of all branch identifiers. |
| `GET /api/branches/{branch_id}` | Branch-level details (name, type, address). |
| `GET /api/branches/{branch_id}/metrics` | Branch financial metrics: total loans, NPA exposure, loan-to-share, delinquency, ROAA, net income, capacity, etc. |
| `GET /api/branches/{branch_id}/loans` | All loans for the branch, with fields: `loan_id`, `borrower_name`, `exposure`, `current_rating`, `payment_status`, `dscr`, `ltv`, `fico`, `sector`, `maturity`, `collateral_type`. |
| `GET /api/branches/{branch_id}/sector-exposures` | Sector-level exposure totals and concentration limits for the branch. |
| `GET /api/branches/{branch_id}/applications` | Pending credit applications for the branch, with fields: `application_id`, `requested_amount`, `sector`, `dscr`, `ltv`, `fico`, `collateral`, `borrower_name`, `term_months`, `startup_flag`. |
| `GET /api/credit-union-segments/{segment_id}` | Segment-level data: capacity, delinquency, recent performance, checklist gates required. |

## General Workflow

1. **Read the task prompt** to identify the task archetype, target entity (branch or segment), review date, and any special parameters.
2. **Load the answer template** from `input/payloads/answer_template.json`. Understand every required key, field type, numeric precision, enum choices, and list ordering rule. The template is the contract — your output must match it exactly.
3. **Fetch policy data** (`GET /api/policies`) early. The policy document defines:
   - Rating-scale definitions (1 = best, 8 = worst)
   - CDFI factor scoring tables and weights
   - Concentration limits per sector
   - LTV and DSCR floors
   - FICO thresholds
   - Capacity calculation formulas
   - Watch-list action tier definitions
4. **Fetch benchmark data** when the task references FDIC or NCUA benchmarks. Match the version string exactly (e.g., `fdic_q4_2024`, `ncua_q1_2025`).
5. **Fetch entity data** (loans, metrics, applications, sector exposures) for the target branch or segment.
6. **Apply the task-specific methodology** (see Archetypes below).
7. **Populate the answer template** field by field, respecting every enum, ordering rule, and precision directive.
8. **Validate your output** — ensure all required keys are present, all numeric fields have the correct precision, all enums use allowed values, and all lists are in the prescribed sort order.
9. **Return only the JSON object. Do not wrap in markdown fences or add narrative text.**

## Task Archetypes

### A. Rating Migration Review

**Goal:** Re-derive risk ratings for a subset of loans (those at or above a minimum current rating), then summarize the migration, material downgrades, NPA benchmark variance, top problem credit, and watch-list action coverage.

**Methodology:**
- Identify the regrade population: all loans where `current_rating >= target_current_rating_min`.
- Re-derive each loan's final rating using the CDFI factor scoring system from `/api/policies`. Each loan's objective characteristics (payment status, DSCR, LTV, FICO, collateral type, sector risk weight, maturity bucket) map to factor points. The policy weights and thresholds translate total points into a final rating (1–8).
- Group loans by final rating to build `final_rating_exposure_totals` (sorted ascending by rating).
- For loans that started at exactly the minimum current rating (e.g., rating 3) and migrated to a worse rating, populate `migration_from_current_rating_3`. Group by `final_rating`, list loan IDs.
- Assign watch-list actions based on final rating and factor score:
  - Rating 7 → `special_assets`
  - Rating 8 → `partial_chargeoff_review` (or `legal_referral` for the most severe)
  - Rating 6 → `watchlist`
  - Rating 5 → `monitor`
- Compute NPA: loans with `payment_status == "Nonaccrual"` summed exposure. Compute `branch_npa_ratio = NPA exposure / total branch loan exposure`. Compare to the FDIC benchmark ratio for the applicable metric. Compute variance as difference and in basis points.
- Material downgrades: any loan where `final_rating - current_rating >= 2` notches qualifies. List ascending by `loan_id`.
- Top problem credit: the loan with the highest combined severity — typically the loan with the worst final rating and nonaccrual status with highest exposure.

### B. Lending Committee Allocation

**Goal:** Evaluate pending applications against branch lending capacity, sector concentration limits, and credit policy minima, then produce application-level decisions and a post-approval concentration view.

**Methodology:**
- Compute `lending_capacity_q1` from branch metrics (total loans × policy capacity factor, or as reported by the metrics endpoint).
- For each application:
  - Check DSCR, LTV, and FICO against policy floors. Applications failing any floor receive `decline` with corresponding reason codes.
  - Check sector concentration: compute `post_approval_pct = (existing sector exposure + requested amount) / (total branch exposure + requested amount)`. If it exceeds the sector limit, flag accordingly (may still approve with conditions or decline if severe).
  - Compute `bank_capacity_used`: for `approve` decisions, it is the `approved_amount`; for `conditional_approve` with `participation_required`, only the bank-retained portion counts against capacity; for `sba_guaranty_required`, only the unguaranteed portion.
  - Apply a priority ranking: approved and conditionally approved applications ranked by policy priority (typically risk-adjusted return or score, lowest CDFI score first).
- Decline reason codes map to specific failures:
  - `high_ltv` → LTV exceeds policy max
  - `weak_dscr` → DSCR below policy min
  - `low_fico` → FICO below threshold
  - `startup_risk` → startup flag set with insufficient collateral/guarantor
  - `recent_bankruptcy` → bankruptcy flag on borrower
  - `capacity_limit` → remaining capacity insufficient
  - `sector_breach` → sector concentration breach
  - `underwater_collateral` → LTV > 1.0
- `gross_approved_amount` is the sum of all approved (including conditional) `approved_amount` values.
- `committed_capacity_amount` is the sum of `bank_capacity_used` across all non-decline decisions.
- `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`.
- Concentration flags: for any sector where post-approval concentration approaches or exceeds the limit, generate a flag entry.
- Post-approval concentrations: recalculate sector concentrations after applying approved amounts.

### C. Credit Union Segment Posture

**Goal:** Assess a credit-union segment's health using NCUA benchmarks and segment-specific data, then recommend a controlled posture with supporting metrics, peer comparisons, controls, escalation triggers, and a committee interpretation.

**Methodology:**
- Fetch the NCUA Q1 2025 benchmark table and the target segment data.
- Extract the segment's state code and locate that state's metrics in the NCUA table: delinquency (bps), loan-to-share ratio (%), ROAA (bps), and positive net income (%).
- Identify peer states (from the policies/manifest — typically adjacent or comparable states in the same region).
- Compare the target state to national US values and to the median of peer states for each of the four metrics. Direction is `higher`, `lower`, or `equal`.
- Set posture:
  - `continue_approving` if all metrics are stronger than or equal to benchmarks
  - `continue_with_tighter_conditions` if metrics are mixed or slightly weaker
  - `temporarily_pause` if metrics are significantly weaker across multiple dimensions
- Required checklist gates: taken from the segment endpoint — these are the standard document/approval gates for this segment type.
- Added operating controls: additional prudential controls recommended based on risk profile. Common controls include: `lien_perfection_prior_to_funding`, `monthly_segment_delinquency_watch`, `quarterly_state_benchmark_monitoring`, `senior_underwriter_second_review`, `pre_close_insurance_binder_verification`.
- Escalation triggers: defined conditions with named owners. Typical triggers and owners:
  - Delinquency rising >= 90 bps → `credit_risk_manager`
  - Missing insurance/lien exception → `operations_control_manager`
  - Capacity exceeded or exception requested → `lending_committee_chair`
- Interpretation: a concise committee-facing assessment in four controlled fields:
  - `capacity_status`: whether the segment has available, constrained, or no capacity
  - `external_risk_status`: how state metrics compare to national and peers
  - `risk_tolerance`: `restrained`, `moderate`, or `expansive`
  - `committee_message`: a template message matching the risk profile

### D. Watch-List Stress Testing

**Goal:** Identify adversely rated loans, assign CDFI-style risk classes, stress DSCR at +200bp, queue workout actions, and summarize payment-status counts by rating bucket.

**Methodology:**
- Identify adverse-rated population: all loans where `current_rating >= adverse_rating_min` (typically 6).
- Assign CDFI risk classes using the factor-scoring system from policies. The factor score maps to a risk class label:
  - Low scores (0–5) → `Prime`
  - Moderate-low (6–9) → `Desirable`
  - Moderate (10–12) → `Satisfactory`
  - Elevated (13–15) → `Watch`
  - High (16–18) → `Doubtful`
  - Very high (19+) → `Projected Loss`
- Determine monitoring cadence: `monthly` if any loans are `Doubtful` or `Projected Loss`; `quarterly` if all are `Watch` or better; `semiannual` otherwise.
- Stress test: compute `stressed_dscr` using the formula specified in the policy or template. For a +200bp rate shock, a common formula is `base_dscr / (1 + (shock_bps / 10000))` — i.e., `base_dscr / 1.02`. For dual-stress CRE tests, the template provides the exact formula (e.g., `dscr * 0.85 / 1.18`). Determine if `stressed_dscr < breach_threshold` (typically 1.0).
- Build workout queue sorted by descending exposure then ascending loan_id. Assign recommended actions:
  - `partial_chargeoff_review` → `Projected Loss` class or rating 8, Nonaccrual
  - `special_assets` → rating 7, or 90+ Days Past Due
  - `watchlist` → rating 6, Current
  - `monitor` → rating 5 or below, Current
- Severe bucket counts: group loans by (current_rating, payment_status), count loans and sum exposure. Sort ascending by rating, then payment_status.

### E. Competing CRE Decision

**Goal:** Compare two CRE applications using weighted CDFI scoring, stressed repayment coverage, branch CRE and sector exposure, and FDIC benchmarks, then recommend one for approval (with conditions) and dispose of the other.

**Methodology:**
- Score both applications using the CDFI factor-scoring system. Lower weighted score is better. Map scores to classes:
  - 0.0–2.5 → `approve_quality`
  - 2.6–3.5 → `conditional`
  - 3.6+ → `weak`
- Apply the CRE dual-stress formula as specified in the template (e.g., `dscr * 0.85 / 1.18`). Compute `stressed_dscr` for both. Check against `coverage_breach_threshold` (1.0).
- Check CRE concentration: compute `existing_cre_concentration` as CRE exposure / total branch loans. Compute post-approval concentration for the selected application. Compare to the CRE policy limit. Compute variance in basis points.
- Compare branch delinquency to FDIC benchmark (e.g., `total_real_estate_30_89_pct`). Compute variance.
- Select the stronger application (lower CDFI score, DSCR that survives stress, lower concentration impact). The unselected gets `decline` or `defer` with reason codes.
- Conditions: apply appropriate conditions from the template's allowed list, e.g.:
  - `bank_retained_exposure_cap` when the exposure is large
  - `committee_cre_exception` when concentration exceeds policy limit
  - `minimum_dscr_covenant_1_25` when DSCR is marginal
  - `quarterly_financial_reporting`
  - `updated_appraisal_before_close`
  - `no_additional_cre_without_committee_review`
  - `tenant_roll_and_lease_review`

## Data Conventions

### Risk Ratings

- Ratings are integers 1 (best) through 8 (worst).
- Rating 4–5: Special Mention / Watch
- Rating 6: Substandard
- Rating 7: Doubtful
- Rating 8: Loss

### Payment Statuses

Allowed values (in ascending severity): `Current`, `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`.

### Watch-List Actions

Allowed values (in ascending severity): `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`.

### CDFI Factor Scoring

The policy endpoint (`GET /api/policies`) returns factor tables and weights. Typical factors include:
- Payment status (0–8 points depending on delinquency)
- DSCR tier (lower DSCR → more points)
- LTV tier (higher LTV → more points)
- FICO band (lower FICO → more points)
- Collateral type risk weight
- Sector risk weight (CRE, Construction, Hospitality rated higher)
- Maturity bucket

Weights are applied multiplicatively; the weighted score determines the CDFI risk class and maps to a risk rating.

### DSCR Stress Formulas

- **Single-factor rate shock (+200bp):** `stressed_dscr = base_dscr / 1.02` or equivalent formula from policy. Always defer to the exact formula provided in the answer template or policy document.
- **Dual-stress CRE formula:** Example from policy: `dscr * (1 - vacancy_stress) / (1 + rate_stress)` — e.g., `dscr * 0.85 / 1.18`. Use exactly the formula provided.

### Concentration Calculations

- **Sector concentration:** `sector_exposure / total_branch_loans` (as a ratio, rounded to 4 decimals).
- **CRE concentration:** `cre_exposure / total_branch_loans` (as a ratio).
- **Limit breach:** when post-approval concentration exceeds the sector limit from policy.
- **Basis points:** `variance * 10000` (multiply ratio difference by 10000 and round to 2 decimals).

### Numeric Precision

Read the precision directives in the answer template carefully:
- Currency fields: round to 2 decimal places.
- Ratios/percentages: round to 4 decimal places (as a ratio, e.g., 0.1135 for 11.35%).
- Basis points: round to 2 decimal places.
- Integers: no decimal places.
- Weighted scores: round to 1 decimal place.

### Sorting Rules

Every list in every answer template specifies an ordering rule. Common rules:
- `ascending by loan_id`, `ascending by application_id`, `ascending by final_rating`, `ascending by sector`, `ascending by current_rating then payment_status`, `descending by exposure then ascending by loan_id`.
- Follow the rule exactly; string-sort IDs lexicographically, numeric-sort ratings numerically.

## Reason Codes

Full enum for credit decision decline/reason codes:

| Code | Meaning |
|---|---|
| `capacity_limit` | Insufficient lending capacity |
| `sector_breach` | Sector concentration limit would be exceeded |
| `weak_dscr` | DSCR below policy minimum |
| `high_ltv` | LTV exceeds policy maximum |
| `low_fico` | FICO below policy threshold |
| `recent_bankruptcy` | Borrower has recent bankruptcy |
| `startup_risk` | Startup entity with insufficient track record |
| `underwater_collateral` | LTV > 100% |
| `policy_floor_missing` | Required policy condition not met |
| `documentation_gap` | Missing required documentation |
| `fdic_adverse_variance` | FDIC benchmark variance unfavorable |
| `ncua_peer_weakness` | NCUA peer comparison unfavorable |

## Benchmark References

- **FDIC Q4 2024:** Contains industry-wide metrics including `total_loans_noncurrent_pct`, `total_real_estate_noncurrent_pct`, `construction_development_noncurrent_pct`, `total_real_estate_30_89_pct`.
- **NCUA Q1 2025:** State-level credit-union metrics: delinquency (bps), loan-to-share (%), ROAA (bps), % of CUs with positive net income. Includes national US values for comparison.

## Final Output Rules

1. Output exactly one JSON object — no surrounding text, no markdown fences, no explanations.
2. Include every key defined as `required` in the answer template.
3. Use only the enum values listed in the template for each field.
4. Match the stated numeric precision exactly.
5. Sort every list according to its declared ordering rule.
6. Do not fabricate data — derive all values from API responses and documented policy rules.
