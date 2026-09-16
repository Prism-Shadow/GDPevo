---
name: finance-api-controls
description: Reconcile finance and compliance control batches against a runner-provided JSON API and return schema-conforming JSON. Use when a task asks Codex to decide AP reimbursement close status, stale AP snapshot corrections, vendor onboarding or payment-release controls, or prepaid schedule-versus-GL close results using TASK_ENV_BASE_URL and local payload templates.
---

# Finance API Controls

## Core Workflow

Use the current task API as the system of record. Treat local payload files as the scope, schema, stale context, or review memo, not as authoritative finance state unless the prompt says otherwise.

1. Read the prompt, `answer_template.json`, and every local payload file before calling the API.
2. Extract the requested IDs, as-of date or close period, accounts, thresholds, allowed enum values, required ordering, and numeric precision from the prompt/template.
3. Discover the API with `GET /endpoints` when endpoint names are uncertain. Prefer `/api/...` endpoints when both bare and `/api` variants exist.
4. Fetch only current API evidence needed for the requested IDs. Use exact-match query parameters by field name and paginate list endpoints.
5. Build a small evidence table per claim, invoice, business, vendor, or account before assigning decisions.
6. Apply the control rules in [references/api-control-patterns.md](references/api-control-patterns.md). If the prompt or template gives a more specific rule, follow it.
7. Return exactly the requested JSON shape. Do not add narrative text, comments, extra keys, or evidence notes unless the template asks for them.

## API Helper

Use [scripts/fetch_task_api.py](scripts/fetch_task_api.py) to fetch and paginate task API records without rewriting curl loops:

```bash
python skill/scripts/fetch_task_api.py /api/claims --filter claim_id=CLAIM-ID --pretty
python skill/scripts/fetch_task_api.py /api/ap/bills --filter claim_id=CLAIM-ID --pretty
python skill/scripts/fetch_task_api.py /api/vendors --filter vendor_id=VENDOR-ID --pretty
python skill/scripts/fetch_task_api.py /api/compliance/objects --filter business_id=BUSINESS-ID --pretty
python skill/scripts/fetch_task_api.py /api/prepaids/invoices --filter account=1250 --pretty
```

The script reads `TASK_ENV_BASE_URL` by default. If the runner supplies the base URL only in the prompt, pass it with `--base-url`.

## Output Discipline

- Sort every ID list exactly as the prompt/template requests, usually ascending lexicographic ID order.
- Preserve template enum spellings exactly.
- Use decimal arithmetic for money. Round final currency fields to the precision specified by the template, usually two decimals.
- For required objects keyed by IDs, include every requested ID even when the value is empty, zero, or false.
- Do not copy local stale snapshots into the answer. Reconcile them to current API state first.
