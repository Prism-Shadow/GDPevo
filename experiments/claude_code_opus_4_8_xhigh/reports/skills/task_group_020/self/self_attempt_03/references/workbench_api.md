# Workbench API and data model

Base URL comes from the environment (an `environment_access.md`, a `<TASK_ENV_BASE_URL>`
placeholder in the prompt, or `GDPEVO_ENV_BASE_URL`). Treat the documented endpoint list as
exhaustive — undocumented routes are not guaranteed to exist.

## Endpoints

HTML views (useful for orientation, not for extraction):
`GET /`, `GET /workspace`, `GET /deals/<deal_id>`, `GET /playbooks`, `GET /policies`

JSON:

| Route | Returns |
|---|---|
| `GET /api/deals` | `{count, deals:[…]}` — every deal, all sides |
| `GET /api/deals/<deal_id>` | one deal record |
| `GET /api/deals/<deal_id>/terms` | `{draft_terms:[…]}` — **includes stale rows** |
| `GET /api/deals/<deal_id>/documents` | `{documents:[…]}` |
| `GET /api/deals/<deal_id>/benchmarks` | `{benchmarks:[…]}` |
| `GET /api/deals/<deal_id>/risk-estimates` | `{risk_estimates:[…]}` |
| `GET /api/deals/<deal_id>/cap-table` | `{cap_table:[…]}` |
| `GET /api/deals/<deal_id>/consents` | `{consents:[…]}` |
| `GET /api/deals/<deal_id>/employees` | `{employees:[…]}` — group rows |
| `GET /api/deals/<deal_id>/material-contracts` | `{material_contracts:[…]}` |
| `GET /api/deals/<deal_id>/regulatory` | `{regulatory:{…}}` — **object, not array** |
| `GET /api/deals/<deal_id>/diligence-findings` | `{diligence_findings:[…]}` |
| `GET /api/deals/<deal_id>/notes` | `{deal_notes:[…]}` |
| `GET /api/playbooks` | `{playbooks:[{playbook_id, rule_count}]}` |
| `GET /api/playbooks/<playbook_id>/rules` | `{playbook_id, rules:[…]}` |
| `GET /api/policies` | `{policies:[{policy_id, threshold_count}]}` |
| `GET /api/policies/<policy_id>/thresholds` | `{policy_id, thresholds:[…]}` |
| `GET /api/search?q=` | keyed by `deals`, `documents`, `notes`, `terms`, `query` |
| `POST /api/query` | read-only SQL |

Envelope keys are not always the plural of the route segment (`/terms` → `draft_terms`,
`/notes` → `deal_notes`), and `/api/deals/<id>` returns `{"deal":{…},"links":{…}}` — two
keys, so a naive "unwrap the only key" rule fails there. Inspect keys before unwrapping.

## SQL endpoint

```bash
curl -s -X POST "$TASK_ENV_BASE_URL/api/query" \
  -H 'Content-Type: application/json' \
  -d '{"token":"deal-workbench-readonly","sql":"SELECT ..."}'
```

Response: `{"columns":[…], "row_count":N, "rows":[[…],…]}` — positional arrays, so keep
column order in mind. Guardrails: only `SELECT`/`WITH` (anything else returns
`{"error":"only SELECT or WITH statements are allowed"}`); a wrong token returns HTTP 401.
No row cap observed. Use double quotes for SQL string literals only if you escape them for
JSON — single quotes are simpler.

Tables: `deals`, `draft_terms`, `playbook_rules`, `policy_thresholds`, `benchmarks`,
`risk_estimates`, `cap_table`, `consents`, `employees`, `material_contracts`, `regulatory`,
`diligence_findings`, `deal_notes`, `documents`.

Recipes worth running on every task:

```sql
-- current draft terms only, with the binding standard beside them
SELECT t.term_id, t.category, t.numeric_value, t.unit, t.clause_ref,
       r.limit_value, r.limit_unit, r.basis, r.preferred_position, r.fallback_position
FROM draft_terms t
LEFT JOIN playbook_rules r
  ON r.category = t.category
 AND r.playbook_id = (SELECT playbook_id FROM deals WHERE deal_id = 'PRJ_XXXX')
WHERE t.deal_id = 'PRJ_XXXX' AND t.staleness_flag = 'current';

-- confirm you are not looking at a same-named decoy deal
SELECT deal_id, project_name, client_side, playbook_id, policy_id
FROM deals WHERE project_name = (SELECT project_name FROM deals WHERE deal_id='PRJ_XXXX');

-- aggregates the templates ask for
SELECT SUM(count) headcount, SUM(pto_liability) pto FROM employees WHERE deal_id='PRJ_XXXX';
SELECT SUM(amount_at_risk) FROM consents
 WHERE deal_id='PRJ_XXXX' AND required_for_closing='yes';
SELECT SUM(annual_revenue) FROM material_contracts
 WHERE deal_id='PRJ_XXXX' AND consent_required='yes';
SELECT SUM(exposure_low), SUM(exposure_high) FROM risk_estimates WHERE deal_id='PRJ_XXXX';
```

Cross-check every SQL aggregate against the REST payload once. If they disagree, you
filtered wrong.

## Record fields

**deals** — `deal_id`, `project_name`, `target_name`, `client_name`, `counterparty_name`,
`client_side` (`buyer`|`seller`), `transaction_type`, `industry`, `status`,
`strategic_context`, `currency`, `headline_value`, `upfront_cash`, `stock_value`,
`milestone_value`, `signing_date`, `meeting_date`, `playbook_id`, `policy_id`.

`headline_value` is independent of the component values — it is *not* their sum. Read it.

**draft_terms** — `term_id`, `deal_id`, `category`, `draft_value` (prose), `numeric_value`,
`unit`, `basis`, `clause_ref`, `source_document`, `counterparty_rationale`, `last_updated`,
`staleness_flag` (`current`|`stale`).

Categories seen: `consent_closing_condition`, `customer_consent_condition`,
`employee_service_credit`, `employee_transfer`, `escrow`, `fiduciary_out`,
`financing_condition`, `indemnity_cap`, `mae_carveouts`, `materiality_scrape`,
`reverse_break_fee`, `reverse_termination_fee`, `rw_survival`,
`stranded_cost_reimbursement`, `survival_period`, `termination_fee`, `transition_services`,
`voting_agreements`.
Units seen: `boolean`, `percent_points`, `months`, `text`, `contracts`,
`restricted_change`, `additional_carveouts`, `dollars`.

**playbook_rules** — `playbook_id`, `category`, `limit_value` (**the fallback bound**),
`limit_unit`, `basis`, `preferred_position` (prose, holds the preferred number),
`fallback_position` (prose, may be conditional), `required_action`, `risk_default`, `notes`.
`limit_value`/`limit_unit` may be `null` for qualitative rules.

**policy_thresholds** — `policy_id`, `category`, `threshold_value`, `threshold_unit`,
`basis`, `policy_standard` (prose), `restricted_flag`, `approval_required`, `notes`.
Committee-escalation tasks key off `restricted_flag` and `approval_required`; `notes` may
mark a policy as legacy.

**consents** — `consent_id`, `contract_name`, `counterparty`, `consent_type`,
`required_for_closing` (`yes`|`no`), `amount_at_risk`, `risk_rating` (`High`/`Medium`/`Low`),
`notes`.

**material_contracts** — `contract_id`, `contract_name`, `contract_type`, `annual_revenue`,
`consent_required` (`yes`|`no`|`notice only`), `change_of_control` (`yes`|`no`),
`anti_assignment` (`yes`|`no`), `notes`. `notice only` maps to a notice/non-blocking
classification, not a closing condition.

**employees** — `employee_id`, `employee_group`, `count`, `pto_liability`,
`service_credit_required` (`yes`), `warn_risk` (`low`|`medium`), `draft_treatment`,
`playbook_requirement`, `notes`. Rows are **groups**.

**cap_table** — `holder`, `security_class`, `shares`, `as_converted_shares`,
`fully_diluted_pct` (fraction, sums to 1.0), `role_notes`.

**benchmarks** — `benchmark_id`, `category`, `metric`, `sample_size`, `median_value`,
`mean_value`, `upper_quartile`, `notable_precedent`, `notes`. Match on `metric`/`category`;
report the position of the draft relative to median and upper quartile.

**risk_estimates** — `estimate_id`, `category`, `exposure_low`, `exposure_high`, `method`,
`confidence` (`low`|`medium`), `notes`. Cite `estimate_id` when a template wants a source.

**regulatory** (one object per deal) — `hsr_required` (`yes`|`no`),
`hell_or_high_water_required` (`yes`|`no`|`limited covenant`), `regulatory_approval`
(`HSR only`|`HSR and industry review`|`none expected`), `threshold_basis`
(`size-of-transaction`|`below threshold`).

**diligence_findings** — `finding_id`, `topic`, `severity` (`High`/`Medium`/`Low`),
`amount`, `source`, `notes`. Drives special indemnities, escrow sizing on a findings basis,
and working-capital mechanics.

**deal_notes** — `note_id`, `note_date`, `author`, `topic`, `content`, `source_document`.
Notes carry negotiation posture ("must-have vs tradeable") that decides priority ordering
and blocker-vs-tradeable classification.

**documents** — `document_id`, `document_type`, `title`, `version`, `effective_date`,
`summary`. Use `effective_date`/`version` to identify the operative draft.
