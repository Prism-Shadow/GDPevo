---
name: harborcrm-reconcile
description: Produce schema-conforming JSON for HarborCRM CRM, event, trade-show, and import-batch tasks. Use when asked to audit post-event CRM handoffs, reconcile sponsor badges, invoices, campaign members, prepare CRM import batches, deduplicate or suppress contacts, or build qualified exhibitor and prospecting summaries from HarborCRM API data.
---

# HarborCRM Reconcile

## Operating Rules

- Read the user prompt and `input/payloads/answer_template.json` first. Treat the template as the output contract for keys, enums, nullability, ordering, and numeric precision.
- Use the API base URL supplied by the runner. Fetch live HarborCRM data before reasoning; do not answer from memory or from examples.
- Return one JSON object only. Do not include prose, comments, Markdown fences, or undeclared fields.
- Read [references/harborcrm-workflows.md](references/harborcrm-workflows.md) before producing the final JSON. It contains the reusable matching, classification, counting, and sorting rules.
- Use [scripts/fetch_harborcrm.py](scripts/fetch_harborcrm.py) when a quick local snapshot would reduce mistakes. The script uses only Python standard library modules and skips optional endpoints that return 404.

## Fetch Plan

Choose the relevant workflow from the prompt:

- Event handoff: fetch the event record, event badges, sponsor/order/package and invoice records when exposed, CRM accounts, contacts, opportunities, campaign members, and policies.
- Trade-show prospecting: fetch the trade-show record, exhibitors, meeting interest, CRM accounts, CRM contacts when useful, and policies.
- Import-batch cleanup: fetch the import batch, raw contacts, suppression list, CRM accounts, CRM contacts, and policies.

Optional snapshot examples:

```bash
python skill/scripts/fetch_harborcrm.py --base-url "$TASK_ENV_BASE_URL" --event-id "$EVENT_ID" --out /tmp/harborcrm-event.json
python skill/scripts/fetch_harborcrm.py --base-url "$TASK_ENV_BASE_URL" --show-id "$SHOW_ID" --out /tmp/harborcrm-show.json
python skill/scripts/fetch_harborcrm.py --base-url "$TASK_ENV_BASE_URL" --batch-id "$BATCH_ID" --out /tmp/harborcrm-batch.json
```

If the prompt names endpoint paths that differ from the helper's defaults, fetch those paths directly as well and use the prompt-specific data.

## Build Process

1. Parse the answer template into a checklist of required top-level keys, required item keys, allowed enum values, ordering rules, and required constants.
2. Normalize records before matching: lowercase trimmed emails, digits-only phones, stable company/account names, and integer currency values.
3. Build indexes for accounts, contacts, opportunities, campaign members, exhibitors, meeting interest, sponsors, invoices, raw rows, and suppressions as applicable.
4. Apply the workflow rules from `references/harborcrm-workflows.md`; when the prompt is more specific, follow the prompt.
5. Compute aggregates from the final included records, not from raw source rows.
6. Apply all sorting rules last.
7. Validate the final response with a JSON parser and compare it against the template checklist before returning it.
