# Workbench Reference

This reference documents the M&A deal workbench API: the endpoint families, the response shapes (field names and types — not deal-specific values), and the read-only SQL interface. All network access goes through `environment_access.md` (base URL + allowed endpoints + SQL token). Use the `/api/...` JSON routes for data; the non-`/api` routes (`/deals/<id>`, `/playbooks`, `/policies`) serve the web UI HTML and are not for parsing.

In every URL below, substitute the task's `<deal_id>` (e.g. a `PRJ_…` id). The base URL is the `<TASK_ENV_BASE_URL>` from `environment_access.md`.

## Deal record

`GET /api/deals/<deal_id>` → `{ "deal": {…}, "links": {…} }`

`deal` object fields:

| field | type | use |
|---|---|---|
| `deal_id` | str | echo into output `deal_id` |
| `client_side` | str | buyer / seller — sets which playbook/policy to apply |
| `client_name` | str | memo / prepared-for fields |
| `counterparty_name` | str | memo / counterparty field |
| `target_name` | str | memo / target field |
| `project_name` | str | memo / project field |
| `transaction_type` | str | APA / SPA / merger — informs which term families apply |
| `currency` | str | output currency (USD) |
| `headline_value` | num | default dollar base for percent→amount math |
| `upfront_cash` | num | alternative base when source states it |
| `stock_value` | num | stock component of consideration |
| `milestone_value` | num | milestone/earnout component |
| `industry` | str | context |
| `strategic_context` | str | context |
| `playbook_id` | str | comparison reference for term-level review |
| `policy_id` | str | comparison reference for committee-threshold review |
| `signing_date` | str | memo dates (`YYYY-MM-DD`) |
| `meeting_date` | str | memo dates (`YYYY-MM-DD`) |
| `status` | str | deal status |

`links` object: keys `benchmarks`, `cap_table`, `consents`, `diligence_findings`, `documents`, `employees`, `material_contracts`, `notes`, `regulatory`, `risk_estimates`, `terms` — each points at the corresponding sub-resource route below.

`GET /api/deals` → `{ "count": N, "deals": [ … ] }` (list of all deals; useful to confirm a deal_id exists and is not a similarly-named sibling).

## Draft terms (the terms under review)

`GET /api/deals/<deal_id>/terms` → `{ "draft_terms": [ … ] }`

Each draft term:

| field | type | use |
|---|---|---|
| `term_id` | str | stable id → `source_term_ids`; `[]` when the required term is absent |
| `deal_id` | str | — |
| `category` | str | join key to playbook rule / policy threshold |
| `clause_ref` | str | citation (e.g. "Article VIII", "Section 5.4") |
| `unit` | str | percent_points / months / restricted_change / additional_carveouts / … |
| `draft_value` | str | human-readable draft position |
| `numeric_value` | num or null | numeric form of the draft position (may be null) |
| `basis` | str | what the value is measured against (equity value, purchase price, …) |
| `source_document` | str | provenance |
| `staleness_flag` | str | if set/stale → exclude from escalation per scope rules |
| `counterparty_rationale` | str | context |
| `last_updated` | str | provenance |

## Comparison references

### Playbook rules
`GET /api/playbooks` → `{ "playbooks": [ { "playbook_id": "…", "rule_count": N } ] }` (buyer and seller playbooks exist).

`GET /api/playbooks/<playbook_id>/rules` → `{ "rules": [ … ] }`

Each rule:

| field | type | use |
|---|---|---|
| `playbook_id` | str | — |
| `category` | str | join key to draft term |
| `basis` | str | must match the term's basis for a valid comparison |
| `limit_unit` | str | unit of the preferred/fallback positions |
| `limit_value` | num | the preferred (target) position value |
| `preferred_position` | str | affirmative preferred position → `playbook_preferred_*` / `preferred_*` |
| `fallback_position` | str | affirmative fallback position → `playbook_fallback_*` / `fallback_*` |
| `required_action` | str | default recommended action |
| `risk_default` | str | default risk rating (LOW/MEDIUM/HIGH) |
| `notes` | str | guidance |

### Policy thresholds (committee)
`GET /api/policies` → `{ "policies": [ { "policy_id": "…", "threshold_count": N } ] }`.

`GET /api/policies/<policy_id>/thresholds` → `{ "thresholds": [ … ] }`

Each threshold:

| field | type | use |
|---|---|---|
| `policy_id` | str | — |
| `category` | str | join key to draft term |
| `basis` | str | comparison basis |
| `threshold_unit` | str/null | unit of the threshold |
| `threshold_value` | num/null | threshold value → `policy_metric.threshold_value` |
| `policy_standard` | str | the required standard |
| `approval_required` | str | whether committee approval is required |
| `restricted_flag` | str | whether the category is restricted (must escalate) |
| `notes` | str | guidance |

## Deal sub-resources

All return `{ "<root>": [ … ] }` unless noted. Object field shapes (names + types only):

### consents — `GET /api/deals/<deal_id>/consents` → `{ "consents": [ … ] }`
`consent_id`, `deal_id`, `contract_name`, `counterparty`, `consent_type`, `required_for_closing` (str), `risk_rating`, `amount_at_risk` (num), `notes`. Use `consent_id` for `required_consent_ids` / blocker ids; sum `amount_at_risk` where `required_for_closing`.

### employees — `GET /api/deals/<deal_id>/employees` → `{ "employees": [ … ] }`
`employee_id`, `deal_id`, `employee_group`, `pto_liability` (num), `service_credit_required` (str), `warn_risk` (str), `draft_treatment` (str), `playbook_requirement` (str), `count` (num), `notes`. Sum `pto_liability` for totals; collect `employee_id` where service credit / WARN risk applies.

### material-contracts — `GET /api/deals/<deal_id>/material-contracts` → `{ "material_contracts": [ … ] }`
`contract_id`, `deal_id`, `contract_name`, `contract_type`, `change_of_control` (str), `anti_assignment` (str), `consent_required` (str), `annual_revenue` (num), `notes`. Use `contract_id` for `required_contract_ids`; sum `annual_revenue` where consent is required.

### benchmarks — `GET /api/deals/<deal_id>/benchmarks` → `{ "benchmarks": [ … ] }`
`benchmark_id`, `deal_id`, `category`, `metric`, `sample_size` (num), `median_value` (num), `mean_value` (num), `upper_quartile` (num), `notable_precedent`, `notes`. Match by `category`/`metric` to populate `benchmark` blocks and classify quartile position.

### risk-estimates — `GET /api/deals/<deal_id>/risk-estimates` → `{ "risk_estimates": [ … ] }`
`estimate_id`, `deal_id`, `category`, `exposure_low` (num), `exposure_high` (num), `method`, `confidence`, `notes`. Match by `category`; cite `estimate_id` as the exposure source; sum low/high for aggregate quantified exposure.

### regulatory — `GET /api/deals/<deal_id>/regulatory` → `{ "regulatory": { … } }` (single object)
`deal_id`, `hsr_required`, `hell_or_high_water_required`, `threshold_basis`, `regulatory_approval`, `notes`. Drives the `regulatory` / HSR blocker fields.

### cap-table — `GET /api/deals/<deal_id>/cap-table` → `{ "cap_table": [ … ] }`
`holder`, `deal_id`, `security_class`, `fully_diluted_pct` (num, fraction), `shares` (num), `as_converted_shares` (num), `role_notes`. Drives `holder_allocation`; allocate consideration pro-rata on `as_converted_shares` / `fully_diluted_pct`.

### diligence-findings — `GET /api/deals/<deal_id>/diligence-findings` → `{ "diligence_findings": [ … ] }`
`finding_id`, `deal_id`, `topic`, `severity`, `amount` (num), `source`, `notes`. Cite `finding_id` as a source (e.g. NWC collar `source_finding_id`); use `amount` for special-indemnity / quantified findings.

### notes — `GET /api/deals/<deal_id>/notes` → `{ "deal_notes": [ … ] }`
`note_id`, `deal_id`, `author`, `note_date`, `topic`, `content`, `source_document`. Context for rationale and priority; usually not echoed as a stable id unless the template asks.

### documents — `GET /api/deals/<deal_id>/documents` → `{ "documents": [ … ] }`
`document_id`, `deal_id`, `document_type`, `title`, `version`, `effective_date`, `summary`. Provenance for clause refs and the governing-law/forum source record.

## Search

`GET /api/search?q=<query>` → an object with keys `deals`, `documents`, `notes`, `terms` (and `query`). Use it to locate records by free text when you only have a name, not an id.

## Read-only SQL

`POST /api/query` with JSON body **`{ "token": "deal-workbench-readonly", "sql": "<SELECT …>" }`** (token goes in the body; the query field is `sql`).

Response: `{ "columns": [ … ], "row_count": N, "rows": [ [ … ], … ] }` (rows are positional arrays aligned to `columns`).

- Read-only. Only `SELECT` against the underlying tables. Some queries are rejected (e.g. querying a non-existent table, or disallowed shapes) — the server returns `{ "error": "…" }`; adjust the query.
- The 14 underlying tables mirror the API resources 1:1: `deals`, `draft_terms`, `consents`, `employees`, `material_contracts`, `benchmarks`, `risk_estimates`, `regulatory`, `cap_table`, `diligence_findings`, `deal_notes`, `documents`, `playbook_rules`, `policy_thresholds`.
- Use SQL for cross-table work that the per-resource GETs make awkward: counts (consents required for closing), grouped sums (PTO liability by employee group), and joins (draft_terms ⋈ playbook_rules on `category`/`basis`; material_contracts ⋈ consents).

## Stable-ID conventions

Every record carries a stable, prefixed id — copy it verbatim into output. Common prefixes: `TERM_` (draft terms), `CNS_` (consents), `MAT_` (material contracts), `EMP_` (employees), `FND_` (diligence findings), `RSK_` (risk estimates), `BMK_`/benchmark ids, `DOC_` (documents), `REG_` (regulatory), `PB_` (playbooks), `POL_` (policies). Synthetic ids the template asks you to mint (e.g. a regulatory blocker id) should follow the template's own naming convention. Never paraphrase or renumber a workbench id.
