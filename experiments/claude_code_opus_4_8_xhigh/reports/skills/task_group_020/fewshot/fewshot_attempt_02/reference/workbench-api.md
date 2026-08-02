# M&A Deal Workbench — API and record reference

Base URL comes from the task prompt (`<TASK_ENV_BASE_URL>`) or the environment
access file. Everything is read-only. Endpoints return a JSON envelope with a
single payload key (`{"draft_terms": [...]}`, `{"consents": [...]}`, etc.).

## Endpoints

| Endpoint | Payload key | Holds |
|---|---|---|
| `GET /api/deals` | `deals` | Every deal (many decoys — always filter by the prompt's `deal_id`) |
| `GET /api/deals/<id>` | `deal` + `links` | Header record: names, sides, value base, `playbook_id`, `policy_id` |
| `GET /api/deals/<id>/terms` | `draft_terms` | The negotiated draft under review |
| `GET /api/deals/<id>/benchmarks` | `benchmarks` | Market comparables |
| `GET /api/deals/<id>/risk-estimates` | `risk_estimates` | Modeled exposure ranges |
| `GET /api/deals/<id>/cap-table` | `cap_table` | Holder groups and ownership |
| `GET /api/deals/<id>/consents` | `consents` | Third-party consents |
| `GET /api/deals/<id>/employees` | `employees` | Employee groups |
| `GET /api/deals/<id>/material-contracts` | `material_contracts` | Key contracts |
| `GET /api/deals/<id>/regulatory` | `regulatory` | Single object, not a list |
| `GET /api/deals/<id>/diligence-findings` | `diligence_findings` | Diligence issues with amounts |
| `GET /api/deals/<id>/notes` | `deal_notes` | Negotiation notes |
| `GET /api/deals/<id>/documents` | `documents` | Document index |
| `GET /api/playbooks` | `playbooks` | Playbook IDs and rule counts |
| `GET /api/playbooks/<pb_id>/rules` | `rules` | Client-side negotiating positions |
| `GET /api/policies` | `policies` | Policy IDs and threshold counts |
| `GET /api/policies/<pol_id>/thresholds` | `thresholds` | Internal approval thresholds |
| `GET /api/search?q=<text>` | `deals`/`terms`/`notes`/`documents` | Cross-deal keyword search |
| `POST /api/query` | `columns`/`rows`/`row_count` | Read-only SQL |

There is also a browsable UI at `/`, `/workspace`, `/deals/<id>`, `/playbooks`,
`/policies`. The APIs carry the same data in a form that is easier to total.

## SQL endpoint

```bash
curl -s -X POST "$BASE/api/query" -H 'Content-Type: application/json' \
  -d '{"token":"deal-workbench-readonly","sql":"SELECT ... FROM draft_terms WHERE deal_id = ..."}'
```

Tables: `deals`, `draft_terms`, `playbook_rules`, `policy_thresholds`,
`benchmarks`, `risk_estimates`, `cap_table`, `consents`, `employees`,
`material_contracts`, `regulatory`, `diligence_findings`, `deal_notes`,
`documents`. Column names match the JSON field names below. SQL is the fastest
way to total columns and to confirm you have not missed a row.

## Record fields

**deal** — `deal_id`, `project_name`, `target_name`, `client_name`,
`client_side` (`buyer`/`seller`), `counterparty_name`, `transaction_type`,
`industry`, `status`, `strategic_context`, `signing_date`, `meeting_date`,
`currency`, `headline_value`, `upfront_cash`, `stock_value`, `milestone_value`,
`playbook_id`, `policy_id`.

`playbook_id` and `policy_id` are frequently null — that tells you whether the
deal is measured against a **playbook** (negotiating positions) or a **policy**
(internal approval thresholds). A prompt naming a specific playbook or policy ID
overrides whatever the deal header points at.

**draft_terms** — `term_id`, `deal_id`, `category`, `draft_value` (prose),
`numeric_value`, `unit` (`percent_points`, `months`, `contracts`, `dollars`,
`boolean`, `text`, `restricted_change`, `additional_carveouts`), `basis`,
`clause_ref`, `source_document`, `counterparty_rationale`, `last_updated`,
**`staleness_flag`** (`current` | `stale`).

`draft_value` prose regularly carries facts absent from `numeric_value` — a
second amount, a carve-out list, an exclusion, a duration alongside a
percentage. Read it on every term; never analyze from `numeric_value` alone.

**playbook_rules** — `playbook_id`, `category`, `preferred_position` (prose),
`fallback_position` (prose), `limit_value`, `limit_unit`, `basis`,
`risk_default`, `required_action`, `notes`. The preferred and fallback numbers
live inside the prose; `limit_value` usually mirrors only one of them.

**policy_thresholds** — `policy_id`, `category`, `policy_standard` (prose),
`threshold_value`, `threshold_unit`, `basis`, **`restricted_flag`**
(`yes`/`no`), **`approval_required`** (e.g. committee vs. a lower authority),
`notes`.

**consents** — `consent_id`, `contract_name`, `counterparty`, `consent_type`,
**`required_for_closing`** (`yes`/`no`), `amount_at_risk`, `risk_rating`
(Title case), `notes`.

**material_contracts** — `contract_id`, `contract_name`, `contract_type`,
**`consent_required`** (`yes` | `no` | `notice only`), `change_of_control`,
`anti_assignment`, `annual_revenue`, `notes`.

**employees** — `employee_id`, `employee_group`, `count`, `pto_liability`,
`service_credit_required`, `warn_risk` (`low`/`medium`/`high`),
`draft_treatment`, `playbook_requirement`, `notes`.

**cap_table** — `holder`, `security_class`, `shares`, **`as_converted_shares`**,
`fully_diluted_pct`, `role_notes`. `shares` and `as_converted_shares` differ for
convertible classes; allocation math uses the as-converted figures.

**risk_estimates** — `estimate_id`, `category` (`closing certainty`,
`indemnity leakage`, `transition disruption`), `exposure_low`, `exposure_high`,
`confidence`, `method`, `notes`.

**diligence_findings** — `finding_id`, `topic`, `severity`, `amount`, `source`,
`notes`.

**benchmarks** — `benchmark_id`, `category`, `metric`, `sample_size`,
`median_value`, `mean_value`, `upper_quartile`, `notable_precedent`, `notes`.

**regulatory** (one object) — `hsr_required`, `hell_or_high_water_required`,
`regulatory_approval`, `threshold_basis`, `notes`.

**deal_notes** — `note_id`, `topic`, `content`, `author`, `note_date`,
`source_document`.

**documents** — `document_id`, `title`, `document_type`, `version`,
`effective_date`, `summary`. Cite the current draft agreement document as the
source record when an issue is that the draft is *silent* on a term.
