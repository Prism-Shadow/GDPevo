---
name: finance-api-close-review
description: Solve shared ERP finance API tasks that require JSON-only reimbursement/AP close decisions, stale AP snapshot correction, prepaid amortization and GL reconciliation, vendor onboarding finance-risk release calls, or account-change payment release reviews. Use when a task supplies TASK_ENV_BASE_URL or a local input payload plus an answer_template and asks Codex to reconcile current API evidence into a close, release, hold, block, or exception output.
---

# Finance API Close Review

## Core Workflow

1. Read the prompt, `input/payloads/answer_template.json`, and every local payload before querying the API. Treat the template as the required output contract.
2. Use the runner-provided API base URL as the source of truth. Local CSV exports or batch payloads identify scope and context; they do not override current API records unless the prompt explicitly says so.
3. Query `/endpoints` first when available. The API supports exact-match query parameters by field name plus `limit` and `offset` pagination.
4. Run `scripts/erp_evidence.py` to gather scoped records and draft calculations:

```bash
python /work/skill/scripts/erp_evidence.py --base-url "$TASK_ENV_BASE_URL" --task-dir .
```

Pass the task root or the directory that contains `prompt.txt`; the helper also detects a child `input/` directory.

5. Apply the decision recipes in `references/decision-rules.md`, then build the final JSON manually to match the template exactly.

## Output Discipline

- Return JSON only when the prompt asks for JSON only.
- Preserve the template's top-level keys, enum values, required constants, and ordering rules.
- Sort ID lists as instructed by the template or prompt. If no special order is specified, sort lexicographically ascending.
- Round currency amounts to two decimals. For USD cents fields, convert dollars to integer cents only when the template asks for cents.
- Do not include records outside the requested candidate IDs, business IDs, invoice IDs, accounts, period, or entity.

## Source Priorities

- Current API records outrank stale AP snapshots, old review statuses, local notes, and copied batch context.
- For claim and AP tasks, reconcile claims, AP bills, payments, AP aging, and close logs together before assigning status.
- For prepaid tasks, use invoice `monthly_amortization` and `data_quality_flags` from the API, then compare computed schedule ending balances to GL ending balances for the requested period and accounts.
- For vendor release tasks, combine compliance objects, per-business compliance endpoints, vendor records, and local account-change or onboarding payloads.

## Reference

Read `references/decision-rules.md` before finalizing any answer. It contains the reusable close/release rules inferred from the staged examples without task-specific answer records.
