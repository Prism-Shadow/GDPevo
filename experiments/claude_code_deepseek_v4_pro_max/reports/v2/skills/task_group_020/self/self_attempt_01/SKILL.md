# Aster Legal Deal Desk — Task Execution Skill

## Environment

| Setting | Value |
|---|---|
| Base URL | `http://34.46.77.124:9020` |
| System | Aster Legal Deal Desk |
| Seed | 20020 |

The environment serves HTML pages and JSON APIs. Always prefer the API endpoints for structured data extraction. The HTML pages mirror the same data and are useful for quick browsing.

### API Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/health` | Status, counts, seed |
| `GET /api/deals` | List of all deal IDs |
| `GET /api/deals/{DEAL_ID}` | Full deal payload: `deal`, `clauses`, `documents`, `policy`, `benchmarks` |
| `GET /api/policies` | All policies with full rule sets |
| `GET /api/benchmarks` | All benchmarks |
| `GET /api/documents/{DOC_ID}` | Individual document detail |

### Web Pages (HTML)

| Path | Purpose |
|---|---|
| `GET /` | Home — deal index, search bar |
| `GET /deals/{DEAL_ID}` | Deal detail page with raw JSON blocks |
| `GET /policies` | Policy listing |
| `GET /benchmarks` | Benchmark listing |
| `GET /clauses/compare?deal_id={DEAL_ID}` | Clause comparison view |

---

## Data Model

### Deal Object (`/api/deals/{ID}` → `.deal`)

Core fields: `deal_id`, `codename`, `client`, `client_side` (BUYER/SELLER), `structure` (STOCK_PURCHASE/ASSET_PURCHASE/MERGER/CARVE_OUT/ROLLOVER_STOCK_PURCHASE), `headline_value`, `equity_value`, `signing_date`, `closing_deadline`, `target`, `buyer`, `seller`, `policy_id`, `industry`, `status`.

**Economics**: `consideration_mix` (cash_at_close, seller_note, rollover_equity, earnout), `escrows` (general_amount/percent, tax_amount/percent), `basket` (percent, type, de_minimis), `indemnity_cap_percent`, `survival_periods` (general_reps_months, fundamental_reps_months, tax_reps_months, plus buyer_covenants_months and seller_reps_months on APA deals), `working_capital` (target, collar, mechanic), `break_fee_percent`, `reverse_termination_fee_percent`.

**Parties**: `buyers[]`, `sellers[]` (name, ownership_percent, role, estimated_proceeds), `key_employees[]`, `committee_members[]`, `representatives[]`.

**Schedules**: `cap_table` (as_of, source_doc_id, status, sellers), `material_contracts[]` (name, annual_revenue, condition_type, consent_required), `regulatory_status` (hsr_required, basis, other_approvals), `employment_terms`, `ip_transition` (required, note), `transition_services` (required, needed_services, duration fields), `stale_cap_table`.

**Draft terms**: Narrative summary of current draft positions (string fields like `consents`, `escrow`, `hsr`, `non_compete`, `nwc`, `financing_condition`, `employee_transfer`, etc.).

**Client positions**: `preferred` (negotiation posture), `fallback` (fallback authority), `escalation` (escalation triggers).

**Negotiation context**: `batna`, `ownership_dynamics`, `rationale`, `strategic_notes`.

**Document references**: `active_documents[]`, `stale_documents[]`, `record_links` (maps logical role → doc ID).

### Clauses Object (`/api/deals/{ID}` → `.clauses`)

Each clause: `clause_id`, `clause_code`, `topic`, `draft_value`, `playbook_value`, `policy_threshold`, `risk_hint`, `version_status` (ACTIVE/STALE), `source_doc_id`, `calculation_base`.

**Critical**: Only ACTIVE clauses represent the current deal state. STALE clauses (CL-*-S01, CL-*-S02) are distractors — they reference template documents and carry generic values. Never use STALE clause values for answers.

### Documents Object (`/api/deals/{ID}` → `.documents`)

Each document: `doc_id`, `doc_type`, `title`, `version_status` (ACTIVE/STALE/TEMPLATE), `effective_date`, `sections[]` (heading + text), `related_ids[]`.

Standard active documents per deal:
- `DOC-{DEALCODE}-TERM-01` — term_sheet
- `DOC-{DEALCODE}-DRAFT-02` — draft_agreement
- `DOC-{DEALCODE}-EMAIL-03` — email (latest client instruction)
- `DOC-{DEALCODE}-CAP-ACTIVE` — active cap_table
- `DOC-{DEALCODE}-FIN-04` — financial_schedule
- `DOC-{DEALCODE}-MATCON-05` — material_contracts
- `DOC-{DEALCODE}-DISC-06` — disclosure_schedule
- `DOC-{DEALCODE}-COMMITTEE-07` — committee_charter (merger/carve-out deals)

Standard stale/template documents:
- `DOC-{DEALCODE}-CAP-STALE` — stale cap_table (STALE)
- `DOC-{DEALCODE}-TEMPLATE-99` — template_provision (TEMPLATE)

### Policy Object (`/api/deals/{ID}` → `.policy`)

Policy: `policy_id`, `policy_type`, `client`, `title`, `version`, `effective_date`, `rules[]`.

Each rule: `rule_id`, `topic`, `preferred`, `fallback_position`, `threshold`, `escalation_triggers[]`, `approval_category`, `basis` ("Applies to active drafts and latest written client instructions.").

### Benchmarks (`/api/deals/{ID}` → `.benchmarks`)

Each benchmark: `benchmark_id`, `topic`, `industry`, `definition`, `mean_percent`, `median_percent`, `range_low`, `range_high`, `sample_size`, `count_above_threshold`, `year`, `notes`.

**Distractor filtering**: Benchmarks with industry/topic mismatched to the deal, or from years far from 2026, or with notes like "Older sample retained as distractor" / "Industry outside core peer set" / "Definition differs from client playbook threshold" — are distractors. Prefer benchmarks matching the deal's industry and topic, from the most recent year.

---

## Source Precedence Rules

This is the single most important section. The environment is rich with conflicting sources. Apply in order:

### Rule 1: Document Status
**ACTIVE > STALE > TEMPLATE**. A document, clause, or cap table marked STALE or TEMPLATE is a distractor. Template documents (`DOC-*-TEMPLATE-99`) contain generic language (e.g., "5-year worldwide non-compete," "generic 10% escrow") that explicitly does NOT reflect client instructions.

### Rule 2: Client Instructions Trump Templates
The **client instruction email** (`DOC-*-EMAIL-03`) and **draft agreement** (`DOC-*-DRAFT-02`) sections labeled "Instruction summary," "Fallbacks," and "Escalations" are authoritative. When they conflict with template provisions or stale cap tables, follow the email/draft.

### Rule 3: Active Cap Table Over Stale Cap Table
Always use the **active cap table** (`DOC-*-CAP-ACTIVE`) for seller names, ownership percentages, roles, and allocation basis. The stale cap table (`DOC-*-CAP-STALE`) is an earlier snapshot superseded by the active one.

### Rule 4: Policy Rules Are Guardrails, Not Replacements
Policy rules set thresholds and escalation triggers. They don't override deal-specific economics or client instructions. Use them to flag deviations and populate policy check fields, but deal-level data (economics, parties, schedules) controls numeric values.

### Rule 5: Active Clauses Only
When using clause comparison data, filter to `version_status: "ACTIVE"`. Clauses from STALE sources (suffix `-S01`, `-S02`) reference template documents and contain generic/incorrect values.

### Rule 6: Deal Economics Are Ground Truth
The `.deal.economics` object contains the authoritative numbers. Calculate derived values (escrow amounts, per-share price) from these. Don't use benchmark percentages as deal values — benchmarks inform policy checks, not deal terms.

---

## Numeric Conventions

| Type | Convention | Example |
|---|---|---|
| Currency (USD) | Integer, no commas or symbols | `184000000` |
| Percentages | Number, two decimal places, as percentage points | `10.00` (not 0.10) |
| Months | Integer | `18` |
| Dates | `YYYY-MM-DD` string | `2026-08-14` |
| Per-share price | Number with two decimals, or `null` if no share count | `4.16` or `null` |
| Null vs Zero | `null` = not applicable; `0` = explicitly zero | Escrow in public merger: `0`, not `null` |

### Percentage Calculations
- General escrow amount = headline_value × general_escrow_percent / 100
- Tax escrow amount = headline_value × tax_escrow_percent / 100
- Aggregate escrow = general_escrow_percent + tax_escrow_percent
- NWC collar percent of EV = (collar / equity_value) × 100
- Basket amount = headline_value × basket_percent / 100
- Indemnity cap amount = headline_value × indemnity_cap_percent / 100
- Per-share price (if share count available) = equity_value / shares_outstanding
- Price per percent point = equity_value / 100

### Seller Allocation Calculations
- Each seller's gross proceeds (pro-rata): headline_value × ownership_percent / 100, then decompose into consideration mix components by the same proportion
- Cash at close allocation = cash_at_close × ownership_percent / 100
- Seller note allocation = seller_note × ownership_percent / 100
- Rollover equity allocation = rollover_equity × ownership_percent / 100
- Earnout allocation = earnout × ownership_percent / 100
- Total proceeds = sum of all allocation components for that seller
- Verify: sum of all sellers' total proceeds ≈ headline_value (within rounding)

---

## Task-Type Workflows

### Type A: Term Population / First Draft (train_001, train_005)

**Goal**: Populate a structured JSON of deal terms from the deal record.

**Process**:
1. Fetch `/api/deals/{DEAL_ID}`
2. Extract from `.deal`: deal_id, structure, target, buyer, seller, signing_date, closing_deadline, headline_value, equity_value
3. Extract from `.deal.economics`: consideration_mix, escrows, basket, indemnity_cap_percent, survival_periods, working_capital
4. Extract from `.deal.schedules.cap_table`: source_doc_id, as_of date, sellers list for allocations
5. Compute seller allocations from cap table sellers × consideration mix (pro-rata by ownership_percent)
6. Extract from `.deal.schedules.material_contracts`: consent items, condition types
7. Extract from `.deal.schedules.regulatory_status`: HSR status, other approvals
8. Extract from `.deal.schedules.employment_terms`: non-compete, founder employment
9. Extract from `.deal.schedules.ip_transition`: IP assignment requirements
10. Extract from `.deal.schedules.transition_services`: TSA requirements
11. Match policy rules to populate policy checks — compare draft values against policy thresholds
12. Identify risk memo overrides from client instructions (e.g., HSR memo analysis, active cap table selection)

**Key fields requiring computation**:
- `per_share_price_usd`: equity_value / shares_outstanding; use `null` if no share count in active cap table
- `per_share_price_basis`: `CALCULATED_FROM_ACTIVE_CAP_TABLE` or `NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE`
- `price_per_as_converted_percent_point_usd`: equity_value / 100, rounded to whole dollars
- `general_escrow_policy_status`: Compare escrow % against policy thresholds → WITHIN_POLICY / ESCALATE / NOT_APPLICABLE
- `tax_escrow_policy_status`: Same logic for tax escrow
- `nwc_collar_percent_of_equity_value`: (collar / equity_value) × 100

### Type B: Counterparty Paper Review (train_002)

**Goal**: Compare active counterparty draft against client playbook and client instructions; produce an issue register.

**Process**:
1. Fetch `/api/deals/{DEAL_ID}`
2. Identify the **client side** from `.deal.client_side` — this determines which playbook rules apply
3. Read the active draft terms from `.deal.draft_terms` — this is the counterparty's draft
4. Read client instructions from `.deal.client_positions` (preferred, fallback, escalation)
5. Read the policy rules from `.policy.rules[]`
6. For each topic area, compare:
   - **Draft value** (counterparty position) vs **Playbook value** (client's preferred position)
   - Check if draft value exceeds policy escalation thresholds
   - Cross-reference with client email instructions for specific fallbacks
7. For each material issue found:
   - Assign an issue_id from the template's allowed_values
   - Determine severity based on deviation magnitude and policy threshold breach
   - Set recommended_action (REVISE, DELETE, ADD, ESCALATE, ACCEPT)
   - Populate corrected_value with the normalized numeric fields
   - List source_ids for audit trail (doc IDs, policy rule IDs, clause IDs)

**Severity guidelines**:
- CRITICAL: Financing condition present (seller), escrow >50% above policy max, missing required TSA
- HIGH: Escrow > policy threshold, cap > policy threshold, worldwide/affiliate-wide non-compete, missing IP transition
- MEDIUM: Tipping basket, de minimis omitted, 5-year non-compete, employee transfer issues
- LOW: Minor percentage deviations within fallback range

**Corrected value field selection**: Only include fields relevant to the specific issue. Use `null` for inapplicable fields. Currency amounts as integers. Percentages as two-decimal numbers.

### Type C: Committee Escalation Analysis (train_003)

**Goal**: Identify draft terms needing committee-level escalation, quantify exposure, summarize risk posture.

**Process**:
1. Fetch `/api/deals/{DEAL_ID}`
2. Extract the deal structure — public mergers have different risk profiles than private deals
3. Read `.deal.draft_terms` and `.deal.economics` for draft values
4. Read the committee policy (P-PUBLIC-MERGER-COMMITTEE-2026) rules
5. Read `.deal.negotiation_context` for BATNA, ownership, strategic rationale
6. For each relevant term_id, compare draft values against policy thresholds:
   - RTF: draft_percent vs policy_threshold_percent
   - FIDUCIARY_OUT: Is termination right blocked?
   - MAE_CARVEOUTS: Which carve-outs are omitted from the draft?
   - RW_SURVIVAL: Is there post-closing survival?
   - REGULATORY_COVENANT: Is the covenant weak?
   - BREAK_FEE: Within policy range?
7. Populate quantification for each escalated term
8. Compute aggregate_risk:
   - Sum quantified exposures and policy excesses
   - Determine final_action and risk_tier
   - Populate strategic_context from negotiation_context
9. List committee_members from `.deal.parties.committee_members`

**Exposure basis mapping**:
- `EQUITY_VALUE`: Draft amount tied to equity value (RTF, break fee)
- `FULL_EQUITY_VALUE_UNCAPPED`: Uncapped exposure (post-closing R&W survival)
- `NON_QUANTIFIED_LEGAL_RISK`: MAE carve-out gaps, regulatory covenant weakness
- `POLICY_THRESHOLD_EXCESS`: Deviation above policy threshold
- `NONE`: No quantifiable financial exposure

**MAE carve-out codes**: The full set is ANNOUNCEMENT_EFFECTS, CYBER_INCIDENT, CUSTOMER_LOSS, INDUSTRY, LAW_CHANGE, MARKET, PANDEMIC, RATES, WAR. Omitted carve-outs are those NOT present in the draft but required by policy.

**Benchmark selection**: Use benchmarks matching the deal's industry and topic, from 2026. Older benchmarks with mismatched industries or "distractor" notes should not be used as primary evidence.

### Type D: Transition-Term Issue Package (train_004)

**Goal**: Priority deviations + structured transition flags for carve-out/seller APA.

**Process**:
1. Fetch `/api/deals/{DEAL_ID}`
2. Identify priority issues by comparing draft values against playbook and policy thresholds
3. Each issue maps to an issue_id and clause_code pairing
4. For each issue: assign severity, recommended_action, approval_owner, source_doc_ids
5. Populate transition_flags with five sub-objects:

**Employee Transfer**:
- `draft_offer_percent`: From disclosure schedule (e.g., 70.0 meaning 70% of employees)
- `seller_warn_or_severance_retained`: true if seller keeps WARN risk
- `required_offer_standard`: Policy-preferred standard
- `issue_present` & `approval_required` based on comparison

**TSA Service Continuity**:
- `draft_duration_months`: From disclosure schedule or draft terms
- `target_duration_months`: Policy preferred (e.g., 12)
- `fallback_duration_months`: Policy fallback (e.g., 9)
- `required_service_codes`: Services listed in disclosure schedule as needed (ERP, IT, PAYROLL, etc.) — sorted alphabetically
- `issue_present` if draft < target or services omitted

**Restrictive Covenants**:
- `draft_non_compete_years` vs `max_non_compete_years`
- `affiliate_scope_allowed`: false if policy prohibits
- `required_scope`: Policy-preferred scope
- `non_solicit_scope`: Policy-preferred non-solicit

**IP Transition**:
- `draft_trademark_phaseout_months` vs `max_trademark_phaseout_months`
- `broad_design_file_access`: true if draft allows source/design access
- `required_scope`: Policy-preferred IP transition terms

**Escrow and Deadline**:
- `general_escrow_percent` and `general_escrow_amount_usd` from economics
- `target_max_escrow_percent`: Policy threshold
- `signing_date` and `draft_closing_deadline`: From deal
- `deadline_days_after_signing`: Calendar days from signing to closing deadline
- `minimum_deadline_days`: Policy minimum (e.g., 60)
- `deadline_escalation_required`: true if days < minimum

**Priority issues ordering**: Sort by `issue_id` ascending. Source doc IDs sorted ascending within each issue.

### Type E: First Draft + Policy Check (train_005)

**Goal**: Full first-draft term population with policy compliance checks.

**Process**:
1. Fetch `/api/deals/{DEAL_ID}`
2. Populate `draft_terms` from deal record:
   - Structure, buyer, seller, target, client_side
   - headline_value_usd, equity_value_usd
   - signing_date, closing_deadline
   - allocation_source_doc_id from active cap table
   - consideration_mix_usd with total_consideration = sum of components
   - seller_allocations computed pro-rata from active cap table
   - indemnity fields from economics
   - working_capital from economics
   - closing_conditions from material contracts + regulatory status
   - drafting_positions derived from draft terms + policy
3. Run `policy_checks` against the applicable policy:
   - One check per relevant policy rule topic
   - `measured_value`: Normalized string (e.g., "10.00%", "$18,400,000", "deductible")
   - `status`: Compare measured value against policy thresholds
   - `approval_required`: true if status is APPROVAL_REQUIRED or ESCALATE_IF_CHANGED
4. Populate `policy_summary`:
   - approval_required_now, current_policy_exception_count
   - required_approval_bodies from rules with approval_required
   - conditional_escalation_triggers for terms that could escalate if changed
5. Populate `risk_memo_overrides`:
   - Active client instructions superseding template
   - HSR override basis from regulatory status memo
   - Active cap table over stale export

---

## Common Pitfalls

1. **Using STALE clauses**: CL-*-S01 and CL-*-S02 clauses are stale distractors. Filter to ACTIVE only.
2. **Using template documents as authority**: DOC-*-TEMPLATE-99 contains generic language explicitly disclaimed as conflicting with client policy.
3. **Using stale cap table**: DOC-*-CAP-STALE is superseded by DOC-*-CAP-ACTIVE. Use the active one for allocations.
4. **Industry-mismatched benchmarks**: A FinTech escrow benchmark doesn't apply to an Industrial Software deal. Match industry + topic + recent year.
5. **Confusing percent-as-fraction with percent-as-points**: 10% escrow = `10.00` in the JSON, not `0.10`.
6. **Rounding errors in allocation sums**: Verify that sum of seller total_proceeds equals headline_value (within $1-2 of integer rounding).
7. **Null vs zero**: Public mergers have `0` escrow (explicitly none), not `null` (not applicable). NWC may be `null` for mergers.
8. **Missing HSR nuance**: "No HSR condition" doesn't mean "ignore HSR" — it means include a cooperation covenant. The regulatory_status.basis explains why.
9. **Non-compete scope interpretation**: "Target products and current territories" maps to TARGET_PRODUCTS_AND_CURRENT_TERRITORIES. "Worldwide all affiliates" maps to WORLDWIDE_ALL_AFFILIATES.
10. **Consent condition_type mapping**: "closing" → CLOSING, "covenant" → COVENANT, "notice" → NOTICE, "post-closing notice" → POST_CLOSING_NOTICE, "government notice" → NOTICE.
11. **NWC mechanic mapping**: "Dollar-for-dollar adjustment outside collar" → DOLLAR_FOR_DOLLAR_OUTSIDE_COLLAR. "Dollar-for-dollar from first dollar" → DOLLAR_FOR_DOLLAR_FROM_FIRST_DOLLAR. "No post-closing adjustment" → NO_POST_CLOSING_ADJUSTMENT.
12. **Basket type mapping**: Lowercase from economics ("deductible", "tipping") → uppercase enum (DEDUCTIBLE, TIPPING, NONE).

---

## Enum and Controlled Value Reference

### Deal Structures
STOCK_PURCHASE | ASSET_PURCHASE | MERGER | CARVE_OUT | ROLLOVER_STOCK_PURCHASE

### Client Side
BUYER | SELLER

### Basket Types
DEDUCTIBLE | TIPPING | NONE

### NWC Mechanics
DOLLAR_FOR_DOLLAR_OUTSIDE_COLLAR | DOLLAR_FOR_DOLLAR_FROM_FIRST_DOLLAR | NO_POST_CLOSING_ADJUSTMENT | TRUE_UP_AGAINST_ACTIVE_BALANCE_SHEET | SELLER_BUDGET_BASELINE | NONE

### Consent Condition Types
CLOSING | COVENANT | NOTICE | POST_CLOSING_NOTICE

### HSR Status
REQUIRED | NOT_REQUIRED | UNCLEAR

### HSR Clause Position
FILING_CONDITION | COOPERATION_COVENANT_ONLY | OMIT_HSR_LANGUAGE

### HSR Condition
HSR_CLOSING_CONDITION | NO_HSR_CONDITION_COOPERATION_ONLY | NOT_ADDRESSED

### HSR Basis Codes
SIZE_OF_PERSON_TEST_NOT_MET | REPORTABLE_THRESHOLDS_MET | COUNSEL_MEMO_MISSING | NOT_APPLICABLE

### Policy Status
WITHIN_POLICY | APPROVAL_REQUIRED | OVERRIDE_APPLIED | ESCALATE_IF_CHANGED

### Approval Categories
DEAL_LEAD | EMPLOYMENT_COUNSEL | FINANCE_COMMITTEE | LEGAL_RISK_COMMITTEE | REGULATORY_COUNSEL | EXECUTIVE_COMMITTEE | SELLER_STEERING_COMMITTEE | HR_COMMITTEE | OPERATIONS_COMMITTEE | IP_COUNSEL | BOARD_TRANSACTION_COMMITTEE | CLIENT_BUSINESS_LEAD

### Severity
CRITICAL | HIGH | MEDIUM | LOW

### Risk Tier
LOW | MEDIUM | HIGH | CRITICAL

### Non-Compete Scope (Buyer SPA)
TARGET_PRODUCTS_AND_CURRENT_TERRITORIES | WORLDWIDE_ALL_AFFILIATES | NO_NON_COMPETE | OTHER_LIMITED_SCOPE

### Non-Compete Scope (Carve-out)
DIVESTED_LINE_EXISTING_GEOGRAPHIES | DIVESTED_LINE_WORLDWIDE | ALL_INDUSTRIAL_HAND_TOOLS | NO_RESTRICTIVE_COVENANT

### IP Transition Scope
NARROW_TRANSITIONAL_LICENSE_WITH_RETAINED_IP_BOUNDARIES | BROAD_DESIGN_FILE_ACCESS | OPEN_ENDED_TRADEMARK_USE | NO_IP_TRANSITION_RIGHTS

### Escrow Policy Status
WITHIN_POLICY | ESCALATE | NOT_APPLICABLE

### Per Share Price Basis
CALCULATED_FROM_ACTIVE_CAP_TABLE | NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE

### Consent Condition Status
MATERIAL_CONSENTS_AS_CLOSING_CONDITIONS | MATERIAL_CONSENTS_AS_POST_CLOSING_COVENANTS | NO_MATERIAL_CONSENTS_REQUIRED

### Drafting Positions (Form)
BUYER_FORM | SELLER_FORM | COMMITTEE_FORM | STANDARD_FORM

### Drafting Positions (Consideration Schedule)
ACTIVE_CAP_TABLE_PRORATA_ALLOCATION | ACTIVE_ALLOCATION_SCHEDULE | STALE_CAP_TABLE | COUNTERPARTY_DRAFT

### Drafting Positions (Escrow/Cap)
CAP_EQUALS_GENERAL_ESCROW | CAP_ABOVE_ESCROW | CAP_BELOW_ESCROW | NO_CAP

### Earnout Position
OBJECTIVE_REVENUE_BASED_FALLBACK | OPERATING_COVENANT_REQUIRED | NO_EARNOUT

### TSA Position
NO_GENERAL_TSA_LIMITED_CUSTOMER_NOTICE_SUPPORT | FULL_TSA_REQUIRED | TSA_STATUS_UNCLEAR

### IP Transition Position
REQUIRE_OPEN_SOURCE_AUDIT_AND_FEDRAMP_ASSIGNMENT | NO_IP_TRANSITION | TRADEMARK_PHASE_OUT_ONLY

### TSA Service Codes
ERP | FINANCE | IT | PAYROLL | PROCUREMENT | QUALITY_RECORDS | REGULATORY

### Employee Offer Standards
BUYER_COMPARABLE_OFFERS_ALL_BUSINESS_EMPLOYEES | BUYER_OFFERS_SELECTED_CRITICAL_EMPLOYEES | NO_EMPLOYEE_COVENANT_REQUIRED | SELLER_RETAINS_EXCLUDED_EMPLOYEES_ONLY

---

## Output Rules (All Task Types)

1. Return **only** the JSON object — no markdown fences, no prose, no explanatory text.
2. Match the answer template's structure exactly: top-level keys, field names, enum values, ordering rules.
3. Sort list fields as specified (alphabetically by name, by ID, or by code).
4. Include every field from the template, using `null` or `[]` for inapplicable/empty values.
5. Follow numeric conventions: integer dollars, two-decimal percentages as points, integer months.
6. Omit fields that are not in the template — do not invent additional keys.
7. Verify arithmetic: allocation totals should sum to headline_value; escrow amounts = headline × percent / 100.
