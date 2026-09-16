---
name: apexcloud-retention-ops
description: Solve ApexCloud Retention Operations API tasks that require strict JSON outputs for customer success QBR packets, renewal risk queues, retention action boards, A/R aging follow-ups, CRM pipeline summaries, HR/event ops context, or churn model validation and candidate ranking. Use when a prompt mentions the ApexCloud Retention Operations API, account metrics, support/NPS/billing/A/R endpoints, retention risk, receivables, pipeline operations, high-touch retention boards, or churn exports.
---

# ApexCloud Retention Operations

Use this skill to turn ApexCloud Retention Operations API data into exact, schema-conforming JSON. The user prompt and any `input/payloads/answer_template.json` are authoritative for field names, labels, date windows, account lists, sort order, and rounding.

## Workflow

1. Read the prompt and answer template completely before fetching data.
2. Set the base URL from the prompt placeholder or environment note. The examples use an unauthenticated HTTP API.
3. Fetch only the business endpoints needed for the requested output. Prefer aggregate billing and A/R endpoints, because account-specific billing/A/R routes may be unavailable in the runtime.
4. Read [references/apexcloud_rules.md](references/apexcloud_rules.md) before calculating final values.
5. Optionally run [scripts/apexcloud_ops.py](scripts/apexcloud_ops.py) to normalize account features, QBR monthly metrics, receivables/pipeline summaries, or churn scores. Treat the script as a helper; the prompt/template still win. Use `--include-all-expansion-reasons` only when the prompt is board-style and wants every open expansion context row surfaced.
6. Return only valid JSON. Do not include prose, comments, markdown fences, or extra keys.

## Common Conventions

- Use posted billing snapshots for current ARR whenever an `as_of` date is supplied.
- Use `61_90 + 90_plus` as the older overdue balance for collections/risk work unless the prompt explicitly says otherwise.
- Clean support tickets by excluding duplicates, spam, and cancelled tickets before counting tickets or calculating ticket SLA.
- Use non-retracted NPS responses. The latest response in the requested period is the latest NPS.
- Filter opportunities by `close_date` inside the requested window. Use `state == "open"` for expansion pipeline, and `stage == "Closed Won"` / `"Closed Lost"` for won/lost pipeline summaries.
- Link receivables to CRM accounts by exact `legal_name` matching. Do not link subsidiary/noise customers through aliases unless the prompt explicitly asks for alias matching.
- Round currency to 2 decimals, percentages to 1 decimal, churn probabilities to 3 decimals, and counts/risk scores to integers.

## Output Discipline

- Fill the exact template shape, including policy-code sections when present.
- Preserve controlled enum spellings exactly from the prompt/template.
- Sort after calculating all fields, then assign ranks sequentially.
- Use `null` only where the template permits it, such as no due date for `no_action`.
- If data is absent, prefer a deterministic zero/null value over inventing a value, and make the choice consistent with the template.

## Validation Checklist

Before finalizing, verify:

- The account/customer list matches the prompt scope; unrelated API rows are excluded except when the prompt requests all overdue customers.
- The billing ARR source is the billing snapshot, not CRM ARR or account profile ARR, when billing snapshots are available.
- A/R totals use only older buckets for follow-up and risk balances.
- Ticket counts and SLA percentages are based on clean tickets.
- Pipeline counts and sums use the requested date window and state/stage logic.
- Churn rankings include only the requested candidate IDs.
- The final response parses as JSON and contains no explanatory text.
