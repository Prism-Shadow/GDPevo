---
name: finance-control-api-review
description: Reconcile finance-control batches against runner-provided JSON APIs and local answer templates. Use when solving ERP, AP, compliance, vendor onboarding, prepaid close, reimbursement close, stale AP snapshot refresh, or account-change payment release tasks that require a strict JSON decision output.
---

# Finance Control API Review

## Core Workflow

1. Read the user prompt, the answer template, and every local payload that defines scope. Treat scoped IDs, review dates, periods, thresholds, and required output keys from those files as authoritative.
2. Use the runner-provided task API as the system of record. Query `/endpoints` first when available, prefer `/api/...` endpoints, and fall back to the non-API aliases named by the prompt.
3. Fetch current records with exact-match filters by ID field. Use local snapshots or batch files only as scope/context unless the prompt explicitly says they are authoritative.
4. Build an evidence table per scoped claim, business, invoice, or ticket before deciding. Do not copy source `review_status` values directly into the answer; derive release or close posture from the current evidence.
5. Return only the JSON object requested by the template. Preserve required key names, enum spellings, precision, and ordering. Sort ID lists ascending unless the template says to keep payload order.

## API Helper

Use [scripts/task_api.py](scripts/task_api.py) when repeated API reads would be error-prone:

```bash
python scripts/task_api.py --base-url "$TASK_ENV_BASE_URL" get /endpoints
python scripts/task_api.py --base-url "$TASK_ENV_BASE_URL" batch /api/claims claim_id ID-1 ID-2
python scripts/task_api.py --base-url "$TASK_ENV_BASE_URL" batch /api/ap/bills claim_id ID-1 ID-2
```

The helper performs read-only GET requests, URL-encodes filters, follows paginated collection responses when requested, and emits JSON.

## Review Patterns

Read [references/control_review_workflows.md](references/control_review_workflows.md) for the decision logic to apply by task family:

- Reimbursement and AP close batches: current claim readiness, matching AP bills, payment evidence, stale snapshot corrections, and close-log references.
- Vendor onboarding finance-risk release: hard-stop flags, UBO counts, follow-up IDs, and overall release readiness.
- Prepaid close checks: scoped straight-line amortization, invoice exceptions, account rollups, GL variances, and account status.
- Account-change payment release reviews: bank, tax, license, screening, vendor status, risk override, review queue, and release/hold/escalate decisions.

## Output Discipline

Use decimal arithmetic or integer cents for money and round only at output boundaries. Include empty arrays or objects when the template requires them. If a required record is missing from the API, mark the item as not ready, blocked, awaiting information, or review queue according to the template rather than inventing evidence.
