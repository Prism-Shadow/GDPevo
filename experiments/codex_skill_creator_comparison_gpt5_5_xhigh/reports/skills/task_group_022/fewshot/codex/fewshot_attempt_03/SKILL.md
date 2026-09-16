---
name: atlas-commerce-ops-solver
description: Solve Atlas Commerce Operations database tasks that provide prompt.txt, request payloads, answer_template.json, and authenticated TASK_ENV_BASE_URL API endpoints. Use for fulfillment, refund, carrier quality, warehouse productivity, support health, inventory, order, payment, customer, SQL analysis, and controlled canonical-correction tasks that must write an exact answer.json.
---

# Atlas Commerce Ops Solver

## Core Workflow

1. Read the task prompt, every file under `input/payloads/`, and especially `answer_template.json`. Treat the request payload and template as the contract; do not add narrative or extra fields to `answer.json`.
2. Fetch live Atlas metadata before writing analysis SQL:

```bash
python skill/scripts/atlas_api.py schema
python skill/scripts/atlas_api.py dictionary
```

3. Use [references/atlas-patterns.md](references/atlas-patterns.md) when designing the SQL plan. Build the solution in auditable CTEs: cohort, effective rows or state at cutoff, metric rows, ordered output arrays, risk/status classification.
4. Query through the read-only endpoint unless the request explicitly requires an approved correction:

```bash
python skill/scripts/atlas_api.py sql --file query.sql
```

5. Keep intermediate ratios and money unrounded. Round only final reported fields to the precision required by the request/template.
6. Write a single JSON object to `answer.json`, then validate it:

```bash
python skill/scripts/validate_answer.py input/payloads/answer_template.json answer.json
```

## SQL Discipline

- Prefer one final SQL query with named CTEs over scattered manual arithmetic. Add diagnostic queries only to inspect cardinalities, distinct statuses, or tie-break behavior.
- Derive state as of a cutoff from the relevant event/source table when a request uses words such as `effective`, `at cutoff`, `as of`, `active`, or `backlog`. Snapshot `current_status` columns are convenient but may lag append-only history.
- Apply production scope through the account flags when the request says production accounts/orders/customers: exclude internal and test accounts unless the request says otherwise.
- Sort every output array in the exact order specified by the request/template. Use stable tie-breakers from the payload, commonly identifier ascending.
- Validate suspicious results with independent cross-checks: cohort count, numerator/denominator count, duplicate logical IDs, missing FX rows, and row counts before/after any mutation.

## Controlled Corrections

Use `POST /api/sql/transaction` only when the request explicitly asks for a controlled correction. First identify the target with read-only SQL, calculate the pre-correction metric, and confirm the approved scope.

For canonical source corrections:

- Update only the approved canonical field and any explicitly allowed correction metadata fields.
- Never change raw source values, source-system identifiers, external event IDs, or unrelated business rows.
- Insert exactly the audit record required by the payload.
- Re-query the business row, audit row, and post-correction metric before reporting `APPLIED`.
- Report `NOT_APPLIED` with the observed row counts if the transaction, audit insert, or post-change verification does not satisfy the request's success rule.

The API helper can post a prepared transaction body without assuming its shape:

```bash
python skill/scripts/atlas_api.py transaction --file transaction.json
```
