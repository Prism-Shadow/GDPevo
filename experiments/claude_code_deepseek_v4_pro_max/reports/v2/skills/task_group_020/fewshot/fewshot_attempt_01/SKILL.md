# Aster Legal Deal Desk — Skill for Task Group 020

## Environment

- **Base URL**: `GDPEVO_ENV_BASE_URL` = `http://34.46.77.124:9020`
- Use the Deal Desk Web/API environment. Each deal room contains: deal profile, active and stale documents, clause records, policy/playbook documents, benchmark data, and search pages.
- Never use localhost, env/ setup scripts, or local environment data files.
- The `<TASK_ENV_BASE_URL>` placeholder in task prompts resolves to the GDPEVO_ENV_BASE_URL above.

## Workflow Rules by Task Shape

The task group covers four distinct deal-desk workflows. Identify which shape a task matches by reading the prompt's stated goal, the requested JSON keys, and the answer template's `schema_name` or top-level required keys.

### Shape A: Term Population / First-Draft Package
**Recognized by**: top-level keys `deal_terms`, `seller_allocations`, `closing_flags` (or `draft_terms`, `policy_checks`).

- Retrieve the deal profile from the deal room (target, buyer, seller, structure, signing date, outside closing date).
- Locate the **active** cap table / allocation schedule (`DOC-{DEALCODE}-CAP-ACTIVE`). A stale export (`DOC-{DEALCODE}-CAP-STALE`) is a distractor — prefer the active one.
- Compute consideration mix: `cash_at_close + seller_note + rollover_equity + earnout = headline_value = equity_value` (for all-cash or no-debt deals).
- For `per_share_price_usd`: set to `null` and `per_share_price_basis` to `NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE` if the cap table does not list share counts.
- `price_per_as_converted_percent_point_usd` = `equity_value_usd / 100` (integer division, whole dollars).
- Escrow amounts: `escrow_usd = round(headline_value * escrow_percent / 100)`.
- NWC collar percent: `nwc_collar_usd / equity_value_usd * 100`, rounded to two decimals.
- Seller allocations: allocate each component of consideration pro-rata by `ownership_percent`. `gross_proceeds_usd = round(headline_value * ownership_percent / 100)`.
- Policy checks (`policy_checks.checks`): compare each draft term against the controlling policy. Set `status` to `WITHIN_POLICY` if compliant, `OVERRIDE_APPLIED` if an active client instruction or documented override applies, `APPROVAL_REQUIRED` or `ESCALATE_IF_CHANGED` otherwise. The `measured_value` is a human-readable summary string using normalized units.
- Policy summary: count exceptions in `current_policy_exception_count` (count of checks where `status != WITHIN_POLICY`). If that count is 0, `approval_required_now` is `false` and `required_approval_bodies` is `[]`.

### Shape B: Counterparty Paper Review / Issue Register
**Recognized by**: top-level keys `deal_id`, `review_type`, `currency`, `issues`.

- Compare the active counterparty draft against current client instructions and the applicable playbook (e.g., seller APA playbook `P-SELLER-APA-2026`).
- Only include issues that are **material** — omit non-issues.
- For each issue, determine:
  - `severity`: `CRITICAL` for financing conditions and non-negotiable client positions; `HIGH` for escrow/survival/cap deviations; `MEDIUM` for scope narrowing; `LOW` for minor accommodations.
  - `recommended_action`: `DELETE` for financing conditions (seller side); `ADD` for missing protections; `ADD_FALLBACK_ONLY` for reverse termination fees; `REVISE` for numeric/scope adjustments; `ACCEPT` for buyer-favorable terms within tolerance.
  - `corrected_value`: include only the normalized fields relevant to that issue.
- `source_ids`: include the draft document, any email/client-instruction docs, applicable clause IDs, the controlling playbook, and relevant benchmarks. These are audit-trail identifiers, not prose.

### Shape C: Committee Escalation Analysis
**Recognized by**: top-level keys `deal_id`, `escalation_terms`, `aggregate_risk`.

- Identify terms needing committee-level escalation. Compare draft terms against policy thresholds.
- Quantify where possible: `draft_percent`, `policy_threshold_percent`, `deviation_percent` (the gap), and corresponding dollar amounts.
- `exposure_basis`: `EQUITY_VALUE` for capped exposure, `FULL_EQUITY_VALUE_UNCAPPED` for uncapped survival exposure, `NON_QUANTIFIED_LEGAL_RISK` when no dollar amount applies, `POLICY_THRESHOLD_EXCESS` for excess over threshold.
- For non-quantified issues (MAE carveouts, fiduciary out): set numeric fields to `null` and `exposure_basis` to `NON_QUANTIFIED_LEGAL_RISK`.
- `aggregate_risk.total_quantified_exposure_dollars` = sum of all `exposure_amount_dollars` across terms.
- `aggregate_risk.total_policy_excess_dollars` = sum of all `excess_amount_dollars` across terms.
- Committee members: exact names from the Deal Desk committee record, sorted as they appear.
- Strategic context (`batna_code`, `batna_leverage`, `ownership_context`, `strategic_rationale`) is sourced from the deal profile and committee records, not from the draft itself.
- Set `benchmark_memo_required: true` when any escalation term has a benchmark showing a minority of deals above threshold.

### Shape D: Transition-Term Issue Package (Carve-Out / Divestiture)
**Recognized by**: top-level keys `deal_id`, `policy_id`, `priority_issues`, `transition_flags`.

- `priority_issues`: only include issues determined to be priority/material. Each gets a `clause_code` (the short topic code) matching the `issue_id` domain.
- `transition_flags`: structured conclusions per domain (employee_transfer, tsa_service_continuity, restrictive_covenants, ip_transition, escrow_and_deadline). Each domain has `issue_present: true/false`.
- Closing deadline in `escrow_and_deadline`: compute `deadline_days_after_signing` as calendar days from `signing_date` to `draft_closing_deadline`. Compare against `minimum_deadline_days`; set `deadline_escalation_required: true` if the draft falls short.
- For restrictive covenants and IP: the `required_scope` reflects the narrowest acceptable position from the playbook, not the draft's position.

## Naming and ID Conventions

| Pattern | Format | Example |
|---------|--------|---------|
| Deal ID | `D-{TICKER}-{NUM}` | `D-ALDER-447` |
| Document ID | `DOC-{DEALCODE}{NUM}-{DOCTYPE}-{NUM}` | `DOC-BRASS219-DRAFT-02` |
| Clause ID | `CL-{DEALCODE}-{NUM}-{NUM}` | `CL-BRASS-219-001` |
| Policy ID | `P-{SIDE}-{SCOPE}-{YEAR}` | `P-SELLER-APA-2026` |
| Policy Rule ID | `{SIDEABBR}-{SCOPEABBR}-{TOPIC}` | `BUY-MID-BASKET` |
| Benchmark ID | `BM-{TOPIC}-[{INDUSTRY}-]{YEAR}[-{NUM}]` | `BM-RTF-HEALTHTECH-2026` |

**Document type codes in IDs**: `DRAFT` (active draft), `EMAIL` (client instructions), `DISC` (disclosure schedules), `FIN` (financial schedules), `MATCON` (material contracts), `TERM` (term sheet), `CAP-ACTIVE` (active cap table), `CAP-STALE` (stale cap table), `TEMPLATE` (template/stale distractor).

## Source Precedence Rules

1. **Active client instructions (EMAIL docs) > template/stale material**. A written client instruction always supersedes a template default.
2. **Active cap table > stale cap table export**. Use `DOC-{DEALCODE}-CAP-ACTIVE`; ignore `DOC-{DEALCODE}-CAP-STALE` for values but include it in `superseded_doc_ids`.
3. **Controlling playbook/policy > counterparty draft defaults**. The applicable playbook is the benchmark for what is "within policy."
4. **Active draft > stale/template distractors**. The deal room may contain multiple documents; the active draft (lowest-numbered DRAFT doc) is authoritative for current terms.
5. **Override codes** document when active client instructions or factual findings change the normal policy outcome (e.g., `NO_HSR_CONDITION_DESPITE_CYBER_ASSETS`).

## Numeric and Unit Conventions

| Type | Format | Example |
|------|--------|---------|
| Currency (USD) | Integer, no commas or symbols | `184000000` |
| Percentages | Number with 2 decimal places, expressed as percentage points | `7.50` (not `0.075`) |
| Per-share price | Number with 2 decimal places, or `null` | `null` or `4.52` |
| Months | Integer | `24` |
| Ownership percent | Number with up to 2 decimal places | `44.2` or `51.0` |
| Calendar days | Integer | `42` |

- **Rounding**: Use standard rounding (>=0.5 rounds up). Dollar amounts are always integer (whole dollars).
- **Null vs zero**: `null` means "not applicable / not calculable." `0` means "the value is zero" (e.g., no seller note, no earnout).

## Key Calculation Rules

- **Escrow amount**: `round(headline_purchase_price_usd * escrow_percent / 100)`
- **Indemnity cap amount**: `round(headline_purchase_price_usd * indemnity_cap_percent / 100)`
- **Basket amount**: `round(headline_purchase_price_usd * basket_percent / 100)`
- **Price per percent point**: `equity_value_usd / 100` (integer)
- **Per-share price**: `equity_value_usd / total_shares` (rounded to 2 decimals) — only when share count is available
- **NWC collar percent**: `round(nwc_collar_usd / equity_value_usd * 100, 2)`
- **Seller gross proceeds**: `round(headline_purchase_price_usd * ownership_percent / 100)`
- **Consideration components per seller**: allocate each component (`cash_at_close`, `seller_note`, `rollover_equity`, `earnout`) pro-rata by `ownership_percent`
- **Total consideration**: must equal `headline_value_usd` (or `equity_value_usd`)
- **Aggregate escrow percent**: `general_escrow_percent + tax_escrow_percent`
- **Deviation percent**: `draft_percent - policy_threshold_percent` (positive = exceeds policy)
- **Deadline days**: calendar days from `signing_date` to `closing_deadline`

## Controlled Enum Usage

### Deal Structure
`STOCK_PURCHASE`, `ASSET_PURCHASE`, `MERGER`, `ROLLOVER_STOCK_PURCHASE`

### Client Side
`BUYER`, `SELLER`

### Basket Type
`DEDUCTIBLE` (most common), `TIPPING`, `NONE`

### NWC Mechanic
`DOLLAR_FOR_DOLLAR_OUTSIDE_COLLAR`, `DOLLAR_FOR_DOLLAR_FROM_FIRST_DOLLAR`, `NO_POST_CLOSING_ADJUSTMENT`, `TRUE_UP_AGAINST_ACTIVE_BALANCE_SHEET`, `SELLER_BUDGET_BASELINE`, `NONE`

### HSR Status
For Shape A: `REQUIRED`, `NOT_REQUIRED`, `UNCLEAR`
For Shape A closing_flags: `HSR_CLOSING_CONDITION`, `NO_HSR_CONDITION_COOPERATION_ONLY`, `NOT_ADDRESSED`
HSR basis codes: `SIZE_OF_PERSON_TEST_NOT_MET`, `REPORTABLE_THRESHOLDS_MET`, `COUNSEL_MEMO_MISSING`, `NOT_APPLICABLE`
HSR override basis: `THRESHOLDS_NOT_MET_AFTER_DEBT_ADJUSTMENTS`, `SIZE_OF_PERSON_NOT_MET`, `COUNSEL_MEMO_MISSING`, `UNKNOWN`

### Consent Condition Status
`MATERIAL_CONSENTS_AS_CLOSING_CONDITIONS`, `MATERIAL_CONSENTS_AS_POST_CLOSING_COVENANTS`, `NO_MATERIAL_CONSENTS_REQUIRED`

### Consent Condition Type (per contract)
`CLOSING`, `COVENANT`, `NOTICE`, `POST_CLOSING_NOTICE`

### Non-Compete Scope
`TARGET_PRODUCTS_AND_CURRENT_TERRITORIES`, `WORLDWIDE_ALL_AFFILIATES`, `NO_NON_COMPETE`, `OTHER_LIMITED_SCOPE`

### Policy Check Status
`WITHIN_POLICY`, `APPROVAL_REQUIRED`, `OVERRIDE_APPLIED`, `ESCALATE_IF_CHANGED`

### Severity
`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`

### Per-Share Price Basis
`CALCULATED_FROM_ACTIVE_CAP_TABLE`, `NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE`

### Escrow Policy Status
`WITHIN_POLICY`, `ESCALATE`, `NOT_APPLICABLE`

### Form Position
`BUYER_FORM`, `SELLER_FORM`, `COMMITTEE_FORM`, `STANDARD_FORM`

### Position Enums (Shape A drafting_positions)
- `escrow_cap_position`: `CAP_EQUALS_GENERAL_ESCROW`, `CAP_ABOVE_ESCROW`, `CAP_BELOW_ESCROW`, `NO_CAP`
- `basket_position`: `DEDUCTIBLE_BASKET`, `TIPPING_BASKET`, `NO_BASKET`
- `consent_position`: `SPECIFIED_MATERIAL_CONSENTS_AS_CLOSING_CONDITIONS`, `POST_CLOSING_COVENANT_ONLY`, `OMIT_CONSENTS`
- `hsr_position`: `NO_HSR_CONDITION_COOPERATION_ONLY`, `HSR_FILING_CONDITION`, `HSR_UNCLEAR_ESCALATE`
- `earnout_position`: `OBJECTIVE_REVENUE_BASED_FALLBACK`, `OPERATING_COVENANT_REQUIRED`, `NO_EARNOUT`
- `non_compete_position`: `TARGETED_PRODUCT_SCOPE_RESTRICTIVE_COVENANT`, `BROAD_GLOBAL_RESTRICTIVE_COVENANT`, `TARGETED_TERRITORY_RESTRICTIVE_COVENANT`, `OMIT_RESTRICTIVE_COVENANT`
- `transition_services_position`: `NO_GENERAL_TSA_LIMITED_CUSTOMER_NOTICE_SUPPORT`, `FULL_TSA_REQUIRED`, `TSA_STATUS_UNCLEAR`
- `ip_transition_position`: `REQUIRE_OPEN_SOURCE_AUDIT_AND_FEDRAMP_ASSIGNMENT`, `NO_IP_TRANSITION`, `TRADEMARK_PHASE_OUT_ONLY`

### Approval Categories
`DEAL_LEAD`, `EMPLOYMENT_COUNSEL`, `FINANCE_COMMITTEE`, `LEGAL_RISK_COMMITTEE`, `REGULATORY_COUNSEL`, `HR_COMMITTEE`, `IP_COUNSEL`, `OPERATIONS_COMMITTEE`, `SELLER_STEERING_COMMITTEE`, `EXECUTIVE_COMMITTEE`

### Conditional Escalation Triggers (Shape A)
`ADD_FINANCING_CONDITION`, `REMOVE_FEDERAL_SOC_CONSENT`, `TAX_ESCROW_THRESHOLD_TRIGGER`, `GENERAL_ESCROW_THRESHOLD_TRIGGER`, `CAP_THRESHOLD_TRIGGER`, `BASKET_THRESHOLD_TRIGGER`, `TOP_CUSTOMER_CONSENT_OMITTED`, `UNCLEAR_HSR_ANALYSIS`

### Override Codes (Shape A)
`ACTIVE_CLIENT_INSTRUCTIONS_SUPERSEDE_TEMPLATE`, `NO_HSR_CONDITION_DESPITE_CYBER_ASSETS`, `USE_ACTIVE_CAP_TABLE_OVER_STALE_EXPORT`

### Recommended Actions (Shape B — Issue Register)
`ACCEPT`, `ADD`, `ADD_FALLBACK_ONLY`, `DELETE`, `ESCALATE`, `NO_ISSUE`, `REVISE`

### Recommended Actions (Shape D — Transition Package)
`ACCEPT`, `DELETE`, `ESCALATE_ONLY`, `EXTEND_AND_ESCALATE`, `NARROW_AND_ESCALATE`, `REDUCE_OR_ESCALATE`, `REVISE`, `REVISE_AND_ESCALATE`

## List Ordering Rules (Mandatory)

| List Key | Sort Order |
|----------|-----------|
| `seller_allocations` | `seller_name` ascending (Shape A older) or `seller_id` ascending (Shape A newer) |
| `required_material_consents` | `contract_name` ascending |
| `employment_employees` | displayed employee name ascending |
| `issues` / `priority_issues` | `issue_id` ascending |
| `escalation_terms` | `term_id` alphabetically |
| `source_doc_ids` / `source_ids` | alphabetically ascending |
| `required_service_codes` | alphabetically |
| `mae_omitted_carveouts` | alphabetically by code |
| `committee_members` | as shown in Deal Desk committee record |
| `primary_driver_term_ids` | alphabetically |
| `tsa_services` | alphabetically |
| `material_consents_as_closing_conditions` | alphabetically by contract name |
| `post_closing_notice_items` | alphabetically by contract name |
| `other_approvals` | alphabetically |
| `checks` (policy) | `check_id` ascending |
| `required_approval_bodies` | alphabetically |
| `conditional_escalation_triggers` | alphabetically |
| `override_codes` | alphabetically |
| `superseded_doc_ids` | alphabetically |

## Common Pitfalls

1. **Using stale cap table data**: Always prefer `DOC-{DEALCODE}-CAP-ACTIVE` over `DOC-{DEALCODE}-CAP-STALE`. The stale cap table is a distractor placed to test source precedence.
2. **Treating null and zero as interchangeable**: `null` = not applicable; `0` = the value is zero. Mixing these breaks downstream validation.
3. **Percent formatting**: Always express as percentage points (e.g., `7.50`, not `0.075`). This applies everywhere — escrow, basket, cap, ownership, collar percent.
4. **Missing the controlling playbook**: The applicable policy/playbook ID (e.g., `P-SELLER-APA-2026`, `P-BUYER-MIDMARKET-2026`) must match the deal's side and structure. A buyer-side stock deal does not use a seller APA playbook.
5. **Forgetting to sort lists**: Every list field in every shape has a required sort order. Unsorted lists are incorrect.
6. **Including non-issues in issue registers**: Only include items that are material deviations. An item fully within policy with no recommended action should not appear.
7. **Escrow/investment-benefit mismatch**: When escrow release is short (12 months or less), `investment_benefit` is typically `FOR_SELLER`. When long (18+ months), it may be `FOR_BUYER` or `SPLIT`.
8. **Financing condition**: For seller-side reviews, financing conditions are always `CRITICAL` severity with `recommended_action: DELETE`. This is a universal seller position.
9. **Reverse termination fee**: Seller-side position is `ADD_FALLBACK_ONLY` — the RTF is contingent on the financing condition being deleted. Always set `financing_condition_must_still_be_deleted: true`.
10. **Survival period**: Seller reps typically survive 12 months (seller preference); buyer drafts often push for 18-24 months. The playbook determines the target.
11. **Total consideration sum check**: The sum of `cash_at_close + seller_note + rollover_equity + earnout` must equal `total_consideration`, which must equal `headline_value_usd` (absent debt adjustments).
12. **Escrow cap relationship**: `CAP_EQUALS_GENERAL_ESCROW` means indemnity cap % = general escrow %. `CAP_ABOVE_ESCROW` means cap % > escrow %. Check the actual numbers.
13. **De_minimis**: A de minimis threshold is almost always paired with a `DEDUCTIBLE` basket type. A `TIPPING` or `NONE` basket typically has no de minimis.
14. **HSR for cyber/defense deals**: Even if size-of-person tests aren't met, cyber-security targets may trigger HSR analysis due to CFIUS or sector-specific concerns. Document with `NO_HSR_CONDITION_DESPITE_CYBER_ASSETS` override.

## Output Format

- Return **only** a JSON object — no markdown fences, no prose, no surrounding text.
- Follow the exact key structure of the answer template (all top-level required keys must be present).
- All enum values must match the template's `allowed_values` exactly (case-sensitive).
- For Shape B: the `currency` field must be `"USD"`.
- For Shape B: `review_type` must match the template's allowed value exactly.

## Deal Room Navigation

When querying the Deal Desk for a deal:
1. Start from the deal profile to get basic identifiers (target, buyer, seller group, structure, dates).
2. Navigate to the cap table / allocation schedule section to get the active version.
3. Review the active draft document for current term proposals.
4. Check client instruction documents (EMAIL docs) for written guidance that may override templates.
5. Consult the applicable policy/playbook for each term category.
6. Use benchmark data for market comparisons when quantifying deviations.
7. Ignore documents marked as stale/template unless they are being explicitly superseded.
