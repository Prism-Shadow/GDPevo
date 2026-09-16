---
name: medbridge-sales-ops
description: Use for MedBridge Sales Ops API tasks that ask for account-ready JSON quote packages, RFQ/module quotes, freight comparisons, customer policy flags, opportunity milestone reconciliation, invoice/payment/revenue recognition status, or linked event/voucher follow-up actions.
license: MIT
compatibility: portable Codex solver with shell, Python 3 standard library, and read-only HTTP access to the task API
---

# MedBridge Sales Ops

Use this skill when a task references the MedBridge Sales Ops API and asks for a JSON-only quote, freight, policy, or opportunity reconciliation answer.

## Required Workflow

1. Read the task prompt and `input/payloads/answer_template.json`.
2. Use the API base URL supplied by the task runner or prompt. Do not reuse any creator-time URL.
3. Extract explicit record IDs, customer names, product codes, dates, quantities, event IDs, and voucher codes from the prompt.
4. Fetch API records before calculating. Start with exact endpoints for explicit IDs, then fetch collection lists when relationships need filtering.
5. Fill the output to match the template exactly: same top-level keys, nested shapes, controlled enum spellings, date format, nulls, arrays, and money precision.
6. Return only valid JSON. Do not include markdown or explanatory text.

For detailed derivation rules, read [references/medbridge-rules.md](references/medbridge-rules.md).

## API Collection Helper

Use [scripts/medbridge_fetch.py](scripts/medbridge_fetch.py) to collect records connected to task IDs:

```bash
python skill/scripts/medbridge_fetch.py "$BASE_URL" --text-file path/to/prompt.txt
python skill/scripts/medbridge_fetch.py "$BASE_URL" --quote Q-... --customer CUST-...
python skill/scripts/medbridge_fetch.py "$BASE_URL" --opportunity OPP-... --event EVT-... --voucher CODE
```

The helper prints selected records grouped by collection. It is only a collector; still apply the template and calculation rules yourself.

## Source Discipline

- Prefer exact IDs from the prompt over name search. Use `/api/search?q=...` only when the prompt gives a name without an ID.
- Treat the API as authoritative over prompt prose for record fields, but treat the prompt as authoritative for the requested output scope and confirmed date/quantity when it explicitly says so.
- Ignore component-composition notes when the prompt or policy says to quote modules at module line level.
- Ignore prior prices, superseded records, archived records, and obvious distractor records unless the target template explicitly asks to report stale or invalid source status.
