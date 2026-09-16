---
name: credit-office-review
description: >
  Solve credit risk committee tasks against a shared credit office REST API.
  Covers loan rating re-derivation, lending allocation, credit union segment
  posture reviews, watch-list stress tests, and competing CRE decisions.  Use
  when the task involves branch portfolios, loan applications, CU segments,
  FDIC or NCUA benchmarks, CDFI factor scoring, DSCR stress, concentration
  analysis, or credit policy rule application.
---

# Credit Office Review Skill

## Overview

This skill covers five committee-task families served by a shared credit office
REST API.  The solver fetches live branch data, applies centralized credit
policy rules, and writes structured JSON answers in the requested template
shape.

The API base URL is always supplied by the task runner as `<TASK_ENV_BASE_URL>`.
All data is read-only; the solver does not write back to the API.

## API Discovery

Start by calling `GET <TASK_ENV_BASE_URL>/api/manifest` to confirm the available
endpoints and record counts.  Then use these endpoints as needed.

All endpoints:

| Endpoint | Returns |
|---|---|
| `/api/health` | Service status, record counts |
| `/api/manifest` | Full endpoint list, benchmark versions, seed, policy version |
| `/api/policies` | Credit policy rules: risk rating, CDFI factors, CRE scoring, stress, concentration |
| `/api/branches` | All branches list with capacities, ceilings, state, institution type |
| `/api/branches/{id}` | Single branch detail |
| `/api/branches/{id}/metrics` | Branch quarterly metrics (NPA, delinquency, deposits, charge-offs) |
| `/api/branches/{id}/loans` | Loan portfolio for a branch |
| `/api/branches/{id}/sector-exposures` | Per-sector exposure, limit, grandfathered flag |
| `/api/branches/{id}/applications` | Pending credit applications for a branch |
| `/api/benchmarks/fdic/q4-2024` | FDIC benchmark ratios |
| `/api/benchmarks/ncua/q1-2025` | NCUA state-level benchmark rows |
| `/api/credit-union-segments/{segment_id}` | Credit union segment profile |

Always fetch `/api/policies` early.  The policy rules govern every task.

## Credit Policy Rules

### Risk Rating Re-Derivation

The policy rule is **dominant factor**: the final rating is the worst (highest
numeric value) among all available factors.  Each factor maps to a rating via
its own threshold table.  If a factor value is `null`, skip that factor.

**DSCR → rating:**

| DSCR range | Rating |
|---|---|
| ≥ 1.50 | 3 |
| ≥ 1.25 | 4 |
| ≥ 1.05 | 5 |
| ≥ 1.00 | 6 |
| < 1.00 | 7 |

**LTV → rating:**

| LTV range | Rating |
|---|---|
| ≤ 0.65 | 3 |
| ≤ 0.75 | 4 |
| ≤ 0.85 | 5 |
| ≤ 1.00 | 6 |
| > 1.00 | 7 |

**Delinquency floor (payment status → minimum rating):**

| Payment status | Minimum rating |
|---|---|
| Current | (no floor) |
| 30 Days Past Due | 4 |
| 60 Days Past Due | 5 |
| 90+ Days Past Due | 7 |
| Nonaccrual | 8 |

**Material downgrade:** two or more notches (`final_rating - current_rating ≥ 2`).

### Watch-List and Workout Actions

Map the final re-derived rating to a recommended action:

| Final rating | Recommended action |
|---|---|
| 6 | `watchlist` |
| 7 | `special_assets` |
| 8 | `partial_chargeoff_review` |

Loans that stay at rating 3 or upgrade do not populate the watch list.  Loans
downgraded to rating 4 or 5 are monitored but do not trigger a watch-list
action entry unless additional qualitative flags exist.

When the task asks for workout-queue ordering, sort by **descending exposure**
and then **ascending loan_id** as tiebreaker.

### CDFI Factor Scoring (Risk Classes)

Score each of the four factors from the policy table, then sum to get a total
factor score.  Classify from the total.

**Factor tables** (from `/api/policies` > `cdfi_factor_scores`):

Debt-to-asset: `<0.40` → 0, `0.40-0.60` → 2, `0.60-0.80` → 4, `>0.80` → 6
FICO: `>720` → 0, `680-720` → 1, `580-679` → 3, `<580` → 5
Liquidity months: `>12` → 0, `6-12` → 1, `3-6` → 3, `<3` → 5
LTV: `<0.40` → 0, `0.40-0.60` → 2, `0.60-0.80` → 4, `>0.80` → 6

**Class from total score:**

| Score range | Class |
|---|---|
| 0 – 5 | Prime |
| 6 – 9 | Desirable |
| 10 – 13 | Satisfactory |
| 14 – 18 | Watch |
| ≥ 19 | Doubtful |
| ≥ 19 **and** LTV > 1.0 | Projected Loss |

The `Projected Loss` class always overrides `Doubtful` when LTV exceeds 1.0.

### DSCR Stress Tests

Two stress formulas are used depending on the task:

- **Watch-list parallel shock** (+200bp): `stressed_dscr = base_dscr / 1.18`
- **CRE dual stress** (rate + vacancy): `stressed_dscr = base_dscr * 0.85 / 1.18`

Breach threshold for both: `stressed_dscr < 1.00`.

### Concentration Analysis

Branch-level sector concentration limit is in `branches[].sector_ceiling_pct`.
CRE-specific limit is `branches[].cre_policy_limit_pct`.  Compare sector
exposures and post-approval concentrations against these limits.

Sector over-concentration mitigations from policy: `participation_required`,
`reduced_amount`, `board_exception`.  Existing over-ceiling exposure may be
grandfathered (`grandfathered: 1`), but new approvals must not worsen that
sector without a mitigation applied.

### CRE Weighted Score (5 C's)

Weighted CRE score uses five components from policy `cre_weighted_score.weights`:

| Component | Weight |
|---|---|
| Capacity | 0.45 |
| Capital | 0.03 |
| Character | 0.05 |
| Collateral / Exposure | 0.36 |
| Conditions | 0.11 |

Score each component from application data (lower is better).  Multiply by its
weight and sum.  Classify:

| Score range | Class |
|---|---|
| ≤ 2.0 | `approve_quality` |
| 2.0 < score ≤ 3.0 | `conditional` |
| > 3.0 | `weak` |

### Benchmark Metrics

FDIC Q4 2024: field `total_loans_noncurrent_pct` for NPA comparison.
FDIC field `total_real_estate_30_89_pct` for CRE delinquency comparison.

NCUA Q1 2025: a table of states with `delinquency_bps`, `loan_to_share_pct`,
`roaa_bps`, `positive_net_income_pct`.  The `US` row is the national aggregate.

Compute branch NPA ratio as `nonperforming_loans / total_loans_outstanding`.
Variance bps = `(branch_ratio - benchmark_ratio) * 10000`.

### Decision and Reason Codes

Decision enum: `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`

Reason codes for declines:

- `capacity_limit` — branch has insufficient remaining Q1 capacity
- `sector_breach` — approval would breach sector ceiling without mitigation
- `weak_dscr` — DSCR is below acceptable thresholds
- `high_ltv` — LTV exceeds policy ceiling
- `low_fico` — FICO score is too low
- `recent_bankruptcy` — applicant has recent bankruptcy
- `startup_risk` — business age under 2 years with other weak factors
- `underwater_collateral` — LTV > 1.0
- `policy_floor_missing` — documentation or policy requirement not met
- `documentation_gap` — required documentation incomplete
- `fdic_adverse_variance` — branch FDIC benchmark performance is materially worse than benchmark
- `ncua_peer_weakness` — NCUA state metrics trail peers

Condition codes: `participation_required`, `reduced_amount`, `board_exception`,
`sba_guaranty_required`, `startup_monitoring`, `none`

## Task-Type Workflows

### 1. Rating Migration Review

Used when the task asks to review and re-derive risk ratings for a branch's
loans in a specified rating band, summarize migration, and produce NPA
benchmark analysis.

1. Fetch `/api/policies`, `/api/branches/{id}`, `/api/branches/{id}/metrics`,
   `/api/branches/{id}/loans`, `/api/benchmarks/fdic/q4-2024`.
2. Filter loans by `current_rating >= target_current_rating_min`.
3. Re-derive each loan's risk rating using the dominant-factor rule (DSCR,
   LTV, delinquency floor).
4. If a loan has no available factors, retain its `current_rating`.
5. Build `final_rating_exposure_totals`: group by `final_rating`, sum loan
   count and exposure; sort ascending by rating.
6. Build `migration_from_current_rating_3`: for loans that were `current_rating
   == 3`, show where they migrated to (only rows where final_rating > 3).
   Each row has `final_rating`, `loan_count`, `exposure`, `loan_ids` sorted.
7. Build `material_downgrades`: loans with `final_rating - current_rating >= 2`.
   Include `loan_id`, `current_rating`, `final_rating`, `downgrade_notches`,
   `exposure`.  Sort ascending by `loan_id`.
8. Build `watch_list_action_coverage`: loans with final_rating ≥ 6.  Group by
   action (final_rating 6 → `watchlist`, 7 → `special_assets`, 8 →
   `partial_chargeoff_review`).  Sort `by_action` ascending by action name.
9. **NPA benchmark**: use `nonperforming_loans` from Q1 2025 branch metrics (the
   `quarter` value `2025Q1`).  Benchmark metric is `total_loans_noncurrent_pct`.
   Branch NPA ratio = `nonperforming_loans / total_loans_outstanding`.
   Variance bps = `(branch_ratio - benchmark_ratio) * 10000`.
10. **Top problem credit**: the loan with the poorest `final_rating` and, as
    tiebreaker, the largest `outstanding_balance`.  Its action follows the
    rating-to-action mapping above.

### 2. Lending Allocation Package

Used when the task asks to allocate branch Q1 lending capacity across pending
applications.

1. Fetch `/api/policies`, `/api/branches/{id}`, `/api/branches/{id}/metrics`,
   `/api/branches/{id}/sector-exposures`, `/api/branches/{id}/applications`.
2. `lending_capacity_q1` comes from the branch record.
3. For each application, evaluate credit quality:
   - **DSCR**: under 1.0 is a hard decline signal (`weak_dscr`).
   - **LTV**: above 1.0 → `underwater_collateral`; above 0.85 without
     compensating strength → `high_ltv`.
   - **FICO**: below 580 → `low_fico`.
   - **Startup**: `years_in_business < 2` with weak supporting factors → `startup_risk`.
   - **Bankruptcy**: `bankruptcy_months_ago` within recent window → `recent_bankruptcy`.
   - **Documentation**: `documentation_complete == 0` → `documentation_gap`.
   - **Capacity**: sum of approved amounts must stay within
     `lending_capacity_q1`.  Applications that would exceed remaining capacity
     get `capacity_limit`.
   - **Concentration**: after approval, sector exposure must not exceed
     `sector_ceiling_pct` without a mitigation.  Breach → `sector_breach`.
4. Assign a decision for each application:
   - Clear credit + capacity → `approve`.
   - Good credit but sector concentration at ceiling → `conditional_approve`
     with `participation_required`.
   - SBA-eligible startup with marginal credit → `conditional_approve` with
     `sba_guaranty_required` and `startup_monitoring`.
   - Multiple hard reasons → `decline`.
5. `priority_ranking` lists `application_id` values for `approve` and
   `conditional_approve` decisions, highest priority first.  Order by
   application with the strongest credit profile (highest DSCR, strongest
   relationship, largest deposit balance) first, then conditional approvals.
6. `bank_capacity_used` for `participation_required` is the retained portion
   (typically `approved_amount * (1 - participation_pct)` where participation
   is the fraction the bank does not retain).  If no explicit participation
   split is given, use a standard 75/25 split (bank retains 75%).
7. `post_approval_concentrations`: re-compute each sector's exposure including
   newly approved amounts.  Compare `post_approval_pct` to `limit_pct`.

### 3. Credit Union Segment Posture

Used when the task asks for a segment-level posture recommendation backed by
NCUA benchmarks.

1. Fetch `/api/policies`, `/api/credit-union-segments/{segment_id}`,
   `/api/benchmarks/ncua/q1-2025`.
2. Extract the state row from NCUA for the segment's `state_code`.
3. Extract the `US` (national) row from NCUA.
4. Compute peer median from the `peer_states` listed in the segment data:
   for each of the four metrics, take the median across the peer states.  If an
   even number of peer states, average the middle two values.
5. Compare NC values to US and peer median on `delinquency_bps`,
   `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`.  Directions are
   `higher`, `lower`, or `equal`.
6. **Posture**: decide based on segment capacity and external risk.
   - Capacity available + risk weaker → `continue_with_tighter_conditions`.
   - Risk stronger than peers + capacity → `continue_approving`.
   - No capacity or severe risk → `temporarily_pause`.
7. Controls: `required_checklist_gates` from the segment's `minimum_checklist`.
   `added_operating_controls` are the full set from the template when tighter
   conditions are needed: `pre_close_insurance_binder_verification`,
   `lien_perfection_prior_to_funding`, `senior_underwriter_second_review`,
   `quarterly_state_benchmark_monitoring`, `monthly_segment_delinquency_watch`,
   `committee_exception_for_capacity_overrun`.
8. Escalation triggers: use the template enum triggers, assign owners based on
   the condition domain (risk → `credit_risk_manager`, ops →
   `operations_control_manager`, capacity/committee →
   `lending_committee_chair`).
9. Interpretation: match `capacity_status`, `external_risk_status`,
   `risk_tolerance` (from segment), and `committee_message` consistently.

### 4. Watch-List Stress and Workout

Used when the task asks to review adversely rated loans, apply CDFI risk
classes, stress DSCR, and queue workout actions.

1. Fetch `/api/policies`, `/api/branches/{id}/loans`, `/api/branches/{id}/metrics`.
2. Filter loans by `current_rating >= adverse_rating_min`.
3. For each loan, compute CDFI factor score:
   - Sum scores from available factors (debt_to_asset, fico, liquidity_months, ltv).
   - Skip null values.
   - Classify using the CDFI class table above.
4. Monitoring cadence: if any loan in the watch list is `Doubtful` or
   `Projected Loss` → `monthly`; if any is `Watch` → `quarterly`; otherwise `semiannual`.
5. **DSCR stress**: for loans with DSCR available, compute `stressed_dscr =
   base_dscr / 1.18`.  Breach when `stressed_dscr < 1.00`.  Sort results
   ascending by `loan_id`.
6. **Workout queue**: all adverse loans, sorted descending by `exposure`,
   then ascending `loan_id`.  Recommended action from rating-to-action map
   above.  `projected_loss` is `true` for `Projected Loss` class.
7. **Severe bucket counts**: group loans with `current_rating ≥ 6` by
   `current_rating` and `payment_status`.  For each bucket: `loan_count`,
   `exposure`.  Sort ascending by `current_rating` then `payment_status`
   lexicographically.

### 5. Competing CRE Decision

Used when the task asks to compare two CRE applications and recommend a path.

1. Fetch `/api/policies`, `/api/branches/{id}`, `/api/branches/{id}/metrics`,
   `/api/branches/{id}/loans`, `/api/branches/{id}/sector-exposures`,
   `/api/branches/{id}/applications`, `/api/benchmarks/fdic/q4-2024`.
2. For each of the two applications, compute the weighted CDFI CRE score:
   - Each of the five components is scored from the application's data.
   - Use the policy weights to produce a weighted sum.
   - Classify using the CRE score class table.
3. **Dual stress**: for each application, compute `stressed_dscr = base_dscr *
   0.85 / 1.18`.  Breach when stressed falls below 1.00.
4. **Concentration analysis**:
   - `cre_policy_limit_pct` from branch data.
   - Sum up existing CRE exposure: all branch loans with `loan_type == "CRE"`.
   - Compute `existing_cre_concentration = existing_cre_exposure / total_loans_outstanding`.
   - `selected_post_approval_cre_concentration = (existing_cre_exposure + selected_app_requested_amount) / total_loans_outstanding`.
   - `selected_policy_variance_bps = (post_approval_concentration - cre_policy_limit_pct) * 10000`.
   - FDIC comparison uses `total_real_estate_30_89_pct` against branch
     `delinquency_30_plus_pct`.
5. **Recommended path**: select the application with the lower (better)
   weighted score.  Its path depends on its score class and concentration:
   - `approve_quality` → `approve` (if concentration allows).
   - `conditional` → `conditional_approve` or `participation_required` (if
     sector is over ceiling).
   - The unselected application gets `decline` or `defer` with its reason codes.
6. **Conditions** for the selected application: derive from risk profile.
   Always include conditions that address identified weaknesses.

## Answer Shape

Every task supplies an `answer_template.json` in `input/payloads/`.  Read it
first.  The template defines all required top-level keys, field types, enums,
and sort orders.  Produce valid JSON conforming exactly to that template.

Pay close attention to:
- **Numeric precision**: currency fields rounded to 2 decimal places;
  ratios rounded to 4 decimal places; bps rounded to 2 decimal places.
- **Sort order**: noted on each list field in the template (ascending by
  `loan_id`, `application_id`, `sector`, `final_rating`, etc.).
- **Enum values**: use only the allowed strings from the template or policy.

## Common Calculation Patterns

### Re-derive a single loan rating (Python pseudocode)

```python
def rederive_rating(loan):
    ratings = []
    if loan["dscr"] is not None:
        dscr = loan["dscr"]
        if dscr >= 1.50:     ratings.append(3)
        elif dscr >= 1.25:   ratings.append(4)
        elif dscr >= 1.05:   ratings.append(5)
        elif dscr >= 1.00:   ratings.append(6)
        else:                ratings.append(7)
    if loan["ltv"] is not None:
        ltv = loan["ltv"]
        if ltv <= 0.65:      ratings.append(3)
        elif ltv <= 0.75:    ratings.append(4)
        elif ltv <= 0.85:    ratings.append(5)
        elif ltv <= 1.00:    ratings.append(6)
        else:                ratings.append(7)
    status = loan["payment_status"]
    if status == "Nonaccrual":       ratings.append(8)
    elif status == "90+ Days Past Due": ratings.append(7)
    elif status == "60 Days Past Due":  ratings.append(5)
    elif status == "30 Days Past Due":  ratings.append(4)
    # "Current" adds no floor

    if not ratings:
        return loan["current_rating"]
    return max(ratings)
```

### Compute CDFI factor score (Python pseudocode)

```python
def cdfi_factor_score(loan):
    score = 0
    if loan.get("debt_to_asset") is not None:
        dta = loan["debt_to_asset"]
        if dta < 0.40:     score += 0
        elif dta <= 0.60:  score += 2
        elif dta <= 0.80:  score += 4
        else:              score += 6
    if loan.get("fico") is not None:
        fico = loan["fico"]
        if fico > 720:      score += 0
        elif fico >= 680:   score += 1
        elif fico >= 580:   score += 3
        else:               score += 5
    if loan.get("liquidity_months") is not None:
        lm = loan["liquidity_months"]
        if lm > 12:    score += 0
        elif lm >= 6:  score += 1
        elif lm >= 3:  score += 3
        else:          score += 5
    if loan.get("ltv") is not None:
        ltv = loan["ltv"]
        if ltv < 0.40:     score += 0
        elif ltv <= 0.60:  score += 2
        elif ltv <= 0.80:  score += 4
        else:              score += 6
    return score

def cdfi_class(score, ltv):
    if score >= 19 and ltv is not None and ltv > 1.0:
        return "Projected Loss"
    if score >= 19:  return "Doubtful"
    if score >= 14:  return "Watch"
    if score >= 10:  return "Satisfactory"
    if score >= 6:   return "Desirable"
    return "Prime"
```

### Watch-list action from final rating (Python pseudocode)

```python
def watch_list_action(final_rating):
    if final_rating >= 8:  return "partial_chargeoff_review"
    if final_rating >= 7:  return "special_assets"
    if final_rating >= 6:  return "watchlist"
    return None  # no watch-list action
```

### DSCR stress (Python pseudocode)

```python
def stress_watch_list(dscr):
    return dscr / 1.18

def stress_cre_dual(dscr):
    return dscr * 0.85 / 1.18
```

## Things to Avoid

- Do not treat `collateral_value` and `ltv` as interchangeable for risk rating;
  use `ltv` directly.
- Do not assume the Q1 2025 branch metrics row is the first element; match on
  `"quarter": "2025Q1"`.
- Do not assume loans are sorted; always sort results as the template dictates.
- Do not apply the delinquency floor to loans that are `Current`; the floor
  only applies to past-due and nonaccrual statuses.
- For the NCUA table, `"US"` is the national aggregate row with `state_code:
  "US"`, not a computed average of all states.
- When computing peer median from NCUA `peer_states`, use only the states listed
  in the segment's `peer_states` field.  Sort the values, pick the median.
- When the policy says "worst numeric rating", that means the highest integer
  value (a rating of 8 is worse than 7, 7 worse than 6, etc.).
- `Partially_required` condition means the bank must place a portion of the
  exposure with a participant.  The bank retains the remainder as
  `bank_capacity_used`.
- The `grandfathered` flag on sector exposures means existing over-ceiling
  exposure is tolerated but must not be worsened by new approvals without
  mitigation.
