# Aster Legal Deal Desk — Deal Term Population, Review, and Escalation Skill

## Purpose

This skill covers preparing structured JSON outputs for the Aster Legal Deal Desk platform across
buyer-side and seller-side M&A transactions. It supports five task types:

1. **Term population** — first-draft SPA/APA term sheets from deal records and cap tables.
2. **Counterparty paper review** — issue registers comparing counterparty drafts against client
   instructions and playbooks.
3. **Committee escalation analysis** — structured escalation packets with quantified exposure.
4. **Transition-term issue packages** — priority deviations and structured transition flags for
   carve-out or divestiture deals.
5. **Policy-check bundles** — policy-rule checks, summary, and risk-memo overrides accompanying a
   first-draft term population.

## Environment

| Variable / Setting        | Value                         |
|---------------------------|-------------------------------|
| Remote base URL           | `http://34.46.77.124:9020`    |
| Placeholder in prompts    | `<TASK_ENV_BASE_URL>`         |
| Local env note            | **Never** use localhost, `127.0.0.1`, `env/` sources, or `env/setup.sh` unless the remote URL itself explicitly redirects there. `environment_access.md` overrides any local-URL reference in a task prompt. |

The Aster Legal Deal Desk exposes web pages and API surfaces. Key data surfaces per deal:

- **Deal profile** — structure, parties, headline value, signing/closing dates, client side.
- **Deal documents** — draft agreements, term sheets, financial schedules, disclosure schedules,
  material-contract logs, client instruction emails.
- **Clause comparison / clause records** — individual clause snapshots with IDs.
- **Playbooks & policies** — seller-APA, buyer-midmarket, carve-out ops, public-company policies.
- **Benchmarks** — industry-specific market studies (RTF, fiduciary-out, MAE, etc.).
- **Cap tables** — active and stale allocation schedules with seller names, roles, ownership
  percentages, and (sometimes) share counts.

## Document-ID and Artifact Naming Conventions

Learn these patterns from the deal room; they are used across all task types.

| Artifact                  | Pattern                                    | Example                                |
|---------------------------|--------------------------------------------|----------------------------------------|
| Deal ID                   | `D-{CODE}-{NUM}`                           | `D-ALDER-447`                          |
| Deal document             | `DOC-{DEALCODE}{NUM}-{DOCTYPE}-{SEQ}`      | `DOC-BRASS219-DRAFT-02`                |
| Clause record             | `CL-{DEALCODE}-{NUM}-{SEQ}`                | `CL-BRASS-219-001`                     |
| Policy / playbook         | `P-{TYPE}-{YEAR}` or `P-{TYPE}`            | `P-SELLER-APA-2026`, `P-CARVEOUT-OPS-2026` |
| Policy rule               | Short code, e.g. `BUY-MID-BASKET`          | `BUY-MID-BASKET`, `PUB-FIDUCIARY`      |
| Benchmark                 | `BM-{TOPIC}-{INDUSTRY}-{YEAR}-{SEQ}`       | `BM-RTF-HEALTHTECH-2026`               |
| Cap table (active)        | `DOC-{DEALCODE}{NUM}-CAP-ACTIVE`           | `DOC-HARBOR562-CAP-ACTIVE`             |
| Cap table (stale)         | `DOC-{DEALCODE}{NUM}-CAP-STALE`            | `DOC-HARBOR562-CAP-STALE`              |
| Template / stale doc      | `DOC-{DEALCODE}{NUM}-TEMPLATE-{SEQ}`       | `DOC-HARBOR562-TEMPLATE-99`            |

**Document-type codes** found in document IDs:

| Code       | Meaning                      | Precedence |
|------------|------------------------------|------------|
| `EMAIL`    | Client instruction email     | Highest    |
| `DRAFT`    | Current deal draft           | High       |
| `FIN`      | Financial document/schedule  | High       |
| `DISC`     | Disclosure schedule          | Medium     |
| `MATCON`   | Material-contract log        | Medium     |
| `TERM`     | Term sheet                   | Medium     |
| `CL-*`     | Clause record                | Medium     |
| `P-*`      | Policy / playbook            | Reference  |
| `BM-*`     | Benchmark study              | Reference  |
| `TEMPLATE` | Stale / template material    | Lowest     |

## Source Precedence (Hierarchy)

When resolving conflicts between sources, apply this order (highest wins):

1. **Active written client instructions** — `EMAIL` documents, current instruction memos.
2. **Current deal draft** — `DRAFT` documents.
3. **Financial schedules** — `FIN` documents.
4. **Disclosure schedules** — `DISC` documents.
5. **Material-contract logs** — `MATCON` documents.
6. **Term sheets** — `TERM` documents.
7. **Clause records** — `CL-*` identifiers.
8. **Deal-specific policy / playbook** — `P-*` identifiers.
9. **Benchmarks** — `BM-*` identifiers.
10. **Stale / template material** — `TEMPLATE`, `CAP-STALE` — superseded when a newer source exists.

### Key precedence rules

- **Active cap table over stale export.** If both `CAP-ACTIVE` and `CAP-STALE` exist, use
  `CAP-ACTIVE` for allocations, share counts, and seller rosters. List `CAP-STALE` in
  `superseded_doc_ids` when an override is recorded.
- **Client instructions supersede template.** When an `EMAIL` doc contains a written instruction
  that contradicts a template or playbook default, the instruction controls. Record the override
  with code `ACTIVE_CLIENT_INSTRUCTIONS_SUPERSEDE_TEMPLATE`.
- **Clause records are deal-specific, not general.** A `CL-{DEALCODE}-*` record reflects the
  current draft language for that deal; do not assume it represents market or policy unless
  cross-referenced.
- **Policy is the fallback, not the override.** Policy/playbook defaults apply only when no
  higher-precedence source addresses the term.

## Output Conventions (Universal)

Every task output is a **single JSON object with no surrounding markdown, prose, or commentary.**

### Numeric conventions

| Type              | Format                                                    | Example          |
|-------------------|-----------------------------------------------------------|------------------|
| Currency (USD)    | Integer, no commas, no `$`, no decimals                   | `184000000`      |
| Percentage        | Number, 2 decimal places (1 if template says precision 1), expressed as percentage points **not fractions** | `10.0`, `0.75`, `7.5` |
| Months / years    | Integer                                                   | `24`, `3`        |
| Calendar days     | Integer                                                   | `42`, `75`       |
| Not applicable    | `null` (never `0` for a field that genuinely doesn't apply) | `null`           |

### Structural conventions

| Element           | Rule                                                      |
|-------------------|-----------------------------------------------------------|
| Empty lists       | `[]`, never `null`                                        |
| Booleans          | `true` / `false`, never `"yes"` / `"no"`                  |
| Dates             | `YYYY-MM-DD` strings                                      |
| Strings           | Exact values as found in deal records; preserve casing    |
| Enums             | UPPER_SNAKE_CASE exactly as defined in the template       |

### List ordering (apply unless a template explicitly says otherwise)

| List                              | Sort key                | Direction  |
|-----------------------------------|-------------------------|------------|
| `seller_allocations`              | `seller_name` or `seller_id` | ascending  |
| `issues` / `priority_issues`      | `issue_id`              | ascending  |
| `escalation_terms`                | `term_id`               | ascending  |
| `required_material_consents`      | `contract_name`         | ascending  |
| `employment_employees`            | displayed name          | ascending  |
| `source_ids` / `source_doc_ids`   | doc ID string           | ascending  |
| `required_service_codes`          | code string             | ascending  |
| `mae_omitted_carveouts`           | carveout code           | ascending  |
| `committee_members`               | as shown in record      | as-is      |
| `other_regulatory_approvals`      | approval name           | ascending  |
| Code lists in `corrected_value`   | code string             | ascending  |
| `override_codes`                  | code string             | ascending  |
| `superseded_doc_ids`              | doc ID string           | ascending  |
| `conditional_escalation_triggers` | trigger code            | ascending  |
| `primary_driver_term_ids`         | `term_id`               | ascending  |
| `required_approval_bodies`        | category enum           | ascending  |
| `policy_checks`                   | `check_id`              | ascending  |

## Core Math / Calculation Rules

These formulas derive values that may not be directly stored in the deal record. Apply them when
the template requires a field that can be calculated.

### Deal-level

```
headline_purchase_price_usd = equity_value_usd  (stock purchase, no debt adjustment)
equity_value_usd = cash_at_close_usd + rollover_equity_usd + seller_note_usd + earnout_usd
total_consideration = headline_value_usd = equity_value_usd  (typically)
```

### Escrow and cap

```
general_escrow_usd       = round(headline_purchase_price_usd × general_escrow_percent / 100)
tax_escrow_usd            = round(headline_purchase_price_usd × tax_escrow_percent / 100)
aggregate_escrow_percent  = general_escrow_percent + tax_escrow_percent
aggregate_escrow_amount_usd = general_escrow_usd + tax_escrow_usd
indemnity_cap_amount_usd  = round(headline_purchase_price_usd × indemnity_cap_percent / 100)
basket_amount_usd         = round(headline_purchase_price_usd × basket_percent / 100)
escrow_amount_usd         = round(headline_value × escrow_percent / 100)
```

### Per-share / per-percent-point

```
price_per_as_converted_percent_point_usd = round(equity_value_usd / 100)
per_share_price_usd = round(equity_value_usd / total_fully_diluted_shares, 2)
  → null if the active cap table does not provide a share count
```

### NWC

```
nwc_collar_percent_of_equity_value = round((nwc_collar_usd / equity_value_usd) × 100, 2)
```

### Seller allocations (pro-rata)

```
gross_proceeds_usd        = round(ownership_percent / 100 × equity_value_usd)
total_proceeds_usd        = cash_at_close_usd + seller_note_usd + rollover_equity_usd + earnout_usd

Per-seller allocation (pro-rata of each consideration component):
  seller.cash_at_close_usd     = round(seller.ownership_percent / 100 × total_cash_at_close)
  seller.seller_note_usd       = round(seller.ownership_percent / 100 × total_seller_note)
  seller.rollover_equity_usd   = round(seller.ownership_percent / 100 × total_rollover_equity)
  seller.earnout_usd           = round(seller.ownership_percent / 100 × total_earnout)
```

### Aggregate risk / escalation

```
total_quantified_exposure_dollars = sum(term.quantification.exposure_amount_dollars) across escalated terms
total_policy_excess_dollars       = sum(term.quantification.excess_amount_dollars) across escalated terms
escalation_term_count             = count of terms where escalation_required == true
deviation_percent                 = draft_percent − policy_threshold_percent  (positive = over threshold)
```

### Reverse termination fee

```
reverse_fee_amount_usd = round(headline_value_usd × reverse_fee_percent / 100)
```

## Task-Type Workflows

### 1. Term Population (Buyer-Side First Draft)

**Inputs**: Deal ID, deal profile, active cap table, policy/playbook, client instructions.

**Steps**:

1. Look up the deal by ID. Extract structure, target, buyer, seller group, headline value,
   signing date, outside closing date.
2. Confirm the deal structure (`STOCK_PURCHASE`, `ASSET_PURCHASE`, `MERGER`).
3. Retrieve the **active** cap table (`CAP-ACTIVE`). If a stale one also exists, note it as
   superseded.
4. From the cap table, extract: seller names, roles, ownership percentages; determine
   `active_cap_table_source_doc_id` and `active_cap_table_as_of`.
5. Determine consideration mix: cash at close, rollover equity, seller note, earnout. These
   must sum to `equity_value_usd`.
6. Compute per-share price: if the active cap table has a share count, calculate
   `per_share_price_usd` to two decimals with basis `CALCULATED_FROM_ACTIVE_CAP_TABLE`;
   otherwise use `null` and `NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE`.
7. Compute `price_per_as_converted_percent_point_usd` = equity_value / 100.
8. Populate escrow percentages and amounts from the deal profile or playbook defaults.
   General escrow is typically 10% for buyer-side midmarket stock purchases; tax escrow is
   typically 2.0–2.5%.
9. Populate indemnity cap, basket, de minimis from policy defaults or deal-specific records.
10. Populate NWC target, collar, and mechanic from the deal financials.
11. Compute seller allocations pro-rata by ownership percent.
12. Populate closing conditions: material consents (from the material-contract log), HSR status,
    other regulatory approvals.
13. Populate employment agreement flags, non-compete, TSA, IP assignment from deal documents
    and policy defaults.
14. Populate the policy-checks block: run each policy rule against the draft terms, record
    status, approval requirements, and measured values.
15. Populate risk-memo overrides when client instructions or active data supersede defaults.
16. Sort all lists per the ordering conventions.

### 2. Counterparty Paper Review (Seller-Side APA)

**Inputs**: Deal ID, counterparty draft, client playbook, active client instructions.

**Steps**:

1. Open the deal. Identify the counterparty draft (`DRAFT-02` or similar).
2. Load the applicable seller playbook (e.g., `P-SELLER-APA-2026`).
3. Load active client instructions (`EMAIL` docs).
4. For each material term category in the template's `issue_id` enum, compare the counterparty
   draft against the playbook position and client instructions.
5. **Only include issues that are material.** Omit terms where the draft matches the playbook
   and client instructions.
6. For each material issue:
   - Assign `issue_id` from the controlled enum.
   - Set `severity` based on economic exposure and deal risk.
   - Set `recommended_action` from the controlled enum (`ACCEPT`, `REVISE`, `DELETE`, `ADD`,
     `ADD_FALLBACK_ONLY`, `ESCALATE`).
   - Populate `corrected_value` with only the normalized fields relevant to that issue.
   - List `source_ids` that support the conclusion (draft, email, clause records, playbook,
     benchmarks).
7. For economic issues, quantify the corrected value (percent, amount, or both).
8. Sort issues by `issue_id` ascending.

### 3. Committee Escalation Analysis

**Inputs**: Deal ID, draft terms, policy thresholds, committee record, benchmarks.

**Steps**:

1. Look up the deal and identify terms that deviate from policy thresholds.
2. For each escalated term:
   - Populate `term_id`, `source_clause_id`, `policy_rule_id`.
   - Set `escalation_required: true` when the draft exceeds policy thresholds.
   - Assign `committee_route` (typically `BOARD_TRANSACTION_COMMITTEE` for material deviations).
   - Assign `deviation_code` from the controlled enum.
   - Set `severity` and `approval_recommendation`.
   - Populate `quantification`: draft percent/amount, policy threshold, deviation, exposure
     amount, exposure basis.
   - For non-quantified risks (fiduciary out, MAE carveouts, R&W survival), use
     `exposure_basis: NON_QUANTIFIED_LEGAL_RISK` or `FULL_EQUITY_VALUE_UNCAPPED` and set
     percent fields to `null`.
   - For quantified terms (RTF), populate percent and dollar fields.
   - Include benchmark data when available (`benchmark_id`, `benchmark_sample_size`,
     `benchmark_count_above_threshold`).
3. Populate `aggregate_risk`:
   - `committee_route`: highest route across all escalated terms.
   - `approval_required`: true if any term requires escalation.
   - `committee_members`: exactly as listed in the Deal Desk committee record.
   - `risk_tier`: highest severity among escalated terms.
   - `final_action`: based on severity and strategic context.
   - `primary_driver_term_ids`: all escalated term IDs, sorted alphabetically.
   - `escalation_term_count`: count of escalated terms.
   - `total_quantified_exposure_dollars`: sum of all `exposure_amount_dollars`.
   - `total_policy_excess_dollars`: sum of all `excess_amount_dollars`.
   - `strategic_context`: BATNA, leverage, ownership, rationale from deal profile.
4. Sort `escalation_terms` by `term_id` ascending. Sort all code lists alphabetically.

### 4. Transition-Term Issue Package (Carve-Out / Divestiture)

**Inputs**: Deal ID, current draft, client playbook, latest client instructions.

**Steps**:

1. Open the deal and load the current draft, the controlling playbook (e.g.,
   `P-CARVEOUT-OPS-2026`), and active client instructions.
2. Identify priority issues by comparing draft terms against playbook and instructions.
3. For each priority issue:
   - Assign `issue_id` and `clause_code` from the controlled enums.
   - Set `severity` and `recommended_action`.
   - Assign `approval_owner` based on the issue domain.
   - List `source_doc_ids` (draft, email, disclosure, material contracts) sorted ascending.
4. Populate `transition_flags` for each category:
   - **employee_transfer**: offer percent, warn/severance retention, required offer standard,
     approval flag.
   - **tsa_service_continuity**: draft/target/fallback durations, required service codes
     (sorted alphabetically), approval flag.
   - **restrictive_covenants**: draft and max non-compete years, affiliate scope, required
     scope, non-solicit scope, approval flag.
   - **ip_transition**: draft and max trademark phaseout months, design-file access, required
     scope, approval flag.
   - **escrow_and_deadline**: general escrow percent and amount, target max, signing date,
     draft closing deadline, deadline days after signing, minimum deadline days, escalation flag.
5. Sort `priority_issues` by `issue_id` ascending. Sort all code lists alphabetically.

### 5. Policy-Check Bundle (Attached to First Draft)

**Inputs**: Draft terms, applicable policy ID and version.

**Steps**:

1. Identify the controlling policy (`policy_id` and `policy_version` from the deal profile).
2. For each policy check area (`BASKET_POLICY`, `CAP_POLICY`, `CONSENTS_POLICY`,
   `ESCROW_POLICY`, `HSR_POLICY`, `NONCOMPETE_POLICY`, `NWC_POLICY`):
   - Look up the applicable rule ID.
   - Compare the draft term against the rule threshold.
   - Set `status`: `WITHIN_POLICY` if compliant, `APPROVAL_REQUIRED` if outside threshold,
     `OVERRIDE_APPLIED` if client instructions justify a deviation, `ESCALATE_IF_CHANGED` if
     the term is currently compliant but close to a threshold.
   - Set `approval_required` based on status.
   - Set `approval_category` to the committee or role that owns the check area.
   - Set `measured_value` as a human-readable normalized string (e.g., `"0.75% deductible;
     50000 de minimis"`).
3. Populate `policy_summary`:
   - `approval_required_now`: true if any check has `APPROVAL_REQUIRED`.
   - `current_policy_exception_count`: count of checks with `APPROVAL_REQUIRED`.
   - `required_approval_bodies`: distinct approval categories from non-compliant checks,
     sorted alphabetically.
   - `conditional_escalation_triggers`: triggers that would fire if certain conditions change,
     sorted alphabetically.
4. Populate `risk_memo_overrides` when source precedence rules were applied:
   - `source_doc_ids`: documents that triggered the override (sorted).
   - `override_codes`: codes describing each override (sorted).
   - `superseded_doc_ids`: documents rendered stale by the override (sorted).
   - `hsr_override_basis`: when HSR is not required despite apparent thresholds, record the
     basis code.
5. Sort all lists per the ordering conventions.

## Common Pitfalls

1. **Using stale cap tables.** Always prefer `CAP-ACTIVE` over `CAP-STALE`. A deal may have
   both; the stale one is a distractor.

2. **Template/default over client instructions.** When an `EMAIL` document says something
   different from the playbook, the email controls. Record the override.

3. **Zero vs. null.** Use `null` for numeric fields that don't apply (e.g., `seller_note_usd: 0`
   means "there is a seller note of $0," which is different from "no seller note applies").
   Use `0` only when the value is genuinely zero.

4. **Confusing headline value with equity value.** In stock purchases with no debt adjustment
   they are typically equal, but verify per deal. Headline value is the total purchase price;
   equity value may differ after debt/POC adjustments.

5. **Including non-material items in issues lists.** The issue register and escalation analysis
   should only include items that are actual issues. Terms that match policy and client
   instructions are not issues.

6. **Missing the sort order.** Unsorted lists are a common failure. Double-check
   `seller_allocations`, `issues`, `escalation_terms`, `required_material_consents`,
   `employment_employees`, and all code lists.

7. **Using the wrong enum variant.** Each template defines its own controlled enums. Match the
   exact `UPPER_SNAKE_CASE` values; do not invent variants.

8. **Percentage precision.** Percentages are decimal percentage points with two decimal places
   (e.g., `0.75` for 0.75%, `10.0` for 10%), not fractions (e.g., not `0.0075`).

9. **Not rounding.** Dollar amounts are integers (whole dollars). Round after multiplication.

10. **Adding prose outside JSON.** Every task says "return only JSON." Do not include markdown
    fences, explanatory text, or narrative outside the JSON object.

## Controlled Enum Quick Reference

These enums appear across multiple task types. Use the exact strings below.

### Deal structure
`STOCK_PURCHASE` | `ASSET_PURCHASE` | `MERGER` | `ROLLOVER_STOCK_PURCHASE`

### Client side
`BUYER` | `SELLER`

### Severity / risk tier
`LOW` | `MEDIUM` | `HIGH` | `CRITICAL`

### Policy status
`WITHIN_POLICY` | `APPROVAL_REQUIRED` | `OVERRIDE_APPLIED` | `ESCALATE_IF_CHANGED`

### Escrow policy status
`WITHIN_POLICY` | `ESCALATE` | `NOT_APPLICABLE`

### Basket type
`DEDUCTIBLE` | `TIPPING` | `NONE`

### NWC adjustment mechanic
`DOLLAR_FOR_DOLLAR_OUTSIDE_COLLAR` | `DOLLAR_FOR_DOLLAR_FROM_FIRST_DOLLAR` | `NO_POST_CLOSING_ADJUSTMENT` | `TRUE_UP_AGAINST_ACTIVE_BALANCE_SHEET` | `SELLER_BUDGET_BASELINE` | `NONE`

### HSR status
`REQUIRED` | `NOT_REQUIRED` | `UNCLEAR`

### HSR condition / clause position
`HSR_CLOSING_CONDITION` | `NO_HSR_CONDITION_COOPERATION_ONLY` | `NOT_ADDRESSED` | `FILING_CONDITION` | `COOPERATION_COVENANT_ONLY` | `OMIT_HSR_LANGUAGE`

### HSR basis / override basis
`SIZE_OF_PERSON_TEST_NOT_MET` | `REPORTABLE_THRESHOLDS_MET` | `COUNSEL_MEMO_MISSING` | `NOT_APPLICABLE` | `THRESHOLDS_NOT_MET_AFTER_DEBT_ADJUSTMENTS` | `SIZE_OF_PERSON_NOT_MET` | `UNKNOWN`

### Consent condition status
`MATERIAL_CONSENTS_AS_CLOSING_CONDITIONS` | `MATERIAL_CONSENTS_AS_POST_CLOSING_COVENANTS` | `NO_MATERIAL_CONSENTS_REQUIRED`

### Per-share price basis
`CALCULATED_FROM_ACTIVE_CAP_TABLE` | `NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE`

### Non-compete scope (buyer-side SPA)
`TARGET_PRODUCTS_AND_CURRENT_TERRITORIES` | `WORLDWIDE_ALL_AFFILIATES` | `NO_NON_COMPETE` | `OTHER_LIMITED_SCOPE`

### Non-compete scope (carve-out)
`DIVESTED_LINE_EXISTING_GEOGRAPHIES` | `DIVESTED_LINE_WORLDWIDE` | `ALL_INDUSTRIAL_HAND_TOOLS` | `NO_RESTRICTIVE_COVENANT`

### Non-compete position (first-draft)
`TARGETED_PRODUCT_SCOPE_RESTRICTIVE_COVENANT` | `BROAD_GLOBAL_RESTRICTIVE_COVENANT` | `TARGETED_TERRITORY_RESTRICTIVE_COVENANT` | `OMIT_RESTRICTIVE_COVENANT`

### Recommended action
`ACCEPT` | `ADD` | `ADD_FALLBACK_ONLY` | `DELETE` | `ESCALATE` | `ESCALATE_ONLY` | `EXTEND_AND_ESCALATE` | `NARROW_AND_ESCALATE` | `NO_ISSUE` | `REDUCE_OR_ESCALATE` | `REVISE` | `REVISE_AND_ESCALATE`

### Approval owner / category
`DEAL_LEAD` | `EMPLOYMENT_COUNSEL` | `EXECUTIVE_COMMITTEE` | `FINANCE_COMMITTEE` | `HR_COMMITTEE` | `IP_COUNSEL` | `LEGAL_RISK_COMMITTEE` | `OPERATIONS_COMMITTEE` | `REGULATORY_COUNSEL` | `SELLER_STEERING_COMMITTEE`

### Committee route
`BOARD_TRANSACTION_COMMITTEE` | `CLIENT_BUSINESS_LEAD` | `NO_COMMITTEE_ROUTE`

### Exposure basis
`EQUITY_VALUE` | `FULL_EQUITY_VALUE_UNCAPPED` | `NON_QUANTIFIED_LEGAL_RISK` | `NONE` | `POLICY_THRESHOLD_EXCESS`

### Final action
`ESCALATE_AND_APPROVE` | `ESCALATE_AND_RENEGOTIATE_BEFORE_SIGNING` | `ESCALATE_FOR_INFORMATION_ONLY` | `NO_ESCALATION`

### BATNA code
`COMPETING_SIGNED_DEAL` | `LOWER_RISK_PRIVATE_PLATFORM` | `NONE_IDENTIFIED` | `STATUS_QUO`

### BATNA leverage
`LOW` | `MODERATE` | `HIGH`

### Ownership context
`ACTIVIST_PRESSURE_INDEX_FUNDS` | `DISPERSED_RETAIL_ONLY` | `FOUNDER_CONTROLLED` | `PRIVATE_SELLER_GROUP`

### Strategic rationale
`DEFENSIVE_BLOCKING_ACQUISITION` | `NEED_PLATFORM_BUT_MARKET_STANDARD_RISK` | `NON_STRATEGIC_ADD_ON` | `PURE_FINANCIAL_BUY`

### Override codes (risk memo)
`ACTIVE_CLIENT_INSTRUCTIONS_SUPERSEDE_TEMPLATE` | `NO_HSR_CONDITION_DESPITE_CYBER_ASSETS` | `USE_ACTIVE_CAP_TABLE_OVER_STALE_EXPORT`

### Conditional escalation triggers
`ADD_FINANCING_CONDITION` | `REMOVE_FEDERAL_SOC_CONSENT` | `TAX_ESCROW_THRESHOLD_TRIGGER` | `GENERAL_ESCROW_THRESHOLD_TRIGGER` | `CAP_THRESHOLD_TRIGGER` | `BASKET_THRESHOLD_TRIGGER` | `TOP_CUSTOMER_CONSENT_OMITTED` | `UNCLEAR_HSR_ANALYSIS`

### Form / drafting positions
`BUYER_FORM` | `SELLER_FORM` | `COMMITTEE_FORM` | `STANDARD_FORM`

### Consideration schedule position
`ACTIVE_CAP_TABLE_PRORATA_ALLOCATION` | `ACTIVE_ALLOCATION_SCHEDULE` | `STALE_CAP_TABLE` | `COUNTERPARTY_DRAFT`

### Escrow-cap position
`CAP_EQUALS_GENERAL_ESCROW` | `CAP_ABOVE_ESCROW` | `CAP_BELOW_ESCROW` | `NO_CAP`

### Consent position
`SPECIFIED_MATERIAL_CONSENTS_AS_CLOSING_CONDITIONS` | `POST_CLOSING_COVENANT_ONLY` | `OMIT_CONSENTS`

### Earnout position
`OBJECTIVE_REVENUE_BASED_FALLBACK` | `OPERATING_COVENANT_REQUIRED` | `NO_EARNOUT`

### Transition services position
`NO_GENERAL_TSA_LIMITED_CUSTOMER_NOTICE_SUPPORT` | `FULL_TSA_REQUIRED` | `TSA_STATUS_UNCLEAR`

### IP transition position
`REQUIRE_OPEN_SOURCE_AUDIT_AND_FEDRAMP_ASSIGNMENT` | `NO_IP_TRANSITION` | `TRADEMARK_PHASE_OUT_ONLY`

### Employment offer standard
`BUYER_COMPARABLE_OFFERS_ALL_BUSINESS_EMPLOYEES` | `BUYER_OFFERS_SELECTED_CRITICAL_EMPLOYEES` | `NO_EMPLOYEE_COVENANT_REQUIRED` | `SELLER_RETAINS_EXCLUDED_EMPLOYEES_ONLY`

### Non-solicit scope
`DIVESTED_BUSINESS_CUSTOMERS_AND_EMPLOYEES_ONLY` | `ALL_ATLAS_AFFILIATES_CUSTOMERS_AND_EMPLOYEES` | `NO_NON_SOLICIT_LIMIT`

### IP transition required scope
`NARROW_TRANSITIONAL_LICENSE_WITH_RETAINED_IP_BOUNDARIES` | `BROAD_DESIGN_FILE_ACCESS` | `OPEN_ENDED_TRADEMARK_USE` | `NO_IP_TRANSITION_RIGHTS`

### TSA service codes
`ERP` | `FINANCE` | `IT` | `IT_HELPDESK` | `PAYROLL` | `PROCUREMENT` | `QUALITY_CERTIFICATIONS` | `QUALITY_RECORDS` | `REGULATORY`

### MAE carveout codes
`ANNOUNCEMENT_EFFECTS` | `CYBER_INCIDENT` | `CUSTOMER_LOSS` | `INDUSTRY` | `LAW_CHANGE` | `MARKET` | `PANDEMIC` | `RATES` | `WAR`

### Investment benefit
`FOR_BUYER` | `FOR_SELLER` | `SPLIT` | `NOT_APPLICABLE`

### Fee base
`HEADLINE_VALUE` | `EQUITY_VALUE` | `NONE`

### Buyer assumed liability covenant
`SURVIVE_UNTIL_FULLY_PERFORMED` | `SIX_MONTHS` | `NOT_APPLICABLE`

### Business scope (restrictive covenant)
`TRANSFERRED_BUSINESS_ONLY` | `ALL_AFFILIATE_BUSINESSES` | `ADJACENT_PRODUCTS` | `NONE`

### Replacement (financing condition)
`CLOSING_CERTAINTY_COVENANT` | `NONE`

### Deviation codes
`ABOVE_RTF_THRESHOLD` | `POST_CLOSING_R_AND_W_SURVIVAL` | `RESTRICTED_MAE_CARVEOUTS` | `TERMINATION_RIGHT_BLOCKED` | `WEAK_REGULATORY_COVENANT` | `WITHIN_POLICY`

### Approval recommendation
`APPROVE_AS_DRAFTED` | `APPROVE_WITH_CONDITIONS` | `DO_NOT_APPROVE_AS_DRAFTED` | `NO_APPROVAL_NEEDED`

### Recommendation (escalation)
`DELETE_POST_CLOSING_R_AND_W_SURVIVAL` | `RTF_POLICY_POSITION` | `RESTORE_FULL_PUBLIC_COMPANY_MAE_CARVEOUTS` | `RESTORE_SUPERIOR_PROPOSAL_TERMINATION_RIGHT` | `NO_CHANGE_REQUIRED`

### Warn and severance liability
`BUYER_FOR_TRANSFERRED_EMPLOYEES` | `SELLER` | `ALLOCATED_BY_STATUTE` | `NOT_APPLICABLE`

## Role-Specific Defaults

| Role / Check Area       | Default Approval Owner      |
|--------------------------|------------------------------|
| Escrow, cap, basket      | `LEGAL_RISK_COMMITTEE`      |
| HSR, regulatory          | `REGULATORY_COUNSEL`        |
| Non-compete, employment  | `EMPLOYMENT_COUNSEL`         |
| Employee transfer        | `HR_COMMITTEE`               |
| IP transition            | `IP_COUNSEL`                 |
| TSA, operations          | `OPERATIONS_COMMITTEE`       |
| NWC, financial           | `FINANCE_COMMITTEE`          |
| Consents                 | `DEAL_LEAD`                  |
| General / unassigned     | `DEAL_LEAD`                  |
