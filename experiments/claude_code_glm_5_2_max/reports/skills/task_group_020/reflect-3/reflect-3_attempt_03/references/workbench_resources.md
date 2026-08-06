# Workbench resources and what each contributes

The deal record at `/api/deals/<deal_id>` is the root. Its `links` map points to every
sub-resource. Fetch all of them for a complete analysis; omitting one is the most common cause of
missed issues.

## Deal record (`/api/deals/<deal_id>`)

| Field | Use |
|---|---|
| `client_side` | `buyer` or `seller` — sets the direction of every playbook comparison |
| `headline_value` | default dollar basis for `purchase price` / `equity value` terms |
| `upfront_cash`, `stock_value`, `milestone_value` | components; `headline_value == upfront_cash + stock_value + milestone_value` |
| `transaction_type` | APA vs SPA vs merger vs carveout — drives which template issues apply (carveouts need Section 1060 / transfer tax / TSA / IP-transition; mergers need fiduciary-out / RTF / MAE) |
| `playbook_id` | `PB_SELLER_A` (seller) or `PB_BUYER_A` (buyer) — fetch `/api/playbooks/<id>/rules` |
| `policy_id` | when set, fetch `/api/policies/<id>/thresholds` for committee escalation tasks |
| `signing_date`, `meeting_date` | memo header / committee routing dates (format `YYYY-MM-DD`) |
| `status` | `draft review`, `negotiation`, `buyer draft markup`, `committee escalation`, `transition schedule review`, `closing package review` |

## Draft terms (`/terms`)

Each term: `term_id`, `category`, `numeric_value`, `unit`, `basis`, `clause_ref`,
`source_document`, `counterparty_rationale`, `staleness_flag`, `last_updated`.

- `staleness_flag == "stale"` → distractor; exclude from escalation unless explicitly required.
- `unit` tells you how to read `numeric_value`: `percent_points`, `months`, `contracts`,
  `dollars`, `boolean`, `text` (text terms have `numeric_value: null`).
- `basis` tells you which deal-value figure to multiply a percent by.

## Playbook rules (`/api/playbooks/<playbook_id>/rules`)

Each rule: `category`, `preferred_position`, `fallback_position`, `limit_value`, `limit_unit`,
`risk_default`, `required_action`.

- `preferred_position` / `fallback_position` carry the textual stance; `limit_value` is the numeric
  threshold (preferred). Extract both numbers when present (fallback is often a different number).
- `risk_default` → the issue's `risk_rating` unless deal facts override.
- `required_action` ("Escalate …") → maps to `recommended_action` of `escalate` or
  `approve_with_conditions`.

## Policy thresholds (`/api/policies/<policy_id>/thresholds`)

Each threshold: `category`, `threshold_value`, `threshold_unit`, `restricted_flag`,
`approval_required`, `policy_standard`.

- Escalate only where `restricted_flag == "yes"` **and** the draft exceeds `threshold_value` (or
  removes a required trigger / adds a restricted carveout), **and** `approval_required` is the
  M&A Committee.
- `approval_required == "General Counsel"` rows with `restricted_flag == "no"` are distractors even
  if near-threshold.

## Consents (`/consents`)

`consent_id`, `consent_type`, `contract_name`, `counterparty`, `required_for_closing`,
`risk_rating`, `amount_at_risk`.

- `required_for_closing == "yes"` → closing blocker + counts toward
  `required_closing_consent_count` / `required_consent_amount_at_risk`.
- The Apex "Master Commercial Agreement" / change-of-control consent is usually the top-customer
  relationship and the largest single consent amount; it reappears as the top material contract.

## Material contracts (`/material-contracts`)

`contract_id`, `contract_name`, `contract_type`, `annual_revenue`, `anti_assignment`,
`change_of_control`, `consent_required` (`yes` / `notice only`).

- `consent_required == "yes"` → closing-condition contract; revenue counts toward
  `material_contract_revenue_requiring_consent`.
- `consent_required == "notice only"` → non-blocking notice; goes in `non_blocking_notices` /
  `excluded_contract_ids`.

## Employees (`/employees`)

Grouped rows: `employee_id`, `employee_group`, `count`, `pto_liability`,
`service_credit_required`, `warn_risk`, `draft_treatment`, `playbook_requirement`.

- Sum `count` → total/continuing employee count; sum `pto_liability` → PTO liability total.
- `warn_risk == "medium"` groups → WARN-risk employee IDs.
- `service_credit_required == "yes"` → service-credit employee IDs.
- A `draft_treatment` saying "Buyer may select continuing employees" → field-selection /
  cherry-pick issue (mark `field_selection_allowed: false` for the seller position).

## Regulatory (`/regulatory`)

`hsr_required`, `regulatory_approval` (`HSR only` / `HSR and industry review` / `none expected`),
`threshold_basis`, `hell_or_high_water_required`.

- `hsr_required == "yes"` → HSR closing-condition issue / regulatory_clearance blocker.
- `hell_or_high_water_required` → `hell_or_high_water_required` boolean field.

## Diligence findings (`/diligence-findings`)

`finding_id`, `topic`, `severity`, `amount`. Topics: customer concentration, privacy and security,
working capital. The working-capital finding (`"may need a collar"`) is the source for an
NWC-collar adjustment; the privacy finding amount feeds `privacy_finding_amount_usd` and a special
indemnity.

## Benchmarks (`/benchmarks`)

`benchmark_id`, `category`, `metric`, `sample_size`, `median_value`, `upper_quartile`,
`mean_value`. Use to classify draft position as `at_or_below_median` /
`between_median_and_upper_quartile` / `at_upper_quartile` / `above_upper_quartile` /
`not_applicable`. Match the benchmark `category` to the issue (termination economics, indemnity,
survival).

## Risk estimates (`/risk-estimates`)

`estimate_id`, `category` (`closing certainty`, `indemnity leakage`, `transition disruption`),
`exposure_low`, `exposure_high`, `method`, `confidence`. Cite by `estimate_id` in each issue's
`exposure` block; sum the distinct included categories for aggregate exposure.

## Notes (`/notes`) and documents (`/documents`)

Deal-team/counsel/finance notes set negotiation posture ("separate must-haves from tradeables",
"counterparty using timing pressure", "quantify consent and indemnity exposure"). They do not
contain numeric answers but confirm which issues to prioritize.
