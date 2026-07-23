# Workbench Data Model

The deal workbench exposes 14 object types. This is the transferable field map — field names and semantics, not any specific deal's values. Use it to know what to pull and what each field means when classifying and quantifying.

## deals (the deal record)
- `deal_id`, `client_name`, `client_side` (`buyer` | `seller`), `counterparty_name`, `target_name`, `project_name`
- `transaction_type` (e.g. Asset purchase agreement, Stock purchase agreement, Carveout asset purchase agreement, Public company merger)
- `currency`, `headline_value` (the primary value base), `upfront_cash`, `stock_value`, `milestone_value`
- `playbook_id` **or** `policy_id` (a deal has one controlling framework)
- `signing_date`, `meeting_date`, `status`, `industry`, `strategic_context`
- `links` — map of available sub-resources for the deal

## draft_terms
Each draft provision:
- `term_id` (stable, e.g. `TERM_<DEAL>_NN`), `category`, `clause_ref`, `source_document`
- `basis` (e.g. `purchase price`, `enterprise value`, `equity value`, `general representations`, `material contracts`, `approved list`)
- `numeric_value`, `unit` (`percent_points` | `months` | `dollars` | `contracts` | `boolean` | `text` | `restricted_change` | `additional_carveouts`)
- `draft_value` (prose), `counterparty_rationale`, `staleness_flag` (`current` | `stale`), `last_updated`

Exclude `staleness_flag: "stale"` terms from escalation/issue sets when the prompt says to.

## playbook_rules (framework when `playbook_id` is set)
Each rule is keyed by `category` and gives the counsel position:
- `preferred_position` (prose), `fallback_position` (prose)
- `limit_unit`, `limit_value` (the preferred threshold)
- `risk_default` (`Low` | `Medium` | `High`) — use as the issue risk rating
- `required_action` (prose; often "Escalate ...") — maps to `recommended_action: escalate` when the deviation matches
- `basis` (must match the term's basis for the comparison to be valid)

Common playbook categories: `escrow`, `financing_condition`, `indemnity_cap`, `survival_period`, `transition_services`, `consent_closing_condition`, `materiality_scrape`, `employee_service_credit`.

## policy_thresholds (framework when `policy_id` is set, e.g. committee policy)
Each threshold is keyed by `category`:
- `policy_standard` (prose), `threshold_unit`, `threshold_value`
- `restricted_flag` (`yes` | `no`) — `yes` means M&A Committee approval required
- `approval_required` (e.g. `M&A Committee` | `General Counsel`) — only committee-restricted items get escalated
- `basis`, `notes`

For committee-escalation tasks: escalate only `current` draft terms that are `out_of_policy` or `restricted` for the committee; exclude stale, in-policy, and non-committee (e.g. General Counsel) distractor terms.

## risk_estimates
Deal-level exposure ranges, keyed by `category`:
- `estimate_id` (stable, e.g. `RSK_<DEAL>_NN`)
- `category`: `closing certainty`, `indemnity leakage`, `transition disruption`
- `exposure_low`, `exposure_high` (integer dollars), `confidence`, `method`, `notes`

Aggregate exposure = sum of low/high over the components the template includes (commonly closing certainty + indemnity leakage; transition disruption is often excluded unless the deal is a carveout).

## benchmarks
Market data, keyed by `category`:
- `benchmark_id`, `category` (`termination economics`, `indemnity`, `survival`)
- `metric`, `median_value`, `upper_quartile`, `mean_value`, `sample_size`, `notable_precedent`

Map term → benchmark by category: fees → "termination economics / fee percent of equity value"; indemnity cap → "indemnity / general cap percent of purchase price"; survival → "survival / general representation survival months". Position vs. median/upper quartile: `at_or_below_median`, `between_median_and_upper_quartile`, `at_upper_quartile`, `above_upper_quartile`, `not_applicable`.

## consents
- `consent_id` (stable), `consent_type` (`change of control` | `assignment` | `landlord consent`), `contract_name`, `counterparty`
- `required_for_closing` (`yes` | `no`), `amount_at_risk`, `risk_rating` (`Low`/`Medium`/`High`)

Closing consent amount at risk = sum of `amount_at_risk` where `required_for_closing: yes`. `required_for_closing: no` consents are notice-only / non-blocking.

## material_contracts
- `contract_id` (stable), `contract_name`, `contract_type` (`customer` | `technology license` | `supplier`)
- `change_of_control` (`yes`/`no`), `anti_assignment` (`yes`/`no`), `consent_required` (`yes` | `notice only`)
- `annual_revenue`

Material-contract revenue requiring consent = sum of `annual_revenue` where `consent_required: yes`. `notice only` contracts are non-blocking notices.

## employees
- `employee_id` (stable), `employee_group` (e.g. executives, engineering and product, field and operations), `count`
- `pto_liability`, `service_credit_required` (`yes`/`no`), `warn_risk` (`low`/`medium`/`high`)
- `draft_treatment` (prose), `playbook_requirement` (prose)

Totals: `count` and `pto_liability` summed across groups. `warn_risk` of `medium`/`high` flags WARN-exposure employee IDs. Field-selection rights ("Buyer may select continuing employees") create retention/service-credit issues.

## regulatory
- `hsr_required` (`yes`/`no`), `hell_or_high_water_required` (`yes`/`no`/`limited covenant`)
- `regulatory_approval` (e.g. `HSR only`, `HSR and industry review`, `none expected`)
- `threshold_basis` (e.g. `size-of-transaction`), `notes`

`hsr_required: yes` with no draft HSR term → `missing_required_term` HSR covenant/closing condition. `hell_or_high_water_required: no` → the required effort covenant is bounded (reasonable efforts), not hell-or-high-water.

## diligence_findings
- `finding_id` (stable), `topic` (customer concentration, privacy and security, working capital), `severity`, `amount`, `source`, `notes`

Findings justify special indemnities, escrows, and NWC collars. A customer-concentration finding can validate a higher indemnity-cap fallback; a working-capital finding calls for a dollar-for-dollar-outside-collar NWC mechanic with the finding as the collar amount and source.

## cap_table
- `holder`, `security_class` (`options` | `common stock` | `preferred stock`)
- `shares`, `as_converted_shares`, `fully_diluted_pct` (use the **stored** value verbatim), `role_notes`

Allocate total consideration by `fully_diluted_pct × headline_value`; split cash vs. stock by each holder's pro-rata share of the cash pool and stock pool (every holder receives the same cash:stock blend). Report `fully_diluted_pct` to the precision the template states, using the stored value.

## deal_notes / documents
Context only (negotiation posture, counterparty rationale, finance follow-ups, draft versions). Use to confirm intent and staleness, not as numeric sources.
