# M&A Deal Workbench — data model reference

Base URL comes from `environment_access.md` (`GDPEVO_ENV_BASE_URL`, typically
`http://task-env:9020/`). All endpoints are GET and unauthenticated except
`POST /api/query`, which needs `{"token": "deal-workbench-readonly", "sql": "..."}`.

## Scale and the name-collision trap

The workbench holds roughly 85 deals. Only a handful are ever the subject of a
task; the rest are distractors, and many are **deliberately near-name clones** of
the real deal — a "Project <Name> North", a "Project <Similar>" — each with its
own full set of terms, consents and employees. Several distractor deals share the
*same* project name as each other.

> Filter every lookup on the exact `deal_id` given in the prompt. Never resolve a
> deal by `project_name`, `target_name` or `client_name`.

## Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/deals` | `{count, deals: [...]}` — all deals, headline economics inline |
| `GET /api/deals/<deal_id>` | `{deal: {...}, links: {...}}` — note the `deal` wrapper |
| `GET /api/deals/<deal_id>/terms` | `{draft_terms: [...]}` |
| `GET /api/deals/<deal_id>/documents` | `{documents: [...]}` |
| `GET /api/deals/<deal_id>/benchmarks` | `{benchmarks: [...]}` |
| `GET /api/deals/<deal_id>/risk-estimates` | `{risk_estimates: [...]}` |
| `GET /api/deals/<deal_id>/cap-table` | `{cap_table: [...]}` |
| `GET /api/deals/<deal_id>/consents` | `{consents: [...]}` |
| `GET /api/deals/<deal_id>/employees` | `{employees: [...]}` |
| `GET /api/deals/<deal_id>/material-contracts` | `{material_contracts: [...]}` |
| `GET /api/deals/<deal_id>/regulatory` | `{regulatory: {...}}` — a **bare object**, not a list |
| `GET /api/deals/<deal_id>/diligence-findings` | `{diligence_findings: [...]}` |
| `GET /api/deals/<deal_id>/notes` | `{deal_notes: [...]}` |
| `GET /api/playbooks` , `GET /api/playbooks/<id>/rules` | playbook positions |
| `GET /api/policies` , `GET /api/policies/<id>/thresholds` | committee policy |
| `GET /api/search` , `POST /api/query` | search / read-only SQL |

`POST /api/query` exposes 14 tables: `deals`, `draft_terms`, `playbook_rules`,
`policy_thresholds`, `benchmarks`, `risk_estimates`, `cap_table`, `consents`,
`employees`, `material_contracts`, `regulatory`, `diligence_findings`,
`deal_notes`, `documents`. It returns `{columns, row_count, rows}` with rows as
positional arrays. Use it for aggregate cross-checks; use the REST endpoints for
the primary read.

## Record shapes and the fields that decide answers

### `deals`
`deal_id, client_name, client_side, counterparty_name, project_name, target_name,
transaction_type, industry, status, strategic_context, currency, headline_value,
upfront_cash, stock_value, milestone_value, playbook_id, policy_id, signing_date,
meeting_date`

- `client_side` (`buyer` / `seller`) sets the direction of every deviation test.
- `headline_value` is the default basis for percentage-to-dollar maths.
- A deal carries a `playbook_id`, a `policy_id`, or both. Playbook deals are
  negotiation/redline tasks; policy deals are committee-escalation tasks.

### `draft_terms`
`term_id, deal_id, category, clause_ref, draft_value, numeric_value, unit, basis,
source_document, counterparty_rationale, staleness_flag, last_updated`

- **`staleness_flag`** is the primary distractor switch. Use only `current` rows.
  Anything else is a superseded draft and must be excluded from the register —
  templates often ask you to list the excluded ids explicitly.
- `numeric_value` carries the headline number, but `draft_value` prose frequently
  carries a **second** figure the template asks for separately (a special
  indemnity amount, a stranded-overhead figure, a match-right period, a second
  survival tail). Read the prose on every term.
- `unit` is one of `percent_points`, `months`, `dollars`, `contracts`, `text`,
  `carveouts`, `restricted_change`, `additional_carveouts`.

### `playbook_rules`
`playbook_id, category, basis, preferred_position, fallback_position, limit_value,
limit_unit, risk_default, required_action, notes`

- `limit_value` is the **fallback** threshold. The *preferred* position lives only
  in the `preferred_position` prose ("at least 12.0% of purchase price",
  "no more than 8.0%"). Parse both strings; never assume `limit_value` is the
  preferred number.
- `fallback_position` prose can carry a **conditional** ("Fallback 15 months if
  escrow is 10.0% or higher"). That condition is often the source of a *different*
  issue's required position — a playbook may have no escrow rule of its own while
  still fixing the required escrow percentage inside the survival rule's fallback.
- `risk_default` seeds `risk_rating` when nothing else overrides it.

### `policy_thresholds`
`policy_id, category, policy_standard, threshold_value, threshold_unit, basis,
approval_required, restricted_flag, notes`

- Escalate only rows with `restricted_flag = yes` (these also show
  `approval_required = M&A Committee`). Rows approved at a lower level, e.g.
  `General Counsel` with `restricted_flag = no`, are non-committee distractors.
- `basis` matters: policy percentages may run off `equity value`, not the deal's
  `headline_value` label. Follow the stated basis.

### `consents`
`consent_id, deal_id, contract_name, counterparty, consent_type,
required_for_closing, amount_at_risk, risk_rating, notes`

- `required_for_closing` (`yes`/`no`) splits closing blockers from notice-only
  items. Only `yes` rows feed "closing consent amount at risk" totals; `no` rows
  usually belong in a `non_blocking_notices` / tradeable list.

### `material_contracts`
`contract_id, deal_id, contract_name, contract_type, annual_revenue,
consent_required, change_of_control, anti_assignment, notes`

- `consent_required` is `yes` / `no` / **`notice only`**. `notice only` is not a
  closing blocker — it typically belongs in an excluded/non-blocking list.
- `contract_type` (`customer`, `supplier`, `technology license`) is how you find
  "top customer revenue at risk".

### `employees`
`employee_id, deal_id, employee_group, count, pto_liability,
service_credit_required, warn_risk, draft_treatment, playbook_requirement, notes`

- Groups are typically executives / engineering and product / field and operations.
- `draft_treatment` vs `playbook_requirement` is the deviation test — a draft that
  lets the buyer "select" or "cherry-pick" employees, or reject accrued PTO,
  breaches a requirement to "define transfer process and accrued PTO allocation".
- `warn_risk` of `medium`/`high` (not `low`) drives WARN-risk employee lists.

### `risk_estimates`
`estimate_id, deal_id, category, exposure_low, exposure_high, method, confidence, notes`

- Categories: `closing certainty`, `indemnity leakage`, `transition disruption`.
- **Copy the numbers verbatim.** Some values end in irregular digits by design;
  rounding them to a "clean" figure is a wrong answer.
- Templates using snake_case want the category normalised
  (`closing certainty` → `closing_certainty`).

### `benchmarks`
`benchmark_id, deal_id, category, metric, sample_size, median_value, mean_value,
upper_quartile, notable_precedent, notes`

- Match a benchmark to a term by its `metric` text, and compare against the metric
  the benchmark actually measures — if the metric is "general representation
  survival months", compare the *general* survival figure, not a longer
  fundamental-rep tail from the same term.
- Not every term has a benchmark; templates provide a `not_applicable` position.

### `diligence_findings`
`finding_id, deal_id, topic, severity, amount, source, notes`

- Topics seen: customer concentration, privacy and security, working capital.
  These supply the "special indemnity", "privacy finding" and "NWC collar"
  amounts that templates ask for by name.

### `documents` / `deal_notes`
- `documents`: `document_id, document_type, title, summary, version, effective_date`.
  The `draft agreement` document is the natural `source_record_id` to cite for a
  **missing** term (silence in the draft).
- `deal_notes`: `note_id, topic, content, author, note_date, source_document` —
  gives negotiation posture, and often flags which items the business treats as
  tradeable versus must-have.
