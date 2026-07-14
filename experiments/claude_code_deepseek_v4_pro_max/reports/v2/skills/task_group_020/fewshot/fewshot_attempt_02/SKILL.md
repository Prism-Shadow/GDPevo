# Aster Legal Deal Desk — Task Execution Skill

## Environment

The only valid environment URL is:

```
GDPEVO_ENV_BASE_URL=http://34.46.77.124:9020
```

Every task prompt contains `<TASK_ENV_BASE_URL>` — substitute the above URL. Do not use localhost, 127.0.0.1, or any other endpoint. The environment exposes both web pages and API surfaces for the Aster Legal Deal Desk platform. Navigate or query it to retrieve deal profiles, documents, clause records, policies, benchmarks, cap tables, and committee records.

## Workflow Rules

### 1. Identify the Task Type First

Every task falls into one of these archetypes. The prompt's verbs, the target deal, and the requested output shape tell you which:

| Archetype | Goal | Output shape |
|---|---|---|
| **Term population / first draft** | Populate all deal terms from the deal room for a buyer-side or seller-side draft | `deal_terms` + `seller_allocations` + `closing_flags` or `draft_terms` + `policy_checks` |
| **Counterparty paper review** | Compare the active counterparty draft against client instructions and the applicable playbook; produce a material-issue register | `issues[]` with `issue_id`, `severity`, `recommended_action`, `corrected_value`, `source_ids` |
| **Committee escalation analysis** | Identify terms deviating from policy that need committee routing; quantify exposure | `escalation_terms[]` + `aggregate_risk` |
| **Transition-term / carve-out review** | Review employee, TSA, restrictive covenant, IP, escrow, and deadline provisions for a carve-out or divestiture | `priority_issues[]` + `transition_flags{}` |

When the prompt mentions "buyer-side SPA," "first-draft," or "term population," use the first archetype. When it mentions "seller-side counsel," "counterparty paper," or "issue register," use the second. When it mentions "committee escalation," use the third. When it mentions "carve-out," "transition-term," or "divestiture," use the fourth.

### 2. Source Precedence (Mandatory)

Apply this hierarchy when any document or instruction conflicts with another:

1. **Active client instructions** (DOC-{DEALCODE}-EMAIL-03 or similar written instructions) — highest authority
2. **Active deal documents** (DOC-{DEALCODE}-DRAFT-02, DOC-{DEALCODE}-DISC-06) — current draft and disclosures
3. **Active cap table / allocation schedule** (DOC-{DEALCODE}-CAP-ACTIVE) — latest ownership data
4. **Applicable playbook / policy** (P-{TYPE}-{YEAR}, e.g. P-SELLER-APA-2026, P-CARVEOUT-OPS-2026, P-BUYER-MIDMARKET-2026)
5. **Clause comparison records** (CL-{DEALCODE}-{NNN}) — term-by-term analysis
6. **Financial schedules** (DOC-{DEALCODE}-FIN-04) — supporting financial data
7. **Benchmarks** (BM-{TERM}-{INDUSTRY}-{YEAR}) — market data, used for context
8. **Stale/template documents** (DOC-{DEALCODE}-TEMPLATE-99, DOC-{DEALCODE}-CAP-STALE) — lowest authority; never use when an active equivalent exists

Override codes that appear in risk memos (e.g. `ACTIVE_CLIENT_INSTRUCTIONS_SUPERSEDE_TEMPLATE`, `USE_ACTIVE_CAP_TABLE_OVER_STALE_EXPORT`) document that this precedence was correctly applied.

### 3. Document ID Conventions

When referencing documents in `source_doc_ids`, `source_ids`, or `allocation_source_doc_id`, use the exact document IDs found in the deal room. Common patterns:

- **Active cap table:** `DOC-{DEALCODE}-CAP-ACTIVE`
- **Stale cap table:** `DOC-{DEALCODE}-CAP-STALE`
- **Current draft:** `DOC-{DEALCODE}-DRAFT-02`
- **Financial schedules:** `DOC-{DEALCODE}-FIN-04`
- **Client instructions / email:** `DOC-{DEALCODE}-EMAIL-03`
- **Material contracts schedule:** `DOC-{DEALCODE}-MATCON-05`
- **Disclosure schedules:** `DOC-{DEALCODE}-DISC-06`
- **Term sheet:** `DOC-{DEALCODE}-TERM-01`
- **Template / stale:** `DOC-{DEALCODE}-TEMPLATE-99`

Clause comparison IDs follow: `CL-{DEALCODE}-{NNN}` (e.g., `CL-BRASS-219-001`).

Policy IDs follow: `P-{SHORTCODE}-{YEAR}` (e.g., `P-SELLER-APA-2026`, `P-CARVEOUT-OPS-2026`, `P-BUYER-MIDMARKET-2026`).

Benchmark IDs follow: `BM-{TERM}-{INDUSTRY}-{YEAR}-{NNN}` (e.g., `BM-RTF-HEALTHTECH-2026`, `BM-REVERSE-TERMINATION-FEE-AEROSPACE-COMPONENTS-2026-014`).

### 4. Output Rules

- Return **only** the JSON object. No markdown fences, no prose, no memo text outside the JSON.
- Match the exact key names from the answer template — do not invent or omit top-level keys.
- Every field in the template must be present in the output (use `null` for inapplicable scalar fields, `[]` for empty lists).
- Follow the ordering rules declared in each template (see §List Ordering below).

### 5. How to Populate Fields

**Read, don't guess.** For each field in the output schema:
1. Find the corresponding data in the deal room (deal profile page, document pages, clause records, cap table, policy pages, benchmark pages).
2. If the data is directly available, use it exactly as shown (names, dates, amounts).
3. If a field must be computed, use the formulas in §Math & Computation below.
4. If a field is not applicable or not available, use `null` (for scalars) or `[]` (for lists).
5. If a field's value is controlled by an enum, use the exact enum string from the template — never paraphrase or abbreviate.

## Field Conventions

### Currency

- All monetary amounts are **integer US dollars**. No commas, no currency symbols, no decimal points.
- Example: $18,400,000 → `18400000`.

### Percentages

- All percentages are **numbers rounded to two decimal places**, expressed as percentage points.
- Example: 10% → `10.0` or `10.00`, 7.26% → `7.26`, 0.75% → `0.75`.
- Do NOT express as fractions (0.10 is wrong for 10%).

### Dates

- All dates use **YYYY-MM-DD** format.
- Example: August 14, 2026 → `"2026-08-14"`.

### Months

- All duration fields in months are **integers**.
- Example: 24 months → `24`.

### Null Handling

- Use `null` for numeric fields that are not applicable (e.g., `per_share_price_usd` when there is no share count, `draft_percent` when the term is not quantified).
- Use `[]` for list fields that have no entries.
- A value of `0` means zero dollars/percent — it is NOT the same as `null`.

### Enums

- Match the exact case and spelling from the template's `allowed_values`. Never invent a variant.
- Common enum sets used across tasks:
  - **Structure:** `STOCK_PURCHASE`, `ASSET_PURCHASE`, `MERGER`, `ROLLOVER_STOCK_PURCHASE`
  - **Severity:** `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`
  - **Escrow policy status / policy check status:** `WITHIN_POLICY`, `ESCALATE`, `APPROVAL_REQUIRED`, `OVERRIDE_APPLIED`, `ESCALATE_IF_CHANGED`, `NOT_APPLICABLE`
  - **Basket type:** `DEDUCTIBLE`, `TIPPING`, `NONE`
  - **NWC mechanic:** `DOLLAR_FOR_DOLLAR_OUTSIDE_COLLAR`, `DOLLAR_FOR_DOLLAR_FROM_FIRST_DOLLAR`, `NO_POST_CLOSING_ADJUSTMENT`
  - **Consent condition:** `MATERIAL_CONSENTS_AS_CLOSING_CONDITIONS`, `MATERIAL_CONSENTS_AS_POST_CLOSING_COVENANTS`, `NO_MATERIAL_CONSENTS_REQUIRED`
  - **HSR condition:** `HSR_CLOSING_CONDITION`, `NO_HSR_CONDITION_COOPERATION_ONLY`, `NOT_ADDRESSED`
  - **HSR basis:** `SIZE_OF_PERSON_TEST_NOT_MET`, `REPORTABLE_THRESHOLDS_MET`, `COUNSEL_MEMO_MISSING`, `NOT_APPLICABLE`, `THRESHOLDS_NOT_MET_AFTER_DEBT_ADJUSTMENTS`, `SIZE_OF_PERSON_NOT_MET`, `UNKNOWN`
  - **Recommended action (issues):** `ACCEPT`, `ADD`, `ADD_FALLBACK_ONLY`, `DELETE`, `ESCALATE`, `NO_ISSUE`, `REVISE`
  - **Recommended action (priority issues):** `ACCEPT`, `DELETE`, `ESCALATE_ONLY`, `EXTEND_AND_ESCALATE`, `NARROW_AND_ESCALATE`, `REDUCE_OR_ESCALATE`, `REVISE`, `REVISE_AND_ESCALATE`
  - **Approval owner:** `DEAL_LEAD`, `EMPLOYMENT_COUNSEL`, `HR_COMMITTEE`, `IP_COUNSEL`, `LEGAL_RISK_COMMITTEE`, `OPERATIONS_COMMITTEE`, `SELLER_STEERING_COMMITTEE`, `EXECUTIVE_COMMITTEE`, `FINANCE_COMMITTEE`, `REGULATORY_COUNSEL`
  - **Exposure basis:** `EQUITY_VALUE`, `FULL_EQUITY_VALUE_UNCAPPED`, `NON_QUANTIFIED_LEGAL_RISK`, `NONE`, `POLICY_THRESHOLD_EXCESS`
  - **Non-compete scope:** `TARGET_PRODUCTS_AND_CURRENT_TERRITORIES`, `WORLDWIDE_ALL_AFFILIATES`, `NO_NON_COMPETE`, `OTHER_LIMITED_SCOPE`

## List Ordering Rules

Always apply the ordering rule declared in the answer template. Common rules:

| List | Sort key | Direction |
|---|---|---|
| `seller_allocations` | `seller_name` (or `seller_id` if specified) | ascending |
| `required_material_consents` | `contract_name` | ascending |
| `employment_employees` | displayed employee name | ascending |
| `escalation_terms` | `term_id` | ascending (alphabetical) |
| `priority_issues` | `issue_id` | ascending |
| `policy_checks` | `check_id` | ascending |
| `source_doc_ids` / `source_ids` | doc ID string | ascending |
| `mae_omitted_carveouts` | carveout code | ascending (alphabetical) |
| `committee_members` | names as shown in committee record | (keep exact names, sorted as specified) |
| `primary_driver_term_ids` | term_id enum values | ascending (alphabetical) |
| `required_service_codes` (TSA) | service code enum | ascending (alphabetical) |
| `other_approvals` | approval name | ascending (alphabetical) |
| `override_codes` | code string | ascending (alphabetical) |
| `superseded_doc_ids` | doc ID string | ascending (alphabetical) |
| `required_approval_bodies` | approval category enum | ascending (alphabetical) |
| `conditional_escalation_triggers` | trigger enum | ascending (alphabetical) |
| `tsa_services` | service code | ascending (alphabetical) |
| `post_closing_notice_items` | contract name | ascending (alphabetical) |
| `material_consents_as_closing_conditions` | contract name | ascending (alphabetical) |

When the template says "Sort by X ascending," do it. When it says "Sort alphabetically," sort the string values A→Z.

## Math & Computation

### Term Population Computations

**Equity value vs. headline purchase price:**
- In a debt-free / cash-free stock purchase with no debt adjustments, `equity_value_usd == headline_purchase_price_usd`.
- If the deal has debt adjustments, equity value may differ — check the deal profile.

**Per-share price:**
```
per_share_price_usd = equity_value_usd / fully_diluted_share_count
```
Round to two decimal places. Set to `null` and use `per_share_price_basis: "NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE"` when the active cap table does not report a share count.

**Price per percentage point:**
```
price_per_as_converted_percent_point_usd = equity_value_usd / 100
```
Round to the nearest integer dollar. This represents the dollar value of 1.00% ownership.

**Escrow amounts:**
```
general_escrow_usd = round(headline_purchase_price_usd * general_escrow_percent / 100)
tax_escrow_usd = round(headline_purchase_price_usd * tax_escrow_percent / 100)
```
Round to the nearest integer dollar.

**Seller gross proceeds (simple):**
```
gross_proceeds_usd = round(headline_purchase_price_usd * ownership_percent / 100)
```

**Seller gross proceeds (mixed consideration):**
Each seller's proceeds are allocated pro rata across the consideration components:
```
cash_at_close_usd = round(total_cash_at_close * ownership_percent / 100)
seller_note_usd = round(total_seller_note * ownership_percent / 100)
rollover_equity_usd = round(total_rollover_equity * ownership_percent / 100)
earnout_usd = round(total_earnout * ownership_percent / 100)
total_proceeds_usd = cash_at_close_usd + seller_note_usd + rollover_equity_usd + earnout_usd
```
The sum of all sellers' `total_proceeds_usd` must equal `total_consideration` (which equals `headline_value_usd` / `equity_value_usd` in a standard deal).

**Consideration mix validation:**
```
total_consideration = cash_at_close + seller_note + rollover_equity + earnout
```
All five consideration mix fields must be consistent.

**NWC collar as percent:**
```
nwc_collar_percent_of_equity_value = round(nwc_collar_usd / equity_value_usd * 100, 2)
```

**Deadline days:**
```
deadline_days_after_signing = calendar_days_between(signing_date, closing_deadline)
```

### Issue / Escalation Computations

**Deviation:**
```
deviation_percent = draft_percent - policy_threshold_percent
```
(When both are available. Round to two decimal places.)

**Excess amount:**
```
excess_amount_dollars = round(equity_value_usd * deviation_percent / 100)
```

**Exposure amount:**
- When `exposure_basis` is `EQUITY_VALUE`: `exposure_amount_dollars = equity_value_usd`
- When `exposure_basis` is `FULL_EQUITY_VALUE_UNCAPPED`: `exposure_amount_dollars = equity_value_usd` (but the risk is uncapped)
- When `exposure_basis` is `NON_QUANTIFIED_LEGAL_RISK`: `exposure_amount_dollars = null`
- When `exposure_basis` is `POLICY_THRESHOLD_EXCESS`: `exposure_amount_dollars = excess_amount_dollars`

**Total exposure:**
```
total_quantified_exposure_dollars = sum of exposure_amount_dollars across escalation terms
total_policy_excess_dollars = sum of excess_amount_dollars across escalation terms
```

**Escrow cap position classification:**
- `CAP_EQUALS_GENERAL_ESCROW` — indemnity cap percent equals general escrow percent
- `CAP_ABOVE_ESCROW` — cap percent exceeds general escrow percent
- `CAP_BELOW_ESCROW` — cap percent is below general escrow percent
- `NO_CAP` — no indemnity cap

**Basket amount:**
```
basket_amount_usd = round(headline_value_usd * basket_percent / 100)
```

## Common Pitfalls

1. **Using stale documents over active ones.** Always check whether a document ID contains `STALE` or `TEMPLATE` — those are distractors. Use `ACTIVE`, `DRAFT`, `EMAIL` equivalents instead.

2. **Percentage-as-fraction errors.** The template says "10.00" for 10%, not "0.10". Write `10.0` for ten percent, not `0.10`.

3. **Not computing per-share price correctly.** If the cap table has no share count, `per_share_price_usd` is `null` and `per_share_price_basis` is `NO_SHARE_COUNT_IN_ACTIVE_CAP_TABLE`. If it has a share count, compute and set the basis to `CALCULATED_FROM_ACTIVE_CAP_TABLE`.

4. **Rounding errors in consideration allocations.** Prorated allocations across consideration components may have rounding differences of ±$1 per seller. Distribute so that column sums match the totals. If a seller's individually rounded components don't sum to exactly their `total_proceeds_usd`, adjust the largest component by the residual.

5. **Including non-material items in issue lists.** The templates explicitly say "Include each material issue once. Omit non-issues." Only list items that actually deviate from the applicable playbook or client instructions.

6. **Wrong enum for the task context.** `recommended_action` has different allowed values for different task types (compare train_002's `ADD`, `DELETE`, `REVISE`, `ADD_FALLBACK_ONLY` vs. train_004's `EXTEND_AND_ESCALATE`, `NARROW_AND_ESCALATE`, `REDUCE_OR_ESCALATE`). Use the enum set from the specific answer template for that task, not a different one.

7. **Missing `source_ids` / `source_doc_ids`.** Every material issue and every override must cite the supporting document IDs. This is for auditability — include the IDs, not prose explanations.

8. **Sort order violations.** Every list has a declared sort order. Sort before returning.

9. **Committee member names.** Use names exactly as they appear in the Deal Desk committee record — do not reorder, abbreviate, or paraphrase.

10. **HSR override documentation.** When HSR is `NOT_REQUIRED` but the deal involves cyber/tech assets, document the override with an override code (`NO_HSR_CONDITION_DESPITE_CYBER_ASSETS`) and a specific basis (`THRESHOLDS_NOT_MET_AFTER_DEBT_ADJUSTMENTS`, `SIZE_OF_PERSON_NOT_MET`, etc.).

## Task-Type Specific Guidance

### Term Population / First Draft (train_001, train_005)

- Start from the deal profile page to get the target, buyer/seller, structure, signing date, and headline price.
- The active cap table (`DOC-{DEALCODE}-CAP-ACTIVE`) controls seller allocations, ownership percentages, and per-share pricing.
- Material contracts determine `required_material_consents` and closing conditions.
- Each consent item needs its `annual_revenue_usd`, `condition_type`, and `consent_required` flag from the deal room.
- Employment agreements define `employment_employees` and `employment_agreement_term_months`.
- HSR analysis: check whether thresholds are met; if not, `hsr_required: false`, `hsr_condition: "NO_HSR_CONDITION_COOPERATION_ONLY"`.
- For first drafts, also populate `drafting_positions` with the appropriate form/position enums reflecting what is in the draft.

### Counterparty Paper Review (train_002)

- Compare the **active counterparty draft** against **client instructions** (EMAIL doc) and the **applicable playbook** (P-SELLER-APA-2026).
- Each material deviation becomes an issue. Use the exact `issue_id` from the template's allowed values.
- `corrected_value` only includes the fields relevant to that specific issue — not every field from the allowed list.
- `source_ids` cite the documents that support the conclusion: draft doc, client instructions, financial schedules, clause records, playbook, and benchmarks.

### Committee Escalation (train_003)

- Identify terms where the draft deviates from policy thresholds.
- Quantify the deviation: `draft_percent` vs `policy_threshold_percent`, compute `deviation_percent`, `draft_amount_dollars`, `excess_amount_dollars`.
- For non-quantified terms (fiduciary out, MAE carveouts, R&W survival), set monetary fields to `null` and use the appropriate `exposure_basis`.
- `mae_omitted_carveouts` lists which standard MAE carveouts are missing from the draft.
- `aggregate_risk` summarizes the overall risk posture, committee routing, and strategic context.
- `committee_members` come from the Deal Desk committee record for that deal.
- `strategic_context` fields come from the deal profile / strategic assessment pages.

### Transition-Term / Carve-Out Review (train_004)

- Each transition category (employee, TSA, restrictive covenants, IP, escrow/deadline) gets a structured `transition_flags` block.
- `issue_present: true` means the draft deviates from the playbook position — always set this accurately.
- `draft_*` fields capture what the current draft says; `target_*` / `max_*` / `required_*` fields capture the playbook position.
- `approval_required` in each transition block reflects whether the deviation needs signoff.
- `priority_issues` lists the clause-level issues that need negotiation action.
- Each priority issue maps to a `clause_code` (a short code like `CLOSE`, `EMPLOYEE`, `ESCROW`, `IP`, `NONCOMPETE`, `TSA`).
- `recommended_action` for priority issues uses the carve-out specific set (`EXTEND_AND_ESCALATE`, `NARROW_AND_ESCALATE`, etc.).
- `approval_owner` is the function that must approve, not a committee name.

### Policy Checks (train_005)

- Each policy check evaluates one dimension (basket, cap, consents, escrow, HSR, non-compete, NWC).
- `measured_value` is a human-readable summary string — include the key numbers and status.
- `WITHIN_POLICY` means the draft position matches policy without needing approval.
- `OVERRIDE_APPLIED` means the draft deviates from the default policy position but the deviation is justified and documented (e.g., HSR thresholds not met).
- `policy_summary.approval_required_now` is `true` only when there are active exceptions needing approval (not when all checks are `WITHIN_POLICY` or `OVERRIDE_APPLIED`).
- `conditional_escalation_triggers` lists events that, if they occur later, would trigger escalation — these are forward-looking warnings, not current issues.
- `risk_memo_overrides` documents active decisions to supersede stale material or template defaults.
