# Task Workflows

Task-type-specific guidance for M&A deal-workbench outputs. Read the section matching the task shape after identifying the task type from the prompt and answer template.

## Seller-Side APA Issue Register

Prompt signals: "seller-side counsel", "issue register", "playbook", "priority order", "summary metrics".

### Data Sources

- Deal record: `/api/deals/<deal_id>`
- Draft terms: `/api/deals/<deal_id>/terms`
- Playbook rules: `/api/playbooks/<playbook_id>/rules`
- Risk estimates: `/api/deals/<deal_id>/risk-estimates`
- Employees: `/api/deals/<deal_id>/employees`
- Consents: `/api/deals/<deal_id>/consents`
- Regulatory: `/api/deals/<deal_id>/regulatory`
- Benchmarks: `/api/deals/<deal_id>/benchmarks`
- Notes: `/api/deals/<deal_id>/notes`

### Issue Construction

For each issue in the template's `possible_issue_ids`, determine whether it applies:

1. If a matching draft term exists, compare against playbook rule preferred/fallback values.
2. If no draft term exists but the playbook requires it or surrounding data shows it is needed, classify as `missing_required_term`.
3. Fill all template fields using the computation rules from business_patterns.md.

### Summary Metrics

- `headline_value_dollars`: from `deal.headline_purchase_price`.
- `total_quantified_exposure_low_dollars`: sum of risk estimate `exposure_low_dollars` for relevant categories.
- `total_quantified_exposure_high_dollars`: sum of risk estimate `exposure_high_dollars` for relevant categories.
- `total_negotiation_delta_dollars`: sum of all issue `delta_to_fallback_dollars`.
- `required_closing_consent_count`: count of consents with `condition_type: "closing_condition"`.
- `total_employee_count`: from employee records.
- `total_pto_liability_dollars`: sum of `pto_accrued_dollars`.

## Buyer-Side SPA Closing and Economics Package

Prompt signals: "buyer-side counsel", "SPA closing", "economics package", "holder allocation", "closing readiness".

### Data Sources

- Deal record: `/api/deals/<deal_id>`
- Draft terms: `/api/deals/<deal_id>/terms`
- Playbook rules: `/api/playbooks/<playbook_id>/rules`
- Cap table: `/api/deals/<deal_id>/cap-table`
- Consents: `/api/deals/<deal_id>/consents`
- Employees: `/api/deals/<deal_id>/employees`
- Material contracts: `/api/deals/<deal_id>/material-contracts`
- Regulatory: `/api/deals/<deal_id>/regulatory`
- Diligence findings: `/api/deals/<deal_id>/diligence-findings`
- Risk estimates: `/api/deals/<deal_id>/risk-estimates`

### Economics Section

Fill `headline_value`, `upfront_cash`, `stock_value`, `milestone_value` from the deal record. Compute holder allocation from the cap table (see business_patterns.md).

### Indemnity Package

Compare draft indemnity cap percent and survival months against buyer playbook. Classify materiality scrape from draft term language. Rate risk: HIGH if draft cap is well below buyer fallback or survival is short.

### NWC Adjustment

Check diligence findings for working-capital-related findings. If a finding indicates a working-capital issue, require a NWC adjustment. Default mechanic is `dollar_for_dollar_outside_collar` when an NWC target is identified.

### Closing Readiness

Classify `overall_status`:
- `READY`: no HIGH-risk closing blockers, all required conditions addressed.
- `READY_WITH_CONDITIONS`: some blockers exist but fixable before signing.
- `NOT_READY`: HIGH-risk consent or regulatory blockers unresolved.

Blockers include: HIGH-risk consents, missing HSR condition, material contracts requiring consent, indemnity package gaps, and NWC issues.

## M&A Committee Escalation Package

Prompt signals: "M&A Committee", "escalation package", "policy thresholds", "benchmark", "out of policy".

### Data Sources

- Deal record: `/api/deals/<deal_id>`
- Draft terms: `/api/deals/<deal_id>/terms`
- Policy thresholds: `/api/policies/<policy_id>/thresholds`
- Benchmarks: `/api/deals/<deal_id>/benchmarks`
- Risk estimates: `/api/deals/<deal_id>/risk-estimates`
- Notes: `/api/deals/<deal_id>/notes`

### Escalation Filtering

Only escalate terms that are `out_of_policy` against the policy thresholds. Exclude terms that are in-policy even if they appear notable. Exclude non-committee categories if the policy only covers specific term types.

### Delta and Exposure

Compute delta by comparing draft metric vs. policy threshold. For quantified exposure, use risk estimates linked to the term. For unquantified exposure (fiduciary out, MAE carveouts), set `type: "not_quantified"`.

### Recommendation Logic

- `reject`: draft removes a core fiduciary protection (e.g., intervening event trigger), or draft fundamentally undermines board obligations.
- `approve_with_conditions`: draft exceeds thresholds but can be remedied with specific changes.
- `approve`: draft is at or within policy thresholds.

## Carveout APA Transition Review

Prompt signals: "carveout APA", "transition review", "transition and separation terms", "redlines", "operational risk".

### Data Sources

- Deal record: `/api/deals/<deal_id>`
- Draft terms: `/api/deals/<deal_id>/terms`
- Playbook rules: `/api/playbooks/<playbook_id>/rules`
- Consents: `/api/deals/<deal_id>/consents`
- Employees: `/api/deals/<deal_id>/employees`
- Material contracts: `/api/deals/<deal_id>/material-contracts`
- Regulatory: `/api/deals/<deal_id>/regulatory`
- Documents: `/api/deals/<deal_id>/documents`
- Risk estimates: `/api/deals/<deal_id>/risk-estimates`

### Transition Issues

Focus on carveout-specific categories: TSA scope/duration/fees, IP/domain transition, employee continuity, customer consent termination rights, outside date extension, tax allocation (Section 1060), transfer tax split, and governing law/forum.

For draft values, normalize the actual draft content into the template's `draft_value_normalized` shape. For required positions, derive from the playbook's preferred and fallback.

### Required Redlines

Each redline maps to a transition issue. `must_have_terms` captures the exact required changes. Use `redline_action: "add"` for missing terms and `"revise"` for terms needing modification.

### Operational Risk

- `overall_risk_rating`: HIGH if any transition issue is HIGH risk.
- `overall_posture`: `revise_before_signing` if HIGH-risk issues exist, `accept_as_drafted` if none.
- Quantified exposures aggregate from consents, employee records, and risk estimates.
- `business_outcomes_protected`: list the seller interests each issue defends.

## Buyer SPA Deviation Matrix

Prompt signals: "buyer-side counsel", "deviation matrix", "position matrix", "closing blockers".

### Data Sources

- Deal record: `/api/deals/<deal_id>`
- Draft terms: `/api/deals/<deal_id>/terms`
- Playbook rules: `/api/playbooks/<playbook_id>/rules`
- Consents: `/api/deals/<deal_id>/consents`
- Material contracts: `/api/deals/<deal_id>/material-contracts`
- Regulatory: `/api/deals/<deal_id>/regulatory`
- Diligence findings: `/api/deals/<deal_id>/diligence-findings`
- Risk estimates: `/api/deals/<deal_id>/risk-estimates`

### Position Matrix

Cover every `issue_id` listed in the template. For each:

1. Find matching draft terms (may be one or multiple).
2. Compare against buyer playbook preferred and fallback values.
3. Classify status and assign risk rating.
4. Select `final_position` from the template's allowed values based on what the buyer needs.
5. Set `priority_rank` starting from 1 (highest priority).

### Priority Assignment

- Rank 1: consent closing conditions (block closing).
- Rank 2: HSR/regulatory conditions (block closing).
- Rank 3: material contract consent conditions (block closing).
- Rank 4+: economic terms ordered by dollar impact size.

### Status Detection for Secondary Fields

When the template includes fields like `basket_status`, `knowledge_qualifier_status`, `escrow_agent_status`, `release_status`:

- `not_found_in_current_records`: the draft terms and deal records do not mention this item.
- `found`: the item is present in draft terms or supporting records.
- `not_applicable`: the issue category does not involve this item.

### Risk Totals

- `headline_purchase_price_usd`: from deal record.
- All count fields: derived from position matrix and blocker arrays.
- `indemnity_cap_shortfall_to_fallback_usd`: `fallback_amount_usd - draft_amount_usd`.
- `total_modeled_exposure_low_usd` / `_high_usd`: aggregate from risk estimates.
- `highest_modeled_exposure_category`: the category with the largest exposure high value.

## General Rules

### Valid JSON Output

Always return exactly one JSON object. Do not wrap in markdown code fences unless the prompt explicitly requests it. Do not include prose outside the JSON.

### Stable IDs

Use IDs exactly as they appear in API responses. Never invent IDs. Use empty arrays when no source IDs exist.

### Values Only from Data

Every number in the output must derive from API data or computation from that data. Do not guess or hardcode.
