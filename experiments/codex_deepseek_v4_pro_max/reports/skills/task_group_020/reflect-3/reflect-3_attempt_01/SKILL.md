## When to Use

Use this skill when the task involves analysing M&A deal workbench data through a REST API, interpreting draft agreement terms against a playbook or policy, or preparing structured legal/transactional outputs (issue registers, deviation matrices, closing packages, escalation memos, transition reviews). The workbench models buy-side and sell-side reviews of asset purchase agreements, stock purchase agreements, and public-company mergers.

## Workbench Data Model

The workbench exposes a read-only REST API at `<TASK_ENV_BASE_URL>`. Discover the base URL from the task prompt or from an `environment_access.md` file when present.

### Core Entities

- **Deal** (`/api/deals/<deal_id>`): transaction metadata including headline value, upfront cash, stock value, milestone value, client side (buyer/seller), playbook ID, policy ID, transaction type, industry, and strategic context.
- **Draft Terms** (`/api/deals/<deal_id>/terms`): individual provisions extracted from the current agreement draft. Each term has a stable `term_id`, `category`, `draft_value` (prose), `numeric_value`, `unit`, `basis`, `clause_ref`, `staleness_flag`, and `counterparty_rationale`.
- **Playbook Rules** (`/api/playbooks/<playbook_id>/rules`): the client's negotiating positions. Each rule has a `category`, `preferred_position`, `fallback_position`, `limit_value`, `limit_unit`, `required_action`, and `risk_default`.
- **Policy Thresholds** (`/api/policies/<policy_id>/thresholds`): hard committee-approval limits with `threshold_value`, `threshold_unit`, `policy_standard`, `restricted_flag`, and `approval_required`.
- **Consents** (`/api/deals/<deal_id>/consents`): third-party approvals with `required_for_closing`, `risk_rating`, `amount_at_risk`, and counterparty details.
- **Material Contracts** (`/api/deals/<deal_id>/material-contracts`): significant agreements with `annual_revenue`, `consent_required`, `change_of_control`, and `anti_assignment` flags.
- **Employees** (`/api/deals/<deal_id>/employees`): workforce groups with `count`, `pto_liability`, `service_credit_required`, `warn_risk`, and `draft_treatment`.
- **Regulatory** (`/api/deals/<deal_id>/regulatory`): HSR and other regulatory requirements with `hsr_required`, `hell_or_high_water_required`, and `regulatory_approval`.
- **Risk Estimates** (`/api/deals/<deal_id>/risk-estimates`): scenario-modeled exposures with `exposure_low`, `exposure_high`, `category`, and `estimate_id`.
- **Benchmarks** (`/api/deals/<deal_id>/benchmarks`): market precedent data with `median_value`, `upper_quartile`, `sample_size`, and `metric`.
- **Diligence Findings** (`/api/deals/<deal_id>/diligence-findings`): identified risks with `finding_id`, `severity`, `amount`, and `topic`.
- **Cap Table** (`/api/deals/<deal_id>/cap-table`): holder-level ownership with `fully_diluted_pct`, `security_class`, and share counts.
- **Deal Notes** (`/api/deals/<deal_id>/notes`): counsel commentary on negotiation posture and counterparty rationale.

### Read-Only SQL

When available, `POST /api/query` with `{"token": "deal-workbench-readonly", "sql": "<query>"}` provides cross-table access. Note that not all tables are queryable via SQL—use the REST endpoints as the primary data source and SQL for cross-table verification when the endpoints are insufficient.

## Solving Workbench Tasks

### Step 1: Orient to the Deal

Fetch the deal record first. Note the `client_side` (buyer or seller—this determines whose playbook or policy to apply and which direction deviations run), the `headline_value` (the base for most dollar calculations), the `playbook_id` or `policy_id`, and the `transaction_type`.

### Step 2: Gather All Available Records

Fetch every endpoint listed in the deal's `links` block. Do not stop at the endpoints mentioned in the prompt—pull consents, employees, material contracts, regulatory, risk estimates, benchmarks, diligence findings, notes, and documents. Missing a record that contains a relevant numeric value or risk flag is a common failure mode.

### Step 3: Read the Answer Template First

Every task includes `input/payloads/answer_template.json`. Study it before building the answer:
- Note every `allowed_enum`—use only these values exactly as spelled.
- Note the `required_output_shape` or `required_top_level_fields`—include every field; omit none.
- Note `stable_issue_ids` or `possible_issue_ids` when present—these are the universe of issues the judge expects. Do not invent new issue IDs or omit ones listed.
- Note the `units` declaration (currency as integer dollars, percent points to two decimals, months as integers, holder percentages to four decimals).

### Step 4: Map Data to Template Fields

For each issue or position in the template:

1. **Find the matching draft term(s)** by `category` and `deal_id`. Use the term's `numeric_value` and `unit` directly. If no draft term exists but the playbook or surrounding data demands one, the status is `missing_required_term` with an empty `source_term_ids` array.

2. **Compare against the playbook or policy**. Determine the status:
   - `in_policy`: draft meets or exceeds the preferred position
   - `draft_below_playbook`: draft is below the preferred position but meets or exceeds the fallback
   - `out_of_policy`: draft is below the fallback position or violates a restricted policy threshold
   - `draft_exceeds_playbook`: draft is more aggressive than the playbook allows (e.g., higher escrow for a seller, higher cap for a buyer)
   - `missing_required_term`: draft is silent but the playbook or deal data shows the term is needed

3. **Assign risk ratings** from the playbook's `risk_default` or the consent's `risk_rating`. Do not guess—use the data source that most directly addresses the issue. For issues spanned by multiple risk indicators, use the highest applicable rating.

4. **Assign recommended actions** that match the playbook's `required_action` and the direction of the deviation. Common patterns:
   - Seller side: `escalate` buyer-friendly provisions, `delete` financing conditions, `revise` above-playbook caps/escrows
   - Buyer side: `escalate` seller-friendly provisions, `add` missing protections, `revise` below-playbook caps/survival
   - Policy escalations: `reject` for fundamental governance violations, `approve_with_conditions` for quantifiable overages

### Step 5: Calculate Dollar Amounts Correctly

- Use the deal's `headline_value` as the purchase price base unless a term or playbook rule explicitly states a different basis (e.g., "enterprise value" or "upfront cash").
- For percentage-based amounts: dollar amount = round(headline_value × percentage / 100). Use integer dollars.
- For holder allocations in stock purchases: total consideration = round(headline_value × fully_diluted_pct), cash = round(upfront_cash × fully_diluted_pct), stock = round(stock_value × fully_diluted_pct).
- Deltas and shortfalls: always subtract the more favourable position from the less favourable one so the result is positive.
- When a term provides its own dollar equivalent (e.g., "5.5% of equity value, equal to 61.6 million dollars"), cross-check your calculation against the stated amount.

### Step 6: Source Every Record Reference

- `source_term_ids`: use the exact `term_id` strings from the terms endpoint. Use an empty array `[]` for missing terms.
- `source_record_ids`: use stable IDs from consents, employees, material contracts, diligence findings, or risk estimates that directly support the issue.
- `source_estimate_id`: always reference the specific `estimate_id` when populating exposure fields.
- Consent and contract IDs in blocker lists must match the workbench records exactly.

### Step 7: Handle Missing and Stale Data

- **Stale terms** (`staleness_flag: "stale"`): exclude from the answer entirely. Only current terms are in play.
- **Missing terms**: only flag as `missing_required_term` when the playbook or policy explicitly covers the category OR when the surrounding deal data (consents, employees, regulatory, diligence findings) demonstrates a concrete need. Do not flag abstract "standard practice" items without workbench data support.
- **Fields without data**: use `null` (not 0) when a numeric field is genuinely inapplicable. Use `0` when the value is known to be zero. Use `"not_found_in_current_records"` for status fields when the workbench has no relevant record.

### Step 8: Validate Before Submitting

- Every enum value matches the template's `allowed_enums` exactly (case-sensitive).
- Every `issue_id` or `redline_id` is from the template's stable list.
- All dollar amounts are integers, percentages have the required decimal precision.
- The output is valid JSON with no trailing commas and no prose outside the JSON structure.
- Issue arrays are sorted as the template specifies (by `issue_id` ascending unless a priority order is requested elsewhere).

## Common Failure Patterns

- **Over-inclusion**: flagging issues that have no supporting data in the workbench. Only raise issues the playbook, policy, or explicit deal records justify.
- **Wrong direction**: applying buyer-side reasoning to a seller-side task or vice versa. Always check `client_side` first.
- **Currency basis errors**: using `headline_value` when a term explicitly uses `enterprise value` or `upfront cash`.
- **Enum mismatches**: using values not in the template's allowed lists (e.g., "Medium" instead of "MEDIUM").
- **Stale data**: including terms with `staleness_flag: "stale"` in the analysis.
- **Missing source references**: failing to populate `source_term_ids`, `source_record_ids`, or `source_estimate_id` with stable workbench identifiers.
- **Template drift**: omitting required top-level fields or including extra fields the template does not specify.
