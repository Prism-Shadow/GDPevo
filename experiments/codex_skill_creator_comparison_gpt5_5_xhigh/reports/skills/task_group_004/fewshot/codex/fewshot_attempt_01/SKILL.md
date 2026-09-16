---
name: apexcloud-retention-ops
description: Build strict JSON reports from the ApexCloud Retention Operations API for customer success QBR metrics, renewal risk queues, receivables and pipeline operations reviews, retention action boards, and churn export validation or outreach ranking. Use when a task mentions ApexCloud, Retention Operations API, account health metrics, billing snapshots, A/R aging, support/NPS, opportunities, HR/event context, or churn CSV exports.
---

# ApexCloud Retention Ops

## Workflow

1. Read the prompt and its answer template first. Extract the base URL, date range, month list or quarter, A/R as-of date, account IDs, due dates, requested count/order, allowed enum labels, and required JSON shape.
2. Fetch only the allowed ApexCloud Retention Operations API endpoints needed for the requested report. Filter dates inclusively and filter rows locally if an endpoint returns a full year or full portfolio.
3. Read [references/apexcloud_workflows.md](references/apexcloud_workflows.md) for endpoint fields, joins, and report recipes before doing nontrivial calculations.
4. Use [scripts/apexcloud_report.py](scripts/apexcloud_report.py) for deterministic normalization when helpful. It uses only the Python standard library and outputs helper JSON for QBR rows, account risk facts, receivables/pipeline summaries, and churn export summaries.
5. Return only JSON matching the prompt/template. Do not include notes, citations, markdown, or extra keys.

## Core Conventions

- Treat ISO date ranges as inclusive. Treat month ranges as inclusive by `YYYY-MM`.
- Prefer billing snapshot ARR over account `crm_arr` or profile ARR whenever the output asks for current ARR, ARR at risk, revenue exposure, or the model check asks whether billing ARR was used.
- For support counts and SLA calculations, use clean tickets: exclude duplicates, spam, and cancelled tickets. A clean ticket is SLA-compliant only when both first-response and resolution SLA flags are true.
- For A/R overdue exposure in retention tasks, use the older aging buckets: `61_90 + 90_plus`. Do not count `current`, `1_30`, or `31_60` as the retention overdue balance unless the prompt explicitly asks for all aging buckets.
- For finance operations reviews that say "older aging buckets", start from rows where `61_90 + 90_plus > 0`.
- For NPS, ignore retracted responses. Use the latest non-retracted response in the requested period for account-level outputs, and monthly metric rows for monthly QBR outputs unless the prompt instructs otherwise.
- For open expansion pipeline, sum open opportunities whose close dates fall inside the requested period.
- If policy code fields contain pipe-separated enum choices and the prompt does not define a separate policy, use the middle option as the standard evidence-backed policy code.
- Use exact enum labels from the prompt/template. Do not invent enum values.

## Helper Script

Run from the skill directory or pass its path explicitly:

```bash
python3 scripts/apexcloud_report.py qbr --base-url "$TASK_ENV_BASE_URL" --account-id acct_x --months 2026-04,2026-05,2026-06 --start-date 2026-04-01 --end-date 2026-06-30 --review-due-date 2026-07-22
python3 scripts/apexcloud_report.py risk-facts --base-url "$TASK_ENV_BASE_URL" --account-ids acct_a,acct_b --months 2026-04,2026-05,2026-06 --start-date 2026-04-01 --end-date 2026-06-30 --as-of 2026-06-30 --assessment-date 2026-06-30
python3 scripts/apexcloud_report.py receivables --base-url "$TASK_ENV_BASE_URL" --quarter 2026-Q3 --as-of 2026-09-30 --due-date 2026-10-15 --event-id apex_connect
python3 scripts/apexcloud_report.py churn-summary --base-url "$TASK_ENV_BASE_URL" --candidate-ids acct_a,acct_b
```

The script output is a working table of facts, not a license to ignore the requested template. Use it to populate and check the exact answer shape.

## Report Dispatch

- **QBR metrics packet**: monthly recognized revenue, clean support ticket counts, clean-ticket SLA compliance, monthly NPS, highlights, source labels, review owner, signoff, and four ordered agenda topics.
- **Renewal risk queue or retention action board**: account profile, billing snapshot ARR, older A/R balance, clean support health, NPS, product usage trend, renewal window, tenure risk, lifecycle status, and open expansion pipeline.
- **Receivables and pipeline operations review**: older A/R followups, CRM account linking by legal name or alias, Q-period opportunity summaries, all-region HR context, and named event context.
- **Churn validation and outreach ranking**: row counts, raw feature count, validation accuracy band, tenure direction, candidate probabilities/ranking, cohort checks, and outreach action mapping.

## Final Checks

- Confirm every numeric value has the requested precision: currency 2 decimals, percentages 1 decimal, probabilities 3 decimals, counts and ranks integers.
- Sort in the prompt's required order: top-N by risk/probability for queues, standard retention board order for boards, customer name ascending for receivables followups.
- Validate JSON with `python3 -m json.tool` or `json.loads` before finalizing.
