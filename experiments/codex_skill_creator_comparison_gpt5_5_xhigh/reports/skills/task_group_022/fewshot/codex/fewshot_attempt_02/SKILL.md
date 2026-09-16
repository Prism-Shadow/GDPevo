---
name: atlas-commerce-ops
description: Solve Atlas Commerce Operations workplace tasks that require authenticated SQL analysis, approved canonical data corrections, and strict answer.json output. Use for prompts mentioning Atlas Commerce Operations APIs, fulfillment scorecards, refund reconciliation, carrier scan quality corrections, warehouse productivity, support health, inventory, payments, orders, shipments, warehouses, support cases, or JSON answer templates.
---

# Atlas Commerce Ops

## Core Workflow

1. Read the prompt, every request payload, and the answer template before querying. Treat the request payload as the business policy and the template as the output contract.
2. Resolve the task service URL and bearer token from the prompt or environment. Fetch `/api/schema` and `/api/data-dictionary` at the start of each task; table availability is part of the runtime contract.
3. Use read-only `POST /api/sql` for analysis. Use `POST /api/sql/transaction` only when the request explicitly approves a concrete correction.
4. Build SQL in named CTEs that mirror the request definitions: cohort, effective source rows, cutoff state, metric rollups, ranking, and final projection.
5. Prefer append-only event/source tables over denormalized `current_status` snapshots for any as-of cutoff calculation. Use snapshots only as a cross-check or when the request defines current-state semantics.
6. Round only final reported numbers, keep ordering based on unrounded values, and apply every template ordering/tie-break rule before limiting arrays.
7. Write exactly one JSON object to `answer.json`. Include no commentary, no extra fields, no omitted required fields, and use empty arrays only when the schema permits them.

Read [references/atlas_patterns.md](references/atlas_patterns.md) before writing SQL for Atlas Commerce Operations tasks.

## API Helper

Use [scripts/atlas_api.py](scripts/atlas_api.py) when it saves time:

```bash
python3 scripts/atlas_api.py schema
python3 scripts/atlas_api.py dictionary
python3 scripts/atlas_api.py sql < query.sql
python3 scripts/atlas_api.py audit
python3 scripts/atlas_api.py post /api/sql/transaction < transaction_body.json
```

The helper uses `TASK_ENV_BASE_URL` when set, otherwise `http://task-env:9022/`, and sends `Authorization: Bearer $TASK_ENV_API_TOKEN` when the token exists.

## Correction Tasks

Apply mutations only for prompts that explicitly request an approved correction. First identify the exact target row with read-only SQL, compute pre-change metrics, and build a transaction that changes only the approved canonical field plus the required audit insert. After the transaction, verify the target value, audit row, and post-change metric with fresh reads. Report `APPLIED` only when the request's success rule is fully satisfied; otherwise report the observed `NOT_APPLIED` state.
