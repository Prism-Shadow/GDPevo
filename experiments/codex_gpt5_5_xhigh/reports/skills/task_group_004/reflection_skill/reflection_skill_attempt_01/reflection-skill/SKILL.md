---
name: reflection-skill
description: Use this skill for ApexCloud Retention Operations API workflows that ask for structured JSON packets, renewal risk queues, QBR metrics, receivables and pipeline reviews, churn validation rankings, or high-touch retention action boards. It is especially useful when the task references account, metrics, support ticket, NPS, billing snapshot, A/R aging, opportunity, HR, event, or churn export endpoints and requires controlled enum labels, policy codes, deterministic rounding, or ranked customer success actions.
---

# ApexCloud Retention Operations Workflow

Use this skill to turn ApexCloud Retention Operations API data into exact JSON outputs. Read the prompt and answer template first, then build the response from API records rather than from narrative intuition.

## Fast SOP

1. Use the API base URL supplied by the current workflow/user. If task text mentions a different local port but the workflow gives a shared API base, use the shared base.
2. Read the requested dates, account IDs, quarter/months, A/R as-of date, event id, and controlled enum vocabulary from the prompt/template.
3. Fetch only the needed endpoint families:
   - `/api/accounts` and `/api/accounts/<account_id>`
   - `/api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM`
   - `/api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`
   - `/api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`
   - `/api/billing/snapshots`
   - `/api/finance/ar-aging?as_of=YYYY-MM-DD`
   - `/api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD`
   - `/api/hr/summary?quarter=YYYY-QN`
   - `/api/events/performance?event=<event_id>&quarter=YYYY-QN`
   - `/exports/churn/train.csv`, `/exports/churn/validation.csv`, `/exports/churn/candidates.csv`
4. Recompute derived fields from raw records. Do not trust similarly named monthly aggregate fields when the output asks for clean support, SLA, overdue, risk, or action fields.
5. Fill the template exactly. Preserve top-level keys, controlled labels, nullability, ordering requirements, and precision.
6. Before returning, validate JSON parseability, enum values, counts, sort order, and rounding.

## Field Rules

**Billing ARR**

- `current_arr` uses `/api/billing/snapshots` at the relevant quarter-end `as_of` date.
- Prefer the snapshot `billing_arr` over `account.billing_arr_current` and `crm_arr` unless the prompt explicitly says otherwise.
- `uses_billing_arr_source` should be `true` when ARR came from billing snapshots.
- Observed ARR source policy code for this workflow family: `REV-4`.

**A/R Aging**

- Overdue risk/follow-up balance means older receivables only: `61_90 + 90_plus`.
- Do not add `1_30`, `31_60`, or `current` to `overdue_balance`.
- A receivables follow-up is in scope when `61_90 + 90_plus > 0`.
- Link A/R customers to CRM accounts by exact legal name, display name, or listed alias. Do not fuzzy-match similar noise names; leave them `unlinked` with `account_id: null`.

**Support Tickets**

- A clean ticket is one where `is_duplicate == false`, `is_spam == false`, and `status != "cancelled"`.
- Open tickets still count as clean if they pass those exclusions.
- For monthly support counts, count clean tickets by `created_date` month.
- For SLA compliance, compute the share of clean tickets where both `first_response_sla_met` and `resolution_sla_met` are true. Use `0.0` if there are no clean tickets.
- Do not copy `support_ticket_count` or `sla_compliance` from metrics when ticket records are available for the requested support/SLA fields.
- Observed support hygiene policy code: `SUP-8`.

**NPS**

- Use non-retracted responses only.
- `latest_nps` is the latest non-retracted response in the requested date window.
- Monthly QBR NPS maps responses/metric rows to the requested months; use `null` only when the template allows it and no response exists.

**Revenue and QBR Metrics**

- Monthly QBR `revenue` comes from account metrics `recognized_revenue`.
- The source enum observed for this revenue field is `crm_closed_won`, even though the numeric value is the metrics revenue value.
- Use `support_export` for support tickets, `sla_report` for SLA, and `nps_survey` for NPS.
- `ticket_trend` compares the first and last requested monthly clean ticket counts: lower is `improving`, higher is `worsening`, equal is `flat`.

**Opportunities**

- Filter opportunities by `close_date` within the prompt's date range.
- Closed won/lost counts use `stage == "Closed Won"` and `stage == "Closed Lost"`.
- Open pipeline uses `state == "open"`.
- `top_open_product_line` is the product line with the largest summed open amount.
- Account `expansion_pipeline` is the sum of open opportunities for that account in the requested window.

**HR and Event Context**

- If the prompt says all regions, sum HR rows across all returned regions for the quarter.
- Use `unpaid_claims_amount` for unpaid claims totals.
- For event context, filter by exact `event_id` and quarter; use `event_orders` and `event_revenue`.

## Risk and Action Rules

Build account risk from explicit signals. Keep reason codes ordered by importance in the final account explanation.

Core reason-code triggers:

- `renewal_window`: renewal date is future-facing and within the requested window, commonly 0-90 days from the assessment date. Already-past renewal dates do not trigger this reason by themselves.
- `overdue_receivable`: older A/R balance `61_90 + 90_plus` is greater than 0.
- `nps_drop`: latest NPS is low, usually below 50, or there is a material negative NPS movement.
- `sla_degradation`: any clean ticket misses first-response or resolution SLA, or clean-ticket SLA compliance is below 100%.
- `usage_decline`: latest product usage is weak, commonly below about 65, or usage materially deteriorates over the period.
- `low_tenure_high_churn`: short-tenure accounts carry more churn risk; use a negative tenure direction.
- `expansion_offset`: account has open expansion pipeline in the requested window.
- `clean_billings`: no older A/R balance is present.

Scoring and levels:

- Use deterministic integer risk scores when required.
- Treat `critical` as severe multi-signal risk, `high` as strong non-low risk, `medium` as actionable but less severe, and `low` as monitor/no-action risk.
- In observed outputs, `critical` generally starts around 80+, `high` around 50+, `medium` around 30+, and lower scores are `low`.
- Risk queues sort by risk score/severity first, then revenue exposure/current ARR.
- Action boards sort by risk level/severity first, then current ARR or revenue exposure. Do not let small overdue balances outrank a higher severity tier.

Action priority:

- Use `collections_followup` for accounts or customers with older A/R balances when the account is actionable.
- Use `technical_recovery` when SLA/support, usage, or low-NPS issues are the dominant non-collections problem.
- Use `renewal_save` for future renewal-window accounts when renewal timing is the primary action and technical issues are mild.
- Use `executive_qbr` for high-value sentiment or executive-readiness situations when it best fits the provided enum.
- Use `nurture_monitor` or `no_action` for low-risk accounts, depending on the enum set in the template. If `no_action` is available and the account is low with only weak or offset signals, prefer it.

Summary formulas:

- `critical_or_high_count`: count only `critical` and `high`.
- `arr_at_risk`: usually sum current ARR for all non-low accounts included in the output.
- `collections_count` and `technical_recovery_count`: count final primary actions, not reason codes.
- `open_expansion_pipeline`: sum open expansion pipeline for all accounts in the board, including low accounts.
- `net_revenue_exposure`: `arr_at_risk - open_expansion_pipeline`.

Useful observed policy-code defaults:

- Risk model: `RS-6`
- ARR source: `REV-4`
- Support hygiene: `SUP-8`
- Action priority: `ACT-5`
- Board sort: `BORD-4`
- Exposure formula: `EXP-6`
- Calendar policy: `CAL-5`
- Receivable trigger: `RCP-7`
- CRM match: `CM-5`
- Pipeline window: `PW-6`
- Follow-up scope: `FS-4`

## Churn Export Workflow

For churn model validation and outreach ranking:

1. Download train, validation, and candidates CSVs from the API.
2. Count `training_rows` and `validation_rows` directly from CSV row counts.
3. `feature_count` excludes `customer_id` and the target `Churn`.
4. Train a deterministic classifier on the train export, validate on validation, and rank only the candidate IDs requested by the prompt.
5. Use numeric scaling and one-hot encoding for categorical fields if using logistic regression. Keep random seeds fixed for any model with randomness.
6. Report validation accuracy as a percentage to 1 decimal and map bands as:
   - `<70`: `below_70`
   - `70-79.9`: `70_to_79`
   - `80-89.9`: `80_to_89`
   - `>=90`: `90_plus`
7. `tenure_coefficient_direction` should be `negative` when shorter tenure increases churn risk.
8. Rank by predicted churn probability descending; use stable tie-breaks such as customer ID if probabilities are equal.
9. Use probabilities on a 0-1 scale rounded to 3 decimals.

Outreach mapping:

- Past-due older receivables or clear receivables risk: `collections_followup` with `overdue_receivable`.
- Low tenure/month-to-month churn risk: `renewal_save` with `low_tenure_high_churn`.
- SLA/support or usage problems: `technical_recovery` with `sla_degradation` or `usage_decline`.
- Clean, lower-risk candidates: `nurture_monitor` with `clean_billings`.

Observed model policy-code defaults:

- Model protocol: `MOD-7`
- Probability scale: `PRB-4`
- Deployment rule: `DEP-5`
- Outreach mapping: `OUT-2`

## Output Hygiene

- Return JSON only when requested.
- Currency: 2 decimals. Percentages: 1 decimal. Probabilities: 3 decimals. Counts and risk scores: integers.
- Keep arrays in the requested order: ranked accounts by rank, receivables follow-ups by customer name when requested, and monthly metrics in chronological order.
- Use controlled enums exactly as provided in the template. Do not invent labels.
- Preserve `null` where the template allows missing values; otherwise choose the best controlled enum or numeric default.

## Common Pitfalls

- Adding all non-current A/R buckets instead of only `61_90 + 90_plus`.
- Treating `1_30` or `31_60` receivables as follow-up-triggering overdue balances.
- Counting cancelled tickets as clean tickets.
- Excluding open tickets from clean support counts.
- Copying monthly metrics `sla_compliance` instead of recomputing SLA from clean ticket records.
- Using `account.billing_arr_current` instead of the quarter-end billing snapshot.
- Fuzzy-linking similarly named A/R noise customers to real CRM accounts.
- Treating already-past renewal dates as `renewal_window`.
- Letting expansion pipeline make a low-risk account actionable by itself.
- Returning explanatory text around the JSON.
