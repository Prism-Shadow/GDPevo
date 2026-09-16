---
name: credit-risk-committee
description: Lending committee analysis using a shared credit office REST API. Use when the task requires preparing committee-ready JSON reports for branch loan portfolio reviews, rating migrations, lending allocation decisions, watch-list stress tests, credit union segment posture assessments, or competing CRE application comparisons. Triggers on tasks mentioning credit risk committee, lending committee packet, branch rating migration, allocation package, segment posture, watch-list stress, or CRE competing decision.
---

# Credit Risk Committee

Use the shared credit office API at `<TASK_ENV_BASE_URL>` to prepare committee-ready JSON outputs. No authentication is needed.

## Quick Start

1. Read the prompt and the `answer_template.json` payload (if present) to understand the required output shape, enum values, and sort orderings.
2. Run `GET /api/manifest` to confirm available endpoints and benchmark versions.
3. Run `GET /api/policies` to load the credit policy rules (risk-rating thresholds, CDFI scoring tables, weighted CRE scores, stress formulas, capacity/concentration rules).
4. Fetch branch, loan, application, sector-exposure, metric, benchmark, and segment data as needed for the specific task.
5. Apply the policy rules to derive ratings, scores, decisions, and actions.
6. Produce a single valid JSON object that matches the template shape exactly.

**Key principle:** Always read the `answer_template.json` first. It defines required keys, enums, sort orders, and numeric precision. Output must conform to every constraint in the template.

## API Reference

See [references/api_endpoints.md](references/api_endpoints.md) for the complete API surface, endpoint shapes, field descriptions, and common patterns.

## Policy Rules

See [references/policy_rules.md](references/policy_rules.md) for risk-rating derivation, CDFI factor scoring, CRE weighted scoring, stress formulas, capacity/concentration logic, watch-list action mapping, decline reason codes, and application decision logic.

## Workflows

### 1. Rating Migration Review

For tasks that ask to review a branch loan portfolio, re-derive risk ratings, and summarize migration.

**Steps:**

1. Fetch branch loans via `GET /api/branches/{branch_id}/loans`.
2. Fetch branch metrics via `GET /api/branches/{branch_id}/metrics` (use the first entry — current quarter).
3. Fetch the appropriate FDIC benchmark (typically `GET /api/benchmarks/fdic/q4-2024`).
4. Filter the loan population: `current_rating >= target_min` (usually 3).
5. Re-derive each loan's `final_rating` using the dominant-factor rule in the policy reference.
6. Compute `portfolio_regrade`: target population counts, exposure, rating buckets, migration from the original rating, and watch-list action coverage.
7. Compute `npa_benchmark`: branch NPA ratio vs FDIC benchmark, variance in ratio and bps.
8. Identify `material_downgrades`: loans where `final_rating - current_rating >= 2` notches.
9. Pick `top_problem_credit`: the loan with the worst final rating; break ties by highest exposure and worst payment status.
10. Assign `recommended_action` per the watch-list action mapping in the policy reference.

**Watch-list action coverage:** Only count loans with `final_rating >= 6` and group by action.

### 2. Lending Allocation Package

For tasks that ask to allocate lending capacity across pending applications for a branch.

**Steps:**

1. Fetch branch details, branch metrics (for total loans outstanding), sector exposures, and pending applications.
2. Compute auto-decline reasons for each application using the conditions in the policy reference.
3. Compute post-approval concentration per sector before ranking:
   - `post_approval_pct = (current_exposure + approved_amount) / (total_loans_outstanding + sum_of_approved_amounts)`.
4. Rank eligible applications (those not auto-declined) by priority:
   - Higher DSCR, lower requested amount, higher FICO, longer relationship, longer years in business.
5. Iterate through the ranked list: approve each application if `remaining_capacity >= bank_capacity_used`, and the sector limit is not breached (or can be mitigated). Track `bank_capacity_used` in dollar terms.
6. For flagged sectors (post-approval pct close to or over limit), apply mitigation: `participation_required`, `reduced_amount`, or `board_exception`.
7. For declined applications, map each to a sorted list of reason codes from the policy reference.
8. Compute `allocation` summary: lending capacity, gross approved, committed capacity, remaining capacity, priority ranking of approved/conditionally-approved apps.
9. Build `concentration_flags` for any sector where post-approval pct is within 0.5% of the limit or over.
10. Build `post_approval_concentrations` for every sector that has exposure.

**Capacity math:**
- `committed_capacity_amount` = sum of `bank_capacity_used` across all decisions.
- For participations: `bank_capacity_used = approved_amount * (1 - participation_share)`. If participation share is not explicitly given, estimate from the required mitigation: typically 75% participation = bank retains 25%.
- `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`.

### 3. Credit Union Segment Posture

For tasks that assess a credit union segment and recommend a posture.

**Steps:**

1. Fetch segment data via `GET /api/credit-union-segments/{segment_id}`.
2. Fetch NCUA benchmarks via `GET /api/benchmarks/ncua/q1-2025`.
3. Look up the target state row and the US row from the benchmark `rows` array.
4. For each peer state in `segment.peer_states`, look up its benchmark row and compute the median across peers for each of the four metrics (`delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`).
5. Compare target state vs US and target state vs peer median on each metric: `higher`, `lower`, or `equal`.
6. Determine posture from the pattern:
   - `continue_approving`: stronger or equal on most metrics.
   - `continue_with_tighter_conditions`: mixed picture, capacity available.
   - `temporarily_pause`: materially weaker on most metrics or `recent_delinquency_bps >= 90`.
7. Select escalation triggers that match the segment's specific risk profile (delinquency, control issues, capacity pressure).
8. Set operating controls from `segment.minimum_checklist` plus additional controls addressing the segment's `control_issue` and `staffing_constraint`.
9. Interpret: `capacity_status` from quarterly capacity and outstanding, `external_risk_status` from benchmark comparisons, `risk_tolerance` from segment, and `committee_message` matching the posture logic.

### 4. Watch-List Stress

For tasks that stress-test adversely rated loans and queue workout actions.

**Steps:**

1. Fetch branch loans via `GET /api/branches/{branch_id}/loans`.
2. Filter to `current_rating >= adverse_rating_min` (typically 6).
3. For each adverse loan, compute the CDFI factor score by summing individual dimension scores from the policy tables (skip null dimensions). Map total to risk class.
4. Assign `monitoring_cadence`: `monthly` if any loan has `risk_class` of Watch or worse, `quarterly` if all are Desirable or better, `semiannual` if all are Prime.
5. For loans with non-null `dscr`, apply the watch-list stress: `stressed_dscr = base_dscr / 1.18`. Mark `breaches_threshold` when `stressed_dscr < 1.0`.
6. Build `breach_loan_ids` list from loans that breach.
7. Build `workout_queue`: all adverse loans, sorted descending by exposure then ascending by loan_id. Assign `recommended_action` per the policy reference and `projected_loss` for `risk_class == "Projected Loss"`.
8. Build `severe_bucket_counts`: group by `current_rating` and `payment_status`, count loans and sum exposure. Include only ratings 6+.

### 5. Competing CRE Decision

For tasks that compare two CRE applications and recommend one.

**Steps:**

1. Fetch branch details, branch metrics, branch loans, branch sector exposures, and the two target applications.
2. Compute the weighted CDFI score for each application using the CRE weighted-score rules in the policy reference.
3. Assign `score_class`: `approve_quality` (<= 2.0), `conditional` (2.0 < score <= 3.0), `weak` (> 3.0).
4. Apply CRE dual stress: `stressed_dscr = base_dscr * 0.85 / 1.18`. Mark `breaches_threshold` when `stressed_dscr < 1.0`.
5. Compute CRE concentration: sum all existing CRE loans (`loan_type == "CRE"`), divide by `total_loans_outstanding` for existing concentration. Add the selected application's `requested_amount` to compute post-approval concentration.
6. Compute FDIC variance: branch `delinquency_30_plus_pct` vs FDIC `total_real_estate_30_89_pct`.
7. Compare the two applications: select the one with the lower weighted score; use stress breach and concentration impact as tiebreakers.
8. For the selected application: determine `path` (approve, conditional_approve, participation_required) based on concentration headroom and stress results.
9. For the unselected: set `decline` or `defer` with reason codes reflecting the weaknesses.
10. Build `conditions` for the selected application: include CRE-specific controls that address concentration, stress, and benchmark variance.

## General Output Rules

- All numeric outputs must use 2-decimal precision for USD values and 4-decimal precision for ratios unless the template specifies otherwise.
- Lists must be sorted per the template ordering directive (ascending/descending by specified field).
- Enum values must match the template's allowed values exactly.
- When a data field is null and a required computation cannot proceed, note the limitation: skip the loan for stress if DSCR is null, skip the factor if the source field is null during CDFI scoring, etc.
- Do not include narrative text outside the JSON response.
- Use the exact field names, casing, and structure from the answer template.
