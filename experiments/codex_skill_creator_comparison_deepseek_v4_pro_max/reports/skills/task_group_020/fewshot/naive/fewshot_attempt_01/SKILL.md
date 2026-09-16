---
name: deal-workbench-solver
description: Solve structured M&A deal review tasks using the deal workbench API. Use for seller-side issue registers, buyer-side closing packages, committee escalation memos, transition/carveout reviews, and SPA deviation matrices. Covers playbook comparison, policy threshold checking, dollar-amount computation, priority ranking, redline drafting, and closing-readiness assessment.
---

# Deal Workbench Solver

Reusable guidance for solving structured M&A deal review tasks against the deal workbench API. Use this skill when the task involves: gathering deal records from the API, comparing draft terms against playbook rules or policy thresholds, computing quantified financial positions, ranking issues by priority, and returning structured JSON output.

## Workbench API

All endpoints live under the base URL provided in the task prompt (e.g. `http://task-env:9020`). Call `GET` for reads and `POST /api/query` with the read-only token for cross-table SQL.

### Core record endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /api/deals/<deal_id>` | Deal overview, headline value, parties, signing date |
| `GET /api/deals/<deal_id>/terms` | Current draft terms with stable `term_id` values |
| `GET /api/deals/<deal_id>/consents` | Required consents, counterparties, condition types |
| `GET /api/deals/<deal_id>/employees` | Employee records, PTO liabilities, service credit needs |
| `GET /api/deals/<deal_id>/regulatory` | HSR status, regulatory clearance requirements |
| `GET /api/deals/<deal_id>/risk-estimates` | Quantified risk ranges (low/high) per risk ID |
| `GET /api/deals/<deal_id>/benchmarks` | Market benchmarks for term values |
| `GET /api/deals/<deal_id>/cap-table` | Holder-level ownership, security classes, share counts |
| `GET /api/deals/<deal_id>/material-contracts` | Material contracts, counterparties, revenue |
| `GET /api/deals/<deal_id>/diligence-findings` | Findings from diligence review |
| `GET /api/deals/<deal_id>/documents` | Draft documents, missing-term gaps |
| `GET /api/deals/<deal_id>/notes` | Negotiation notes |

### Playbook and policy endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /api/playbooks` | List available playbooks |
| `GET /api/playbooks/<playbook_id>/rules` | Preferred, fallback, and minimum positions per term |
| `GET /api/policies` | List committee policies |
| `GET /api/policies/<policy_id>/thresholds` | Approval thresholds, allowed/enum values |

### Search and SQL

| Endpoint | Use |
|----------|-----|
| `GET /api/search` | Find records by keyword or filter |
| `POST /api/query` | Read-only SQL; use token `deal-workbench-readonly` in the request body |

### Gathering strategy

Always start by fetching the deal record to get the headline purchase price, then fetch terms, the applicable playbook/policy, and every supporting record referenced in the task prompt. Fetch records in parallel when they are independent of each other. If an endpoint returns an empty array, treat it as authoritative absence (e.g., no draft term means the provision is missing).

## Data conventions

- **Currency:** integer USD. Round to the nearest dollar after computation.
- **Percent points:** decimal number. Use two decimal places unless the answer template specifies one.
- **Months:** integer months.
- **Holder percentages:** four decimal places for fully-diluted cap-table percentages when the template calls for that precision.
- **Dates:** `YYYY-MM-DD` format.
- **Source IDs:** always use stable IDs exactly as returned by the API (`TERM_PRJ_*`, `CNS_PRJ_*`, `MAT_PRJ_*`, `EMP_PRJ_*`, `REG_*`, `RSK_PRJ_*`, `FND_PRJ_*`, `DOC_PRJ_*`). Do not invent or reformat IDs.

## Dollar-amount computation

Base all dollar calculations on the deal's **headline purchase price** (equity value) unless a specific record explicitly states a different basis. The headline value comes from the deal record's `headline_value` or `purchase_price` field.

```
draft_amount_dollars    = draft_percent    * headline_value
preferred_amount_dollars = preferred_percent * headline_value
fallback_amount_dollars  = fallback_percent  * headline_value
delta_to_fallback_dollars = draft_amount_dollars - fallback_amount_dollars
```

Shortfall / exposure calculations:
- `shortfall_dollars` is the gap from the current draft to the required position.
- Exposure ranges (`low`/`high`) come from risk-estimate records; sum across relevant estimates.
- When a term is entirely missing and must be added, the shortfall equals the full required amount.

## Issue identification rules

Compare every draft term against the applicable playbook or policy. Also check for **missing required terms**: a term absent from the draft that the playbook or deal context shows is needed.

### status values

| Status | When to use |
|--------|-------------|
| `in_policy` | Draft matches or is within playbook/policy bounds |
| `out_of_policy` | Draft violates a policy threshold |
| `draft_exceeds_playbook` | Draft is more favorable to counterparty than the seller/buyer fallback (e.g., cap too low for buyer, escrow too high for seller) |
| `draft_below_playbook` | Draft is less favorable to the client than the fallback (e.g., cap too low for buyer, fee too low for seller) |
| `missing_required_term` | Term is absent from the draft but the playbook, policy, or deal data shows it is needed |

### playbook comparison direction

The direction of "exceeds" vs "below" depends on the client side:
- **Seller-side:** higher escrow, higher indemnity cap, longer survival, broader covenants all favor the buyer and are `draft_exceeds_playbook` from the seller's perspective.
- **Buyer-side:** lower indemnity cap, lower escrow, shorter survival, missing consents favor the seller and are `draft_below_playbook` from the buyer's perspective.

### filtering for escalation/committee tasks

When the task asks for a committee escalation package (like train_003), only include terms that are **out of policy** or **restricted for committee approval**. Exclude terms that are:
- In-policy or within thresholds
- Stale, resolved, or previously approved
- Not subject to committee review (distractors)

The answer must explicitly list excluded in-policy terms and excluded categories in the aggregate summary.

## Priority ranking

Rank issues from highest to lowest negotiation priority. Apply these heuristics in order:

1. **Closing certainty** issues first (financing conditions, reverse break fees, HSR, closing consents) -- these determine whether the deal closes at all.
2. **High-risk** issues before medium-risk before low-risk.
3. **Largest dollar exposure** within the same risk tier.
4. **Operational continuity** (employee transition, TSA, IP transition) after pure economic terms.
5. **Legal boilerplate** (governing law, forum, tax allocation) last unless they carry quantified risk.

## Playbook and policy traversal

### Playbook rules

Each playbook rule defines three tiers where available:
- **preferred:** the client's ideal position
- **fallback:** the minimum acceptable position
- **minimum / hard floor:** must not be crossed

Use the preferred value to compute `preferred_amount_dollars` and the fallback to compute `fallback_amount_dollars` and `delta_to_fallback_dollars`. When only one value is present, treat it as the fallback and leave preferred as null.

### Policy thresholds

Policy thresholds (from `/api/policies/<policy_id>/thresholds`) define numeric or enum limits. A term is `out_of_policy` when its draft value exceeds a threshold. Compute the delta between draft and threshold for escalation reports.

### Benchmark integration

When benchmarks are available (from `/api/deals/<deal_id>/benchmarks`), compare the draft value to the benchmark distribution to determine market position:
- `at_or_below_median`: draft <= median
- `between_median_and_upper_quartile`: median < draft <= upper_quartile
- `at_upper_quartile`: draft == upper_quartile
- `above_upper_quartile`: draft > upper_quartile

## Redline specifications

Some tasks require redline instructions alongside issue analysis. Each redline maps to a related issue and specifies:
- **redline_action:** `add` (for missing terms), `revise` (for out-of-policy terms), `delete` (for provisions that must be removed)
- **must_have_terms:** a structured object with the concrete provisions the redline must include (specific IDs, dollar amounts, durations, enums)

Redlines should be consistent with the issue's `required_position_code` or `recommended_action`.

## Closing readiness

Assess closing readiness by checking:
- Whether all **required closing consents** are obtained or conditioned
- Whether **HSR or other regulatory clearance** is obtained or conditioned
- Whether **material contract consents** are addressed
- Whether **indemnity, escrow, and survival** terms are agreed
- Whether **employee and operational transition** terms are resolved

Classify blockers:
- `required_consent`: consent not yet obtained that is a closing condition
- `regulatory_clearance`: HSR or other regulatory approval not yet obtained
- `material_contract_consent`: material contract change-of-control consent not conditioned

Overall status: `READY` (no blockers), `READY_WITH_CONDITIONS` (blockers have clear resolution paths), `NOT_READY` (at least one blocker without a clear path).

## Summary metrics

Always compute aggregate metrics when the template requires them:
- **issue_count:** total issues in the register
- **high/medium/low risk counts**
- **headline_value_dollars:** from the deal record
- **total_quantified_exposure:** sum exposure low/high across all issues that have quantified exposure
- **total_negotiation_delta_dollars:** sum of `delta_to_fallback_dollars` across all issues
- **required_closing_consent_count:** count of consents marked as closing conditions
- **total_employee_count / total_pto_liability_dollars:** sum from employee records

## Output rules

1. Return **only valid JSON** conforming to the answer template in the task payloads. No narrative, no markdown, no explanatory prose outside the JSON object.
2. Use the **exact enum values** from the template. Do not invent new enum members.
3. Every issue object must include every field defined in the template, using `null` for fields that do not apply.
4. Sort issues and redlines as specified by the template (usually by `issue_id` ascending or by `priority_rank`).
5. Ensure `priority_order` arrays contain all issue IDs with no duplicates and no omissions.
6. All IDs must be stable values from API responses -- never hard-code an ID that does not appear in the responses.

## Common task types

### Seller-side issue register

Compare buyer-drafted APA terms against the seller playbook. For each term in the playbook: check whether a corresponding draft term exists, whether its value is within acceptable bounds, and flag it with the appropriate status. Include employee continuity, TSA, IP transition, and tax allocation even when absent from the draft. Compute all dollar amounts from the headline price.

### Buyer-side closing and economics package

Compute holder-level consideration from the cap table. Compare draft indemnity, escrow, survival, and NWC terms against the buyer playbook. Assess consent and regulatory closing conditions. Classify blockers and tradeable issues. Include employment covenant assessment and D&O tail.

### Committee escalation memo

Filter terms against committee policy thresholds. Only escalate out-of-policy terms. Provide benchmark position, quantified exposure, delta to threshold, and specific required conditions for each escalated term. Explicitly list excluded in-policy terms and categories.

### Transition / carveout review

Focus on separation terms: TSA scope/duration/fees, IP and domain transition, employee transfer and PTO, tax allocation (Section 1060), transfer tax, governing law, and outside date. Each issue maps to a corresponding redline with must-have terms.

### SPA deviation matrix

Compare each buyer position area against the draft and playbook. Classify status, set final positions from the template enums, rank by priority, and compute shortfall amounts. Map closing blockers to specific consent, regulatory, and contract IDs with amounts at risk.

## Anti-patterns to avoid

- **Do not** hard-code values from training examples. All values must come from the live API responses.
- **Do not** include narrative text outside the JSON object.
- **Do not** invent source IDs -- use only IDs returned by the API.
- **Do not** apply the wrong playbook or policy -- read the task prompt to determine which playbook/policy ID to use.
- **Do not** treat a missing term as acceptable when the playbook requires it. Missing required terms are issues.
- **Do not** include in-policy terms in escalation or deviation reports.
- **Do not** compute dollar amounts from any basis other than the headline purchase price unless a specific record explicitly provides a different basis.
- **Do not** skip parallel API calls -- fetch independent endpoints concurrently.
