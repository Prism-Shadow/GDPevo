# M&A deal workbench — data model

Base URL and credentials come from `environment_access.md` in the task directory
(`GDPEVO_ENV_BASE_URL=...`). Everything is read-only.

## HTTP surface

| Route | Returns |
| --- | --- |
| `GET /api/deals` | all deals (large; there are dozens of unrelated ones) |
| `GET /api/deals/<deal_id>` | `{"deal": {...}, "links": {...}}` |
| `GET /api/deals/<deal_id>/terms` | `draft_terms[]` — the counterparty draft |
| `GET /api/deals/<deal_id>/benchmarks` | `benchmarks[]` — market data |
| `GET /api/deals/<deal_id>/risk-estimates` | `risk_estimates[]` — modeled exposure |
| `GET /api/deals/<deal_id>/cap-table` | `cap_table[]` |
| `GET /api/deals/<deal_id>/consents` | `consents[]` |
| `GET /api/deals/<deal_id>/employees` | `employees[]` — grouped, not per-person |
| `GET /api/deals/<deal_id>/material-contracts` | `material_contracts[]` |
| `GET /api/deals/<deal_id>/regulatory` | `regulatory{}` — single object |
| `GET /api/deals/<deal_id>/diligence-findings` | `diligence_findings[]` |
| `GET /api/deals/<deal_id>/documents` | `documents[]` |
| `GET /api/deals/<deal_id>/notes` | `deal_notes[]` |
| `GET /api/playbooks`, `GET /api/playbooks/<id>/rules` | negotiation playbooks |
| `GET /api/policies`, `GET /api/policies/<id>/thresholds` | committee policies |
| `GET /api/search?q=` | matches deals and documents |
| `POST /api/query` | read-only SQL |

SQL body: `{"token": "deal-workbench-readonly", "sql": "SELECT ..."}` — the token
is required; without it the endpoint returns `{"error":"invalid token"}`. Response
is `{"columns": [...], "rows": [[...]], "row_count": N}`. Tables: `deals`,
`draft_terms`, `playbook_rules`, `policy_thresholds`, `benchmarks`,
`risk_estimates`, `cap_table`, `consents`, `employees`, `material_contracts`,
`regulatory`, `diligence_findings`, `deal_notes`, `documents`. Column names match
the JSON field names below. Use SQL for cross-deal or cross-table checks; the REST
routes are simpler for a single deal.

## Record fields that matter

**deals** — `deal_id`, `project_name`, `target_name`, `client_name`,
`counterparty_name`, `client_side` (`buyer`/`seller`), `transaction_type`,
`headline_value`, `upfront_cash`, `stock_value`, `milestone_value`, `currency`,
`signing_date`, `meeting_date`, `status`, `industry`, `strategic_context`,
`playbook_id`, `policy_id`.

A deal carries a `playbook_id` **or** a `policy_id`, sometimes neither. The
playbook drives negotiation-position tasks; the policy drives committee-escalation
tasks. Use the one the deal record points to, and prefer the ID named in the
prompt when it names one.

**draft_terms** — `term_id`, `category`, `clause_ref`, `draft_value` (prose),
`numeric_value`, `unit` (`percent_points` / `months` / `boolean` /
`restricted_change` / `additional_carveouts` / `contracts`), `basis`,
`source_document`, `counterparty_rationale`, `staleness_flag`
(`current` / `stale`), `last_updated`.

`numeric_value` holds only the term's *primary* metric. Secondary figures live in
the `draft_value` prose — a special-indemnity dollar amount, a release period
alongside an escrow percent, a carve-out that the condition excludes, a match-right
window. Read the prose for every term you use.

**playbook_rules** — `playbook_id`, `category`, `preferred_position` (prose),
`fallback_position` (prose), `limit_value`, `limit_unit`, `basis`, `risk_default`,
`required_action`, `notes`.

**policy_thresholds** — `policy_id`, `category`, `policy_standard` (prose),
`threshold_value`, `threshold_unit`, `basis`, `restricted_flag` (`yes`/`no`),
`approval_required` (e.g. `M&A Committee`, `General Counsel`), `notes`.

**consents** — `consent_id`, `contract_name`, `counterparty`, `consent_type`,
`required_for_closing` (`yes`/`no`), `risk_rating` (`High`/`Medium`/`Low` —
title case, uppercase it for enums), `amount_at_risk`, `notes`.

**material_contracts** — `contract_id`, `contract_name`, `contract_type`,
`annual_revenue`, `consent_required` (`yes` / `no` / `notice only`),
`change_of_control`, `anti_assignment`, `notes`.

**employees** — `employee_id`, `employee_group` (e.g. executives, engineering and
product, field and operations), `count`, `pto_liability`,
`service_credit_required`, `warn_risk` (`low`/`medium`/`high`), `draft_treatment`
(what the buyer draft does to this group), `playbook_requirement`, `notes`. Rows
are **groups**, so `count` and `pto_liability` are group totals.

**risk_estimates** — `estimate_id`, `category` (`closing certainty`,
`indemnity leakage`, `transition disruption`), `exposure_low`, `exposure_high`,
`method`, `confidence`, `notes`. Note the space-separated category names; answer
enums normally want the snake_case form.

**benchmarks** — `benchmark_id`, `category`, `metric`, `sample_size`,
`median_value`, `mean_value`, `upper_quartile`, `notable_precedent`, `notes`.

**diligence_findings** — `finding_id`, `topic` (customer concentration, privacy
and security, working capital, …), `amount`, `severity`, `source`, `notes`.

**regulatory** — `hsr_required`, `hell_or_high_water_required`,
`regulatory_approval`, `threshold_basis`, `notes`.

**cap_table** — `holder`, `security_class`, `shares`, `as_converted_shares`,
`fully_diluted_pct` (a fraction, e.g. `0.185`, not percent points), `role_notes`.
`shares` and `as_converted_shares` differ for convertible classes; allocate on
`as_converted_shares` / `fully_diluted_pct`.

**documents** — `document_id`, `document_type`, `title`, `summary`, `version`,
`effective_date`. Summaries only; there is no clause text. When a required
provision appears in no draft term, cite the draft-agreement document ID as the
source record for the gap.

## Decoys

The workbench holds dozens of deals, and several shadow the target's name closely
— a near-homograph of the project name, or the same name with a directional
suffix appended. Some carry `strategic_context` text such as "Records include
stale and duplicate rows from earlier drafts." Prompts sometimes warn about this
directly; assume the hazard even when they do not.

Filter every query by the exact `deal_id` from the prompt. Never match on project
name, target name, or client name. Record IDs embed their deal ID
(`TERM_<deal_id>_NN`, `CNS_<deal_id>_NN`), so any ID you emit whose middle segment
is not your deal is a leak from a decoy.
