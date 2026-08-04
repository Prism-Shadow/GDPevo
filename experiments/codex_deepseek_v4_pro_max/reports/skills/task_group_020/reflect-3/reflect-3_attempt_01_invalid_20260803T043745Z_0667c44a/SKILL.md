 # M&A Deal Workbench — Counsel Analysis Skill

 ## Overview

 Use this skill when analyzing M&A deal terms through the Deal Workbench API. The workbench provides structured deal records, draft terms, playbook rules, policy thresholds, consents, employees, material contracts, regulatory records, diligence findings, risk estimates, benchmarks, and notes. This skill covers the methodology for comparing draft terms against playbook or policy rules, identifying deviations, quantifying exposure, and producing structured counsel work product.

 ## Core Workflow

 ### 1. Orient to the Deal

 Start with `GET /api/deals/<deal_id>` to establish:

- **Client side**: `buyer` or `seller` — determines which playbook or policy applies
- **Transaction type**: Asset purchase agreement, Stock purchase agreement, Carveout asset purchase agreement, or Public company merger
- **Headline value**: The headline purchase price in USD — use this as the default basis for all dollar calculations unless a specific source states a different basis
- **Playbook ID** or **Policy ID**: The applicable rule set for the client's side

### 2. Gather Relevant Records

 Pull all available records using the GET endpoints. The key endpoints are:

| Endpoint | Content |
|---|---|
| `/api/deals/<deal_id>/terms` | Current draft terms with numeric values, units, and clause references |
| `/api/playbooks/<playbook_id>/rules` | Client-side playbook rules with preferred and fallback positions |
| `/api/policies/<policy_id>/thresholds` | Policy thresholds for committee-escalation matters (public company deals) |
| `/api/deals/<deal_id>/consents` | Required and non-required third-party consents with amounts at risk |
| `/api/deals/<deal_id>/employees` | Employee groups, counts, PTO liabilities, service-credit requirements |
| `/api/deals/<deal_id>/material-contracts` | Material contracts with annual revenue and consent requirements |
| `/api/deals/<deal_id>/regulatory` | HSR status, hell-or-high-water requirements, approval type |
| `/api/deals/<deal_id>/risk-estimates` | Quantified exposure ranges (low/high) by category |
| `/api/deals/<deal_id>/diligence-findings` | Diligence findings with amounts, severity, and topics |
| `/api/deals/<deal_id>/benchmarks` | Market benchmarks for termination fees, indemnity caps, survival periods |
| `/api/deals/<deal_id>/notes` | Deal-team notes on negotiation posture and counterparty rationale |
| `/api/deals/<deal_id>/cap-table` | Capitalization table with holders, share counts, and fully-diluted percentages |
| `/api/deals/<deal_id>/documents` | Document metadata (draft agreements, negotiation trackers, financial models) |

 If cross-table checks are needed, use `POST /api/query` with `{"token": "deal-workbench-readonly", "sql": "<SELECT or WITH query>"}`. This provides read-only SQL access across all workbench tables.

### 3. Compare Draft Terms Against Playbook or Policy Rules

 For each playbook rule category, locate the corresponding draft term (if any) and compare:

- **Preferred position**: The client's ideal outcome
- **Fallback position**: The minimum acceptable outcome, often with conditions
- **Draft value**: What the counterparty's draft actually provides

 Classify each issue using these statuses:

- `in_policy` — Draft meets or exceeds the client's preferred position
- `out_of_policy` — Draft deviates from the client's preferred position
- `missing_required_term` — The draft does not address a term that the playbook, deal data, or regulatory requirements show is needed
- `draft_exceeds_playbook` — Draft value is more aggressive than the client would accept (seller-side: buyer asks for too much; buyer-side: seller offers too little)
- `draft_below_playbook` — Draft value falls short of the client's minimum (buyer-side: seller's offer is below buyer's minimum)

 Assign a risk rating to each issue:
- `HIGH` — Threatens closing certainty, creates material uncapped exposure, or requires escalation to committee
- `MEDIUM` — Material but negotiable; within the playbook fallback range
- `LOW` — Routine or administrative; in policy or easily resolved

 Assign a recommended action:
- `escalate` — Requires business-lead or committee approval
- `revise` — Negotiate toward the preferred or fallback position
- `add` — Insert a missing required term
- `accept` — Draft position is acceptable
- `delete` — Remove an unfavorable provision
- `approve` / `approve_with_conditions` / `reject` — Committee-level decisions

### 4. Calculate Financial Impacts

 All dollar amounts derive from the deal's headline purchase price unless a source explicitly states a different basis (e.g., "enterprise value" for reverse break fees, "upfront cash" for specific allocation calculations).

- **Currency**: Integer USD (no cents)
- **Percentages**: Decimal numbers in percent points, rounded to two decimal places (e.g., `12.50` for 12.5%)
- **Months**: Integer months

 Common calculations:
- `draft_amount_dollars = headline_value × draft_percent`
- `preferred_amount_dollars = headline_value × preferred_percent`
- `fallback_amount_dollars = headline_value × fallback_percent`
- `delta_to_fallback_dollars = draft_amount - fallback_amount` (absolute difference)
- `delta_to_fallback_months = draft_months - fallback_months`
- `required_fee_dollars = basis_value × required_fee_percent`
- `shortfall_dollars = required_fee_dollars - draft_fee_dollars` (when draft is below requirement)

 Sum risk-estimate exposures across categories for aggregate exposure ranges:
- `total_quantified_exposure_low_dollars = sum of all risk estimate exposure_low values`
- `total_quantified_exposure_high_dollars = sum of all risk estimate exposure_high values`

 Sum deltas across issues for total negotiation delta.

### 5. Build the Structured Output

 Produce JSON conforming to the provided answer template. Key rules:

- Use only the enums specified in the template — never invent new values
- Reference stable, workbench-sourced IDs for all source terms, consents, contracts, employees, findings, and risk estimates
- For missing terms, use an empty array `[]` for `source_term_ids`
- Sort issue registers as specified (alphabetically by `issue_id` or by counsel workflow priority)
- Keep `null` for inapplicable numeric fields rather than defaulting to zero
- Include all required top-level fields and summary metrics
- Output only JSON — no explanatory prose outside the structure

### 6. Validate Completeness

 Before finalizing:

- Every playbook rule category has been checked against the draft terms
- Every consent marked `required_for_closing: "yes"` has been addressed in closing conditions
- Every material contract with `consent_required: "yes"` has been addressed
- Employee service-credit and PTO requirements from the playbook have been checked
- HSR and regulatory requirements have been addressed in covenants
- Risk estimates have been aggregated correctly
- Dollar amounts are integer USD and derived from the correct basis
- Percentages have exactly two decimal places
- Source IDs are stable (from the workbench, not invented)

## Analysis by Deal Type

### Asset Purchase Agreement (Seller-Side)

 Sellers prioritize: no financing condition, minimal reverse break fee, low escrow with short release, capped indemnity, short survival periods, limited transition services, employee protections, and clean consent/HSR covenants. Compare the buyer's draft APA against the seller playbook. Treat absent seller-protective terms as issues when surrounding deal data (playbook rules, consent requirements, regulatory facts, risk estimates) shows the term is needed.

### Asset Purchase Agreement — Carveout (Seller-Side)

 Additional focus on: transition service scope and duration, stranded-cost reimbursement, customer consent termination rights, employee cherry-picking restrictions, IP/domain transition, tax allocation (Section 1060), and transfer tax splits. Carveouts inherently have higher transition-disruption risk.

### Stock Purchase Agreement (Buyer-Side)

 Buyers prioritize: high indemnity caps, full materiality scrapes, long survival periods, robust escrow/holdback, broad consent closing conditions, HSR clearance conditions, service-credit and PTO protections, restrictive covenants on founders/executives, D&O tail coverage, and working-capital adjustments. Include holder-level consideration allocation from the cap table.

### Public Company Merger (Buyer-Side, Committee Escalation)

 Governed by policy thresholds (e.g., `POL_MA_2025_A`) rather than playbooks. Key escalation categories: reverse termination fee, fiduciary out, R&W survival, and MAE carveouts. Compare draft metrics against policy thresholds, calculate deltas, and benchmark against market data. Produce committee-ready escalation memos with clear recommendations and quantified exposure.

## SQL Usage

 When the GET endpoints do not surface cross-table relationships, use `POST /api/query`:

```
POST /api/query
{"token": "deal-workbench-readonly", "sql": "SELECT ... FROM ... WHERE ..."}
```

 Available tables: `deals`, `draft_terms`, `playbook_rules`, `policy_thresholds`, `consents`, `employees`, `material_contracts`, `regulatory`, `risk_estimates`, `diligence_findings`, `benchmarks`, `deal_notes`, `cap_table`, `documents`.

 Use SQL for:
- Discovering which playbook categories lack corresponding draft terms
- Aggregating exposure across categories
- Validating that all required consents are addressed
- Checking for data consistency across related records

## Common Pitfalls

- **Wrong basis for calculations**: Always check the `basis` field on each draft term and playbook rule. Not everything uses the headline purchase price — reverse break fees may use enterprise value, employee matters may use count-based metrics.
- **Missing required terms**: The absence of a term from the draft is itself an issue when the playbook, consent records, regulatory requirements, or employee data shows the term is needed. Use `missing_required_term` status.
- **Stale draft flags**: Check the `staleness_flag` on draft terms. A `stale` flag means the data may not reflect the current negotiation state.
- **Mixed units**: Confirm the `unit` field (percent_points, months, dollars, contracts, boolean, text) before comparing values.
- **Inventing IDs**: Never fabricate source IDs. Use only stable IDs that appear in workbench API responses.
- **Boolean vs. numeric**: Some terms are boolean conditions (present/absent), not numeric. Handle these with `null` in numeric fields.
- **Rounding**: Use integer dollars and two-decimal-place percentages consistently.
