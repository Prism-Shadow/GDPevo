---
name: credit-risk-committee-analyst
description: Analyze bank and credit-union loan portfolios for lending-committee or credit-risk-committee decision packages. Use this skill whenever a user asks about branch risk ratings, loan portfolio regrades, watch-list stress testing, lending allocations, credit-union segment posture, concentration analysis, competing credit decisions, or FDIC/NCUA benchmark comparisons. Also trigger when the task involves a shared credit office API, branch loan data, credit policy rules, or committee-ready JSON outputs for any financial-institution workflow—even if the user doesn't use the exact words "committee" or "credit risk."
---

# Credit Risk Committee Analyst

This skill guides analysis of bank and credit-union lending portfolios for committee decision packages. The target environment provides a shared credit office REST API with branch data, loans, applications, sector exposures, policies, and FDIC/NCUA benchmark data. The solver reads raw data from the API, applies policy rules algorithmically, and produces structured committee-ready JSON answers.

## Core workflow

Every committee task follows the same general pattern:

1. **Read the task prompt** to identify the target entity (branch_id or segment_id), the review type, and the required output template from `input/payloads/answer_template.json`. The template defines the exact JSON shape, enum choices, precision, and ordering rules.

2. **Fetch the manifest** from `{TASK_ENV_BASE_URL}/api/manifest` to confirm available endpoints and benchmark versions. The manifest is the authoritative source for what data exists.

3. **Fetch policy data** from `{TASK_ENV_BASE_URL}/api/policies`. The policy document contains every rule you need: risk-rating thresholds, CDFI factor scoring tables, CRE weighted score weights and classes, stress formulas, concentration rules, and watch-list action definitions. Always read `references/policy-rules.md` alongside the raw policy JSON to understand how to apply each rule section.

4. **Fetch the target entity data** — branch detail, metrics, loans, sector exposures, and applications — from the branch endpoints or the segment endpoint. For benchmarks, fetch FDIC Q4 2024 or NCUA Q1 2025 depending on the entity type (bank vs. credit union) and what the task specifies.

5. **Apply the policy rules** to derive ratings, scores, stressed values, concentration calculations, and action recommendations. Do not guess — every derivation has a rule in the policy JSON. See `references/policy-rules.md` for the exact formulas.

6. **Write a clean JSON answer** matching the template. Follow enum choices, precision rules, ordering rules, and required keys exactly. Round numbers at the end; do not propagate rounded intermediates.

## API navigation

The base URL is supplied as `{TASK_ENV_BASE_URL}` in the task prompt. Key endpoints:

| Endpoint | Use |
|---|---|
| `/api/manifest` | Available endpoints, benchmark versions, record counts |
| `/api/policies` | Rating thresholds, factor scores, stress formulas, concentration rules |
| `/api/branches` | All branches (id, capacity, ceilings, state, type) |
| `/api/branches/{id}` | Single branch detail |
| `/api/branches/{id}/metrics` | Quarterly metrics: deposits, loans outstanding, NPA, delinquency, allowance |
| `/api/branches/{id}/loans` | Full loan portfolio with financials, ratings, payment status |
| `/api/branches/{id}/sector-exposures` | Sector-level exposure, limits, grandfathering |
| `/api/branches/{id}/applications` | Pending applications with financials, collateral, guarantees |
| `/api/benchmarks/fdic/q4-2024` | FDIC bank benchmarks (NPA ratios, delinquency ratios) |
| `/api/benchmarks/ncua/q1-2025` | NCUA credit-union benchmarks by state |
| `/api/credit-union-segments/{id}` | Credit-union segment detail with internal context, peer states, controls |

For most tasks you need the branch loans, the branch metrics (latest quarter), the sector exposures, and, if applications are involved, the branch applications. Benchmark data may be needed for NPA comparison or for segment posture.

Use the latest quarter's metrics values unless the task specifies otherwise. The metrics array is ordered with latest first.

## Policy rules

The policy endpoint returns the complete credit rule set. Read `references/policy-rules.md` for detailed application guidance. Key rule families:

### Risk rating re-derivation

The dominant-factor rule picks the **worst** (highest numeric) rating from:
- **DSCR factor** — map the loan's `dscr` through the `risk_rating.dscr_thresholds` table
- **LTV/collateral factor** — map `ltv` through `risk_rating.ltv_thresholds`; if LTV is null but `collateral_value` is also null, this factor contributes no rating
- **Delinquency floor** — map `payment_status` through `risk_rating.delinquency_minimums` (Current → no floor, Nonaccrual → 8)

If any loan has a null DSCR and a null LTV, only the delinquency floor (if any) applies. For loans where both DSCR and LTV are null, the current rating stands unless the delinquency floor elevates it.

When computing rating migration, compare `final_rating` to `current_rating`. A downgrade is material when `final_rating - current_rating >= 2` (the `material_downgrade_notches` value from policy).

### CDFI risk classification (for watch-list tasks)

Score each factor from the `cdfi_factor_scores` tables: `fico`, `ltv`, `debt_to_asset`, `liquidity_months`. Null factors contribute 0. Sum to a total score, then classify:

| Class | Score range |
|---|---|
| Prime | 0–5 |
| Desirable | 6–9 |
| Satisfactory | 10–13 |
| Watch | 14–18 |
| Doubtful | >=19 |
| Projected Loss | >=19 and ltv > 1.0 |

### CRE weighted credit scoring (for CRE comparison tasks)

Each application gets a weighted score using the weights in `cre_weighted_score.weights`:
- **capacity** (0.45) — score based on DSCR. Map: DSCR >= 1.50 → 0, 1.25–1.49 → 1, 1.05–1.24 → 2, 1.00–1.04 → 3, < 1.00 → 4
- **capital** (0.03) — score from CDFI LTV factor table
- **character** (0.05) — score from CDFI FICO factor table
- **collateral_exposure** (0.36) — score from CDFI debt_to_asset factor table
- **conditions** (0.11) — score: 0 if prior_delinquencies_12m = 0, 1 for 1–2, 2 for 3+

Multiply each score by its weight and sum. Classify: <= 2.0 → approve_quality, > 2.0 and <= 3.0 → conditional, > 3.0 → weak.

### Stress testing

- **Watch-list DSCR stress** (`+200bp`): `stressed_dscr = dscr / 1.18`. Breach threshold: 1.0.
- **CRE dual-stress formula**: `stressed_dscr = dscr * 0.85 / 1.18`. Breach threshold: 1.0.

Only apply stress to loans/applications where DSCR is available.

### Concentration analysis

The branch's `sector_ceiling_pct` is the default limit for most sectors. Some sectors may have an override in the `sector_exposures` table with a different `limit_pct`.

- `existing_concentration = sector_exposure / total_loans_outstanding`
- `post_approval_concentration = (sector_exposure + approved_amount) / (total_loans_outstanding + approved_amount)` for that sector
- `policy_variance_bps = (post_approval_concentration - limit_pct) * 10000`

For CRE-specific concentration, use `cre_policy_limit_pct` and sum all loans with `loan_type: "CRE"` plus any CRE application being considered.

Grandfathering: existing over-ceiling exposure may be grandfathered, but new approvals may not worsen that sector without mitigation (`participation_required`, `reduced_amount`, or `board_exception`).

### Benchmark comparison

For FDIC benchmarks, branch NPA ratio = `nonperforming_loans / total_loans_outstanding`. Variance ratio = branch_ratio - benchmark_ratio. Variance bps = variance_ratio * 10000.

For NCUA state benchmarks, compare the segment's state data to the NCUA benchmark rows. Peer states come from the segment endpoint. Compute US and peer-median comparisons directionally (higher/lower/equal) per metric.

### Watch-list actions

Actions escalate with severity: `monitor` → `watchlist` → `special_assets` → `workout` → `partial_chargeoff_review` → `legal_referral`. Assignment guidelines:
- Current + low DSCR but not breaching → `watchlist`
- 90+ DPD or Nonaccrual + moderate DSCR → `special_assets`
- Nonaccrual + underwater (ltv > 1.0) + breached → `partial_chargeoff_review`
- Current but structurally weak (high factor_score, breached stress) → `special_assets`
- Factor score 6–9 and Current → `watchlist`

### Application decline reason codes

Match decline reason codes from the answer template's allowed enums. Common mappings:
- `weak_dscr` — DSCR below policy floor
- `high_ltv` — LTV above 0.80
- `low_fico` — FICO below 580
- `recent_bankruptcy` — bankruptcy_months_ago is present
- `startup_risk` — years_in_business < 2
- `capacity_limit` — remaining capacity insufficient
- `sector_breach` — post-approval would breach sector limit without mitigation
- `documentation_gap` — documentation_complete == 0
- `fdic_adverse_variance` — branch significantly underperforming FDIC benchmark
- `policy_floor_missing` — DSCR or LTV below policy minimums

## Common task patterns

### Rating migration review (branch loan portfolio)

1. Fetch branch loans, metrics, and FDIC benchmark
2. Filter loans by `target_current_rating_min` (from template)
3. Re-derive every filtered loan's rating using the dominant-factor rule
4. Compute `final_rating_exposure_totals` — group by final_rating, sum loan_count and exposure
5. Compute `migration_from_current_rating_3` — for loans originally rated exactly 3, group by new final_rating
6. Assign watch-list actions to loans with final_rating >= 6 or that breached stress
7. Compute NPA benchmark comparison using branch metrics
8. Identify material downgrades (>=2 notches) from the entire portfolio (not just filtered loans)
9. Select the top problem credit — the loan with the worst final_rating + payment_status combination, using exposure as tiebreaker

### Allocation package

1. Fetch branch detail, applications, sector exposures, and metrics
2. Determine `lending_capacity_q1` from branch detail
3. Rank applications by priority: strong DSCR, strong FICO, long relationship, no delinquency history, complete documentation. Approved + conditionally approved only for priority_ranking
4. For each application, evaluate: capacity, policy floors, sector concentration, credit quality
5. Track remaining capacity after each approval
6. For declined applications, assign reason codes
7. Compute post-approval concentration per sector

### Credit-union segment posture

1. Fetch segment data, NCUA benchmarks, policies
2. Compare state metrics to NCUA benchmark rows for the target state
3. Compute peer comparisons: US row and peer-state medians
4. Determine posture based on external risk status and capacity
5. Set controls from the segment's minimum checklist plus added operating controls
6. Set escalation triggers matching the segment's risk profile
7. Write the controlled interpretation

### Watch-list stress packet

1. Fetch branch loans for adversely rated loans (rating >= adverse_rating_min from template)
2. Score each loan's CDFI factors, classify, assign factor_score
3. Run +200bp DSCR stress on loans with available DSCR
4. Build the workout queue sorted by exposure descending, then loan_id ascending
5. Assign recommended actions based on risk_class, payment_status, and stress breach
6. Compute severe bucket counts: group loans rated 6+ by current_rating and payment_status

### Competing credit decision

1. Fetch branch detail, both target applications, sector exposures, loans, metrics, FDIC benchmark
2. Score both applications using the CRE weighted scoring formula
3. Apply the CRE dual-stress formula to each
4. Compute existing CRE concentration and post-approval concentration for the stronger credit
5. Compare FDIC delinquency benchmark to branch delinquency
6. Select the stronger credit (lower weighted score); decline or defer the weaker one with reason codes
7. Assign conditions for the selected credit

## Answer formatting

- Follow all ordering rules from the template: ascending loan_id, ascending application_id, ascending sector, ascending final_rating, ascending current_rating, ascending action, ascending trigger_id, etc.
- Round numeric fields to the precision specified in the template (currency to 2 decimals, percentages/ratios to 4 decimals, basis points to 2 decimals). Round only in the final output, not in intermediate steps.
- Use exact enum strings from the template — no synonyms or abbreviations.
- Lists must be ordered as specified; use the template's `ordering` field as the definitive sort rule.
- Do not include null loan_ids in loan_id lists; only include loans that actually belong to that group.
- `breaches_threshold` is a boolean (true/false), not a string.
- All required top-level keys must be present even if their value would be empty.

## Validation

A validation script is available at `scripts/validate_answer.py`. Run it against your JSON output to catch structural issues before finalizing:

```bash
python3 skill/scripts/validate_answer.py answer.json input/payloads/answer_template.json
```

This checks required keys, enum values, numeric types, and ordering rules against the template. It does not verify correctness of derived values — only structural compliance.

## Resources

- `references/policy-rules.md` — detailed explanation of every policy rule with worked examples
- `references/api-surface.md` — complete API reference with field descriptions and response shapes
- `scripts/validate_answer.py` — structural answer validator

Read the reference files when you need precise rule application guidance or API field definitions. The policy-rules reference is especially important — it explains the dominant-factor rule, factor scoring, stress formulas, and action assignments in detail.
