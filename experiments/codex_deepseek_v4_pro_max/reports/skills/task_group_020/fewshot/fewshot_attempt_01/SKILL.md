---
name: ma-deal-workbench
description: Navigate and analyze M&A deal records using the Deal Workbench REST API. This skill handles seller- and buyer-side SPA/APA document review, issue registers, economics packages, committee escalation memos, transition reviews, and deviation matrices. Use this skill when a prompt references a deal workbench endpoint at <TASK_ENV_BASE_URL>, deal IDs in `PRJ_XXXX` format, or asks for structured M&A deal analysis.
---

# M&A Deal Workbench Skill

## Overview

This skill covers structured analysis of M&A deal records from an HTTP-based deal workbench.
It supports seller-side asset purchase agreement (APA) review, buyer-side stock purchase agreement (SPA) closing and economics packages, M&A Committee escalation packages, carveout transition reviews, and SPA deviation matrices.

## Environment

The workbench is reachable at the base URL provided as `<TASK_ENV_BASE_URL>` in the prompt. All API calls use that base.
Unless the prompt overrides it, read-only SQL access uses `POST /api/query` with the JSON body `{"token":"deal-workbench-readonly","sql":"<string SELECT or WITH query>"}`.

## API Discovery and Navigation

### Core entity endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/deals` | List all deal records |
| `GET /api/deals/<deal_id>` | Single deal detail (project name, value, side, dates) |
| `GET /api/deals/<deal_id>/terms` | Current draft terms on the deal |
| `GET /api/deals/<deal_id>/benchmarks` | Market benchmarks tied to the deal |
| `GET /api/deals/<deal_id>/risk-estimates` | Risk-estimate records for the deal |
| `GET /api/deals/<deal_id>/notes` | Negotiation or analyst notes |
| `GET /api/deals/<deal_id>/documents` | Deal document metadata |
| `GET /api/deals/<deal_id>/cap-table` | Capitalization table (SPA / stock deals) |
| `GET /api/deals/<deal_id>/consents` | Third-party consents |
| `GET /api/deals/<deal_id>/employees` | Employee records |
| `GET /api/deals/<deal_id>/material-contracts` | Material contracts |
| `GET /api/deals/<deal_id>/regulatory` | Regulatory filings and status |
| `GET /api/deals/<deal_id>/diligence-findings` | Diligence findings |

### Playbook and policy endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/playbooks` | List available playbooks |
| `GET /api/playbooks/<playbook_id>/rules` | Rules for a specific playbook (e.g., `PB_SELLER_A`, `PB_BUYER_A`) |
| `GET /api/policies` | List committee policies |
| `GET /api/policies/<policy_id>/thresholds` | Policy thresholds (for committee escalation tasks) |

### Read-only SQL

Use `POST /api/query` with `Content-Type: application/json` and body `{"token":"deal-workbench-readonly","sql":"<query>"}` for cross-table joins, aggregations, and checks that individual endpoints cannot answer. Only `SELECT` and `WITH` (CTE) queries are permitted. Prefer the entity endpoints when they suffice; use SQL when you need to join across entity types or verify relationships.

### Discovery strategy

1. Always start with `GET /api/deals/<deal_id>` to confirm the deal identity, value, and status.
2. Pull the applicable playbook rules with `GET /api/playbooks/<playbook_id>/rules` (the prompt tells you which playbook to use based on your role - seller or buyer).
3. If committee policies apply, pull `GET /api/policies/<policy_id>/thresholds`.
4. Pull terms with `GET /api/deals/<deal_id>/terms`.
5. Collect supporting records - consents, employees, regulatory, material contracts, benchmarks, risk estimates, diligence findings, documents, notes - based on what the task asks.
6. Use SQL for cross-validation when endpoint data seems incomplete or when you need to join values across tables.

## Data Model Conventions

### Stable Identifiers

Every entity type uses a stable, predictable identifier format. Always use these IDs verbatim from the workbench - never invent them:
- **Deal**: `PRJ_XXXX` (e.g., `PRJ_JUNIPER`)
- **Term**: `TERM_PRJ_XXXX_NN` (e.g., `TERM_PRJ_JUNIPER_01`)
- **Consent**: `CNS_PRJ_XXXX_NN` (e.g., `CNS_PRJ_MERIDIAN_01`)
- **Employee**: `EMP_PRJ_XXXX_NN` (e.g., `EMP_PRJ_MERIDIAN_01`)
- **Material contract**: `MAT_PRJ_XXXX_NN` (e.g., `MAT_PRJ_ORION_01`)
- **Regulatory**: `REG_PRJ_XXXX` or `REG_PRJ_XXXX_HSR`
- **Finding**: `FND_PRJ_XXXX_NN` (e.g., `FND_PRJ_MERIDIAN_03`)
- **Risk estimate**: `RSK_PRJ_XXXX_NN` (e.g., `RSK_PRJ_LYRA_01`)
- **Document**: `DOC_PRJ_XXXX_NN` (e.g., `DOC_PRJ_ORION_01`)
- **Policy**: `POL_MA_YYYY_X` (e.g., `POL_MA_2025_A`)
- **Playbook**: `PB_SELLER_A`, `PB_BUYER_A`, etc.

### Purchase Price Hierarchy

When calculating dollar amounts, use this hierarchy:
1. If the deal record or terms specify an explicit purchase price for the calculation (e.g., "upfront cash", "equity value"), use that basis.
2. Otherwise, use the headline purchase price from the deal record as the default basis for percentages.
3. If a risk estimate or benchmark gives a different basis, note it in the output but prioritize explicit deal-level numbers.

Percentages (indemnity cap, escrow, reverse break fee, etc.) are expressed in whole percentage points (e.g., `10.0` means 10%, `5.5` means 5.5%).

### Output Formatting Rules

Unless the answer template specifies otherwise:
- **Currency**: integer USD (no cents, no commas, no `$` sign).
- **Percent values**: decimal numbers in whole percentage points. Round to the precision specified in the template (e.g., two decimal places for percent points, one decimal place, or four decimals for holder percentages).
- **Months**: integer months.
- **Dates**: `YYYY-MM-DD` format when dates are requested.
- **Booleans**: strictly `true` or `false` (JSON boolean, not string).
- **Nulls**: use JSON `null` when a field is not applicable or data is absent; do not use the string `"null"` or zero as a placeholder for missing data.

### Enum Values

Always use the exact enum values defined in the answer template. Common enums include:
- **Risk rating**: `LOW`, `MEDIUM`, `HIGH`
- **Recommended action**: `delete`, `revise`, `add`, `accept`, `escalate`, `approve`, `approve_with_conditions`, `reject`
- **Issue status**: `in_policy`, `out_of_policy`, `missing_required_term`, `draft_exceeds_playbook`, `draft_below_playbook`

Do not introduce enum values that are not listed in the template.

## Analysis Workflows

### Workflow 1: Issue Register (Seller APA Review)

**When to use**: The prompt asks you to act as seller-side counsel reviewing a buyer's APA draft and producing an issue register.

**Method**:
1. Pull the deal record, draft terms, and the seller playbook rules.
2. For each term in the draft, compare it against the corresponding playbook rule:
   - If the draft term exceeds the playbook preferred or fallback value, classify as `draft_exceeds_playbook`.
   - If the draft term is below the playbook value, classify as `draft_below_playbook`.
   - If a seller-protective term the playbook requires is completely absent, classify as `missing_required_term`.
   - If it matches the playbook, classify as `in_policy`.
3. For each issue, determine the `business_outcome` (closing_certainty, escrow_economics, indemnity_exposure, etc.) based on what the term governs.
4. Assign a `risk_rating` based on the size of the delta and the strategic importance.
5. Set the `recommended_action`:
   - `delete` for terms that are entirely buyer-protective with no seller benefit (e.g., financing condition).
   - `revise` for existing terms that need numeric or structural changes.
   - `add` for missing required terms.
   - `accept` for terms that are within playbook tolerances.
   - `escalate` for committee-level decisions.
6. Fill dollar amounts: for percent-based terms, multiply the percentage by the headline purchase price. For employee-related terms, sum PTO liability from employee records.
7. Build the `priority_order` array: most consequential issues first (HIGH risk, large dollar delta) to least.
8. Build `summary_metrics`: count issues by risk, sum quantified exposures, sum employee counts and PTO liabilities.

**Key calculations**:
- `draft_amount_dollars` = draft_percent × headline_value / 100
- `preferred_amount_dollars` = preferred_percent × headline_value / 100
- `fallback_amount_dollars` = fallback_percent × headline_value / 100
- `delta_to_fallback_dollars` = draft_amount_dollars − fallback_amount_dollars

### Workflow 2: Closing and Economics Package (Buyer SPA)

**When to use**: The prompt asks for a buyer-side SPA closing and economics package covering economics, indemnity, escrow, closing conditions, covenants, regulatory, and closing readiness.

**Method**:
1. Pull the deal record, terms, cap table, consents, employees, material contracts, regulatory, diligence findings, and the buyer playbook rules.
2. **Economics**: Extract headline value, upfront cash, stock value, and milestone value from the deal record. Use the cap table to allocate consideration to each holder group. Calculate each holder's share as `(fully_diluted_pct × total_value)` for cash and stock portions.
3. **Indemnity package**: Compare draft cap percent, survival months, and materiality scrape against the buyer playbook preferred and fallback positions. Classify the risk.
4. **Escrow**: Determine the required escrow amount (usually as a percent of purchase price), release timeline, and trigger. Classify status as `required_buyer_fallback` when the draft lacks escrow and the buyer playbook requires it at fallback.
5. **NWC adjustment**: Check diligence findings for working-capital issues. If a finding identifies NWC risk, propose a dollar-for-dollar adjustment with a collar amount.
6. **Closing conditions**: Review each consent and material contract. Classify each as `closing_condition` if it blocks closing, `notice_only` if it is informational, or `post_closing_covenant` if it can be addressed after close.
7. **Employment covenants**: Count continuing employees, identify service-credit employees, total PTO liability, flag WARN-risk employees.
8. **Restrictive covenants**: If the buyer playbook requires non-compete/non-solicit and terms are missing, flag as required.
9. **D&O tail and expenses**: Check for D&O tail requirements, allocate costs per the playbook.
10. **Regulatory**: Determine HSR applicability based on transaction size. Flag if a closing condition is needed.
11. **Closing readiness**: Synthesize all blockers. Set overall status to `NOT_READY` if any HIGH-risk blocker exists without an agreed resolution.

**Key calculations for holder allocation**:
- `cash_amount` = `fully_diluted_pct × upfront_cash` (rounded to integer)
- `stock_amount` = `fully_diluted_pct × stock_value` (rounded to integer)
- `total_consideration` = `cash_amount + stock_amount`

### Workflow 3: Committee Escalation Package

**When to use**: The prompt asks for an M&A Committee escalation package comparing draft terms against committee policy thresholds.

**Method**:
1. Pull the deal record, terms, the applicable committee policy thresholds, benchmarks, risk estimates, and deal notes.
2. **Filtering rule**: Only escalate terms that are `out_of_policy`. Exclude terms that are within policy thresholds, stale, or non-committee matters (the template provides `excluded_in_policy_terms` and `excluded_in_policy_categories` for this).
3. For each escalated term:
   - Map the draft value to `draft_metric` (value, unit, basis).
   - Map the policy threshold to `policy_metric` (threshold_value, unit, basis).
   - Compute the `delta` (difference between draft and policy threshold).
   - Pull benchmark data where available (sample size, median, upper quartile) and classify the draft's position (`at_or_below_median`, `above_upper_quartile`, etc.).
   - Pull exposure estimates from risk-estimate records. Classify the exposure type (`closing_certainty`, `indemnity_leakage`, `not_quantified`).
   - Recommend `approve`, `approve_with_conditions`, or `reject` based on severity.
   - List `required_conditions` that would bring the term into compliance.
4. **Aggregate summary**: Count escalated terms, tally risk counts, sum quantified exposures (low and high), compute RTF excess. Set `overall_recommendation` to the most restrictive among the escalated terms. Write a `committee_action` string summarizing the key asks. Set `negotiation_priority` in descending order of importance.

### Workflow 4: Carveout APA Transition Review

**When to use**: The prompt asks for a transition review of a carveout asset purchase agreement, focusing on separation and transition terms.

**Method**:
1. Pull the deal record, terms, consents, employees, material contracts, regulatory, documents, and the seller playbook.
2. Check for eight standard transition issues:
   - **IP/Domain Transition**: Whether transitional trademark license and domain redirect provisions exist. If missing, flag as `missing_required_term`.
   - **Employee Continuity & PTO**: Whether the buyer is allowed to cherry-pick employees, whether service credit is required, whether accrued PTO is allocated. Check employee records for field/operations staff.
   - **TSA Scope, Duration & Fees**: Whether transition services are scoped, the duration, and the fee model. Compare duration against playbook preferences.
   - **Customer Consent Termination Right**: Whether the buyer can terminate if key customer consents are missing. Check consent records to identify which are required closing consents vs. notice-only.
   - **Outside Date Extension**: Whether an outside date and seller regulatory extension exist (critical when HSR is required).
   - **Section 1060 Allocation**: Whether purchase-price allocation under Section 1060 is addressed.
   - **Transfer Tax Split**: Whether transfer taxes are allocated between buyer and seller.
   - **Governing Law/Forum**: Whether Delaware governing law and forum are specified.
3. For each issue, populate:
   - `draft_value_normalized`: what the current draft says (or empty/null values if missing).
   - `required_position_normalized`: what the seller playbook requires.
   - `quantified_impact_dollars`: the dollar exposure from the gap (from risk estimates, consent amounts, PTO liability, etc.).
4. Produce `required_redlines` for each issue - these are the specific clause changes needed. Match each redline to its `related_issue_id`.
5. Build `operational_risk`: overall risk rating, posture, priority order, quantified exposures (stranded cost gap, PTO liability, consent amounts at risk, customer revenue at risk, transition disruption high estimate).

### Workflow 5: SPA Deviation Matrix (Buyer)

**When to use**: The prompt asks for a buyer-side SPA deviation matrix covering key positions on indemnity, escrow, survival, consents, HSR, and material contracts.

**Method**:
1. Pull the deal record, terms, buyer playbook, consents, material contracts, regulatory, diligence findings, documents, benchmarks, risk estimates, and notes.
2. Evaluate seven standard issues:
   - **indemnity_cap_and_basket**: Compare draft cap percent against buyer preferred/fallback. Check for basket (deductible) presence.
   - **survival_and_knowledge**: Compare draft survival period against buyer playbook. Check for knowledge qualifiers.
   - **materiality_scrape**: Whether a materiality scrape (double materiality) clause exists and matches the buyer playbook.
   - **escrow_holdback_release**: Whether an escrow or holdback is in the draft, its amount, agent designation, and release mechanism.
   - **consent_closing_condition**: Whether all material consents are required as closing conditions.
   - **hsr_condition**: Whether HSR clearance is a closing condition.
   - **material_contracts**: Whether key material contracts require consent as closing conditions.
3. For each issue, assign:
   - `status`: based on comparison with buyer playbook.
   - `final_position`: one of the predefined position codes from the template.
   - `priority_rank`: 1 = most critical, 7 = least critical.
   - Dollar amounts calculated from the headline purchase price.
4. Build `closing_blockers`: each consent, regulatory clearance, or material contract that must be satisfied before closing. Include `amount_at_risk_usd` where the consent amount is known, and `annual_revenue_usd` for material contracts.
5. Build `risk_totals`: sum up all the counts, amounts, and exposures.

## Common Calculations

### Dollar from Percentage
```
amount = round(percent × headline_purchase_price / 100)
```
Always round to the nearest integer dollar after multiplication.

### Delta Calculation
```
delta_to_fallback_dollars = draft_amount − fallback_amount
shortfall_to_fallback_usd = fallback_amount − draft_amount  (when draft is below fallback)
shortfall_to_preferred_usd = preferred_amount − draft_amount  (when draft is below preferred)
```

### PTO Liability
Sum the PTO liability field across all affected employee records from the employees endpoint.

### Consent Amount at Risk
Sum the `amount` or `amount_at_risk` field across consents classified as `closing_condition`.

### Material Contract Revenue
Sum the `annual_revenue` field across material contracts requiring consent as closing conditions.

### Exposure Modeling
For risk totals:
- `total_modeled_exposure_low_usd` = sum of low-end exposure estimates across all quantified risk categories.
- `total_modeled_exposure_high_usd` = sum of high-end exposure estimates.
- Prefer risk-estimate records (`RSK_*`) for exposure values; fall back to delta calculations when risk estimates are unavailable.

## Cross-Validation with SQL

When endpoint data appears inconsistent or when you need to validate relationships:

```bash
curl -sS -X POST "<TASK_ENV_BASE_URL>/api/query" \
  -H "Content-Type: application/json" \
  -d '{"token":"deal-workbench-readonly","sql":"SELECT ..."}'
```

Useful SQL patterns:
- `SELECT * FROM deals WHERE deal_id = '...'` to verify deal identity.
- `SELECT * FROM terms WHERE deal_id = '...'` to cross-check term data.
- `SELECT * FROM consents WHERE deal_id = '...' ORDER BY consent_id` to verify consent completeness.
- Join queries when you need to verify that entity references (e.g., term ↔ contract, consent ↔ contract) are consistent.

## Output Discipline

1. **Read the answer template first**. Every task provides `input/payloads/answer_template.json` that defines the exact output shape, enum values, and field types.
2. **Match the template exactly**. Do not add extra top-level keys. Do not omit required fields. Use `null` for fields where the template allows it and you have no data.
3. **Use stable IDs from the workbench**. Never fabricate IDs. If a record has ID `CNS_PRJ_MERIDIAN_01`, use that string verbatim.
4. **Produce only JSON**. Unless the prompt explicitly says otherwise, the output must be a single valid JSON object with no explanatory prose before, after, or around it.
5. **Sort arrays as directed**. If the template says to sort by `issue_id` ascending, do so. If it says to sort by `priority_order` descending, do so.
6. **Preserve nulls correctly**. A missing numeric value is `null`, not `0`. A missing string is `null`, not `""`. A missing array is `null` or `[]` as the template dictates.

## Quality Checklist

Before finalizing, verify:
- [ ] All record IDs match what the workbench returned (no fabricated IDs).
- [ ] Dollar amounts are integers (no decimal places, no `$`).
- [ ] Percentages are in the correct format (whole percentage points rounded to the template's decimal precision).
- [ ] Months are integers.
- [ ] All enum values match the allowed values in the template.
- [ ] Required top-level fields are present.
- [ ] Arrays are sorted as specified.
- [ ] `null` is used for absent data, not zero or empty string (unless the template explicitly uses zero/empty as a sentinel).
- [ ] The output is valid JSON (no trailing commas, no comments, no prose).
- [ ] Cross-validated key numbers (sum of holder considerations ≈ total value, PTO sum from employee records matches the total, etc.).
