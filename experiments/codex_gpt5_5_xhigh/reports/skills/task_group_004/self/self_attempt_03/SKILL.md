---
name: apexcloud-retention-ops
description: Use this skill for ApexCloud Retention Operations API tasks that ask for customer success, renewal risk, QBR metrics, receivables, pipeline, churn-model validation, or retention action-board JSON outputs. It is especially useful when prompts mention ApexCloud, account metrics, support tickets, NPS, billing snapshots, A/R aging, opportunities, HR/event context, churn exports, controlled labels, policy codes, or answer templates; use it even when the user only asks for the final JSON.
---

# ApexCloud Retention Ops

This skill helps solve structured ApexCloud retention-operations tasks. The work is mostly data reconciliation: gather the requested records from the public API, apply strict exclusions and date windows, then emit JSON that exactly matches the prompt or template.

## First Moves

1. Read the user prompt and any `input/payloads/answer_template.json` before querying data. The template is the schema source of truth when it exists, including fields such as `policy_codes` that may not be repeated in the prose.
2. Use the environment entrypoint from `environment_access.md` when present. If a prompt says `http://127.0.0.1:8074` but the evaluation supplies a remote `GDPEVO_ENV_BASE_URL`, replace the local URL with the remote base URL and keep the same paths.
3. Query only the endpoint families named by the task, plus directly needed lookup endpoints such as `/api/accounts`.
4. Filter to the exact account IDs, regions, dates, quarters, events, and candidate IDs named in the prompt. Do not expand the portfolio unless the prompt says all regions or all accounts.
5. Return JSON only. No Markdown, explanations, comments, trailing commas, or extra top-level keys.

## Endpoint Habits

Use `curl`, a short script, or another structured client. Parse JSON/CSV as data rather than copying terminal text by hand.

Common endpoints:

- `GET /api/accounts` returns `{accounts, count}` for all CRM accounts.
- `GET /api/accounts/<account_id>` returns one account profile.
- `GET /api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM` returns monthly account metrics.
- `GET /api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` returns ticket rows.
- `GET /api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` returns NPS survey responses.
- `GET /api/billing/snapshots?account_id=<id>` returns billing snapshots; filter client-side to the requested `as_of` date or latest posted snapshot at or before the assessment date.
- `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` returns A/R aging rows.
- `GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD` returns opportunities; verify `close_date` and state client-side.
- `GET /api/hr/summary?quarter=YYYY-QN` returns HR rows by region.
- `GET /api/events/performance?event=<event_id>&quarter=YYYY-QN` returns event context.
- `GET /exports/churn/train.csv`, `/exports/churn/validation.csv`, and `/exports/churn/candidates.csv` return churn-model CSVs.

The API may return broader data than the query implies. Always re-filter locally on the relevant field (`month`, `created_date`, `response_date`, `close_date`, `as_of`, `quarter`, `region`, `account_id`, or `customer_id`).

## Source Rules

Account profile:

- Use `billing_arr_current`, `crm_arr`, `contract_tenure_months`, `renewal_date`, `segment`, `region`, `legal_name`, `display_name`, and `account_aliases` for account context.
- When a task asks for current ARR or revenue exposure, prefer posted billing snapshot ARR for the requested as-of date. Fall back to account `billing_arr_current` only if no matching snapshot exists.
- Treat lower tenure as higher churn risk; in model-check fields this means tenure risk direction is usually `negative` unless a task explicitly defines the opposite.

Metrics:

- Monthly QBR revenue comes from `recognized_revenue` in account metrics.
- Monthly support count comes from `support_ticket_count` unless the task explicitly asks for cleaned ticket rows.
- SLA percentage comes from `sla_compliance`.
- Metrics `nps_score` is useful for month-by-month tables, but latest sentiment should come from NPS responses when the task asks for latest NPS.
- Usage trend is the latest `product_usage` minus the first `product_usage` in the requested period.

Tickets:

- A clean ticket excludes rows where `is_duplicate` is true or `is_spam` is true.
- SLA health should consider both `first_response_sla_met` and `resolution_sla_met`; any false value is a service-risk signal.
- Count tickets only inside the requested date range, inclusive.

NPS:

- Exclude retracted responses.
- Latest NPS is the valid response with the greatest `response_date` in the period.
- For NPS trend/reason codes, compare latest valid score to the earliest valid score in the period.
- Use `null` where the schema allows null and there is no valid response; do not invent a score.

Billing and A/R:

- Posted billing snapshots are the most reliable ARR source for as-of reporting.
- A/R `current` is not overdue. Generic overdue balance is `1_30 + 31_60 + 61_90 + 90_plus`.
- If the prompt says "older aging buckets", use `61_90 + 90_plus` as the trigger/scope for follow-up inclusion, while still reporting the overdue balance requested by the schema.
- Link A/R rows to CRM accounts through the account ID embedded in `aging_id` when present (`AR-<account_id>-...`), otherwise match `customer_name` to account `legal_name`, `display_name`, or aliases.
- Mark unmatched A/R customers as `unlinked` and use `account_id: null` if the schema asks for link status.

Opportunities:

- Filter by `close_date` within the task window.
- Open pipeline includes `state: "open"` opportunities.
- Won revenue/count uses closed opportunities with `stage: "Closed Won"` or equivalent won state.
- Lost count uses `stage: "Closed Lost"` or equivalent lost state.
- Top open product line is the product line with the greatest summed open amount; use a deterministic tie-break such as alphabetical order.

HR and events:

- If the task says all regions, sum numeric HR totals across regions for counts and money fields. Average only when the prompt asks for a rate.
- For event context, use the exact requested `event_id` and quarter, then report `event_orders` and `event_revenue` unless the schema asks for a different field.

Churn exports:

- Train the model on `train.csv`, validate on `validation.csv`, and score `candidates.csv`.
- Drop identifier columns (`customer_id`) and the target (`Churn`) from features. Count raw predictor columns unless the task explicitly asks for encoded dimensionality.
- Encode categorical fields consistently across train, validation, and candidates; keep numeric fields numeric.
- Report validation row counts from the CSVs, accuracy as a percentage to one decimal, and probability outputs on the 0-to-1 scale to three decimals.
- Rank only the candidate/customer IDs named in the prompt; ignore other candidates.

## Risk and Action Workflow

For renewal-risk queues and action boards, build one per-account record first, then rank. Useful fields include current ARR, days to renewal, latest NPS and NPS change, clean ticket count, SLA misses, usage change, overdue balance, old-bucket overdue balance, tenure, lifecycle status, and open expansion pipeline.

Reason-code guidance:

- `overdue_receivable`: any overdue balance, especially old-bucket A/R.
- `low_tenure_high_churn`: short contract tenure, typically around 18 months or less, especially with other risk signals.
- `sla_degradation`: SLA percentage declines, low SLA, or ticket rows with missed first-response/resolution SLA.
- `nps_drop`: latest NPS is low or materially lower than the first valid NPS in the period.
- `usage_decline`: product usage drops across the period or the export shows negative usage trend.
- `renewal_window`: renewal is near the assessment date, commonly within the next 90 days or recently passed.
- `expansion_offset`: meaningful open expansion pipeline offsets commercial risk.
- `clean_billings`: no meaningful overdue A/R and billing is clean.

Primary-action guidance:

- Use `collections_followup` when overdue A/R, especially old-bucket A/R, is the dominant issue.
- Use `technical_recovery` when SLA, tickets, or usage are the dominant issues.
- Use `renewal_save` when renewal timing plus churn/sentiment signals dominate.
- Use `executive_qbr` for strategic/high-value accounts needing executive alignment, especially with expansion or mixed signals.
- Use `nurture_monitor` for lower-risk accounts that still need monitoring.
- Use `no_action` only if the enum allows it and no material risk is present.

Risk ranking should be deterministic. Sort by severity first (`critical`, `high`, `medium`, `low`), then by primary action urgency, ARR/exposure, renewal urgency, and finally `account_id` as a stable tie-break. For board tasks that mention a "standard retention board order", use this risk/action ordering rather than alphabetical order.

## Output Conventions

- Preserve every key from the prompt/template and omit keys that are not requested.
- Use exact controlled enum strings from the prompt/template. Do not create synonyms.
- Use integers for counts, ranks, and risk scores.
- Use numeric JSON values for money, percentages, probabilities, and counts, not formatted strings.
- Round currency to 2 decimals, percentages to 1 decimal, and churn probabilities to 3 decimals unless the prompt says otherwise.
- Sort arrays exactly as requested: top-N rankings by risk/probability, overdue follow-ups by `customer_name` when asked, QBR metrics in month order, and action boards in retention board order.
- Dates must be ISO strings from the prompt or source data.
- For summary fields, compute from the returned/reviewed population, not from the entire API dataset unless the prompt says all accounts/regions.

Policy-code blocks are methodology fields. If a codebook is not exposed by the API, choose the allowed code that corresponds to the workflow you actually used, keep it inside the provided enum, and use it consistently. Never leave placeholder strings such as `RS-2|RS-6|RS-9`.

## Common Pitfalls

- Do not use local filesystem environment data or source code when the task provides a public API entrypoint.
- Do not trust the prompt's localhost host in a remote evaluation; swap only the host/base URL, not the API path.
- Do not count duplicate or spam tickets as clean tickets.
- Do not include retracted NPS responses.
- Do not treat A/R `current` as overdue.
- Do not report CRM ARR when the task asks for billing ARR/current revenue exposure and a billing snapshot exists.
- Do not include accounts, candidates, regions, or customers outside the requested scope.
- Do not let templates remain as placeholders; all enum-pipe strings and sample IDs must be replaced.
- Do not add explanatory text around the JSON; many graders parse the response directly.
