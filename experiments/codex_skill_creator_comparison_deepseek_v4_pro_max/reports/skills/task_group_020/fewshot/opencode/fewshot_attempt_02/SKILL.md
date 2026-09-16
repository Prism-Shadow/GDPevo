---
name: ma-deal-review
description: Review and analyze M&A deal terms on a deal workbench when the task involves comparing draft purchase-agreement terms against a buyer or seller playbook, identifying out-of-policy or missing terms, computing dollar amounts from headline purchase price, producing a structured JSON deliverable (issue register, closing package, committee escalation memo, deviation matrix, or transition review), or assessing closing readiness and blockers for an acquisition. Use this skill whenever the user mentions deal review, APA, SPA, issue register, closing package, committee escalation, deviation matrix, transition review, playbook comparison, or any M&A workbench task with a deal ID and a client side (buyer/seller).
---

# M&A Deal Review

Workflow for reviewing a draft purchase agreement against a buyer or seller playbook on an M&A deal workbench, producing structured JSON deliverables.

## Core Workflow

### Step 1 -- Read the prompt and answer template

The task prompt supplies a deal ID and client side, describes the deliverable type, and points to an answer template (`input/payloads/answer_template.json`). Read both files before fetching any workbench data.

The answer template defines the exact JSON shape, allowed enum values, required fields, and unit conventions. The template is authoritative -- every field, enum, and structure in it must be honored.

### Step 2 -- Identify what workbench data is needed

From the prompt and answer template, determine which workbench endpoints are relevant. Not every endpoint is needed for every task. The workbench is at `<TASK_ENV_BASE_URL>`. All GET endpoints are documented in [references/api_reference.md](references/api_reference.md). A read-only SQL endpoint is also available at `POST <TASK_ENV_BASE_URL>/api/query` with token `deal-workbench-readonly` for cross-table checks.

Send all needed GET requests in parallel. After they return, inspect the records and determine whether SQL queries are needed for cross-referencing (e.g., linking consent IDs to contract IDs, verifying relationship counts).

### Step 3 -- Identify the applicable playbook or policy

If the prompt names a specific playbook (e.g., `PB_SELLER_A`, `PB_BUYER_A`), fetch its rules directly. Otherwise, infer it from the client side:

- Seller-side work: use the seller playbook
- Buyer-side work: use the buyer playbook

For committee escalation tasks, the applicable policy and its thresholds are usually referenced by ID in the prompt or answer template. Fetch the policy rules and thresholds.

### Step 4 -- Compare draft terms against the playbook

For each draft term that corresponds to a playbook rule:

1. Read the draft term's value (percent, amount, months, boolean, or qualitative clause)
2. Read the playbook's preferred and fallback positions
3. Determine the issue status:

   **For seller-side review:**
   - `draft_exceeds_playbook` -- draft value is worse for the seller than the fallback (e.g., escrow higher, cap higher, survival longer)
   - `draft_below_playbook` -- draft falls below what the seller needs (e.g., no reverse break fee when one is needed, fee too low)
   - `in_policy` -- draft is within acceptable range
   - `missing_required_term` -- a term the playbook requires is absent from the draft

   **For buyer-side review:**
   - `draft_below_playbook` -- draft value is worse for the buyer than the fallback (e.g., cap too low, survival too short, escrow too low)
   - `draft_exceeds_playbook` -- draft exceeds what the buyer wants (rare, but possible)
   - `in_policy` -- draft is within acceptable range
   - `missing_required_term` -- a term the playbook requires is absent from the draft

4. For `missing_required_term` issues: set `source_term_ids` to an empty array `[]` and populate the required position from the playbook.

5. Exclude in-policy terms from the deliverable unless the answer template explicitly requires them. Committee escalation tasks specifically filter to out-of-policy terms only.

6. For terms not found in the draft but required by the playbook, treat as missing and populate the required position.

### Step 5 -- Compute amounts from the headline purchase price

All dollar amounts derive from the deal's headline purchase price unless a source record or the answer template explicitly states a different basis. To compute a percent-based amount: multiply the headline purchase price by the percent (expressed as a decimal) and round to integer dollars.

Read the headline value from the deal record or cap table. If the deal record provides multiple value bases (equity value, upfront cash, etc.), use the one specified by the answer template or prompt.

### Step 6 -- Map source record IDs

Every issue must cite stable source IDs from the workbench:

- `source_term_ids`: term IDs that define the current draft position (e.g., `TERM_PRJ_...`)
- `source_record_ids`: consent IDs, contract IDs, risk estimate IDs, employee IDs, finding IDs that support the analysis

IDs must be exactly as returned by the workbench APIs. Do not invent or truncate IDs. For missing terms, source_term_ids is an empty array.

### Step 7 -- Order issues by priority

The priority order reflects negotiation leverage, risk severity, and deal economics. General rules:

- Closing certainty issues (financing conditions, reverse break fees, HSR, consent conditions) rank highest
- Economic issues (escrow, indemnity cap) rank next
- Employee/transition issues follow
- Restrictive covenants, survival periods, baskets
- Tax allocation and governing law rank lowest

Adjust based on risk ratings and quantified exposure. HIGH risk issues with large dollar exposure move up.

### Step 8 -- Compute summary metrics

Aggregate counts across the issue register:

- `issue_count`: total issues in the register
- `high_risk_count`, `medium_risk_count`: count by risk rating
- `business_outcome_count`: count of distinct business outcome categories
- Exposure totals: sum `delta_to_fallback_dollars` or shortfall amounts across applicable issues
- Employee totals: sum `employee_count` and `pto_liability_dollars` from employee-related issues
- Consent counts: count unique required closing consent IDs

Do not double-count or include null values. Only include exposure amounts where a quantified delta exists.

### Step 9 -- Produce the final JSON

Assemble the object exactly as the answer template prescribes. Every required field must be present. Null fields are used when the data is genuinely unavailable, not as a default for skipped work.

Currency must be integer USD. Percentages must be decimal numbers to the precision specified in the template (typically two decimal places for seller APA tasks, one decimal place for buyer SPA tasks, four decimals for holder percentages). Months must be integers. Dates must be in `YYYY-MM-DD` format when required.

Return only the JSON object. No explanatory prose, no markdown wrapping.

## Task-Specific Guidance

### Seller APA Issue Register

Produced when the prompt describes a seller-side review of buyer-drafted APA terms. Structure: `issue_register` array, `priority_order` array, `summary_metrics` object with aggregate counts and dollar exposures. Compare each draft term against the seller playbook; flag terms where the draft exceeds the seller's acceptable range. Include missing required terms that the playbook requires but the draft omits.

### Buyer SPA Closing and Economics Package

Produced when the prompt describes a buyer-side review with holder-level allocation, closing conditions, and covenant analysis. Requires cap table data for holder allocation. Structure: `economics` (headline value, holder allocation, indemnity package, escrow, NWC adjustment), `closing_conditions` (required consents, material contract conditions, non-blocking notices), `covenants` (employment, restrictive covenants, D&O tail and expenses), `regulatory`, `closing_readiness` (overall status, blockers, tradeable issues).

### M&A Committee Escalation Package

Produced when the prompt asks for committee escalation of out-of-policy terms. The core filter: **only include terms that are out of policy and require committee approval**. Exclude stale, in-policy, or non-committee distractor terms. Structure: `memo` (prepared for, client, deal names, policy ID, dates, value basis), `escalation_terms` array with draft/policy/delta comparisons and benchmark support, `aggregate_summary` with risk counts, exposure totals, and overall recommendation.

### Carveout APA Transition Review

Produced when the prompt describes a carveout asset purchase with transition/separation focus. Structure: `transition_issues` (issue_id, category, source_term_ids, source_record_ids, issue_status, risk_rating, recommended_action, draft_value_normalized, required_position_normalized, quantified_impact_dollars), `required_redlines` (redline_id, related_issue_id, redline_action, must_have_terms), `operational_risk` (overall_risk_rating, overall_posture, priority_order, quantified_exposures, required_closing_consent_ids, material_contract_consent_ids, business_outcomes_protected).

### Buyer SPA Deviation Matrix

Produced when the prompt describes a buyer-side deviation matrix. Organizes the buyer's positions on indemnity cap/basket, survival/knowledge qualifiers, materiality scrape, escrow/holdback/release, consent closing conditions, HSR, and material contracts. Structure: `position_matrix` array, `closing_blockers` array, `risk_totals` object. Each position includes final position codes, priority rank, and shortfall amounts. Closing blockers identify specific consent, regulatory, and contract issues that must be resolved before closing.

## Calculation Rules

- **Dollar amounts from percent**: `round(headline_purchase_price * (percent / 100))`
- **Delta to fallback**: `draft_amount - fallback_amount` (positive when draft exceeds fallback in the direction unfavorable to the client)
- **Shortfall**: `fallback_amount - draft_amount` (positive when draft falls short of what the client needs)
- **Employee PTO liability**: sum of accrued PTO liabilities from employee records, in integer dollars
- **Total quantified exposure**: sum of delta amounts or shortfall amounts across quantified issues, computed for low and high bounds where risk estimates provide a range

## Output Conventions

- Return only valid JSON conforming exactly to the answer template
- Use `null` only for genuinely unavailable data, never as a placeholder
- Empty arrays `[]` for missing source_term_ids on missing-required-term issues
- Stable source IDs exactly as returned by the workbench -- no truncation or invention
- Integer dollars, decimal percentages, integer months
- Dates in `YYYY-MM-DD` format when required
- No explanatory prose outside the JSON object
