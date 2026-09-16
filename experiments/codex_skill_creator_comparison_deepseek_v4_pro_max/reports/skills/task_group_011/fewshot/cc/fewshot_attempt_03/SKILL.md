---
name: credit-risk-committee
description: Prepare credit risk committee packets from the shared credit office API. Use when the user needs a rating migration review, lending-committee allocation, credit-union segment posture analysis, watch-list stress test, competing-CRE decision, or any branch-level risk report that pulls from the credit office API. This skill covers policy-driven risk-rating re-derivation, CDFI risk classification, DSCR stress testing, concentration and capacity enforcement, FDIC/NCUA benchmark comparisons, and committee-ready JSON output.
---

# Credit Risk Committee Packet Preparation

Use this skill whenever a user asks you to prepare a committee-ready credit risk
analysis that draws from the shared credit office API. The API is public (no
credentials) and is reached at the base URL the runner provides as
`<TASK_ENV_BASE_URL>`. Every task follows the same basic rhythm: fetch live
data, apply the credit policy rules, run any required computations, and produce
strictly shaped JSON.

## Overall workflow

1. **Fetch the manifest and policies** first. `GET /api/manifest` tells you what
   endpoints and record counts are available. `GET /api/policies` returns the
   single source of truth for all rating, scoring, stress, and
   capacity/concentration rules (see [references/policy_rules.md](references/policy_rules.md) for
   a detailed walkthrough of every section in the policy response).
2. **Pull the entity data** for the target branch, segment, or applications.
3. **Apply the policy logic** to derive risk ratings, risk classes, decision
   outcomes, or posture recommendations.
4. **Pull relevant benchmark data** from the FDIC or NCUA endpoints when the
   task calls for an external comparison.
5. **Produce JSON output** that strictly matches the answer template shape. Every
   template provides a `required_top_level_keys` array and field-level
   constraints — treat those as the authoritative schema. Do not add keys
   the template does not request, and do not reorder items contrary to the
   stated ordering rules.

## API quick reference

All endpoints return JSON arrays or objects. No pagination is needed; every
collection fits in a single response.

| Endpoint | Purpose |
|---|---|
| `GET /api/manifest` | Map of available endpoints and record counts |
| `GET /api/policies` | All policy rules: risk rating, CDFI, CRE scoring, stress, capacity |
| `GET /api/branches` | List of all branches with lending capacity, sector ceilings, FDIC set |
| `GET /api/branches/{id}` | Single branch detail |
| `GET /api/branches/{id}/metrics` | Branch delinquency, NPA, deposit, and loan totals by quarter |
| `GET /api/branches/{id}/loans` | Every loan with collateral, DSCR, LTV, FICO, payment status, and more |
| `GET /api/branches/{id}/sector-exposures` | Per-sector current exposure, limit_pct, and grandfathered flag |
| `GET /api/branches/{id}/applications` | Pending applications with financials, collateral, and flags |
| `GET /api/benchmarks/fdic/q4-2024` | FDIC Q4 2024 benchmark ratios |
| `GET /api/benchmarks/ncua/q1-2025` | NCUA Q1 2025 state-by-state metrics (12 rows including `US`) |
| `GET /api/credit-union-segments/{id}` | Segment detail including peer states, capacity, and internal context |

## Policy rule application

Every policy rule lives in the `/api/policies` response. Read the full policy
walkthrough in [references/policy_rules.md](references/policy_rules.md). The most commonly
used sections are summarised below.

### Risk-rating re-derivation (dominant-factor rule)

When a task tells you to re-derive a risk rating, follow the policy's
`risk_rating.dominant_factor_rule`: **the final rating is the worst (highest
numeric) rating from the three available factor dimensions — DSCR, LTV or
collateral, and delinquency.**

For each loan in scope:

1. **DSCR rating**: Map the loan's `dscr` through the `dscr_thresholds` table.
   Rows with `min` define a floor; the row with `max_below` defines a
   ceiling. If `dscr` is null, skip this dimension.
2. **LTV or collateral rating**: Map the loan's `ltv` through the
   `ltv_thresholds` table (same structure as DSCR). If `ltv` is null, skip.
3. **Delinquency rating**: Use `delinquency_minimums` with the loan's
   `payment_status`. `"Current"` maps to `null`, meaning no delinquency-based
   rating floor.
4. Take the **maximum** of the numeric ratings you obtained. That is the
   re-derived `final_rating`. If none of the dimensions produced a rating,
   keep the loan's `current_rating`.

A downgrade is **material** when `final_rating - current_rating >= 2` (the
policy's `material_downgrade_notches`).

### CDFI risk classification

Used for watch-list and adverse-credit workflows. Score each loan across four
factor dimensions using the tables in `cdfi_factor_scores`, sum the scores,
then classify:

| Class | Score range | Special condition |
|---|---|---|
| Prime | 0–5 | |
| Desirable | 6–9 | |
| Satisfactory | 10–13 | |
| Watch | 14–18 | |
| Doubtful | ≥19 | and ltv ≤ 1.0 |
| Projected Loss | ≥19 | and ltv > 1.0 |

Factor dimensions: `ltv`, `fico`, `liquidity_months`, `debt_to_asset`. Each
maps a value range to an integer score. If a field is null, score it as 0 for
that dimension.

### CRE weighted scoring

When comparing CRE applications, compute a weighted score from five dimensions
using the weights in `cre_weighted_score.weights`. The raw inputs come from
the application objects. Score each dimension with a 1–3 integer (1 best,
3 worst) based on the thresholds described in the policy walkthrough, then
multiply by the dimension weight and sum.

Classify: ≤2.0 → `approve_quality`, ≤3.0 → `conditional`, >3.0 → `weak`.

### DSCR stress formulas

Two variants exist in `stress`:

- **Watch-list / parallel shock (+200bp)**: `stressed_dscr = base_dscr / 1.18`
- **CRE dual-stress**: `stressed_dscr = base_dscr * 0.85 / 1.18`

The breach threshold (`coverage_breach_threshold`) is always `1.0`. Only
apply stress to loans or applications that have a numeric `dscr`.

### Lending capacity and sector-concentration enforcement

- The branch's Q1 lending capacity is `lending_capacity_q1` from the branch
  detail or branch list.
- The general sector ceiling is `sector_ceiling_pct`; CRE-specific policy limits
  use `cre_policy_limit_pct` (from the branch).
- Per-sector limits come from the sector-exposures endpoint (`limit_pct` and
  `current_exposure`). New approvals must not cause a sector to exceed its
  limit. When a sector limit would be breached, the `allowed_mitigations` are
  `participation_required`, `reduced_amount`, and `board_exception`.

When computing post-approval concentrations, add approved amounts (bank-held
portion only — participation shares are excluded) to the current sector
exposure, then divide by `total_loans_outstanding` (from the most recent
quarter's branch metrics).

## Benchmark comparisons

### FDIC Q4 2024

The FDIC endpoint returns a single object with five ratio fields. Use the
metric that matches the task context:

- `total_loans_noncurrent_pct`: For general NPA comparison
- `total_real_estate_noncurrent_pct`: For real-estate-specific NPA
- `total_real_estate_30_89_pct`: For 30–89 day delinquency in real estate
- `construction_development_noncurrent_pct`: For construction-specific NPA
- `construction_development_30_89_pct`: For construction 30–89 day delinquency

Compute variance as `branch_ratio - fdic_benchmark_ratio` and in basis points
as `variance_ratio * 10000`.

### NCUA Q1 2025

The NCUA endpoint returns an array under `rows`. Each row is a state or `"US"`.
The four metrics are `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, and
`positive_net_income_pct` — all integers.

For a segment posture analysis:
- Look up the target state's row and the `US` row.
- Identify the peer states from the segment's `peer_states` list, then compute
  the peer median for each metric.
- Compare the target state to both US and peer median using `higher`, `lower`,
  or `equal`.

## JSON output discipline

Every task provides a template file (`answer_template.json`) that defines the
exact JSON shape. Key rules that apply across all templates:

- **Required keys**: The `required_top_level_keys` array is absolute — every
  listed key must appear. Nested objects have their own `required_keys`.
- **Ordering**: When a field says `"ordering": "ascending by X"`, sort the items
  exactly as stated. Use locale-free string ordering for IDs.
- **Enums**: When a field lists `allowed_values`, use only those exact strings.
  Do not abbreviate, hyphenate differently, or introduce new values.
- **Numeric precision**: Round currency values to 2 decimals and ratios to 4
  decimals unless the template says otherwise.
- **Lists of IDs**: Sort them ascending.
- **No text outside JSON**: Unless the prompt says otherwise, answer with only
  the JSON object.

## Workflow patterns

### Rating migration review (branch-level)

1. Fetch branch, loans, metrics, policies, and FDIC benchmark.
2. Filter loans by `current_rating >= target_min`.
3. Re-derive `final_rating` for each using the dominant-factor rule.
4. Build the regrade summary: count and exposure by final rating.
5. Identify material downgrades: `final_rating - current_rating >= 2`.
6. Compute the migration specifically for loans that started at rating 3.
7. Compute NPA benchmark comparison using the branch's `nonperforming_loans`
   and `total_loans_outstanding` from the most recent quarter.
8. Pick the top problem credit (highest exposure among the worst-rated
   nonperforming or heavily downgraded loans).
9. Assign watch-list actions: `special_assets` for rating 7,
   `partial_chargeoff_review` for rating 8 (nonaccrual),
   `watchlist` for rating 6.
10. Fill the JSON template.

### Lending-committee allocation (branch-level)

1. Fetch branch detail, sector exposures, applications, and policies.
2. Score/discriminate applications using credit factors: DSCR, LTV, FICO,
   bankruptcy, years in business, documentation completeness, relationship
   strength.
3. Rank approvable applications by credit quality, relationship value, and
   sector fit. Only approved and conditionally approved applications go in
   the priority ranking.
4. Allocate capacity sequentially: `bank_capacity_used = approved_amount` for
   full approvals, or the bank-retained portion for participations. For SBA
   loans, the bank portion is `approved_amount * (1 - sba_guaranty_pct)`.
5. For each application, check whether adding its bank-held exposure would
   push the sector past its `limit_pct` limit. Flag and apply mitigations
   (participation, reduced amount, etc.) when it would.
6. Assign decline reason codes from the policy's allowed list based on
   the specific weaknesses of each declined application.
7. Compute post-approval concentration per sector.
8. Fill the JSON template.

### Credit-union segment posture

1. Fetch policies, NCUA benchmark, and the target segment.
2. Look up the segment's state in the NCUA rows. Also fetch `US` and each
   peer state from the segment's `peer_states` list.
3. Compute peer medians for each metric.
4. Compare NC to US and NC to peer median on all four dimensions.
5. Determine posture: `continue_approving` when state metrics are stronger
   or equal to both US and peers; `continue_with_tighter_conditions` when
   mixed (some weaker but capacity exists); `temporarily_pause` when all
   indicators are weaker and no mitigating controls exist.
6. Use the segment's `minimum_checklist` as the required gates. Add operating
   controls from the policy's context (insurance binders, lien perfection,
   quarterly monitoring, senior underwriter review).
7. Define escalation triggers with condition-owner pairs.
8. Write the interpretation block using the controlled enum choices.
9. Fill the JSON template.

### Watch-list stress and workout

1. Fetch branch loans and policies.
2. Filter loans with `current_rating >= adverse_rating_min` (usually 6).
3. Assign CDFI risk classes from the factor-score tables.
4. Set monitoring cadence: `monthly` when any loan is Watch or worse,
   `quarterly` when all are Desirable or better, `semiannual` otherwise.
5. Apply the watch-list DSCR stress (`dscr / 1.18`) to every adverse loan
   that has a DSCR value.
6. Build the workout queue sorted by descending exposure then ascending
   loan_id. Recommended actions: `partial_chargeoff_review` for Projected Loss,
   `special_assets` for 90+ or Nonaccrual, `watchlist` for Watch class,
   `workout` for Doubtful, `monitor` for Satisfactory or better.
7. A `projected_loss` flag is `true` when the risk class is `Projected Loss`
   or the loan is on nonaccrual with ltv > 1.0.
8. Build severe bucket counts: group by `current_rating` and `payment_status`
   for all adverse loans, sorted ascending by rating then payment status.
9. Fill the JSON template.

### Competing CRE decision

1. Fetch branch detail, branch loans, sector exposures, the two target
   applications, policies, and FDIC benchmark.
2. Score each application using the CRE weighted scoring dimensions.
3. Apply the dual-stress DSCR formula (`dscr * 0.85 / 1.18`) to each
   application that has a DSCR.
4. Compute the branch's existing CRE exposure: sum all loans where
   `loan_type == "CRE"` from the loans endpoint. Compute the CRE
   concentration as that sum divided by `total_loans_outstanding` (latest
   quarter metrics). Compute the post-approval concentration by adding
   the selected application's amount.
5. Compare the branch's 30+ delinquency ratio against the FDIC
   `total_real_estate_30_89_pct` benchmark.
6. The recommended path selects the stronger application (lower weighted
   score, DSCR above breach threshold, manageable concentration).
   Disposition for the unselected: `decline` or `defer`.
7. Assign conditions from the template's allowed list based on the risk
   profile (CRE concentration over policy limit, FDIC variance, DSCR
   vulnerability).
8. Fill the JSON template.

## What to read next

When you need the detailed step-by-step for every policy rule section, open
[references/policy_rules.md](references/policy_rules.md). It walks through the JSON
structure returned by `/api/policies` field by field so you know exactly how
to map each loan or application value to its policy outcome.
