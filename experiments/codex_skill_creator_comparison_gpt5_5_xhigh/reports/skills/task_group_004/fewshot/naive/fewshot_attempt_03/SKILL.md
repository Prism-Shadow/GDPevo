---
name: apexcloud-retention-ops
description: Solve ApexCloud Retention Operations API tasks for customer success and revenue operations, including QBR metrics packets, renewal risk queues, high-touch retention boards, Q3 receivables and pipeline reviews, and churn validation or outreach ranking from ApexCloud account, metrics, support, NPS, billing snapshot, A/R aging, opportunities, HR/event, and churn export endpoints.
---

# ApexCloud Retention Ops

Use this skill when the task asks for a JSON-only business output from the ApexCloud Retention Operations API.

## Workflow

1. Parse the prompt for dates, months, account IDs, region/event filters, due dates, top-N limits, and the required answer shape.
2. Fetch only read-only business endpoints from the task base URL. Never call judge or evaluator endpoints.
3. Start from the provided answer template, preserve its top-level shape, and use exact controlled enum labels from the prompt/template.
4. Compute from source records rather than account profile shortcuts when a source-specific field is requested. Use billing snapshots for ARR, clean support tickets for ticket/SLA metrics, non-retracted NPS responses for sentiment, and A/R older buckets for overdue balances.
5. Apply deterministic precision at the end: currency 2 decimals, percentages 1 decimal, churn probabilities 3 decimals, risk scores and counts as integers.
6. Return one JSON object only.

Read [references/apexcloud-retention-ops.md](references/apexcloud-retention-ops.md) for formulas, policy-code choices, and edge cases.

## Helper Script

The helper is optional but useful for collection and repeatable calculations:

```bash
python /work/skill/scripts/apexcloud_ops.py --base "$TASK_ENV_BASE_URL" qbr \
  --account-id acct_example --start-month 2026-04 --end-month 2026-06 \
  --start-date 2026-04-01 --end-date 2026-06-30
```

Available subcommands:

- `qbr`: monthly revenue, clean support ticket counts, ticket-derived SLA, NPS, highlights, and standard QBR source labels.
- `receivables`: older-bucket A/R followups, exact legal-name CRM linkage, pipeline summary, HR totals, and event context.
- `risk-queue`: renewal-risk facts, scores, primary actions, portfolio summary, and standard risk policy codes.
- `board`: high-touch retention action board, segment summary, follow-up calendar, and board policy codes.
- `churn`: export validation counts, conservative validation accuracy, tenure direction, heuristic probability ranking, and churn policy codes.

Use script output as computed evidence. Reconcile it with the prompt and template before finalizing JSON, especially when the prompt asks for a variant not covered exactly by a subcommand.
