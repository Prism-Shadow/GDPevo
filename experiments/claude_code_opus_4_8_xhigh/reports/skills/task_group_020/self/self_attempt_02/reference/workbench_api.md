# Workbench API reference

Base URL and credentials come from `environment_access.md`. Use only the
endpoints that file authorizes; the list below is the superset seen so far.

## HTML pages (browsable, non-authoritative)

`GET /` · `GET /workspace` · `GET /deals/<deal_id>` · `GET /playbooks` · `GET /policies`

Useful for orientation. Always confirm values against the JSON APIs or SQL — the
pages summarize.

## JSON endpoints and their wrapper keys

Every deal sub-resource returns an object with a **single wrapper key**, which is
not always the URL segment. Unwrap before iterating.

| Endpoint | Wrapper key | Shape |
|---|---|---|
| `GET /api/deals` | `deals` (+ `count`) | list |
| `GET /api/deals/<id>` | `deal`, `links` | object |
| `GET /api/deals/<id>/terms` | **`draft_terms`** | list |
| `GET /api/deals/<id>/documents` | `documents` | list |
| `GET /api/deals/<id>/benchmarks` | `benchmarks` | list |
| `GET /api/deals/<id>/risk-estimates` | **`risk_estimates`** | list |
| `GET /api/deals/<id>/cap-table` | **`cap_table`** | list |
| `GET /api/deals/<id>/consents` | `consents` | list |
| `GET /api/deals/<id>/employees` | `employees` | list |
| `GET /api/deals/<id>/material-contracts` | **`material_contracts`** | list |
| `GET /api/deals/<id>/regulatory` | `regulatory` | **object, not a list** |
| `GET /api/deals/<id>/diligence-findings` | **`diligence_findings`** | list |
| `GET /api/deals/<id>/notes` | **`deal_notes`** | list |
| `GET /api/playbooks` | `playbooks` | list of `{playbook_id, rule_count}` |
| `GET /api/playbooks/<id>/rules` | **`rules`** (beside scalar `playbook_id`) | list |
| `GET /api/policies` | `policies` | list of `{policy_id, threshold_count}` |
| `GET /api/policies/<id>/thresholds` | **`thresholds`** (beside scalar `policy_id`) | list |
| `GET /api/search?q=<term>` | `deals`, `documents`, `notes`, `terms` | **cross-deal** |

`GET /api/search` is not deal-scoped. Use it to discover, never to source
values.

## Read-only SQL

```
POST /api/query
Content-Type: application/json
{"token": "<token from environment_access.md>", "sql": "SELECT ..."}
```

Returns `{"columns": [...], "rows": [[...]], "row_count": N}`.

SQLite dialect. Use it for anything cross-table — reconciling consents against
material contracts, checking whether a category exists only as a stale row,
confirming a deal's playbook before you rely on it.

## Table schema

```sql
deals(deal_id PK, project_name, transaction_type, client_side, client_name,
      counterparty_name, target_name, industry, headline_value, upfront_cash,
      stock_value, milestone_value, currency, signing_date, meeting_date,
      playbook_id, policy_id, status, strategic_context)

draft_terms(term_id PK, deal_id, category, draft_value, numeric_value, unit,
            basis, source_document, clause_ref, counterparty_rationale,
            last_updated, staleness_flag)

playbook_rules(playbook_id, category, preferred_position, fallback_position,
               limit_value, limit_unit, basis, required_action, risk_default,
               notes)

policy_thresholds(policy_id, category, policy_standard, threshold_value,
                  threshold_unit, basis, approval_required, restricted_flag,
                  notes)

benchmarks(benchmark_id PK, deal_id, category, metric, sample_size,
           median_value, mean_value, upper_quartile, notable_precedent, notes)

risk_estimates(estimate_id PK, deal_id, category, exposure_low, exposure_high,
               confidence, method, notes)

cap_table(deal_id, holder, security_class, shares, as_converted_shares,
          fully_diluted_pct, role_notes)

consents(consent_id PK, deal_id, contract_name, counterparty, consent_type,
         required_for_closing, risk_rating, amount_at_risk, notes)

employees(employee_id PK, deal_id, employee_group, count, draft_treatment,
          playbook_requirement, pto_liability, service_credit_required,
          warn_risk, notes)

material_contracts(contract_id PK, deal_id, contract_name, contract_type,
                   annual_revenue, anti_assignment, change_of_control,
                   consent_required, notes)

regulatory(deal_id PK, hsr_required, threshold_basis, regulatory_approval,
           hell_or_high_water_required, notes)

diligence_findings(finding_id PK, deal_id, topic, severity, amount, source, notes)

deal_notes(note_id PK, deal_id, author, note_date, topic, content, source_document)

documents(document_id PK, deal_id, document_type, title, summary, version,
          effective_date)
```

## ID conventions

Stable IDs are prefixed and deal-scoped, e.g. `TERM_<DEAL>_NN`, `CNS_<DEAL>_NN`,
`EMP_<DEAL>_NN`, `FND_<DEAL>_NN`, `RSK_<DEAL>_NN`, `BM_<DEAL>_NN`,
`NOTE_<DEAL>_NN`, `DOC_<DEAL>_NN`, `MC_<DEAL>_NN`.

Quote them exactly as returned. When a template asks for "stable source IDs",
it means these — not names, not indices, not IDs you compose yourself.

## Useful reconnaissance queries

```sql
-- confirm the comparison basis before relying on it
SELECT deal_id, client_side, playbook_id, policy_id, headline_value,
       upfront_cash, stock_value, milestone_value, transaction_type
FROM deals WHERE deal_id = 'PRJ_XXXX';

-- current draft positions only
SELECT term_id, category, numeric_value, unit, basis, clause_ref, draft_value
FROM draft_terms
WHERE deal_id = 'PRJ_XXXX' AND staleness_flag = 'current'
ORDER BY category;

-- categories the draft is silent on because their only row is stale
SELECT category FROM draft_terms WHERE deal_id='PRJ_XXXX' AND staleness_flag='stale'
EXCEPT
SELECT category FROM draft_terms WHERE deal_id='PRJ_XXXX' AND staleness_flag='current';

-- closing blockers and money at risk
SELECT consent_id, contract_name, counterparty, risk_rating, amount_at_risk
FROM consents WHERE deal_id='PRJ_XXXX' AND required_for_closing='yes';

SELECT contract_id, contract_name, annual_revenue, consent_required
FROM material_contracts WHERE deal_id='PRJ_XXXX' AND consent_required='yes';

-- workforce totals
SELECT SUM(count), SUM(pto_liability) FROM employees WHERE deal_id='PRJ_XXXX';
```
