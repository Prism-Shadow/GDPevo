---
name: credit-office
description: "Credit committee analysis for a shared credit office REST API. Covers risk-rating regrades, lending-committee allocations, credit-union segment posture reviews, watch-list stress testing, and competing CRE decisions. Use when the task involves any branch-level or segment-level credit analysis against the credit office API — including portfolio rating migration, application scoring, concentration checks, FDIC benchmark comparisons, NCUA peer analysis, CDFI factor scoring, DSCR stress tests, or committee-ready JSON reporting."
---

# Credit Office

## Overview

The credit-office API serves branch loan portfolios, pending applications, sector exposures, branch metrics, FDIC/NCUA benchmarks, credit-union segments, and a single credit policy endpoint. Every task type in this domain follows the same pattern: fetch the policy and relevant branch or segment data, apply policy rules to compute derived values (risk ratings, scores, concentrations, stress results), and produce a committee-ready JSON answer shaped by a provided answer template.

## General Workflow

### 1. Fetch policy and branch/segment data

Always start with two parallel calls:

- `GET /api/policies` — the authoritative rule source for ratings, scoring, stress formulas, and concentration limits.
- `GET /api/branches/{branch_id}` or `GET /api/credit-union-segments/{segment_id}` — the target entity.

Then fetch the supporting data needed for the specific task: loans, applications, sector exposures, metrics, benchmarks. Use the most recent metrics quarter where applicable.

### 2. Apply policy rules

Compute derived values — risk ratings, CDFI factor scores, CRE weighted scores, stressed DSCRs, concentration ratios — using the formulas in the policies response. Read [references/policy.md](references/policy.md) for the complete rule tables and formulas. Read [references/api.md](references/api.md) for endpoint details and field descriptions.

### 3. Produce JSON output

Every task provides an `input/payloads/answer_template.json` that defines the required output shape, field types, enums, precision, and sort order. Follow it exactly. All numbers at precision 2 or 4 as specified; all lists sorted as specified; all string fields drawn from the template's allowed enums. Do not add narrative text outside the JSON.

## Workflow Patterns

### Rating Migration Review

Prompt keywords: "rating migration", "regrade", "risk-rating review", "NPA benchmark"

- Fetch branch loans, metrics, policies, and FDIC benchmarks.
- Filter loans to those with `current_rating >= target_current_rating_min` (stated in prompt or default to 3).
- Re-derive the final rating for each target loan using the dominant factor rule.
- Identify material downgrades (`final_rating - current_rating >= 2`).
- Assign watch-list actions by final_rating band.
- Compute NPA benchmark variance against the relevant FDIC metric.
- Identify the top problem credit (highest exposure among worst-rated loans).

### Lending Committee Allocation

Prompt keywords: "allocation package", "lending committee", "pending applications"

- Fetch branch applications, metrics, sector exposures, and policies.
- Score applications with policy flags; decline any with automatic decline criteria.
- Rank surviving applications by priority (consider DSCR, relationship strength, FICO, years in business).
- Allocate capacity in priority order, checking sector concentration before each approval.
- For concentration breaches, either apply mitigation (`participation_required`) or decline with `sector_breach`.
- Record decline reason codes per the template enums.
- Compute post-approval sector concentrations.

### Credit Union Segment Posture

Prompt keywords: "credit-union segment", "posture page", "NCUA", "segment_id"

- Fetch the segment, NCUA benchmarks, policies, and the branch record for the CU.
- Extract NC, US, and peer state rows from the NCUA benchmark table.
- Compute peer median for each metric.
- Compare NC vs US and NC vs peer median directionally.
- Recommend posture based on capacity and external risk signals.
- Populate controls, checklist gates, escalation triggers using the segment's `minimum_checklist` and `internal_context`.

### Watch-List Stress and Workout

Prompt keywords: "watch-list stress", "adverse-rated", "workout", "CDFI risk class"

- Fetch branch loans (filter to `current_rating >= 6`), policies, and metrics.
- Compute CDFI factor score and risk class for each adverse loan.
- For loans with DSCR available, compute +200bp stressed DSCR.
- Flag loans that breach the 1.00 threshold after stress.
- Build workout queue sorted by descending exposure.
- Count severe buckets: group by `current_rating` and `payment_status`.

### Competing CRE Decision

Prompt keywords: "competing", "CRE", "two applications", "weighted score"

- Fetch branch applications (filter to the two specified), loans, sector exposures, metrics, policy, and FDIC benchmarks.
- Compute the weighted 5-Cs score for each CRE application.
- Run dual-stress on both applications.
- Evaluate CRE concentration: existing CRE exposure plus each candidate's requested amount against `cre_policy_limit_pct`.
- Compare branch delinquency to the relevant FDIC benchmark.
- Select the stronger credit; give the unselected a disposition with reason codes.

## Computation Rules

All computation rules live in the policies API response. Read [references/policy.md](references/policy.md) for the full reference including:

- Risk rating derivation (dominant factor rule with DSCR/LTV/delinquency tables)
- CDFI factor scoring (FICO, LTV, liquidity_months, debt_to_asset)
- CRE weighted 5-Cs scoring with component weights
- Stress formulas (+200bp watch-list and CRE dual-stress)
- Capacity and concentration rules

Do not hardcode policy values from train examples; always fetch the live `/api/policies` response and use its values.

## Output Precision and Sort Order

Read the answer template carefully:

- Dollar amounts: round to 2 decimal places.
- Ratio/percentage values: round to 4 decimal places (if specified) or 2 decimal places.
- Integer values (loan counts, ratings, scores): use integers.
- Lists: sort as the template specifies (typically ascending by id, rating, or sector).
- Enum values: use only the allowed values listed in the template for each field.
- Include all required keys even when empty (empty lists as `[]`, zero values as `0` or `0.0`).

## Key Policies Endpoint Fields

Always read the live `/api/policies` response, but these are the stable top-level keys to expect:

- `risk_rating` — DSCR thresholds, LTV thresholds, delinquency minimums, dominant factor rule, material downgrade notch count
- `cdfi_factor_scores` — factor tables and risk class mapping
- `cre_weighted_score` — component weights and score class ranges
- `stress` — formulas, breach thresholds
- `capacity_concentration` — capacity field names, allowed mitigations

## Branch Data Sources

For a branch task, the data you typically need:

| Data | Endpoint |
|------|----------|
| Branch info | `GET /api/branches/{branch_id}` |
| Loan portfolio | `GET /api/branches/{branch_id}/loans` |
| Applications | `GET /api/branches/{branch_id}/applications` |
| Sector exposures | `GET /api/branches/{branch_id}/sector-exposures` |
| Metrics | `GET /api/branches/{branch_id}/metrics` |
| Policy | `GET /api/policies` |
| FDIC benchmarks | `GET /api/benchmarks/fdic/q4-2024` |
| NCUA benchmarks | `GET /api/benchmarks/ncua/q1-2025` |

For a segment task, start with `GET /api/credit-union-segments/{segment_id}` plus the NCUA benchmark endpoint and the branch record for the related CU (use the branch list to find it).

## Common Pitfalls

- **Don't skip the policy call.** Every computation depends on values from `/api/policies`. Fetch it first.
- **Factor availability.** DSCR, LTV, FICO, liquidity_months, debt_to_asset can all be null. When null, omit that factor from rating derivation and substitute score 0 for scoring.
- **Capacity arithmetic.** `committed_capacity_amount` differs from `approved_amount` only for `participation_required` approvals, where committed = `approved_amount * (1 - sba_guaranty_pct)`. Otherwise they are equal.
- **Quarter selection.** Always use the most recent quarter from branch metrics (e.g., `2025Q1` over `2024Q4`).
- **Concentration post-approval.** Compute against the *new* total loans outstanding, which is `existing_total_loans + sum(approved_amounts)`.
- **Grandfathering.** A sector with `grandfathered == 1` means its existing over-limit exposure is tolerated, but you cannot approve more in that sector without mitigation.
- **Template precision.** Check the template's numeric_precision or precision fields. Dollar amounts are always rounded to 2 decimals. Ratios are rounded as specified (usually 4 decimals for pct fields).
