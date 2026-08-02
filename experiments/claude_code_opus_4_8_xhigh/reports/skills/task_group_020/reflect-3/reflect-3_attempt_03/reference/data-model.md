# Workbench data model

One relational store behind both the HTML pages and the JSON API. Every table carries `deal_id`;
filter on it exactly. Per-deal record endpoints are enumerated by the `links` object on the deal
record itself, so you never need to guess a route.

| Table | ID prefix | Fields that drive the analysis |
|---|---|---|
| `deals` | `PRJ_…` | `client_name`, `client_side` (buyer/seller), `counterparty_name`, `target_name`, `project_name`, `transaction_type`, `headline_value`, `upfront_cash`, `stock_value`, `milestone_value`, `currency`, `signing_date`, `meeting_date`, `status`, `industry`, `strategic_context`, `playbook_id`, `policy_id` |
| `draft_terms` | `TERM_…` | `category`, `draft_value` (prose), `numeric_value`, `unit`, `basis`, `clause_ref`, `source_document`, `counterparty_rationale`, `last_updated`, **`staleness_flag`** |
| `playbook_rules` | `PB_…` | `category`, `preferred_position`, `fallback_position`, `limit_value`, `limit_unit`, `basis`, `required_action`, `risk_default`, `notes` |
| `policy_thresholds` | `POL_…` | `category`, `policy_standard`, `threshold_value`, `threshold_unit`, `basis`, `restricted_flag`, `approval_required`, `notes` |
| `benchmarks` | `BM_…` | `metric`, `category`, `sample_size`, `median_value`, `mean_value`, `upper_quartile`, `notable_precedent` |
| `risk_estimates` | `RSK_…` | `category` (closing certainty / indemnity leakage / transition disruption), `exposure_low`, `exposure_high`, `method`, `confidence` |
| `cap_table` | — | `holder`, `security_class`, `shares`, `as_converted_shares`, `fully_diluted_pct`, `role_notes` |
| `consents` | `CNS_…` | `contract_name`, `counterparty`, `consent_type`, `amount_at_risk`, **`required_for_closing`**, `risk_rating`, `notes` |
| `employees` | `EMP_…` | `employee_group`, `count`, `pto_liability`, `service_credit_required`, `warn_risk`, `draft_treatment`, `playbook_requirement`, `notes` |
| `material_contracts` | `MAT_…` | `contract_name`, `contract_type`, `annual_revenue`, **`consent_required`** (yes / no / notice only), `change_of_control`, `anti_assignment` |
| `regulatory` | — | `hsr_required`, `threshold_basis`, `regulatory_approval`, `hell_or_high_water_required`, `notes` (one row per deal) |
| `diligence_findings` | `FND_…` | `topic`, `severity`, `amount`, `source`, `notes` |
| `deal_notes` | `NOTE_…` | `topic`, `content`, `author`, `note_date`, `source_document` |
| `documents` | `DOC_…` | `document_type`, `title`, `version`, `effective_date`, `summary` |

## Reading notes

- **`playbook_id` xor `policy_id`.** A playbook deal is a bilateral negotiation review measured
  against preferred/fallback positions. A policy deal is an internal committee escalation
  measured against thresholds plus `restricted_flag` and `approval_required`.
- **`draft_value` prose carries facts the numeric column does not** — a second amount, a
  carve-out list, an exclusion, a duration alongside a percentage, an explicit dollar figure
  usable to back-solve the base. Parse the sentence, don't stop at `numeric_value`.
- **`numeric_value` is unit-dependent.** Read it together with `unit`
  (`percent_points`, `months`, `dollars`, `contracts`, `boolean`, `text`, and change-count units
  such as `restricted_change` / `additional_carveouts`, where the number is a *count of
  deviations*, not a magnitude).
- **`basis`** names the measurement base for the term (purchase price, enterprise value, equity
  value, general representations, material contracts, continuing employees, …). It decides which
  deal figure a percentage multiplies.
- **`playbook_requirement` on the employee rows** is a playbook position even though it lives
  outside `playbook_rules`; the same applies to `regulatory` fields for regulatory-covenant
  issues. Absence of a rule in `playbook_rules` does not mean absence of a required position.
- **Cross-table duplicates are the same real-world relationship.** The top customer typically
  appears as both a consent row and a material-contract row. Count it once per metric, and don't
  list it twice in a single blocker list.
- `risk_estimates` exposure figures are deal-level scenario ranges, not per-issue amounts. Attach
  one estimate to the issue whose category it matches; leave other issues unquantified rather
  than reusing the same range twice in one aggregate.
