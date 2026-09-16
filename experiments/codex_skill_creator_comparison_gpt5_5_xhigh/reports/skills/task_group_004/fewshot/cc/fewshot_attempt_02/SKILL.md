---
name: apexcloud-retention-ops
description: Build strict JSON reports from the ApexCloud Retention Operations API, including renewal-risk queues, retention boards, QBR packets, receivables and pipeline reviews, churn validation summaries, and similar operating readouts. Use whenever a prompt mentions ApexCloud, the retention operations API, account risk, A/R aging, NPS, support health, pipeline, HR/event context, churn exports, or asks for a JSON-only report from the task environment.
---

# ApexCloud Retention Ops

Use this skill for any task that turns ApexCloud operational data into a strict JSON artifact.

## First pass
- Read the prompt first.
- Read the task's answer template from its input payloads next. Treat it as the schema oracle.
- Identify the report family before you fetch data.
- Use the task environment URL provided with the exercise and the allowed ApexCloud endpoints only.

## Source map
- Read `references/source-map.md` for the endpoint map and field rules.
- Use it when you need to remember which source provides ARR, A/R aging, ticket quality, monthly revenue, or churn data.

## Core workflow
1. Copy the exact top-level structure from the answer template.
2. Pull only the data needed for the requested report.
3. Reconcile names, dates, account IDs, and periods against the prompt before you compute anything.
4. Apply the report-specific rules below.
5. Verify formatting, ordering, and enum values against the template.
6. Return JSON only. No commentary, markdown, or code fences.

## Report playbooks

### Renewal-risk queue and retention board
- Use only the selected account IDs.
- Pull account profile, monthly metrics, tickets, NPS, billing snapshot, and A/R aging data.
- Use the billing snapshot at the requested as-of date for current ARR or exposure. If a snapshot is missing, fall back to the account profile only as a secondary check.
- Treat overdue balance as the sum of the 61_90 and 90_plus A/R buckets at the requested as-of date.
- Count clean tickets by excluding duplicate and spam tickets.
- Use the latest non-retracted NPS in the requested window.
- Rank by the strongest retention risk signals first: overdue receivables, renewal proximity, NPS decline, SLA degradation, usage decline, then tenure or lifecycle context.
- Use the prompt's controlled action and reason labels exactly. Do not invent labels.
- If the prompt asks for a "standard retention board order," preserve the risk order implied by the prompt and break ties deterministically with exposure or urgency.

### QBR packet
- Build the monthly series from the requested quarter or month range.
- Use `recognized_revenue`, clean ticket counts, SLA compliance, and NPS from the account-level metrics, tickets, and NPS data.
- For ticket counts, exclude duplicate and spam tickets.
- For SLA compliance, compute the share of clean tickets whose first-response SLA was met.
- Use the earliest month as the default tie-breaker for tied highlight fields unless the prompt says otherwise.
- Treat ticket trend as improving when clean ticket volume decreases over the requested period, worsening when it increases, and flat when it is unchanged.
- Choose agenda topics only from the vocabulary in the prompt.

### Receivables and pipeline review
- Pull overdue balances from `/api/finance/ar-aging` at the requested as-of date.
- Link A/R customers to CRM accounts by account_id first, then by normalized legal name, display name, or aliases.
- Mark the row `linked` only when the CRM match is real and the account_id can be resolved.
- Sort overdue follow-ups alphabetically by `customer_name` unless the prompt says otherwise.
- Sum open opportunities that fall inside the requested window, and separate won/lost/open counts exactly as the prompt asks.
- Pull HR and event context from the quarter-level summary endpoints requested in the prompt.

### Churn validation and candidate ranking
- Treat `train.csv` and `validation.csv` as labeled data and `candidates.csv` as unlabeled scoring input.
- Validate the dataset from the files themselves before ranking candidates.
- Keep preprocessing identical across train, validation, and candidate files.
- Use a deterministic classifier or scorecard; do not hand-wave probabilities.
- Report probabilities with the precision requested by the prompt, and rank candidates strictly by probability descending.
- Keep the top-N list to the exact candidate set named in the prompt.

## Formatting rules
- Match the template's key order, nesting, and nullability.
- Use controlled enum values exactly as shown in the prompt or template.
- Use integers for counts and risk scores, 2 decimals for currency, 1 decimal for percentages, and 3 decimals for churn probabilities when requested.
- Do not round early. Round once at the end.
- Keep lists sorted exactly as the prompt requests.

## Final check
- Confirm every required top-level key is present.
- Confirm the output is valid JSON with no trailing text.
- Confirm no task-specific example values leaked into the reusable instructions.
