# Workbench record model

The workbench is a normalized set of record families. Almost every one is keyed by deal
ID, so pull all of them for the single deal named in the prompt. Column names below are
the ones that actually drive answers.

## Deal record (one per deal)

`project_name`, `transaction_type`, `client_side` (buyer/seller — this sets which
direction of deviation hurts you), `client_name`, `counterparty_name`, `target_name`,
`industry`, `headline_value`, `upfront_cash`, `stock_value`, `milestone_value`,
`currency`, `signing_date`, `meeting_date`, `playbook_id`, `policy_id`, `status`,
`strategic_context`.

- `headline_value` is the default base for percentage-derived dollar amounts.
- `playbook_id` / `policy_id` name the **one** governing rule set. Do not use another.
- `strategic_context` and `status` often state the deliverable's framing in one line
  (e.g. how many non-standard provisions are up for approval).

## Draft terms (many per deal)

`term_id`, `category`, `draft_value` (prose), `numeric_value`, `unit`, `basis`,
`source_document`, `clause_ref`, `counterparty_rationale`, `last_updated`,
`staleness_flag`.

- `category` is the join key to playbook/policy rules.
- `numeric_value` + `unit` is the machine-readable draft position; `draft_value` prose
  frequently carries a second fact the numeric field does not (a dollar figure that
  confirms the base, an excluded item, a match-right period, a removed trigger).
  **Read the prose for every term.**
- `staleness_flag` other than current means the term is a distractor.
- `clause_ref` is what templates want in a `clause_ref` field — copy it verbatim.

## Playbook rules (per playbook, per category)

`preferred_position`, `fallback_position`, `limit_value`, `limit_unit`, `basis`,
`required_action`, `risk_default`, `notes`.

- `preferred_position` and `fallback_position` are prose but state both numbers; the
  `limit_value` column usually holds the **fallback**, so parse the preferred figure out
  of the prose rather than assuming `limit_value` is the preferred position.
- A fallback often carries a condition ("fallback 15 months if escrow is 10% or higher").
  If the condition is unmet in the draft, the draft is not in policy.
- `risk_default` is a reasonable starting risk rating for that category.
- A playbook category with **no** matching draft term is the main signal for a
  missing-required-term issue.

## Policy thresholds (per policy, per category)

`policy_standard`, `threshold_value`, `threshold_unit`, `basis`, `approval_required`,
`restricted_flag`, `notes`.

- For committee-escalation deliverables, a term qualifies only if it breaches
  `threshold_value` **and** its category is restricted / routed to that committee.
  In-policy terms, non-restricted categories, and stale terms are all excluded — the
  template usually has explicit fields to name what you excluded.
- `policy_standard` prose lists required elements (e.g. the triggers a fiduciary out must
  contain). Removal of any listed element is the deviation.

## Benchmarks

`benchmark_id`, `category`, `metric`, `sample_size`, `median_value`, `mean_value`,
`upper_quartile`, `notable_precedent`.

Position a draft figure against median and upper quartile, matching the template's
position enum. Compare against the metric the benchmark actually measures — if the metric
names general representations, compare the general figure, not the fundamental one. Where
no benchmark covers the category, use the not-applicable enum rather than inventing one.

## Risk estimates

`estimate_id`, `category` (closing certainty, indemnity leakage, transition disruption),
`exposure_low`, `exposure_high`, `confidence`, `method`.

Attach an estimate to an issue by category, and cite `estimate_id` where the template asks
for a source. Aggregate only the categories the template's inclusion list names.

## Cap table

`holder`, `security_class`, `shares`, `as_converted_shares`, `fully_diluted_pct`,
`role_notes`.

`fully_diluted_pct` is a fraction that sums to 1 across holders. Allocate consideration by
multiplying each consideration component (cash, stock, total) by that fraction; the
per-holder totals must sum back to the deal totals. `role_notes` flags which holder groups
need support agreements or restrictive covenants.

## Consents

`consent_id`, `contract_name`, `counterparty`, `consent_type`, `required_for_closing`,
`risk_rating`, `amount_at_risk`.

`required_for_closing` is the sole test for whether a consent is a closing condition or
blocker; everything else is a notice / post-closing item. Closing-consent amount at risk
is the sum of `amount_at_risk` over the required-for-closing rows only.

## Employees

`employee_id`, `employee_group`, `count`, `draft_treatment`, `playbook_requirement`,
`pto_liability`, `service_credit_required`, `warn_risk`.

`draft_treatment` versus `playbook_requirement` is the issue: selection/cherry-pick rights
and disclaimed service credit are the recurring deviations. Total headcount and total PTO
sum across groups; a field scoped to one group (a field-operations PTO figure) takes that
group's row only.

## Material contracts

`contract_id`, `contract_name`, `contract_type`, `annual_revenue`, `anti_assignment`,
`change_of_control`, `consent_required`.

`consent_required` distinguishes consent contracts from notice-only ones. Revenue
requiring consent sums `annual_revenue` over the consent-required rows only.

## Regulatory (one per deal)

`hsr_required`, `threshold_basis`, `regulatory_approval`,
`hell_or_high_water_required`, `notes`. Copy these values through rather than reasoning
about them; templates usually mirror the same vocabulary.

## Diligence findings

`finding_id`, `topic`, `severity`, `amount`, `source`. Findings supply the amounts behind
special indemnities, working-capital collars, and privacy exposure, and the `finding_id`
that templates ask you to cite.

## Deal notes and documents

`note_id` / `document_id`, author, date, topic, content, title, version. Notes state the
business framing — e.g. splitting must-have protections from tradeable terms, or which
exposures finance wants quantified. Use them to decide framing fields, not numbers.
