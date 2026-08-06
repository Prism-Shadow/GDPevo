# Workbench API reference

## Access

The base URL is in `environment_access.md` as `GDPEVO_ENV_BASE_URL`. Prompts write it as the
placeholder `<TASK_ENV_BASE_URL>`; substitute the real value. Use only the endpoints listed in
that file. No auth is needed for `GET`; the SQL endpoint needs the token given there.

## Endpoints

HTML (human view, same data): `GET /`, `/workspace`, `/deals/<deal_id>`, `/playbooks`, `/policies`

JSON:

| Endpoint | Returns (top-level key) |
| --- | --- |
| `GET /api/deals` | `{count, deals[]}` — every deal, including decoys |
| `GET /api/deals/<deal_id>` | `{deal, links}` |
| `GET /api/deals/<deal_id>/terms` | `draft_terms[]` |
| `GET /api/deals/<deal_id>/documents` | `documents[]` |
| `GET /api/deals/<deal_id>/benchmarks` | `benchmarks[]` |
| `GET /api/deals/<deal_id>/risk-estimates` | `risk_estimates[]` |
| `GET /api/deals/<deal_id>/cap-table` | `cap_table[]` |
| `GET /api/deals/<deal_id>/consents` | `consents[]` |
| `GET /api/deals/<deal_id>/employees` | `employees[]` |
| `GET /api/deals/<deal_id>/material-contracts` | `material_contracts[]` |
| `GET /api/deals/<deal_id>/regulatory` | `regulatory` (single object) |
| `GET /api/deals/<deal_id>/diligence-findings` | `diligence_findings[]` |
| `GET /api/deals/<deal_id>/notes` | `deal_notes[]` |
| `GET /api/playbooks` | `playbooks[]` with rule counts |
| `GET /api/playbooks/<playbook_id>/rules` | `{playbook_id, rules[]}` |
| `GET /api/policies` | `policies[]` with threshold counts |
| `GET /api/policies/<policy_id>/thresholds` | `{policy_id, thresholds[]}` |
| `GET /api/search?q=<text>` | `{deals[], documents[], notes[], terms[], query}` |
| `POST /api/query` | `{columns[], row_count, rows[][]}` |

`/api/search` is **global**. Its `terms[]` results come from every deal in the workbench, so
filter by `deal_id` before using anything it returns.

`regulatory` is one object per deal, not a list.

## SQL endpoint

Read-only SQLite. Body is JSON with the token from `environment_access.md` and a `sql` string:

```bash
curl -s -X POST "$BASE/api/query" -H 'Content-Type: application/json' \
  -d '{"token":"<token from environment_access.md>","sql":"SELECT ... "}'
```

Response is positional: `{"columns": [...], "row_count": N, "rows": [[...], ...]}` — zip
`columns` with each row yourself. A bad/missing token returns `{"error":"invalid token"}`.

Use SQL for cross-table work the REST routes can't do in one hop: joining draft terms to
playbook rules on `category`, summing exposure by category, or checking that a category is
absent from the current draft.

```sql
-- current draft terms joined to the governing playbook
SELECT t.term_id, t.category, t.numeric_value, t.unit, t.basis,
       r.limit_value, r.limit_unit, r.preferred_position, r.fallback_position, r.risk_default
FROM draft_terms t
LEFT JOIN playbook_rules r
  ON r.category = t.category AND r.playbook_id = '<PB_ID>'
WHERE t.deal_id = '<DEAL_ID>' AND t.staleness_flag = 'current';

-- playbook categories with no current draft term (missing_required_term candidates)
SELECT r.category FROM playbook_rules r
WHERE r.playbook_id = '<PB_ID>'
  AND r.category NOT IN (SELECT category FROM draft_terms
                         WHERE deal_id = '<DEAL_ID>' AND staleness_flag = 'current');
```

## Tables

`deals(deal_id PK, project_name, transaction_type, client_side, client_name, counterparty_name,
target_name, industry, headline_value, upfront_cash, stock_value, milestone_value, currency,
signing_date, meeting_date, status, strategic_context, playbook_id, policy_id)`

`draft_terms(term_id PK, deal_id, category, draft_value, numeric_value, unit, basis,
source_document, clause_ref, counterparty_rationale, last_updated, staleness_flag)`

`playbook_rules(playbook_id, category, preferred_position, fallback_position, limit_value,
limit_unit, basis, required_action, risk_default, notes)`

`policy_thresholds(policy_id, category, policy_standard, threshold_value, threshold_unit,
basis, approval_required, restricted_flag, notes)`

`benchmarks(benchmark_id PK, deal_id, category, metric, sample_size, median_value, mean_value,
upper_quartile, notable_precedent, notes)`

`risk_estimates(estimate_id PK, deal_id, category, exposure_low, exposure_high, confidence,
method, notes)`

`cap_table(deal_id, holder, security_class, shares, as_converted_shares, fully_diluted_pct,
role_notes)`

`consents(consent_id PK, deal_id, contract_name, counterparty, consent_type,
required_for_closing, risk_rating, amount_at_risk, notes)`

`employees(employee_id PK, deal_id, employee_group, count, draft_treatment,
playbook_requirement, pto_liability, service_credit_required, warn_risk, notes)`

`material_contracts(contract_id PK, deal_id, contract_name, contract_type, annual_revenue,
anti_assignment, change_of_control, consent_required, notes)`

`regulatory(deal_id PK, hsr_required, threshold_basis, regulatory_approval,
hell_or_high_water_required, notes)`

`diligence_findings(finding_id PK, deal_id, topic, severity, amount, source, notes)`

`deal_notes(note_id PK, deal_id, author, note_date, topic, content, source_document)`

`documents(document_id PK, deal_id, document_type, title, summary, version, effective_date)`

## Source value vocabularies

Read these as *source* conventions; the answer template decides the *output* convention.

- `draft_terms.staleness_flag`: `current` | `stale`.
- `draft_terms.unit`: `percent_points`, `months`, `dollars`, `contracts`, `boolean`, `text`,
  `restricted_change`, `additional_carveouts`. A `text`/`boolean` term carries its meaning in
  `draft_value` prose with `numeric_value` null — read the prose.
- `basis` (terms and rules): `purchase price`, `equity value`, `enterprise value`,
  `general representations`, `all representations`, `material contracts`, `indemnity claims`,
  `continuing employees`, `post-closing operations`, `approved list`, and similar.
- Risk-ish fields are **title case** in the source: `consents.risk_rating`,
  `diligence_findings.severity`, `playbook_rules.risk_default` → `High` | `Medium` | `Low`.
  `employees.warn_risk` is **lower case** (`low` | `medium`).
- Boolean-ish fields are **`yes`/`no` strings**: `consents.required_for_closing`,
  `employees.service_credit_required`, `material_contracts.consent_required` /
  `anti_assignment` / `change_of_control`, `regulatory.hsr_required`,
  `policy_thresholds.restricted_flag`. `regulatory.hell_or_high_water_required` also takes
  `limited covenant`.
- `cap_table.fully_diluted_pct` is a **fraction** — the rows sum to `1.0`, not `100`. Sum them
  to confirm before converting to whatever the template wants.
- `draft_terms.numeric_value` for a `percent_points` term is already in percent points
  (`18.0` means 18%), and is a REAL — cast to int where the template wants months or counts.
- `risk_estimates.category` per deal: `closing certainty`, `indemnity leakage`,
  `transition disruption`. Templates name these in snake_case; map accordingly.
- `benchmarks.metric` names the comparison (fee percent of equity value, general cap percent
  of purchase price, general representation survival months) with `median_value`,
  `mean_value`, `upper_quartile`, `sample_size`.

## Decoys

The workbench contains many deals beyond the target. Each target deal has several decoys
sharing a near-miss `project_name`/`target_name` (one syllable apart), usually with
`PRJ_D###` IDs, and often a *different* `client_side` and a *different* bound playbook — so a
wrong-deal lookup silently yields a wrong governing standard as well. Some decoy deals
advertise in `strategic_context` that their records include stale and duplicate rows.

Match on `deal_id` only. Confirm `client_side` and `playbook_id`/`policy_id` from the deal
record against what the prompt asserts before using any rule.
