---
name: task-group-005-finance-controls
description: Use this skill for task_group_005 shared ERP, AP, compliance, vendor onboarding, prepaid close, reimbursement close, stale AP export, account-change release, or finance-risk JSON tasks that require calling a runner-provided task API and returning an answer_template-shaped JSON object. It guides API discovery, current-record reconciliation, close-control decisions, and strict schema output.
---

# Task Group 005 Finance Controls

Use this skill when the task asks for finance-risk, AP reimbursement, vendor onboarding, prepaid close, stale AP snapshot, or account-change payment-release decisions from a shared ERP/compliance API.

## Core Workflow

1. Read the prompt and every local payload in `input/payloads/`.
2. Treat `answer_template.json` as the output contract: preserve required keys, enum values, order requirements, numeric precision, and ID ordering.
3. Use the runner-provided API base URL as the system of record. Local snapshots and batch files define scope and context, but current API records decide the answer unless the prompt says otherwise.
4. Call `/endpoints` first when available. Prefer `/api/...` endpoints, but fall back to the non-API aliases named in the prompt or endpoint list.
5. Fetch only the scoped records needed for the requested IDs/accounts/period, plus related bills, payments, vendors, compliance details, GL balances, and close logs when relevant.
6. Build a scratch reconciliation table before writing final JSON. Record the source evidence for each ID, especially status, amount, vendor, payment, bank, screening, tax, license, and data-quality fields.
7. Return only the requested JSON object when the prompt asks for JSON only. Do not include narrative text, citations, or extra properties.

For detailed decision rules, read [references/control-rules.md](references/control-rules.md). For paginated API pulls, use [scripts/api_fetch.py](scripts/api_fetch.py).

## API Access Pattern

Normalize the base URL, then use exact-match query parameters and pagination:

```bash
python skill/scripts/api_fetch.py --base-url "$TASK_ENV_BASE_URL" --endpoint /endpoints
python skill/scripts/api_fetch.py --base-url "$TASK_ENV_BASE_URL" --endpoint /api/claims --param claim_id=CLAIM_ID
python skill/scripts/api_fetch.py --base-url "$TASK_ENV_BASE_URL" --endpoint /api/ap/bills --param claim_id=CLAIM_ID
python skill/scripts/api_fetch.py --base-url "$TASK_ENV_BASE_URL" --endpoint /api/ap/payments --param bill_id=BILL_ID
```

If the runner supplies the base URL in the prompt rather than an environment variable, pass it with `--base-url`. If exact filters return multiple rows, disambiguate using all available fields, not just one ID.

## Output Discipline

- Sort ID lists exactly as the template or prompt says, usually ascending lexical ID order.
- Preserve payload order only where the template says "same order as" a local scope file.
- Round USD amounts to two decimals unless the template asks for cents or another precision.
- Use booleans and enums exactly as allowed by the template.
- Do not copy source `review_status` or `status` fields directly into decisions. Decisions are release-control conclusions from reconciled evidence.
- When evidence conflicts, current API records outrank stale local exports. The prompt and schema outrank example-derived heuristics.
