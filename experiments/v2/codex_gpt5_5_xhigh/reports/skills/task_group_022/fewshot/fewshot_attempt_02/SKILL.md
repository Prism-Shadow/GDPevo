---
name: atlas-commerce-ops
description: Use for Atlas Commerce Operations workplace tasks that require authenticated schema/data-dictionary lookup, read-only SQL analysis, cutoff-based operational metrics, exact JSON answers from templates, or explicitly approved canonical data corrections with audit records. Applies to fulfillment, refunds, carrier quality, warehouse productivity, support health, and related Atlas Commerce database analysis requests.
---

# Atlas Commerce Ops

Use this skill when a task references the Atlas Commerce Operations workplace, `<TASK_ENV_BASE_URL>`, `environment_access.md`, or the Atlas order/warehouse/refund/carrier/support schema.

## Required Workflow

1. Read the user prompt, every file under `input/payloads/`, and especially `answer_template.json` plus the business request payload.
2. If the task environment is needed, read `environment_access.md` for the base URL and `Authorization` header. Do not get credentials from anywhere else.
3. Fetch `GET /api/schema` and `GET /api/data-dictionary` before writing SQL. The dictionary defines UTC timestamp, money, source-row, and snapshot conventions.
4. Use `POST /api/sql` for read-only analysis. Do not mutate workplace data unless the request explicitly asks for a controlled correction and includes an approved correction/audit policy.
5. Treat request timestamps and dates as exact boundaries. Honor the payload's inclusive/exclusive wording; otherwise use the boundary text in the prompt.
6. Build the answer object to match `answer_template.json` exactly: required fields only, no commentary, correct ordering for arrays, final-only rounding.
7. Save the JSON result to the requested `answer.json`.

## API Helper

The bundled helper can reduce curl boilerplate:

```bash
python3 skill/scripts/atlas_api.py schema
python3 skill/scripts/atlas_api.py dictionary
python3 skill/scripts/atlas_api.py sql 'select count(*) as n from orders'
python3 skill/scripts/atlas_api.py sql-file query.sql
```

The helper reads `environment_access.md` by default and prints the API JSON response. For correction tasks, prefer explicit curl or a reviewed JSON request to the transaction endpoint; only use the helper's `transaction-file` command after pre-checking the exact transaction payload.

## Data Rules

- Production account scope means `accounts.is_internal = 0` and `accounts.is_test = 0` unless the request defines a different population.
- Header `current_status` fields are convenience snapshots and can be later than the requested cutoff. For state at a cutoff, reconstruct from de-duplicated append-only events up to that cutoff.
- Imported event/source tables may contain retries. De-duplicate rows by `(source_system, external_event_id)`, keeping the row with the latest `ingested_at`; use a stable row id as a tie-break if needed.
- For logical refunds, after source de-duplication count distinct `refund_id` values, not raw rows.
- Monetary `*_minor` values are in the smallest unit of the row currency. Convert with `fx_rates.usd_per_unit` for the row's service date or requested comparison date, divide by 100, and round only the final reported money value.
- Rank using unrounded metrics, then round reported values to the template precision.
- Sort ID arrays exactly as the template or request states, commonly ascending by the stable ID.

## Task Patterns

Read `references/query-patterns.md` when implementing one of these task types:

- **Fulfillment scorecards**: campaign/window eligibility, latest order state at cutoff, shipment completion from latest effective carrier scan, on-time and severe-exception classification.
- **Refund reconciliation**: production account filtering, de-duplicated settled refunds, linked reversals, FX conversion, leakage candidates, and reason ranking.
- **Carrier quality correction**: identify exactly one raw/canonical contradiction, calculate pre/post backlog, apply only approved canonical-field mutation, insert one audit row, and verify before returning `APPLIED`.
- **Warehouse productivity**: production task cohort, de-duplicated warehouse task events, completed units, units per hour, delayed high-priority tasks, team completion rate, and status policy.
- **Support health**: eligible support case scope, state at cutoff from case events, support active-time clocks, SLA breaches, severe active cases, median resolved active time, and risk policy.

## Correction Safety

For any mutation request:

- First prove the target row, old value, new value, and allowed field from read-only SQL.
- Confirm the request permits mutation and supplies the audit metadata.
- The transaction must update only the approved canonical field on exactly one business row and insert exactly one `correction_audit` row.
- Preserve raw/source identity fields and unrelated rows.
- After the transaction, re-query the target value and audit view. Return `APPLIED` only when the request's success rule is fully satisfied; otherwise return `NOT_APPLIED` with observed counts.

## Output Checks

Before finalizing:

- Re-run small reconciliation queries for eligible counts, component counts, rates, and list sizes.
- Validate the answer shape against `answer_template.json` when possible.
- Ensure no explanatory text is written outside `answer.json`.
