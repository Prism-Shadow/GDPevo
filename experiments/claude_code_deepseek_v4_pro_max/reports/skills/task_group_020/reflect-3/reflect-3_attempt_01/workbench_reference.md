# M&A Workbench Data Model Reference

## Core Tables (accessible via REST API and read-only SQL)

### deals
Primary deal record. Key fields: `deal_id`, `project_name`, `transaction_type`, `client_side`, `client_name`, `counterparty_name`, `target_name`, `industry`, `headline_value`, `upfront_cash`, `stock_value`, `milestone_value`, `currency`, `signing_date`, `meeting_date`, `playbook_id`, `policy_id`, `status`, `strategic_context`.

**Value hierarchy:** `headline_value` = total deal value (default basis for % calculations). `upfront_cash` + `stock_value` + `milestone_value` may or may not equal headline. Use `headline_value` as the default calculation basis unless a term or rule explicitly specifies a different basis (e.g., "enterprise value", "upfront_cash").

### draft_terms
Current negotiation terms. Key fields: `term_id`, `deal_id`, `category`, `draft_value` (human-readable), `numeric_value`, `unit` (percent_points, months, dollars, contracts, text, boolean), `basis` (what the % applies to), `source_document`, `clause_ref`, `counterparty_rationale`, `last_updated`, `staleness_flag` (current/stale).

**Staleness rule:** Only use terms where `staleness_flag = "current"`. Terms flagged `stale` represent outdated negotiation positions.

### playbook_rules
Negotiation playbook for a client. Key fields: `playbook_id`, `category`, `preferred_position`, `fallback_position`, `limit_value`, `limit_unit`, `basis`, `required_action`, `risk_default`, `notes`.

**Application:** `preferred_position` = ideal outcome. `fallback_position` = minimum acceptable. If the draft value exceeds `limit_value` in the direction unfavorable to the client, escalate. The `risk_default` field provides the default risk rating when the playbook is violated.

### policy_thresholds
Committee approval policies. Key fields: `policy_id`, `category`, `policy_standard`, `threshold_value`, `threshold_unit`, `basis`, `approval_required`, `restricted_flag`, `notes`.

**Application:** If `restricted_flag = "yes"`, the policy sets a hard limit. If the draft exceeds the `threshold_value`, the term is out of policy and requires committee approval. Any term with `restricted_flag = "no"` is not escalated even if it exceeds threshold.

### employees
Key fields: `employee_id`, `deal_id`, `employee_group`, `count`, `draft_treatment`, `playbook_requirement`, `pto_liability`, `service_credit_required` (yes/no), `warn_risk`, `notes`.

### consents
Third-party consents needed. Key fields: `consent_id`, `deal_id`, `contract_name`, `counterparty`, `consent_type`, `required_for_closing` (yes/no), `risk_rating`, `amount_at_risk`, `notes`.

**Closing conditions:** Consents with `required_for_closing = "yes"` are closing conditions. Those with `"no"` may still require notice or post-closing action.

### regulatory
Key fields: `deal_id`, `hsr_required` (yes/no), `threshold_basis`, `regulatory_approval`, `hell_or_high_water_required` (yes/no), `notes`.

### risk_estimates
Key fields: `estimate_id`, `deal_id`, `category` (closing certainty, indemnity leakage, transition disruption), `exposure_low`, `exposure_high`, `confidence`, `method`, `notes`.

### benchmarks
Market precedent data. Key fields: `benchmark_id`, `deal_id`, `category`, `metric`, `sample_size`, `median_value`, `mean_value`, `upper_quartile`, `notable_precedent`, `notes`.

**Position classification:** Compare the draft value against benchmark quartiles: at_or_below_median, between_median_and_upper_quartile, at_upper_quartile, above_upper_quartile.

### cap_table
Holder ownership for stock deals. Key fields: `deal_id`, `holder`, `security_class`, `shares`, `as_converted_shares`, `fully_diluted_pct`, `role_notes`.

### material_contracts
Key fields: `contract_id`, `deal_id`, `contract_name`, `contract_type`, `annual_revenue`, `anti_assignment`, `change_of_control`, `consent_required`, `notes`.

### diligence_findings
Key fields: `finding_id`, `deal_id`, `topic`, `severity`, `amount`, `source`, `notes`.

### deal_notes
Key fields: `note_id`, `deal_id`, `author`, `note_date`, `topic`, `content`, `source_document`.

---

## Common Enumeration Values

### Risk Ratings
`LOW`, `MEDIUM`, `HIGH` — always uppercase.

### Issue Status (playbook comparison)
- `in_policy` — draft matches or is better than preferred position
- `out_of_policy` — draft violates playbook or policy
- `missing_required_term` — term is absent but required
- `draft_exceeds_playbook` — draft value is worse than playbook limit (higher cap, longer survival, larger escrow for seller; lower cap, shorter survival for buyer)
- `draft_below_playbook` — draft value falls short of playbook requirement (lower fee, shorter non-compete)

### Recommended Actions
`delete`, `revise`, `add`, `accept`, `escalate`, `approve`, `approve_with_conditions`, `reject`

### Regulatory Approval Types
`HSR only`, `HSR and industry review`, `none expected`, `other`

### Fee Models (for transition services)
`at_cost`, `cost_plus_stranded_overhead`, `fixed_fee`, `not_applicable`

### Tax Allocation Methods
`buyer_sole_discretion`, `seller_sole_discretion`, `mutually_agreed_section_1060`

### Forum Choices
`Delaware Court of Chancery or Delaware federal court`, `state court`, `federal court`, `other`

---

## Dollar Amount Conventions

1. Identify the correct basis for each % term — check `basis` on both the draft term and the playbook rule
2. `amount = round(percent / 100 * basis)` — integer dollars
3. When a term has no explicit basis, default to `headline_value`
4. Enterprise value = headline_value for most deals (unless separate enterprise value is stated)
5. For holder consideration allocation: `cash_amount = fully_diluted_pct * upfront_cash`, `stock_amount = fully_diluted_pct * stock_value`
