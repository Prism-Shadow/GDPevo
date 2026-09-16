# Northstar Data Map

## Environment Access

Use the base URL and bearer token from the current task prompt or task context. The SQL endpoint uses this request shape:

```bash
curl -sS -X POST "$BASE_URL/sql/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT 1 AS ok"}'
```

The SQL request body key is `sql`. The response contains `columns`, `rows`, `row_count`, and may be limited.

Allowed business endpoints are usually:

- `GET /`
- `GET /health`
- `GET /portal`
- `GET /api/tables`
- `GET /api/cases`
- `GET /api/cases/{case_id}`
- `GET /api/policies`
- `GET /api/policies/{policy_id}`
- `GET /api/documents/{document_id}`
- `GET /api/rate-schedules`
- `GET /api/appeals`
- `POST /sql/query`

## Tables and Keys

- `cases`: `case_id`, `member_id`, `provider_id`, `request_type`, `service_domain`, `policy_id`, dates, stage/status, urgency, summary.
- `members`: `member_id`, `plan_id`, plan/product/member status fields.
- `plans`: `plan_id`, payer/plan type/state/network/effective dates.
- `providers`: `provider_id`, provider identity and specialty.
- `request_lines`: `line_id`, `case_id`, CPT, modifier, service name, requested units, requested dates, diagnoses, charge.
- `authorizations`: `auth_id`, `case_id`, auth number, status, approved units/dates/CPT/modifier, denial reason.
- `policies`: `policy_id`, policy name, version, effective dates, precedence, summary.
- `policy_criteria`: `criterion_id`, `policy_id`, key, criterion text, approval flag, result if missing.
- `case_criteria`: `case_id`, `criterion_id`, result, evidence fact IDs, gap description, reviewer scope.
- `documents`: `document_id`, `case_id`, type, document date, received date, source system, `is_current`, title, summary.
- `document_facts`: `fact_id`, `document_id`, `case_id`, key/value/numeric/unit, supported criteria.
- `appeals`: `appeal_id`, `case_id`, denial/received dates, requested type, appeal path, expedited attestation, deadline, outcome, owner, notes.
- `drug_trials`: `trial_id`, `case_id`, medication, outcome, documented flag, dates, notes.
- `assistance_screen`: `case_id`, program name, income FPL, insurance type, denial requirement/file status, missing fields, assistance status.
- `claims`: `claim_id`, `member_id`, `case_id`, payer, received date, status, auth number, billed total, paid total.
- `claim_lines`: `claim_line_id`, `claim_id`, line number, CPT, modifier, units, billed/paid amounts, denial code, service date.
- `payment_benchmarks`: `benchmark_id`, payer, plan type, service domain, CPT, modifier, effective dates, allowed amount, source name/version.
- `p2p_events`: `p2p_id`, `case_id`, scheduled time, duration, provider argument, new information, outcome, final status, reviewer, notes.
- `service_margin`: `month_id`, period, payer, payer segment, service domain, CPT, visits, net revenue, variable cost, fixed cost allocated, charge-sensitive flag.

## Query Patterns

Start with the target and pull related rows explicitly. Replace placeholder values before sending SQL; the endpoint accepts a raw SQL string in the `sql` field, not a separate parameters object.

Case-centered review:

```sql
SELECT * FROM cases WHERE case_id = :case_id;
SELECT * FROM request_lines WHERE case_id = :case_id ORDER BY line_id;
SELECT * FROM authorizations WHERE case_id = :case_id;
SELECT * FROM case_criteria WHERE case_id = :case_id ORDER BY criterion_id;
SELECT * FROM documents WHERE case_id = :case_id ORDER BY document_id;
SELECT * FROM document_facts WHERE case_id = :case_id ORDER BY fact_id;
```

Policy context:

```sql
SELECT * FROM policies WHERE policy_id = :policy_id;
SELECT * FROM policy_criteria WHERE policy_id = :policy_id ORDER BY criterion_id;
```

Appeal and assistance:

```sql
SELECT * FROM appeals WHERE appeal_id = :appeal_id OR case_id = :case_id;
SELECT * FROM drug_trials WHERE case_id = :case_id ORDER BY medication;
SELECT * FROM assistance_screen WHERE case_id = :case_id;
```

Claim repricing:

```sql
SELECT * FROM claims WHERE claim_id = :claim_id;
SELECT * FROM claim_lines WHERE claim_id = :claim_id ORDER BY line_number;
SELECT * FROM payment_benchmarks
WHERE payer = :payer
  AND plan_type = :plan_type
  AND service_domain = :service_domain
  AND cpt_code IN (:cpt_codes);
```

When applying benchmarks, filter each candidate line by modifier equality, treating SQL null and empty output modifier carefully, and require `service_date BETWEEN effective_start AND effective_end`.

Margin queue:

```sql
SELECT * FROM service_margin
WHERE month_id IN (:row_ids);
```

Reorder the returned rows to match the row ID order from task context.

## Field Normalization

- Boolean-like integer fields use `1` as true and `0` as false.
- Text fields such as approved CPT, evidence fact IDs, supported criteria, missing fields, and notes may need splitting or JSON parsing depending on their content.
- Use `document_id` for evidence/excluded documents, `trial_id` for drug-trial audit records, `benchmark_id` for benchmark audit records, `claim_line_id` for claim-line audit records, `p2p_id` for P2P audit records, and `month_id` for margin queue audit records.
- Keep identifiers exactly as returned by the environment.
