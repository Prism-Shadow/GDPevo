# Workbench data model

Fourteen deal-scoped tables. Every row carries `deal_id`; the same table names are
available through the read-only SQL endpoint named in the task's environment notes.

`deals`, `draft_terms`, `playbook_rules`, `policy_thresholds`, `benchmarks`,
`risk_estimates`, `cap_table`, `consents`, `employees`, `material_contracts`,
`regulatory`, `diligence_findings`, `deal_notes`, `documents`

The deal record returns a `links` object naming the route for each of its child
collections — follow it instead of assuming routes.

## Which fields decide things

### deals
`deal_id`, `client_name`, `client_side` (`buyer`/`seller`), `counterparty_name`,
`project_name`, `target_name`, `transaction_type`, `headline_value`, `upfront_cash`,
`stock_value`, `milestone_value`, `signing_date`, `meeting_date`, `status`,
`playbook_id`, `policy_id`, `strategic_context`.

- `headline_value == upfront_cash + stock_value`; `milestone_value` sits outside it.
- Exactly one of `playbook_id` / `policy_id` is populated — that is your standard.
- `client_side` sets the polarity of every deviation.
- `strategic_context` sometimes states the expected count or scope of the deliverable
  outright, in words. Read it before deciding how many rows to produce.

### draft_terms
`term_id`, `category`, `clause_ref`, `draft_value` (prose), `numeric_value`, `unit`,
`basis`, `source_document`, `counterparty_rationale`, `staleness_flag`, `last_updated`.

- **Only `staleness_flag == "current"` rows are live.** `"stale"` rows are distractors.
- `numeric_value` + `unit` carry the machine-readable value; `draft_value` prose often
  carries a *second* fact the numeric field does not (a dollar figure, a second survival
  period, an exclusion, a removed trigger). Read both.
- `unit` ∈ `percent_points`, `months`, `dollars`, `contracts`, `boolean`, `text`,
  `restricted_change`, `additional_carveouts`.

### playbook_rules
`category`, `preferred_position`, `fallback_position`, `limit_value`, `limit_unit`,
`basis`, `risk_default`, `required_action`, `notes`.

Preferred and fallback live in the prose. `limit_value` is not reliably either one.
`risk_default` is the default `risk_rating` for issues under that rule.
A rule whose `category` has no current draft term is the primary signal for a
`missing_required_term`.

### policy_thresholds
`category`, `policy_standard`, `threshold_value`, `threshold_unit`, `basis`,
`restricted_flag`, `approval_required`, `notes`.

`restricted_flag == "yes"` plus `approval_required` matching the requested body is what
makes a breach escalatable. A row with `approval_required` set to a lower authority is a
distractor even when the draft is near its threshold.

### consents
`consent_id`, `contract_name`, `counterparty`, `consent_type`, `amount_at_risk`,
`required_for_closing`, `risk_rating`, `notes`.

`required_for_closing == "yes"` → closing condition / blocker. `"no"` → notice-only,
non-blocking. Sum `amount_at_risk` over the `"yes"` rows only.

### material_contracts
`contract_id`, `contract_name`, `contract_type`, `annual_revenue`, `consent_required`,
`change_of_control`, `anti_assignment`, `notes`.

`consent_required == "yes"` → blocking. `"notice only"` → excluded / non-blocking.
"Top customer revenue at risk" = the single largest `annual_revenue` among consent-
required customer contracts.

### employees
`employee_id`, `employee_group`, `count`, `pto_liability`, `service_credit_required`,
`warn_risk`, `draft_treatment`, `playbook_requirement`, `notes`.

Groups are typically `executives`, `engineering and product`, `field and operations`.
Totals sum all groups; a metric naming one group (e.g. "field operations PTO") takes
that group's row only. WARN lists take `warn_risk` in `{medium, high}`.

### regulatory
Single object: `hsr_required`, `threshold_basis`, `regulatory_approval`,
`hell_or_high_water_required`, `notes`. Convert `"yes"`/`"no"` to the template's type
(boolean or string enum) as the template dictates.

### risk_estimates
`estimate_id`, `category`, `exposure_low`, `exposure_high`, `method`, `confidence`.
Categories are `closing certainty`, `indemnity leakage`, `transition disruption`.
These are the *only* sanctioned exposure ranges — never model your own.

### benchmarks
`benchmark_id`, `category`, `metric`, `sample_size`, `median_value`, `mean_value`,
`upper_quartile`, `notable_precedent`, `notes`.

Position a draft against `median_value` / `upper_quartile` using the metric that matches
the draft's unit — for a survival benchmark whose metric is "general representation
survival months", compare the *general* period, not the fundamental one.

### cap_table
`holder`, `security_class`, `shares`, `as_converted_shares`, `fully_diluted_pct`,
`role_notes`. `fully_diluted_pct` is a decimal fraction summing to 1.0. Allocate cash and
stock separately by that fraction and confirm each column sums back to its total.

### diligence_findings
`finding_id`, `topic`, `severity`, `amount`, `source`, `notes`.
Topics recur: `customer concentration`, `privacy and security`, `working capital`.
The working-capital finding is the source for a net-working-capital collar; the privacy
finding backs a special indemnity.

### documents / deal_notes
Context only. They carry no gradeable numbers, but notes state what the business team
wants the deliverable to separate (must-have vs tradeable).
