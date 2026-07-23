# M&A Deal Workbench — Structured Analysis Skill

## When to use

Invoke this skill whenever the task involves analyzing M&A deal terms using the deal workbench API — producing issue registers, economics packages, escalation memos, transition reviews, deviation matrices, or any structured JSON output that compares draft deal terms against playbook rules, policy thresholds, benchmarks, or market standards.

## Environment

The deal workbench runs at a base URL provided as `<TASK_ENV_BASE_URL>`. All API routes are relative to this base. Read `environment_access.md` (in the task root) for the actual base URL and credentials — do not guess them.

- **Read-only SQL token**: `deal-workbench-readonly` — use with `POST /api/query` for cross-table or aggregate checks when the standard endpoints are insufficient.
- **Web UI**: The workbench also serves a browsable interface at the base URL. Use it for discovery when API responses are ambiguous.

## Available API endpoints

All GET unless noted. Endpoint catalog is also in `api_reference.md` (this skill's supporting file).

| Route | Returns |
|---|---|
| `/workspace` | High-level workspace overview |
| `/api/deals` | List of all deals |
| `/api/deals/<deal_id>` | Deal record (headline price, parties, deal type, status) |
| `/api/deals/<deal_id>/terms` | Current draft terms with stable term IDs |
| `/api/deals/<deal_id>/benchmarks` | Market benchmarks for term comparison |
| `/api/deals/<deal_id>/risk-estimates` | Quantified risk estimates with stable estimate IDs |
| `/api/deals/<deal_id>/consents` | Required third-party consents with counterparty and amount-at-risk |
| `/api/deals/<deal_id>/employees` | Employee roster with service credit, PTO liability, WARN risk |
| `/api/deals/<deal_id>/material-contracts` | Material contracts with annual revenue and consent requirements |
| `/api/deals/<deal_id>/regulatory` | HSR thresholds, filing requirements, regulatory approvals |
| `/api/deals/<deal_id>/cap-table` | Capitalization table — holders, security classes, fully-diluted percentages |
| `/api/deals/<deal_id>/diligence-findings` | Due diligence findings with stable finding IDs and quantified impact |
| `/api/deals/<deal_id>/notes` | Negotiation notes and counsel commentary |
| `/api/deals/<deal_id>/documents` | Deal documents and exhibits |
| `/api/playbooks` | List of available playbooks |
| `/api/playbooks/<playbook_id>/rules` | Playbook rules with preferred and fallback positions |
| `/api/policies` | List of committee/board policies |
| `/api/policies/<policy_id>/thresholds` | Policy thresholds for escalation triggers |
| `/api/search` | Search across deals and records |
| `POST /api/query` | Read-only SQL; send `{"token": "<token>", "query": "<sql>"}` |

## Core operating rules

### 1. Identify your role and the deal

Every task specifies:
- **Client side**: `seller-side`, `buyer-side`, or neutral counsel.
- **Deal ID**: A stable code like `PRJ_XXXXXX` used in all API routes.
- **Deal type**: APA (asset purchase), SPA (stock purchase), or carveout APA — determines which terms and mechanics are in play.

Read the deal record (`GET /api/deals/<deal_id>`) first to confirm the parties, headline purchase price, and deal structure. Every subsequent dollar calculation derives from this headline price unless a source explicitly states a different basis.

### 2. Load the governing rules

Depending on the task, load one or more rule sources:

- **Playbook rules**: `GET /api/playbooks/<playbook_id>/rules` — provides preferred position, fallback position, and rationale for each term.
- **Policy thresholds**: `GET /api/policies/<policy_id>/thresholds` — provides the committee-approved boundary for each term category; exceeding it triggers escalation.

When both a playbook and a policy are relevant, the policy threshold is the hard boundary and the playbook is the negotiating position.

### 3. Pull all relevant deal records

Load every endpoint the task references. The standard set for a full analysis:

- Deal record, terms, benchmarks, risk estimates
- Consents, material contracts, regulatory
- Employees, cap table (for SPA), diligence findings
- Notes (for negotiation context)

Cross-reference records by stable IDs. When a term references a consent, contract, or finding, verify that the referenced record exists and its values are consistent.

### 4. Compare draft against rules

For each draft term, determine its **issue status**:

| Status | Meaning |
|---|---|
| `in_policy` | Draft is within the playbook/policy boundary — no action needed |
| `out_of_policy` | Draft deviates from the policy threshold — requires escalation |
| `missing_required_term` | The draft is silent on a term the playbook says must be present |
| `draft_exceeds_playbook` | Draft is more aggressive than the playbook's preferred position |
| `draft_below_playbook` | Draft is weaker than the playbook's fallback position |

**Absence is evidence.** If the playbook requires a term and the draft terms contain no matching entry, that is a `missing_required_term` issue — do not skip it. The most consequential findings are often what the draft omits.

### 5. Quantify every issue

For each identified issue, calculate numeric deltas:

- **Percent-point gaps**: `|draft_percent - required_percent|` for cap rates, basket thresholds, fee rates.
- **Dollar gaps**: `|draft_amount - required_amount|` for escrow, holdbacks, fee amounts. Derive from the headline purchase price unless a source states otherwise.
- **Month gaps**: `|draft_months - required_months|` for survival periods, escrow release, transition service duration.
- **Employee counts**: Sum headcount from the employee endpoint; sum PTO liability dollars.
- **Consent amounts at risk**: Sum `amount_at_risk` from the consents endpoint for closing-condition consents.
- **Material contract revenue**: Sum `annual_revenue` from material contracts requiring closing consent.

When exposure is modeled as a range, the **low** end uses the fallback position (minimum acceptable) and the **high** end uses the preferred position (best case).

### 6. Assign risk ratings

| Rating | Criteria |
|---|---|
| `HIGH` | Directly threatens closing certainty, exposes client to unquantified or large liability, or is a missing required term with no draft coverage |
| `MEDIUM` | Material economic impact but negotiable, or a consent/regulatory condition with manageable timeline |
| `LOW` | Minor economic impact, market-standard position, or a term where the draft is within negotiating range of the fallback |

### 7. Rank by negotiation priority

Order issues from highest to lowest priority:
1. Closing blockers (consents, regulatory clearance, financing conditions)
2. High-risk economic issues (indemnity caps, escrow, reverse break fees)
3. Medium-risk structural issues (survival periods, baskets, employee continuity)
4. Low-risk or market-standard items (governing law, tax allocation if standard)

### 8. Use stable identifiers

Every ID referenced in the output must come from the workbench records — never invent IDs. This includes:
- Term IDs from `/terms`
- Consent IDs from `/consents`
- Contract IDs from `/material-contracts`
- Employee IDs from `/employees`
- Estimate IDs from `/risk-estimates`
- Finding IDs from `/diligence-findings`
- Holder names from `/cap-table`

### 9. Use the SQL endpoint for cross-checks

When you need to verify consistency across records (e.g., "do the consent amounts at risk sum to the same total as the risk estimate?" or "are there employees listed in consents but not in the employee roster?"), use `POST /api/query` with:
```json
{"token": "deal-workbench-readonly", "query": "<your SQL>"}
```

### 10. Output rules

- **Return only valid JSON** conforming exactly to the provided `answer_template.json`. No explanatory prose, no markdown fences around the JSON, no trailing commentary.
- **Use the template's enums only** — never introduce an enum value that is not in the template's `allowed_enums` or equivalent field constraints.
- **Currency**: Integer USD dollars (no cents, no decimals, no commas).
- **Percentages**: Match the template's precision — two decimal places unless the template specifies one.
- **Months**: Integer months.
- **Dates**: `YYYY-MM-DD` format when the template requires dates.
- **Null vs. zero**: Use `null` when a value is genuinely absent or not applicable; use `0` when the computed value is zero. Do not substitute one for the other.
- **Empty arrays**: Use `[]` for missing required terms, not `null` and not omission of the field.

## Analysis type patterns

### Issue register (playbook comparison)

Used for: train_001. Seller APA review comparing buyer draft against seller playbook.

Method:
1. Load the deal record and all draft terms.
2. Load the applicable playbook rules.
3. For every playbook rule, find the corresponding draft term (or note its absence).
4. Compare each term's draft value against the playbook's preferred and fallback values.
5. Compute deltas, assign risk, and rank by priority.
6. Produce summary metrics: total issues, risk counts, total quantified exposure range, total negotiation delta.

### Economics and closing package

Used for: train_002. Buyer SPA review producing holder-level economics and closing mechanics.

Method:
1. Load deal record, cap table, terms, consents, employees, regulatory.
2. Allocate purchase price across holders per the cap table.
3. Compute indemnity package: cap, basket, survival, materiality scrape.
4. Compute escrow: amount, basis, release mechanics.
5. Evaluate closing conditions: required consents, material contract conditions, non-blocking notices.
6. Evaluate covenants: employment (service credit, PTO, WARN), restrictive covenants, D&O tail, transaction expenses.
7. Evaluate regulatory: HSR, hell-or-high-water, closing condition.
8. Produce closing readiness: overall status, blockers, tradeable issues.

### Committee escalation package

Used for: train_003. Policy-threshold comparison for committee approval.

Method:
1. Load the deal record, draft terms, and the applicable policy thresholds.
2. Identify ONLY terms that are out of policy — exclude in-policy terms (list them but don't analyze them).
3. For each escalated term, provide: category, clause reference, draft metric vs. policy metric, delta, benchmark support, quantified exposure, recommendation, required conditions.
4. Produce aggregate summary: escalated count, risk counts, aggregate exposure, overall recommendation, committee action, negotiation priority order.

### Transition review (carveout APA)

Used for: train_004. Seller-side review of carveout-specific transition and separation terms.

Method:
1. Load deal record, terms, employees, consents, material contracts.
2. Focus on carveout-specific issues: IP/domain transition, trademark redirects, transition services scope/fees/duration, Section 1060 purchase-price allocation, transfer-tax split, employee continuity, outside date extension, governing law/forum.
3. For each issue, normalize draft and required positions into comparable values.
4. Produce transition issues, required redlines, and operational risk summary.
5. Quantify stranded cost gaps, PTO liability, consent amounts at risk, top-customer revenue at risk, transition disruption exposure.

### Deviation matrix

Used for: train_005. Buyer-side structured position matrix across key SPA terms.

Method:
1. Load deal record, terms, buyer playbook, consents, material contracts, regulatory, risk estimates, benchmarks.
2. For each position category (indemnity, survival, materiality scrape, escrow, consents, HSR, material contracts), determine the buyer's preferred, fallback, and the draft's current value.
3. Classify each position's status against the playbook.
4. Identify closing blockers from consents, regulatory, and material contracts.
5. Compute risk totals: shortfalls, exposure ranges, counts by status and risk.

## Cross-cutting patterns

### Benchmark usage

When the workbench returns benchmark data for a term, use it to contextualize the position:
- `at_or_below_median` — market-standard, low negotiation risk
- `between_median_and_upper_quartile` — slightly aggressive but defensible
- `at_upper_quartile` — at the edge of market, needs justification
- `above_upper_quartile` — outside market, high negotiation risk unless justified by deal specifics

### Playbook fallback logic

Every playbook rule provides two reference points:
- **Preferred**: The ideal position — ask for this first.
- **Fallback**: The minimum acceptable position — concede no further.

When computing exposure, the low estimate assumes the fallback is achieved; the high estimate assumes the draft position prevails unchanged.

### Missing term detection

A term is "missing" when:
1. The playbook or policy lists it as required, AND
2. No draft term with a matching category/ID exists, AND
3. The deal structure (APA, SPA, carveout) is one where that term is customary.

When a term is missing, set `source_term_ids` to `[]`, `issue_status` to `missing_required_term`, and quantify the gap as the full required amount/percent/months from the playbook's fallback position.

### Consent classification

From the consents endpoint, classify each consent:
- **Closing condition**: Must be obtained before or at closing — a blocker.
- **Notice only**: Requires notice but not consent — non-blocking.
- **Post-closing covenant**: Can be satisfied after closing — non-blocking.

Only closing-condition consents with material amounts at risk count as blockers.

### Regulatory evaluation

From the regulatory endpoint:
- Determine if HSR filing is required (size-of-transaction test or below threshold).
- If HSR is required, check whether the draft includes an HSR clearance closing condition.
- Check for hell-or-high-water covenant requirements.
- Identify any industry-specific regulatory approvals beyond HSR.

## Error handling and edge cases

- If an API endpoint returns an empty response or 404, that record genuinely does not exist for this deal — note it as `not_found_in_current_records` rather than treating it as an error.
- If two records appear to conflict (e.g., employee count in `/employees` differs from count in `/notes`), trust the structured endpoint over the notes, and flag the discrepancy if it is material.
- If the draft terms contain a term the playbook does not address, it is not an issue unless it affirmatively harms the client's position.
- If the template requires a field you cannot populate from any workbench record, use `null` (not `0` and not omission) and ensure the field is present.
