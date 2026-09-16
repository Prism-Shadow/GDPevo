---
name: erp-batch-reconciler
description: Reconcile finance and compliance batch tasks against a runner-provided ERP/task API and return strict JSON. Use when a prompt mentions task_group ERP data, shared finance/compliance APIs, reimbursement claims, AP bills/payments, stale AP snapshots, vendor onboarding or payment release, account-change risk review, prepaid close schedules, GL balances, or answer_template.json-driven finance close outputs.
---

# ERP Batch Reconciler

Use this skill to solve batch reconciliation tasks where local payloads define the scope and output schema, but the authoritative evidence lives in the task environment API.

## Core Workflow

1. Read the prompt and every file under `input/payloads/`, especially `answer_template.json`.
2. Treat local batch/scope/snapshot files as scope and context. Treat the API as the current system of record.
3. Resolve the base URL supplied by the runner. If the prompt shows `<TASK_ENV_BASE_URL>`, do not call that literal string; use the actual environment/task base URL available in the run.
4. Call `GET /endpoints` first when endpoint names are uncertain. The API supports exact-match query parameters by field name, plus `limit` and `offset`.
5. Fetch only the records needed for the requested IDs, then build a small evidence table before deciding.
6. Apply the domain rules in [references/rules.md](references/rules.md).
7. Return only one JSON object matching the template. Do not include notes, markdown, or derivation text unless the template asks for them.

## API Shortcuts

Prefer exact-match queries such as:

```bash
curl -sS "$TASK_ENV_BASE_URL/api/claims?claim_id=$CLAIM_ID"
curl -sS "$TASK_ENV_BASE_URL/api/ap/bills?claim_id=$CLAIM_ID"
curl -sS "$TASK_ENV_BASE_URL/api/ap/payments?bill_id=$BILL_ID"
curl -sS "$TASK_ENV_BASE_URL/api/vendors?vendor_id=$VENDOR_ID"
curl -sS "$TASK_ENV_BASE_URL/api/compliance/objects?business_id=$BUSINESS_ID"
curl -sS "$TASK_ENV_BASE_URL/api/compliance/ownership/$BUSINESS_ID"
curl -sS "$TASK_ENV_BASE_URL/api/compliance/registry/$BUSINESS_ID"
curl -sS "$TASK_ENV_BASE_URL/api/compliance/screening/$BUSINESS_ID"
curl -sS "$TASK_ENV_BASE_URL/api/compliance/bank/$BUSINESS_ID"
curl -sS "$TASK_ENV_BASE_URL/api/prepaids/invoices?prepaid_invoice_id=$INVOICE_ID"
curl -sS "$TASK_ENV_BASE_URL/api/prepaids/gl-balances?period=$PERIOD"
curl -sS "$TASK_ENV_BASE_URL/api/close/logs"
```

If many records are needed, the optional helper [scripts/fetch_task_api.py](scripts/fetch_task_api.py) can collect records into one JSON bundle:

```bash
python scripts/fetch_task_api.py --base-url "$TASK_ENV_BASE_URL" \
  --claim-id CLAIM-1 --business-id BUSINESS-1 --prepaid-invoice-id INVOICE-1 \
  --period YYYY-MM --include-close-logs
```

The helper is only a fetcher. You still need to apply the template and decision rules.

## Output Discipline

- Follow `answer_template.json` over natural-language hints when they conflict on type or precision.
- Preserve required top-level key order when the template provides `top_level_order` or `required_top_level_keys`.
- Sort ID lists exactly as requested, usually ascending by ID.
- Use two-decimal USD numbers when the template says `precision: 2`. Use integer cents only when the template explicitly requires integer cents.
- Do not include extra properties when the template disallows them.
- Recompute counts and totals from the final classified records, not from source-system status labels alone.
