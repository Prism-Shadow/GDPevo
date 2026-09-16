---
name: atlas-commerce-workplace
description: Use this skill for Atlas Commerce Operations workplace tasks that ask Codex to compute an exact JSON answer from an authenticated schema, data dictionary, and SQL API. Use it for fulfillment scorecards, refund reconciliation, carrier or inventory data-quality corrections, warehouse productivity, support/SLA health, account/order/shipment/payment reports, and any task mentioning TASK_ENV_BASE_URL, Atlas workplace data, read-only SQL, controlled SQL transactions, or correction audit records.
---

# Atlas Commerce Workplace Solver

This skill helps solve Atlas Commerce Operations tasks where the prompt provides
business rules, payload JSON files, an answer template, and an authenticated
workplace API. The reliable path is to turn the business definitions into SQL,
verify entity-level rows before rollups, and write exactly one JSON object to the
requested output file.

## First Moves

1. Read the task prompt completely.
2. Read every file under `input/payloads/`, especially the request facts and
   `answer_template.json`.
3. Fetch the live schema and data dictionary before writing SQL. The database is
   the source of truth for table names, timestamp fields, event fields, and
   nullable columns.
4. Build exploratory queries for enum-like values, date ranges, and join counts.
   Keep these small and read-only unless the request explicitly approves a
   correction.
5. Compute results from entity-level CTEs, then aggregate. Avoid calculating each
   answer field with unrelated ad hoc queries because denominators, cutoffs, and
   effective states must stay consistent.
6. Validate the final JSON against the template, including no extra keys, exact
   arrays, ordering, precision, and enum values.

Read [references/atlas_workflow.md](references/atlas_workflow.md) for the SQL
patterns and domain rules before doing the main analysis.

## API Helpers

The API uses bearer auth from `TASK_ENV_API_TOKEN`. If the prompt gives a base
URL, pass it with `--base-url` or set `TASK_ENV_BASE_URL`. In this harness, a
literal `<TASK_ENV_BASE_URL>` placeholder usually means the service is reachable
as `http://task-env:9022/`.

Use [scripts/atlas_api.py](scripts/atlas_api.py) from this skill directory:

```bash
python scripts/atlas_api.py schema > /tmp/atlas_schema.json
python scripts/atlas_api.py dictionary > /tmp/atlas_dictionary.json
python scripts/atlas_api.py sql "select count(*) as n from orders"
python scripts/atlas_api.py audit
```

For longer SQL, pipe stdin:

```bash
python scripts/atlas_api.py sql < /tmp/query.sql
```

For an approved controlled correction, prepare the transaction JSON required by
the task environment and post it with:

```bash
python scripts/atlas_api.py transaction /tmp/transaction.json
```

Only use the transaction endpoint when the request explicitly authorizes a
minimal correction. Otherwise use read-only SQL.

## Output Discipline

Return only the JSON object requested by the prompt. Do not include commentary in
`answer.json`. Match the template's key spelling exactly, including templates
that use nonstandard schema spellings such as `additional_properties`,
`min_items`, `max_items`, or `unique_items`.

Use [scripts/validate_answer.py](scripts/validate_answer.py) before finalizing:

```bash
python scripts/validate_answer.py input/payloads/answer_template.json answer.json
```

The validator is intentionally conservative. If it flags a type, key, precision,
pattern, or uniqueness issue, fix the answer JSON rather than explaining around
the mismatch.

## Habits That Matter

- Treat `production` accounts as excluding internal and test accounts unless the
  task defines a different production rule.
- Apply inclusive boundaries exactly when requested with `>= start` and
  `<= end`. For exclusive conditions such as "strictly before the cutoff", use
  `< cutoff`.
- Use event tables to derive effective state at a cutoff. Snapshot fields such
  as `current_status` are convenient hints, not proof, when the request defines
  event-derived state.
- Dedupe imported source rows when logical IDs or source retry fields make this
  necessary. Prefer the latest `ingested_at` for the same source identity.
- Keep one row per business entity for eligibility and flags. Then aggregate from
  that CTE so counts, rates, lists, and risk/status policies share the same
  denominator.
- Round only final reported numbers. Use unrounded values for rankings and
  thresholds unless the request says otherwise.
- Sort output arrays with the exact ordering rule in the request or template.
  ID lists are usually ascending.
- For correction tasks, update only the approved canonical field, preserve raw
  source values and identity fields, insert the requested audit record, and
  report the applied correction status only after post-change verification
  proves the success rule.
