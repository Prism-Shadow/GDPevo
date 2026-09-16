---
name: credit-office
description: Build credit-office committee packets from a public credit office API. Re-derive risk ratings, score CDFI factors, apply stressed-DSCR shocks, check sector/CRE concentration against policy limits and FDIC/NCUA benchmarks, assign watch-list actions and decline reason codes, and produce committee-ready JSON from the answer template supplied with each task.
---

# Credit Office Skill

This skill teaches the solver how to construct committee-ready credit packets from the public credit office API (`<TASK_ENV_BASE_URL>`). Every task supplies a prompt, an `input/payloads/answer_template.json` that defines the required output shape, and a target branch or segment. The API, the policy endpoint, and the template constrain every answer so that only the provided enums, identifiers, and shapes are used.

## Phase 1: Collect All Inputs

Before any computation, collect four sets of inputs in parallel.

### 1A. Read the answer template

Read `input/payloads/answer_template.json` first. It defines:
- Required top-level keys
- Field types, enums, allowed values, numeric precision
- Sort orders ("ascending loan_id", "descending exposure, then ascending loan_id", etc.)
- Every enum list (decision, condition, reason code, posture, risk class, action, etc.)

Every output value must be drawn from the template's enums. Never invent a value outside them.

### 1B. Fetch API data

From `<TASK_ENV_BASE_URL>` fetch these endpoints in parallel (all are GET, no auth):

| Endpoint | Purpose |
|---|---|
| `/api/manifest` | benchmark versions, record counts, seed info |
| `/api/policies` | risk rating rules, CDFI factor tables, CRE weights, stress formulas, concentration rules |
| `/api/branches/{branch_id}` | branch detail (capacity, sector ceiling, CRE limit, state, institution type) |
| `/api/branches/{branch_id}/metrics` | Q1 2025 and Q4 2024 metrics (NPA, delinquency, deposits, total loans) |
| `/api/branches/{branch_id}/loans` | full loan portfolio with DSCR, LTV, collateral, payment status, FICO, debt-to-asset, liquidity |
| `/api/branches/{branch_id}/applications` | pending applications with DSCR, LTV, FICO, collateral, bankruptcy, SBA guaranty |
| `/api/branches/{branch_id}/sector-exposures` | current exposure per sector with limit_pct |
| `/api/benchmarks/fdic/q4-2024` | five FDIC benchmark ratios (only for banks) |
| `/api/benchmarks/ncua/q1-2025` | 12 rows of NCUA state-level metrics (only for credit unions) |
| `/api/credit-union-segments/{segment_id}` | segment profile, peer states, checklist, internal context |

Fetch only the endpoints relevant to the task. Credit union tasks use NCUA benchmarks and the segment endpoint; bank tasks use FDIC benchmarks and branch endpoints.

### 1C. Determine task type from the prompt and template

The prompt and template together signal which computations to run. Five task patterns recur:

| Pattern | Signature template keys | Core computation |
|---|---|---|
| Rating migration review | `portfolio_regrade`, `material_downgrades`, `npa_benchmark` | Re-derive ratings for loans rated >= N, dominant-factor rule |
| Allocation package | `allocation`, `decisions`, `concentration_flags`, `decline_reasons` | Policy gate checks, capacity ranking, sector ceiling |
| Segment posture | `posture`, `state_metrics`, `peer_comparison`, `controls` | NCUA row reads, peer median computation, posture decision |
| Watch-list stress | `watch_list_summary`, `stress_results`, `workout_queue` | CDFI factor scoring, +200bp DSCR shock, workout actions |
| Competing CRE decision | `applications_compared`, `recommended_path`, `stress`, `concentration` | Weighted CRE scoring, dual-stress, CRE/FDIC concentration |

## Phase 2: Apply the Policy Engine

The `/api/policies` response is the single source of truth for every rule. Extract these structures and use them literally; do not approximate ranges.

### 2A. Risk-rating dominant-factor rule

```
Final rating = max(DSCR_rating, LTV_rating, delinquency_minimum)
```

The policy provides `risk_rating.dscr_thresholds` and `risk_rating.ltv_thresholds` as ordered arrays. Walk the arrays from lowest rating to highest to find the first match. `risk_rating.delinquency_minimums` maps payment_status to a floor rating (`null` for Current means no floor).

For loans missing DSCR or collateral/LTV, omit that factor from the max. A loan with only a delinquency floor gets that rating.

Material downgrade: `final_rating - current_rating >= risk_rating.material_downgrade_notches` (which is 2).

### 2B. CDFI factor scoring

The policy provides `cdfi_factor_scores` with four tables: `debt_to_asset`, `fico`, `liquidity_months`, `ltv`. Score each factor against its range table. Sum the four scores. Classify from `cdfi_factor_scores.classes`:

- **Projected Loss**: score >= 19 AND ltv > 1.0
- **Doubtful**: score >= 19 (ltv not > 1.0)
- **Watch**: 14-18
- **Satisfactory**: 10-13
- **Desirable**: 6-9
- **Prime**: 0-5

Missing factors (null) contribute 0 to the score. Do not fabricate values.

### 2C. CRE weighted scoring (for CRE competing decisions)

The policy provides `cre_weighted_score` with five weight keys (`capacity`, `capital`, `character`, `collateral_exposure`, `conditions`) and class thresholds. Compute a weighted score using available application fields:

- **capacity** (weight 0.45): Use DSCR. Lower DSCR -> higher risk. Map: DSCR >= 1.5 -> 1, >= 1.25 -> 2, >= 1.05 -> 3, >= 1.0 -> 4, < 1.0 -> 5.
- **capital** (weight 0.03): Use debt-to-asset from total_debt / total_assets on the application.
- **character** (weight 0.05): Use FICO and prior_delinquencies_12m.
- **collateral_exposure** (weight 0.36): Use LTV.
- **conditions** (weight 0.11): Use documentation_complete, years_in_business, and relationship deposit balance.

Compute `weighted_score = sum(weight_i * factor_score_i)` and classify:
- approve_quality: <= 2.0
- conditional: <= 3.0
- weak: > 3.0

### 2D. Stress formulas

The policy provides two stress formulas:

- **Watch-list (+200bp)**: `stressed_dscr = dscr / 1.18`
- **CRE dual-stress**: `stressed_dscr = dscr * 0.85 / 1.18`

The coverage_breach_threshold is 1.0. A DSCR below 1.0 after stress breaches.

### 2E. Concentration checks

Branch-level concentration uses the single sector ceiling (`branch.sector_ceiling_pct`), with per-sector entries in `sector-exposures` that may override that default (`limit_pct` on the exposure record).

```
post_approval_pct = (current_exposure + approved_amount) / branch.total_assets
flag = post_approval_pct > limit_pct
```

For CRE-specific concentration:

```
existing_cre_concentration = existing_cre_exposure / branch.total_assets
post_approval_cre_concentration = (existing_cre_exposure + approved_amount) / branch.total_assets
policy_variance_bps = (post_approval_cre_concentration - cre_policy_limit_pct) * 10000
```

Existing over-ceiling exposure is grandfathered; new approvals may not worsen a sector that is already over its limit without mitigation (participation, reduced amount, board exception per `capacity_concentration.allowed_mitigations`).

### 2F. FDIC benchmark variance

For bank tasks matching the FDIC Q4 2024 benchmarks:

```
branch_ratio = npa_exposure / total_loans
variance_ratio = branch_ratio - benchmark_ratio
variance_bps = variance_ratio * 10000
```

Select the benchmark metric that matches the template's `benchmark_metric` enum and the task's focus.

### 2G. NCUA benchmark comparison

For credit union tasks: read the NC state row from `/api/benchmarks/ncua/q1-2025`. Compute the peer median for each metric across the `peer_states` list from the segment endpoint. Compare NC to US and NC to peer median with direction labels (`higher`, `lower`, `equal`).

### 2H. Watch-list action assignment

Map final ratings to actions using the action enum from the template (sorted from lightest to heaviest):

| Final rating | Recommended action |
|---|---|
| 3-4 | monitor |
| 5-6 | watchlist |
| 7 | special_assets |
| 8 | partial_chargeoff_review |

When payment_status is Nonaccrual and rating is 8, use `partial_chargeoff_review`. When 90+ Days Past Due, consider `special_assets` or `workout`. When a loan has a DSCR breach under stress, escalate the action one level.

## Phase 3: Allocate and Rank (Allocation Tasks)

For branch allocation tasks, follow this priority logic:

1. Filter applications: exclude any with documentation_complete = 0 (documentation gap).
2. Policy-gate each application against:
   - DSCR < 1.0 -> `weak_dscr`
   - LTV > 1.0 -> `underwater_collateral`; LTV > 0.85 -> `high_ltv`
   - FICO < 580 -> `low_fico`
   - bankruptcy_months_ago <= 36 -> `recent_bankruptcy`
   - years_in_business < 2 -> `startup_risk`
3. Rank surviving applications by priority: strongest credits (highest DSCR, lowest LTV) first.
4. Allocate capacity in rank order. Track `bank_capacity_used` (for participation, use the bank-retained portion, computed as `requested_amount * (1 - participation_pct)`; for SBA guaranty, use `requested_amount * 0.25`). Stop when `remaining_capacity` < next request.
5. Applications that cannot fit within capacity get declined with `capacity_limit`.
6. Sector concentration: after allocating, recompute post-approval percentages. Flag any sector over its limit.

## Phase 4: Build the Output JSON

Match the template exactly. Key rules:

- **Sort orders**: Observe every sort directive in the template (ascending/descending by specified field). Sort strings lexicographically, numbers numerically.
- **Numeric precision**: Currency fields to 2 decimals, ratios to 4 decimals, bps to 2 decimals, scores to 1 decimal, integer fields as whole numbers.
- **Enum membership**: Every enum field must use only the template's allowed_values. Reason codes, actions, decisions, conditions, posture, risk_class, payment_status, handling, etc. — all bounded.
- **Missing/null data**: For DSCR stress results, include only loans where base DSCR is available. For CDFI scoring, null factors contribute 0. For delinquency floors, Current (null) means no floor.
- **Empty lists**: Use `[]` not `null` when a list field has no entries.
- **Required keys**: Every key marked required in the template must appear. Omit nothing.

## Phase 5: Validate Before Returning

Before finalizing, check:

1. Every top-level key from the template is present.
2. Every nested required key is present.
3. All sort orders match the template directives.
4. All enum values are from the template's allowed lists.
5. All numeric values match the template's precision rules.
6. Computed values are consistent with policy rules and the data fetched from the API.
7. The answer is valid JSON with no trailing commas or comments.

Return only the JSON. The answer template says "Do not include narrative text outside the JSON."

## API Data Reference

### Branch fields

| Field | Description |
|---|---|
| `branch_id` | stable identifier |
| `lending_capacity_q1` | Q1 lending capacity in USD |
| `sector_ceiling_pct` | default single-sector concentration limit (ratio) |
| `cre_policy_limit_pct` | CRE portfolio concentration limit (ratio) |
| `total_assets` | total branch assets in USD |
| `institution_type` | "bank" or "credit_union" |
| `state_code` | 2-letter state |

### Loan fields (from `/branches/{id}/loans`)

| Field | Description |
|---|---|
| `loan_id` | stable identifier |
| `borrower_name` | business or individual name |
| `current_rating` | 1-8 risk rating |
| `outstanding_balance` | current exposure in USD |
| `payment_status` | Current, 30/60/90+ Days Past Due, Nonaccrual |
| `dscr` | debt service coverage ratio (may be null) |
| `ltv` | loan-to-value ratio (may be null) |
| `collateral_value` | appraisal value in USD (may be null) |
| `fico` | FICO score (may be null) |
| `debt_to_asset` | debt-to-asset ratio (may be null) |
| `liquidity_months` | months of liquidity (may be null) |
| `sector` | industry sector |
| `loan_type` | C&I, CRE, HELOC, Residential Mortgage, SBA |
| `days_past_due` | integer days delinquent |

### Application fields (from `/branches/{id}/applications`)

| Field | Description |
|---|---|
| `application_id` | stable identifier |
| `requested_amount` | amount requested in USD |
| `dscr` | projected debt service coverage ratio |
| `ltv` | projected loan-to-value ratio |
| `fico` | applicant FICO (may be null) |
| `bankruptcy_months_ago` | months since bankruptcy (null if none) |
| `years_in_business` | years operating |
| `documentation_complete` | 1 = complete, 0 = incomplete |
| `sector` | industry sector |
| `loan_type` | CRE, C&I, SBA |
| `sba_guaranty_pct` | SBA guaranty percentage (null if not SBA) |
| `collateral_value` | appraisal value |
| `relationship_deposit_balance` | deposit relationship |

### Sector exposure fields

| Field | Description |
|---|---|
| `sector` | industry sector name |
| `current_exposure` | current USD exposure |
| `limit_pct` | per-sector concentration limit (overrides branch default if present) |
| `grandfathered` | amount grandfathered |

### Policy constants (memorize these)

These come from `/api/policies` and are stable across tasks:

- Material downgrade threshold: 2 notches
- Coverage breach threshold: 1.0
- Watch-list stress formula: `dscr / 1.18`
- CRE dual-stress formula: `dscr * 0.85 / 1.18`
- FDIC benchmark version: `fdic_q4_2024`
- NCUA benchmark version: `ncua_q1_2025`

### DSCR rating thresholds

| DSCR range | Rating |
|---|---|
| >= 1.50 | 3 |
| >= 1.25 | 4 |
| >= 1.05 | 5 |
| >= 1.00 | 6 |
| < 1.00 | 7 |

### LTV rating thresholds

| LTV range | Rating |
|---|---|
| <= 0.65 | 3 |
| <= 0.75 | 4 |
| <= 0.85 | 5 |
| <= 1.00 | 6 |
| > 1.00 | 7 |

### Delinquency minimums

| Payment status | Minimum rating |
|---|---|
| Current | none |
| 30 Days Past Due | 4 |
| 60 Days Past Due | 5 |
| 90+ Days Past Due | 7 |
| Nonaccrual | 8 |

### CDFI factor score tables

**FICO**

| Range | Score |
|---|---|
| > 720 | 0 |
| 680-720 | 1 |
| 580-679 | 3 |
| < 580 | 5 |

**LTV**

| Range | Score |
|---|---|
| < 0.40 | 0 |
| 0.40-0.60 | 2 |
| 0.60-0.80 | 4 |
| > 0.80 | 6 |

**Debt to Asset**

| Range | Score |
|---|---|
| < 0.40 | 0 |
| 0.40-0.60 | 2 |
| 0.60-0.80 | 4 |
| > 0.80 | 6 |

**Liquidity Months**

| Range | Score |
|---|---|
| > 12 | 0 |
| 6-12 | 1 |
| 3-6 | 3 |
| < 3 | 5 |

### CDFI risk class thresholds

| Class | Score range |
|---|---|
| Prime | 0-5 |
| Desirable | 6-9 |
| Satisfactory | 10-13 |
| Watch | 14-18 |
| Doubtful | >= 19 |
| Projected Loss | >= 19 and LTV > 1.0 |

### CRE weighted scoring (5 C's)

| Factor | Weight |
|---|---|
| capacity | 0.45 |
| collateral_exposure | 0.36 |
| conditions | 0.11 |
| character | 0.05 |
| capital | 0.03 |

| Class | Score threshold |
|---|---|
| approve_quality | <= 2.0 |
| conditional | <= 3.0 |
| weak | > 3.0 |

### Concentration mitigation rules

Grandfathered over-ceiling exposure may remain, but new approvals that worsen an over-limit sector require mitigation: `participation_required`, `reduced_amount`, or `board_exception`.

### Capacity allocation for participation and SBA

- Participation: bank retains `requested_amount * (1 - participation_share)` of capacity. Participation share defaults to 0.75 unless otherwise indicated.
- SBA guaranty: bank retains `requested_amount * 0.25` of capacity (SBA covers 75%).
- Direct approve: bank retains full `requested_amount`.

## Task-Specific Workflows

### Rating Migration Review

Applies when template has `portfolio_regrade`, `material_downgrades`, `npa_benchmark`.

1. Fetch branch, metrics, loans, FDIC benchmark, policies.
2. Filter loans with `current_rating >= target_current_rating_min` (from template/prompt).
3. Re-derive each loan's rating using the dominant-factor rule (Phase 2A).
4. Build `final_rating_exposure_totals`: group by final_rating, sum loan_count and exposure.
5. Build migration from a specific current rating: only loans whose current_rating was exactly that value, grouped by final_rating with loan_ids.
6. Identify material downgrades: `final_rating - current_rating >= 2`.
7. Compute NPA benchmark variance: NPA = sum of Nonaccrual and 90+ DPD balances, divide by total_loans, compare to FDIC ratio.
8. Assign watch-list actions (Phase 2H). Top problem credit is the loan with the worst final rating and largest exposure.

### Allocation Package

Applies when template has `allocation`, `decisions`, `concentration_flags`, `decline_reasons`.

1. Fetch branch, applications, sector-exposures, policies, metrics.
2. Gate each application through the policy checks (Phase 3).
3. Rank surviving applications by credit quality.
4. Allocate capacity in rank order.
5. Check concentration after allocation.
6. Assign decline reasons to each declined app.
7. Build post-approval concentration view.
8. Set `approved_amount` to 0.0 and `bank_capacity_used` to 0.0 for declined apps.
9. `priority_ranking` includes only approved and conditional_approve apps.
10. `committed_capacity_amount` = sum of `bank_capacity_used` for approved + conditional apps.

### Segment Posture

Applies when template has `posture`, `state_metrics`, `peer_comparison`, `controls`.

1. Fetch segment, NCUA benchmarks, policies.
2. Report state metrics exactly from the NCUA row for the segment's state_code.
3. Compute peer median: sort peer state values, take the middle value (for odd count, the central element).
4. Compare state vs US direction, state vs peer median direction.
5. Set posture:
   - `temporarily_pause`: recent delinquency >= 90 bps and external risk weaker on all metrics
   - `continue_with_tighter_conditions`: capacity available but external risk mixed or weaker
   - `continue_approving`: external risk stronger, capacity available
6. Controls: `required_checklist_gates` from segment's `minimum_checklist`. `added_operating_controls` based on segment's internal_context issues.
7. Escalation triggers: map conditions from segment data (e.g., `recent_delinquency_bps`, `control_issue`, staffing).
8. Interpretation: use segment notes and NCUA comparison to select the interpretation enum values.

### Watch-List Stress

Applies when template has `watch_list_summary`, `stress_results`, `workout_queue`.

1. Fetch branch loans, policies.
2. Filter loans with `current_rating >= adverse_rating_min` (from prompt, e.g., 6).
3. Score CDFI factors for each loan (Phase 2B).
4. Stress DSCR with watch-list formula: `dscr / 1.18`.
5. Breach when stressed_dscr < 1.0.
6. Build workout queue sorted by descending exposure, assign actions.
7. Severe bucket counts: group by current_rating and payment_status for ratings in the severe range.
8. Set `monitoring_cadence`: monthly when any Projected Loss or Doubtful class exists; quarterly otherwise.
9. `projected_loss`: true when risk_class is Projected Loss or payment_status is Nonaccrual with stressed DSCR breach.

### Competing CRE Decision

Applies when template has `applications_compared`, `recommended_path`, `stress`, `concentration`.

1. Fetch branch, the target applications, sector-exposures, loans (for existing CRE exposure), FDIC benchmark, policies.
2. Compute weighted CRE score for each application (Phase 2C).
3. Apply CRE dual-stress: `dscr * 0.85 / 1.18`.
4. Compute existing CRE exposure: sum outstanding_balance for all loans where loan_type = "CRE".
5. Compute CRE concentration pre and post selected application.
6. Compare FDIC benchmark: use the benchmark metric from the template.
7. Recommend: select the application with the better score (lower weighted score). Path = approve / conditional_approve / participation_required based on concentration and stress. Unselected gets decline or defer with reason codes.
8. Conditions: alphabetically sorted from the template enum, selected based on stress breaches, concentration over-limit, and FDIC variance.

## Cross-Cutting Rules

- **Always read the template first** — it controls every output decision.
- **Never guess an enum value** — use only values in the template's `allowed_values` or `choices` lists.
- **Sort before writing** — every list in the template has an ordering rule; apply it.
- **Compute from API data, not from memory** — fetch fresh data for each task.
- **The policy endpoint is canonical** — use its ranges and formulas, not approximations.
- **Null means absent** — skip the factor, don't invent a zero unless the rule says so.
- **Currency in USD with 2 decimals, ratios with 4, bps with 2** — unless the template says otherwise.
- **The answer template lives at `input/payloads/answer_template.json`** — always read it first.
