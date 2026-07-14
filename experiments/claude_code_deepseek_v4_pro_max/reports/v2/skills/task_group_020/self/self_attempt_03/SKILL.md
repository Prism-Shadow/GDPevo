# SKILL: condition_self — Closing Conditions & Deal Term Population (task_group_020)

## Overview

This skill covers Aster Legal Deal Desk tasks that require populating or reviewing closing conditions, deal terms, seller allocations, policy checks, and transition flags for M&A transactions. The tasks span buyer-side and seller-side perspectives across stock purchases, asset purchases, mergers, and carve-outs.

## Environment

- **Base URL**: `http://34.46.77.124:9020` (set as `GDPEVO_ENV_BASE_URL`; override any localhost/127.0.0.1 references in task text)
- **System**: Aster Legal Deal Desk (Python 3.11, seed 20020)
- **Navigation**: Web UI at `/` with links to `/deals`, `/policies`, `/benchmarks`, `/clauses/compare`, `/api/health`
- **API Endpoints**:
  - `GET /api/deals/{deal_id}` — Full deal JSON (deal record, clauses, documents, benchmarks, policy)
  - `GET /api/policies/{policy_id}` — Policy rules with linked deals
  - `GET /api/health` — System health and counts
- **No authentication required** on this environment.

## Data Model

### Deal Record (`/api/deals/{deal_id}`)

The API returns a single JSON object with four top-level arrays: `deal`, `clauses`, `documents`, `benchmarks`, `policy`.

**`deal` object — primary fields:**
- `deal_id`, `codename`, `client`, `client_side` (BUYER/SELLER), `structure` (STOCK_PURCHASE/ASSET_PURCHASE/MERGER/CARVE_OUT/ROLLOVER_STOCK_PURCHASE)
- `buyer`, `seller`, `target`, `headline_value`, `equity_value`, `industry`
- `signing_date`, `closing_deadline`, `status`, `policy_id`
- `economics` — nested: `basket`, `escrows`, `consideration_mix`, `indemnity_cap_percent`, `survival_periods`, `working_capital`, `break_fee_percent`, `reverse_termination_fee_percent`
- `parties` — nested: `buyers` (list), `sellers` (list of objects with name/ownership_percent/role/estimated_proceeds), `committee_members`, `key_employees`, `representatives`
- `schedules` — nested: `cap_table`, `employment_terms`, `ip_transition`, `material_contracts`, `regulatory_status`, `transition_services`, `material_contracts_source_doc_id`, `stale_cap_table`
- `draft_terms` — narrative key-value pairs describing the current draft state
- `client_positions` — `preferred`, `fallback`, `escalation` text
- `negotiation_context` — `batna`, `ownership_dynamics`, `rationale`, `strategic_notes`
- `record_links` — maps document roles to doc IDs
- `active_documents` — list of ACTIVE doc IDs
- `stale_documents` — list of STALE/TEMPLATE doc IDs

**`clauses` array — each clause:**
- `clause_id`, `clause_code`, `topic`, `deal_id`
- `draft_value`, `playbook_value`, `policy_threshold`, `calculation_base`
- `risk_hint` (narrative), `source_doc_id`, `version_status` (ACTIVE or STALE)

**`documents` array — each document:**
- `doc_id`, `title`, `doc_type` (term_sheet/draft_agreement/email/cap_table/financial_schedule/material_contracts/disclosure_schedule/template_provision)
- `version_status` (ACTIVE/STALE/TEMPLATE), `effective_date`, `related_ids`, `sections` (list of heading/text)

**`policy` object:**
- `policy_id`, `policy_type`, `client`, `effective_date`, `version`, `title`
- `rules` array: each has `rule_id`, `topic`, `preferred`, `fallback_position`, `escalation_triggers`, `threshold`, `approval_category`, `basis`

**`benchmarks` array — each benchmark:**
- `benchmark_id`, `topic`, `industry`, `year`, `definition`, `sample_size`
- `mean_percent`, `median_percent`, `range_low`, `range_high`, `count_above_threshold`, `notes`

## Source Precedence Rules (CRITICAL)

When multiple sources contain conflicting information, apply this precedence:

1. **Active client instructions** (`doc_type: "email"` with `version_status: "ACTIVE"`) — highest authority
2. **Active draft agreement** (`doc_type: "draft_agreement"` with `version_status: "ACTIVE"`)
3. **Active term sheet** (`doc_type: "term_sheet"` with `version_status: "ACTIVE"`)
4. **Active cap table** (`doc_type: "cap_table"` with `version_status: "ACTIVE"`)
5. **Active financial schedule / material contracts / disclosure schedules**
6. **Policy rules** — apply to active drafts; use for policy checks and escalation decisions
7. **Active clauses** (`version_status: "ACTIVE"`) — use as confirmation, never as primary source
8. **Stale documents** (`version_status: "STALE"`) — reference only for audit trail; do NOT use values
9. **Template provisions** (`version_status: "TEMPLATE"`) — ignore for deal-specific values; they contain generic language that may conflict

**Key precedence rules:**
- `deal.economics` values come from the ACTIVE financial schedule and term sheet
- `deal.schedules` values come from the respective ACTIVE source documents
- `deal.schedules.cap_table` is authoritative for seller allocation; ignore `deal.schedules.stale_cap_table`
- `deal.draft_terms` are narrative summaries; cross-reference with clause records and schedules for precise values
- Clause records with `version_status: "STALE"` are template distractors — never use their values
- Client instructions (email) supersede template defaults when they conflict
- Cap table: ACTIVE > STALE. A stale cap table note like "Pre-option-exercise summary; superseded by June cap table" means ignore it entirely

## API Usage Patterns

### Getting a deal

```
GET /api/deals/{deal_id}
```

Returns everything needed in one call. No pagination, no filtering needed.

### Extracting specific data from the response

- **Deal identity**: `deal.deal_id`, `deal.structure`, `deal.target`, `deal.buyer`, `deal.seller`, `deal.client_side`
- **Economics**: `deal.economics` — read basket, escrows, consideration_mix, indemnity_cap_percent, survival_periods, working_capital
- **Seller allocations**: `deal.parties.sellers` — each has `name`, `ownership_percent`, `role`, `estimated_proceeds`
- **Cap table**: `deal.schedules.cap_table` — `source_doc_id`, `as_of`, `status`, `sellers`
- **Material consents**: `deal.schedules.material_contracts` — list of objects with `name`, `annual_revenue`, `condition_type`, `consent_required`
- **HSR/regulatory**: `deal.schedules.regulatory_status` — `hsr_required` (boolean), `basis` (narrative), `other_approvals` (list)
- **Employment**: `deal.schedules.employment_terms` — `founder_employment`, `non_compete`, `WARN`, `employee_transfer`
- **IP**: `deal.schedules.ip_transition` — `required`, `note`
- **TSA**: `deal.schedules.transition_services` — `required`, `note`, `needed_services`, `draft_duration_months`, `required_duration_months`
- **Policy rules**: `policy.rules[]` — each rule maps to a topic with `preferred`, `fallback_position`, `escalation_triggers`, `threshold`
- **Client positions**: `deal.client_positions.preferred`, `.fallback`, `.escalation`
- **Key employees**: `deal.parties.key_employees` — list of "Name, Role" strings

### Getting a policy

```
GET /api/policies/{policy_id}
```

Returns the policy with rules and linked deals. Use this to cross-reference policy thresholds.

## Common Task Type Workflows

### Task Type A: Term Population (First Draft) — train_001, train_005

Given a deal ID, populate deal terms, seller allocations, and closing flags from the active deal record.

**Workflow:**
1. Fetch `GET /api/deals/{deal_id}`
2. Extract deal identity: `deal_id`, `structure`, `target`, `buyer`, `seller` (from `deal.seller` or aggregate from `deal.parties.sellers` for the seller_group)
3. Extract dates: `signing_date`, `closing_deadline` (use field `closing_deadline`, not `outside_closing_date` unless the template specifically asks for a different field)
4. Extract economics:
   - `headline_purchase_price_usd` = `deal.headline_value`
   - `equity_value_usd` = `deal.equity_value`
   - Consideration mix from `deal.economics.consideration_mix`: `cash_at_close`, `seller_note`, `rollover_equity`, `earnout`
   - `cash_at_close_usd` = `consideration_mix.cash_at_close`
   - Escrows from `deal.economics.escrows`
   - Basket from `deal.economics.basket`
   - Indemnity cap from `deal.economics.indemnity_cap_percent`
   - Survival periods from `deal.economics.survival_periods`
   - NWC from `deal.economics.working_capital`
5. Extract cap table: `deal.schedules.cap_table.source_doc_id`, `deal.schedules.cap_table.as_of`
6. Compute per-share price:
   - If cap table provides share count → compute `equity_value / total_shares`, round to 2 decimals, basis = `CALCULATED_FROM_ACTIVE_CAP_TABLE`
   - If cap table does NOT provide share count → `per_share_price_usd = null`, basis = `NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE`
7. Compute price per as-converted percent point: `headline_value / 100`, integer dollars
8. Extract seller allocations from `deal.parties.sellers`:
   - `seller_name` = seller's `name`
   - `role` = seller's `role`
   - `ownership_percent` = seller's `ownership_percent`
   - `gross_proceeds_usd` = seller's `estimated_proceeds` (or compute: `ownership_percent / 100 * headline_value` if not directly available)
   - Sort by `seller_name` ascending
9. Extract closing flags:
   - **Material consents**: From `deal.schedules.material_contracts` — include all contracts; map `condition_type` to the template's condition_type enum; `consent_required` is boolean
   - **consent_condition_status**: `MATERIAL_CONSENTS_AS_CLOSING_CONDITIONS` if any contracts have `condition_type: "closing"` and `consent_required: true`; `MATERIAL_CONSENTS_AS_POST_CLOSING_COVENANTS` if only covenants/post-closing; `NO_MATERIAL_CONSENTS_REQUIRED` if none
   - **HSR**: `hsr_required` from `deal.schedules.regulatory_status.hsr_required`; `hsr_condition` from draft terms (read the HSR clause `draft_value`); `hsr_basis_code` from the regulatory `basis` narrative
   - **Other approvals**: `deal.schedules.regulatory_status.other_approvals` list
   - **Employment**: Read `deal.schedules.employment_terms` — extract founder employment requirement, term months, named employees
   - **Non-compete**: Duration from draft terms / employment terms; scope from client positions + draft terms
   - **TSA**: `deal.schedules.transition_services.required`
   - **IP**: `deal.schedules.ip_transition.required`
10. For policy checks (train_005): Compare each draft term against the corresponding policy rule; determine `WITHIN_POLICY`, `APPROVAL_REQUIRED`, `ESCALATE_IF_CHANGED`, or `OVERRIDE_APPLIED` based on the rule's threshold

### Task Type B: Counterparty Draft Review (Issue Register) — train_002

Given a deal ID as seller-side counsel, review the buyer's draft against client instructions and playbook.

**Workflow:**
1. Fetch deal API
2. Identify the `client_side` (here: SELLER) and confirm you're reviewing the counterparty (buyer) draft
3. For each clause area (`clauses[]` array), compare:
   - Draft value vs. playbook value vs. policy threshold
   - Check if draft violates a policy escalation trigger
4. For each material issue found:
   - Assign `issue_id` from the allowed enum matching the topic
   - Set `severity`: CRITICAL (financing condition, missing TSA), HIGH (escrow/scope violations beyond playbook), MEDIUM (basket/survival mismatches within fallback), LOW (minor deviations)
   - Set `recommended_action`: ACCEPT (within policy), DELETE (must remove), REVISE (modify value), ESCALATE (needs committee), ADD (missing provision), ADD_FALLBACK_ONLY (can accept as fallback)
   - Populate `corrected_value` with specific normalized fields
   - Populate `source_ids` with document/clause/policy IDs that support the finding
5. Sort issues by `issue_id` ascending
6. Only include issues that are material — if a term aligns with the playbook or falls within policy range, it's not an issue

**Severity assignment guidelines:**
- **CRITICAL**: Financing condition present, TSA completely missing for dependent division, worldwide non-compete with affiliate scope, WARN retained by seller
- **HIGH**: Escrow above 10% (seller) / 12% (buyer), cap far above escrow, missing employee offer standard, no IP transition license
- **MEDIUM**: Basket below preferred range but at fallback, survival period below playbook, closing deadline near margin
- **LOW**: Minor percentage deviations within policy range, de minimis amount slightly different

### Task Type C: Committee Escalation Analysis — train_003

Given a deal ID, identify terms requiring committee escalation, quantify exposure, and assess aggregate risk.

**Workflow:**
1. Fetch deal API
2. Identify escalation terms from `clauses[]` where `draft_value` exceeds `policy_threshold`
3. For each escalation term:
   - Map to `term_id` from the escalation enums
   - Determine `deviation_code` based on the nature of the deviation
   - Compute `quantification`:
     - `draft_percent` = actual percent in draft
     - `policy_threshold_percent` = policy limit
     - `deviation_percent` = `draft_percent - policy_threshold_percent` (when applicable)
     - `draft_amount_dollars` = `draft_percent / 100 * deal.equity_value` (for percent-based terms)
     - `exposure_amount_dollars` = `deviation_percent / 100 * deal.equity_value`
     - `exposure_basis` = EQUITY_VALUE or FULL_EQUITY_VALUE_UNCAPPED or NON_QUANTIFIED_LEGAL_RISK
   - Use relevant benchmarks from the `benchmarks[]` array (filter by matching topic and industry)
4. Populate `aggregate_risk`:
   - `committee_route`: highest-level route among escalated terms
   - `risk_tier`: CRITICAL if any CRITICAL severity, else HIGH/MEDIUM/LOW
   - `final_action`: ESCALATE_AND_RENEGOTIATE_BEFORE_SIGNING for deal-breakers, ESCALATE_AND_APPROVE for acceptable deviations
   - `primary_driver_term_ids`: the 1-2 terms driving the escalation
   - `total_quantified_exposure_dollars`: sum of all exposure amounts
   - `total_policy_excess_dollars`: sum of amounts above policy thresholds
   - `strategic_context`: from `deal.negotiation_context` — map narrative to enum

### Task Type D: Transition-Term Issue Package — train_004

For seller-side carve-out APA, identify priority deviations and structured transition flags.

**Workflow:**
1. Fetch deal API
2. For each clause topic, check if draft deviates from playbook/policy. If it does, create a priority_issue entry
3. Map each issue to allowed `issue_id` and `clause_code` enums
4. For each transition flag area, populate the structured object:
   - **employee_transfer**: Derive `draft_offer_percent` from the employment narrative; check if `seller_warn_or_severance_retained`
   - **tsa_service_continuity**: `draft_duration_months` from transition_services; compare to `target_duration_months` and `fallback_duration_months` from policy
   - **restrictive_covenants**: Non-compete years from draft; `max_non_compete_years` from policy; scope from draft terms
   - **ip_transition**: Trademark phase-out months; check for broad design file access
   - **escrow_and_deadline**: Escrow percent/amount; signing date; `deadline_days_after_signing` = days between signing_date and closing_deadline; compare to minimum from policy
5. Sort `priority_issues` by `issue_id` ascending; sort code lists alphabetically

### Task Type E: First-Draft with Policy Checks — train_005

Combines term population (Type A) with policy compliance checks.

**Workflow:**
1. Follow Type A workflow for term population
2. For each policy area (escrow, cap, basket, NWC, non-compete, consents, HSR), compare draft values against policy rules:
   - `check_id` from the allowed enum
   - `rule_id` from the policy rule
   - `status`: WITHIN_POLICY if draft ≤ threshold; APPROVAL_REQUIRED if draft > threshold; OVERRIDE_APPLIED if client instructions explicitly override; ESCALATE_IF_CHANGED for conditional triggers
   - `approval_required`: boolean based on status
   - `approval_category`: from policy rule's `approval_category`
   - `measured_value`: string representation of the actual value with units
3. Populate `policy_summary`:
   - `approval_required_now`: true if any check requires approval
   - `current_policy_exception_count`: count of checks not WITHIN_POLICY
   - `required_approval_bodies`: unique approval categories needed
   - `conditional_escalation_triggers`: active triggers from policy rules
4. Populate `risk_memo_overrides`:
   - `source_doc_ids`: ACTIVE documents that support overrides (client email, regulatory memo, active cap table)
   - `override_codes`: from the allowed enum based on what is being overridden
   - `superseded_doc_ids`: STALE/TEMPLATE documents being superseded
   - `hsr_override_basis`: from `deal.schedules.regulatory_status.basis` narrative — map to the correct enum code

## Output Conventions

### Currency
- All USD amounts are **integers** (whole dollars, no cents, no commas, no `$` prefix)
- Compute: `percent_value / 100 * base_value` and round to nearest integer
- Example: `headline_value_usd: 184000000` NOT `"$184,000,000"`

### Percentages
- All percentages are **numbers** expressed as percentage points (not fractions)
- Precision: **two decimal places** (e.g., `10.00`, `0.75`, `2.50`)
- Example: 0.75% is `0.75`, NOT `0.0075`
- For "percent of headline value" calculations: `(amount / headline_value) * 100`

### Dates
- Format: `YYYY-MM-DD` strings
- Source from `deal.signing_date` and `deal.closing_deadline`
- Compute `deadline_days_after_signing` as calendar day difference between `closing_deadline` and `signing_date`

### Lists
- Material consents: sort by `contract_name` ascending
- Seller allocations: sort by `seller_name` ascending
- Employment employees: sort by displayed name ascending (alphabetically)
- Code lists: sort alphabetically
- Issue lists: sort by `issue_id` ascending

### Enums
- Always use **exact** enum values from the answer template — case-sensitive, underscore-separated
- If a value doesn't match any enum option, pick the closest match; never invent new enum values
- Structure enums: `STOCK_PURCHASE`, `ASSET_PURCHASE`, `MERGER`, `CARVE_OUT`, `ROLLOVER_STOCK_PURCHASE`
- Condition type enums: map narrative descriptions to `CLOSING`, `COVENANT`, `NOTICE`, `POST_CLOSING_NOTICE`

### Null handling
- Use `null` (JSON null) for numeric fields that are not applicable (e.g., `per_share_price_usd` when no share count)
- Use `[]` for empty lists
- Use `false` for boolean fields that are not applicable (NOT `null`)

## HSR (Hart-Scott-Rodino) Convention

HSR decisions are among the most nuanced parts of condition_self:

- `hsr_required` (boolean): From `deal.schedules.regulatory_status.hsr_required`
- `hsr_condition`:
  - `HSR_CLOSING_CONDITION` — if HSR filing is a condition to closing
  - `NO_HSR_CONDITION_COOPERATION_ONLY` — cooperation covenant but no closing condition
  - `NOT_ADDRESSED` — HSR language omitted
- `hsr_basis_code`:
  - `SIZE_OF_PERSON_TEST_NOT_MET` — "size-of-person test is not met"
  - `REPORTABLE_THRESHOLDS_MET` — "thresholds met" or "reportable"
  - `COUNSEL_MEMO_MISSING` — antitrust/counsel memo is missing
  - `NOT_APPLICABLE` — HSR not relevant

Map the regulatory `basis` narrative to the correct code. Key phrases:
- "size-of-person test is not met" → `SIZE_OF_PERSON_TEST_NOT_MET`
- "thresholds are not met after debt adjustments" → `SIZE_OF_PERSON_TEST_NOT_MET`
- "reportable" / "exceeds threshold" → `REPORTABLE_THRESHOLDS_MET`
- "memo missing" / "in progress" → `COUNSEL_MEMO_MISSING`

## Consent Condition Mapping

From `deal.schedules.material_contracts[]`:
- `condition_type: "closing"` + `consent_required: true` → Condition type = `CLOSING`
- `condition_type: "covenant"` + no consent → Condition type = `COVENANT`, consent_required = false
- `condition_type: "government notice"` → Condition type = `NOTICE`
- `condition_type: "post-closing notice"` → Condition type = `POST_CLOSING_NOTICE`
- `condition_type: "security approval"` + consent → treat as `CLOSING` or `NOTICE` based on context
- `condition_type: "TSA"` or `condition_type: "labor notice"` → these are operational items, NOT material consent conditions for closing

**consent_condition_status determination:**
- If ANY contract has `condition_type: "closing"` with `consent_required: true` → `MATERIAL_CONSENTS_AS_CLOSING_CONDITIONS`
- If only covenant/post-closing items → `MATERIAL_CONSENTS_AS_POST_CLOSING_COVENANTS`
- If contract list is empty → `NO_MATERIAL_CONSENTS_REQUIRED`

## Employment Agreement Convention

- `founder_employment_agreements_required`: true if `employment_terms.founder_employment` references specific named individuals and an agreement term
- `employment_agreement_term_months`: extract duration from employment_terms text (e.g., "Two-year" → 24, "three-year" → 36)
- `employment_employees`: list of named employees from `deal.parties.key_employees` that are tied to the employment agreements, sorted alphabetically
- The narrative in `employment_terms.founder_employment` names the specific individuals

## Non-Compete Convention

- `non_compete_duration_months`: extract from draft terms or employment terms
- `non_compete_scope`: determine from draft terms + client positions:
  - `TARGET_PRODUCTS_AND_CURRENT_TERRITORIES` — limited to specific products and geographies
  - `WORLDWIDE_ALL_AFFILIATES` — global and covers all affiliates
  - `NO_NON_COMPETE` — no non-compete provision
  - `OTHER_LIMITED_SCOPE` — some other limited scope
- `broad_affiliate_covenant_allowed`: true only if client positions explicitly allow affiliate-wide scope

## Benchmarks: When and How to Use

- Benchmarks are **supporting evidence**, not primary sources
- Filter by matching `topic` AND `industry` to the deal
- Prefer current-year (2026) benchmarks over older years
- Benchmarks with notes like "Older sample retained as distractor" or "Industry outside core peer set" should be deprioritized
- When quantifying exposure, use the most relevant benchmark's `median_percent` or `range_high` as reference
- If no matching industry benchmark exists, use a general market benchmark (e.g., `BM-ESCROW-MIDMARKET-2026`)

## Policy Rule Interpretation

Each policy rule provides:
- `preferred`: The ideal position
- `fallback_position`: Acceptable compromise
- `escalation_triggers`: Conditions that require escalation
- `threshold`: The numeric/qualitative boundary for escalation
- `approval_category`: Who must approve deviations

**When checking compliance:**
1. Is the draft value within the preferred range? → `WITHIN_POLICY`
2. Is it within the fallback but outside preferred? → `APPROVAL_REQUIRED` (by the approval category)
3. Does it trigger an escalation trigger? → Escalate
4. Has the client explicitly instructed an override? → `OVERRIDE_APPLIED`

## Common Pitfalls

1. **Using stale cap table data**: Always check `version_status`. The stale cap table exists as a distractor. The note "superseded by [later] cap table" means the active one controls.

2. **Using stale clause records**: Clauses with `version_status: "STALE"` and `source_doc_id` pointing to a TEMPLATE document are distractors. Their `draft_value` says "Generic template value retained in drafting system" — ignore these.

3. **Template provisions masquerading as instructions**: Documents with `version_status: "TEMPLATE"` and `doc_type: "template_provision"` contain generic language like "Includes generic 10% escrow, 5-year worldwide non-compete" — these are NOT the deal's actual terms.

4. **Wrong benchmark industry**: Using a benchmark from a different industry. Always match `benchmark.industry` to `deal.industry` when possible.

5. **Mixing up buyer vs seller thresholds**: Buyer playbook (P-BUYER-MIDMARKET-2026) and seller playbook (P-SELLER-APA-2026) have different thresholds. Check `deal.client_side`.

6. **Confusing condition_type enums**: `condition_type` in material contracts uses lowercase ("closing", "covenant"), but the output template uses uppercase ("CLOSING", "COVENANT", "NOTICE", "POST_CLOSING_NOTICE"). Always map to the output enum.

7. **Incorrect HSR basis mapping**: The narrative `basis` field contains prose. Map key phrases to the correct enum code.

8. **Forgetting to check the "deal.seller" field**: For single-seller deals (100% ownership), `deal.seller` is the seller group name. For multi-seller deals, aggregate or derive from `deal.parties.sellers`.

9. **NWC mechanic mapping**: The `working_capital.mechanic` field is prose. Map to enum:
   - "Dollar-for-dollar adjustment outside collar" → `DOLLAR_FOR_DOLLAR_OUTSIDE_COLLAR`
   - "Dollar-for-dollar from first dollar" → `DOLLAR_FOR_DOLLAR_FROM_FIRST_DOLLAR`
   - Explicit "no adjustment" → `NO_POST_CLOSING_ADJUSTMENT`

10. **Consideration total check**: `total_consideration` should equal `cash_at_close + seller_note + rollover_equity + earnout`, which should also equal `headline_value`.

11. **Employment employees sorting**: Sort by the full displayed name string alphabetically, not by role or last name.

12. **"All employees" vs "selected employees"**: When a draft says "all employees deemed transferred", the offer standard is mandatory/automatic. When it says "offers to 70%", that's a selective offer. Map to the correct enum.

## Math Formulas

- **Price per as-converted percent point**: `floor(headline_value / 100)` — integer dollars
- **Per-share price**: `equity_value / total_shares` rounded to 2 decimal places (only if share count available)
- **General escrow amount**: `headline_value * general_escrow_percent / 100` → integer
- **Tax escrow amount**: `headline_value * tax_escrow_percent / 100` → integer
- **Aggregate escrow**: `general_escrow_percent + tax_escrow_percent` (sum of percentages)
- **Basket amount**: `headline_value * basket_percent / 100` → integer
- **Indemnity cap amount**: `headline_value * indemnity_cap_percent / 100` → integer
- **NWC collar as % of equity**: `(collar_usd / equity_value) * 100` → 2 decimal places
- **Deadline days after signing**: calendar days between `signing_date` and `closing_deadline`
- **Seller gross proceeds**: `ownership_percent / 100 * headline_value` → integer (or use `estimated_proceeds` if directly provided)
- **Seller-specific consideration splits**: For each seller, `seller.cash_at_close = ownership_percent / 100 * total_cash_at_close` (pro-rata), similarly for note/rollover/earnout

## Quick Reference: Deal → Policy Mapping

| Policy ID | Client | Type | Key Thresholds |
|---|---|---|---|
| P-BUYER-MIDMARKET-2026 | Northstar Capital Partners | BUYER_RISK_MEMO | Escrow >12%, Tax escrow >3%, Cap >12.5%, Basket <0.5% or tipping, Non-compete >36mo or worldwide, NWC: escalate unverified target |
| P-SELLER-APA-2026 | Meridian Seller Desk / BrassWorks | SELLER_PLAYBOOK | Financing condition = executive, Escrow >10%, Cap >12.5%, Basket <0.75% or tipping, Non-compete: worldwide or affiliate-wide, Missing TSA = escalate, WARN retained = escalate |
| P-PUBLIC-MERGER-COMMITTEE-2026 | Helios Health Systems | COMMITTEE | RTF >5.5%, Blocked fiduciary out, Post-closing R&W survival, Restricted MAE carve-outs |
| P-CARVEOUT-OPS-2026 | Atlas Industrial Holdings | SELLER_OPS | TSA <6 months, WARN retained, Broad IP access, 5-year non-compete, Closing <60 days |
| P-HYBRID-INVEST-2026 | — | HYBRID | Used for rollover/earnout-heavy deals |
| P-ROLLOVER-SPA-2026 | — | ROLLOVER | Used for rollover stock purchases |
| P-STANDARD-FORM-2026 | — | TEMPLATE | Generic template; NOT a client instruction |

## Final Validation Checklist

Before submitting any output JSON:
- [ ] All dollar amounts are integers (no decimals, no commas, no `$`)
- [ ] All percentages are numbers with at most 2 decimal places
- [ ] All enum values match the template exactly (case-sensitive)
- [ ] All lists are sorted per the ordering rules in the template
- [ ] Only ACTIVE sources contribute values; STALE/TEMPLATE are excluded
- [ ] `deal_id` matches the requested deal
- [ ] `structure` matches the deal record (not assumed from task description)
- [ ] HSR basis is mapped from the regulatory `basis` prose, not guessed
- [ ] If no share count exists, `per_share_price_usd` is `null` and basis is `NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE`
- [ ] Consent condition status is consistent with the material contracts list
- [ ] No narrative prose outside JSON — output is pure JSON
