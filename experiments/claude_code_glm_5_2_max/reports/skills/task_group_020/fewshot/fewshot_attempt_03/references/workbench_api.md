# Workbench API Reference

The M&A deal workbench is a read-only HTTP service (Werkzeug). Get `base_url` and
`sql_token` from `environment_access.md`; never hardcode them.

All `GET` endpoints return JSON. A `GET /api/deals/<deal_id>` response includes a `links`
map giving the canonical relative path to every sub-resource for that deal — prefer
following `links` over guessing paths.

## List / discovery endpoints

| Endpoint | Returns | Notes |
|---|---|---|
| `GET /` | HTML workbench home | UI; not machine-friendly. |
| `GET /workspace` | HTML | UI console. |
| `GET /api/deals` | `{count, deals:[…]}` | All deals; use to confirm a `deal_id` exists. |
| `GET /api/deals/<deal_id>` | `{deal:{…}, links:{…}}` | Master record + sub-resource links. |
| `GET /api/playbooks` | `{playbooks:[{playbook_id, rule_count}]}` | |
| `GET /api/policies` | `{policies:[{policy_id, threshold_count}]}` | |
| `GET /api/search?q=<text>` | `{deals:[…]}` | Free-text deal search. |

## Deal record fields (`deal` object)

`deal_id`, `client_name`, `client_side` (`seller`/`buyer`), `counterparty_name`,
`project_name`, `target_name`, `transaction_type`, `industry`, `currency`,
`headline_value`, `upfront_cash`, `stock_value`, `milestone_value`, `status`,
`signing_date`, `meeting_date`, `playbook_id`, `policy_id` (may be `null`),
`strategic_context`.

`headline_value` is the default base for percent-to-dollar conversion unless a source
states otherwise.

## Sub-resource endpoints and shapes

Every sub-resource is keyed by `deal_id`. Field names below are the actual JSON keys.

### `GET /api/deals/<deal_id>/terms` → `{draft_terms:[…]}`
`term_id`, `category`, `clause_ref`, `numeric_value`, `unit`, `basis`, `draft_value`,
`source_document`, `counterparty_rationale`, `staleness_flag` (bool — **drop stale terms
unless the task explicitly includes them**), `last_updated`, `deal_id`.

### `GET /api/deals/<deal_id>/consents` → `{consents:[…]}`
`consent_id`, `contract_name`, `counterparty`, `consent_type`
(`closing_condition` / `notice_only` / `post_closing_covenant`), `required_for_closing`
(bool), `risk_rating`, `amount_at_risk`, `notes`, `deal_id`.

### `GET /api/deals/<deal_id>/employees` → `{employees:[…]}`
`employee_id`, `employee_group`, `count`, `pto_liability`, `service_credit_required`
(bool), `warn_risk`, `draft_treatment`, `playbook_requirement`, `notes`, `deal_id`.

### `GET /api/deals/<deal_id>/material-contracts` → `{material_contracts:[…]}`
`contract_id`, `contract_name`, `contract_type`, `annual_revenue`, `change_of_control`
(bool), `anti_assignment` (bool), `consent_required` (bool), `notes`, `deal_id`.

### `GET /api/deals/<deal_id>/diligence-findings` → `{diligence_findings:[…]}`
`finding_id`, `topic`, `severity`, `amount`, `source`, `notes`, `deal_id`.

### `GET /api/deals/<deal_id>/risk-estimates` → `{risk_estimates:[…]}`
`estimate_id`, `category`, `exposure_low`, `exposure_high`, `confidence`, `method`,
`notes`, `deal_id`.

### `GET /api/deals/<deal_id>/benchmarks` → `{benchmarks:[…]}`
`benchmark_id`, `category`, `metric`, `sample_size`, `median_value`, `upper_quartile`,
`mean_value`, `notable_precedent`, `notes`, `deal_id`.

### `GET /api/deals/<deal_id>/regulatory` → `{regulatory:{…}}`
Single object: `hsr_required` (`yes`/`no`), `hell_or_high_water_required`
(`yes`/`no`/`limited covenant`), `regulatory_approval`
(`HSR only` / `HSR and industry review` / `none expected` / `other`), `threshold_basis`
(`size-of-transaction` / `below threshold` / `other`), `notes`, `deal_id`.

### `GET /api/deals/<deal_id>/cap-table` → `{cap_table:[…]}`
`holder`, `security_class`, `fully_diluted_pct` (decimal, e.g. 0.185 = 18.5%),
`shares`, `as_converted_shares`, `role_notes`, `deal_id`.

### `GET /api/deals/<deal_id>/notes` → `{deal_notes:[…]}`
`note_id`, `topic`, `content`, `author`, `note_date`, `source_document`, `deal_id`.

### `GET /api/deals/<deal_id>/documents` → `{documents:[…]}`
`document_id`, `document_type`, `title`, `summary`, `version`, `effective_date`, `deal_id`.

## Governing positions

### `GET /api/playbooks/<playbook_id>/rules` → `{rules:[…]}`
`category`, `preferred_position`, `fallback_position`, `limit_value`, `limit_unit`,
`required_action`, `risk_default`, `basis`, `playbook_id`. Use `playbook_id` from the deal
record. Compare each draft term to the rule with the matching `category`.

### `GET /api/policies/<policy_id>/thresholds` → `{thresholds:[…]}`
`category`, `threshold_value`, `threshold_unit`, `policy_standard`, `restricted_flag`
(bool — restricted categories need committee approval), `approval_required` (bool), `basis`,
`policy_id`. Use `policy_id` from the deal record (escalation-memo tasks only).

## Read-only SQL — `POST /api/query`

```
POST {base_url}/api/query
Content-Type: application/json
{"token": "<sql_token from environment_access.md>", "sql": "SELECT …"}
```

Response: `{"columns": [...], "row_count": N, "rows": [[...], ...]}` (rows are positional
arrays aligned to `columns`).

**Auth gotcha:** the token goes in the JSON **body** under `"token"`, and the SQL string
goes under `"sql"` (not `"query"`). Header-based auth (`Authorization: Bearer …`,
`X-API-Key`, `?token=`) returns `{"error":"invalid token"}`; a `query` body key returns
`{"error":"missing sql"}`.

### Backing tables (14)
`deals`, `draft_terms`, `playbook_rules`, `policy_thresholds`, `benchmarks`,
`risk_estimates`, `cap_table`, `consents`, `employees`, `material_contracts`,
`regulatory`, `diligence_findings`, `deal_notes`, `documents`.

Table names differ slightly from endpoint keys (e.g. `draft_terms` vs `terms`,
`deal_notes` vs `notes`). Inspect columns first:
`SELECT name FROM sqlite_master WHERE type='table'` then
`SELECT * FROM <table> LIMIT 0` for column names.

Use SQL when a REST fetch plus client-side join is awkward — e.g. "every material contract
whose `consent_required` is true, joined to the consents that reference it," or "sum of
`pto_liability` across employee groups for this deal."

## Working rules

- Filter every resource by the **exact** `deal_id` from the prompt; the workbench serves
  many deals with overlapping names.
- `headline_value` is the percentage base unless a term/risk estimate states a different
  `basis`.
- Some fields are strings that look numeric (`hsr_required: "yes"`); normalize to the
  enum the template expects.
- The deal record's `links` map is the source of truth for sub-resource paths.
