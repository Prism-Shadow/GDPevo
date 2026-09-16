# ApexCloud Rules Reference

This reference captures reusable rules inferred from the ApexCloud Retention Operations examples. Apply the prompt first when it gives a more specific instruction.

## Endpoint Map

- Accounts: `GET /api/accounts`, `GET /api/accounts/{account_id}`
- Monthly account metrics: `GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM`
- Support tickets: `GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`
- NPS: `GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`
- Billing snapshots: `GET /api/billing/snapshots?as_of=YYYY-MM-DD`
- A/R aging: `GET /api/finance/ar-aging?as_of=YYYY-MM-DD`
- Opportunities: `GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD`
- HR summary: `GET /api/hr/summary?quarter=YYYY-QN`
- Event performance: `GET /api/events/performance?event=EVENT_ID&quarter=YYYY-QN`
- Churn exports: `/exports/churn/train.csv`, `/exports/churn/validation.csv`, `/exports/churn/candidates.csv`

## Support Hygiene

Clean tickets exclude rows where:

- `is_duplicate` is true
- `is_spam` is true
- `status` is `cancelled`

Ticket SLA passes only when both `first_response_sla_met` and `resolution_sla_met` are true. For monthly QBR fields, group clean tickets by `created_date` month and calculate:

- `support_tickets`: clean ticket count for that month
- `sla_compliance_pct`: clean SLA passes divided by clean tickets, multiplied by 100. If no clean tickets exist, use the metrics endpoint value only if the prompt/template needs a non-null percentage.

## Billing And A/R

- Current ARR: use `billing_arr` from the posted billing snapshot matching the requested `as_of` date.
- Older overdue balance: `61_90 + 90_plus`.
- Receivables follow-ups: include customers with older overdue balance greater than zero, sort by `customer_name` ascending, and set the action to `collections_followup` unless the prompt overrides it.
- CRM matching for receivables: exact match from A/R `customer_name` to account `legal_name`. Keep unmatched customers as `link_status: "unlinked"` with `account_id: null`.

## Opportunity And Pipeline Rules

- Filter by `close_date` within the requested date range.
- Open expansion pipeline: sum `amount` for rows with `state == "open"`.
- Won pipeline: rows with `stage == "Closed Won"`.
- Lost pipeline: rows with `stage == "Closed Lost"`.
- Open count: rows with `state == "open"`.
- Win rate: `won_count / (won_count + lost_count) * 100`; use 0.0 if the denominator is zero.
- Top open product line: product line with the largest summed open amount; break ties deterministically by product-line name.

## Risk Reason Codes

Use these reason-code triggers for risk queues and retention boards:

- `renewal_window`: renewal date falls from the assessment date through the next 90 days.
- `overdue_receivable`: older overdue balance is greater than zero.
- `sla_degradation`: at least one clean ticket in the period missed first-response or resolution SLA.
- `nps_drop`: latest non-retracted NPS is 40 or lower, or latest non-retracted NPS dropped by at least 10 points from the first non-retracted NPS in the period.
- `usage_decline`: product usage or active seats deteriorate during the period and there is also negative sentiment context such as `nps_drop`.
- `low_tenure_high_churn`: contract tenure is under 18 months, especially when churn exports or month-to-month context show elevated risk.
- `expansion_offset`: open expansion pipeline in the requested window is material to the account context or exposure calculation.
- `clean_billings`: older overdue balance is zero; use this as a positive context code when the template expects reason codes for lower-risk rows.

The helper script keeps `expansion_offset` conservative by default; pass `--include-all-expansion-reasons` when the prompt is board-style and wants every open expansion context row surfaced.

Recommended risk scoring for queues and boards:

- Start at 0 and cap at 100.
- Add 20 for `renewal_window`.
- Add 20 for `overdue_receivable`.
- Add 15 for exactly one SLA miss; add 20 for two or more SLA misses.
- Add 10 for `nps_drop`.
- Add 10 for `usage_decline`.
- Add 10 for `low_tenure_high_churn`.
- Add 10 for high-ARR accounts in a near-term renewal window when the prompt emphasizes revenue exposure.
- Treat `expansion_offset` primarily as context and for net exposure; only use it to break close risk ties unless the prompt asks expansion to affect scoring.

Risk levels:

- `critical`: score 70 or above
- `high`: score 50 to 69
- `medium`: score 30 to 49
- `low`: below 30

Primary action priority:

1. `collections_followup` when `overdue_receivable` is present.
2. `technical_recovery` when SLA, usage, or NPS health is the main issue.
3. `renewal_save` when renewal timing or low-tenure churn risk is the main issue.
4. `executive_qbr` for strategic/high-ARR multi-factor risk when the prompt asks for executive intervention.
5. `nurture_monitor` for low modeled churn with no urgent collection or technical issue.
6. `no_action` for low-risk board rows when the template allows it.

For retention boards, sort by risk level/score descending, then by severity of reasons, current ARR, and account ID for deterministic ties. `arr_at_risk` is the sum of current ARR for medium, high, and critical accounts. `net_revenue_exposure` is `arr_at_risk - open_expansion_pipeline`.

## QBR Metrics Packets

For each requested month:

- `revenue`: monthly `recognized_revenue` from account metrics.
- `support_tickets`: clean ticket count for that month.
- `sla_compliance_pct`: clean-ticket SLA percentage for that month.
- `nps_score`: non-retracted NPS response score for that month, or the metrics NPS value when it aligns with the response data.

Highlights:

- Average revenue is the arithmetic mean of monthly revenue.
- Peak/max fields choose the first chronological month if values tie.
- `ticket_trend` is `improving` when the last monthly clean-ticket count is lower than the first, `worsening` when higher, otherwise `flat`.
- Use metric source labels: `crm_closed_won` for recognized revenue in QBR packets, `support_export` for ticket counts, `sla_report` for SLA, and `nps_survey` for NPS.
- Choose `technical_recovery` as an agenda topic when ticket/SLA health is weak; choose `commercial_expansion` only when open expansion is a material QBR topic.

## Receivables, Pipeline, HR, And Events

Financial summary:

- `overdue_client_count`: count of A/R rows with older overdue balance greater than zero.
- `overdue_total`: sum of older overdue balances.
- `linked_followup_count` and `unlinked_followup_count`: counts after exact legal-name matching.

Pipeline summary:

- Count and sum won/lost/open opportunities in the requested close-date window.
- `open_pipeline`: sum open opportunity amounts.
- `top_open_product_line`: open product line with the largest open amount.

Ops context:

- If the prompt asks for all HR regions, sum `headcount` and `unpaid_claims_amount` across all HR rows for the quarter.
- For event context, use the matching event/quarter row and copy `event_orders` and `event_revenue`.

## Churn Model Tasks

Use `train.csv` for fitting, `validation.csv` for validation metrics, and `candidates.csv` for scoring. The raw feature count is the number of columns excluding `customer_id` and `Churn`.

Recommended protocol:

1. Parse `Churn` as the binary target.
2. One-hot encode categorical fields and standardize numeric fields using training-set statistics.
3. Fit a logistic regression model. If a library is unavailable, use deterministic gradient descent with L2 regularization.
4. Validate with a 0.5 threshold and report accuracy percentage and band.
5. Determine tenure coefficient direction from the fitted coefficient for `tenure`; shorter tenure should increase risk when the coefficient is negative.
6. Score only the candidate IDs requested by the prompt, rank by predicted probability descending, and round probabilities to 3 decimals.

Outreach mapping:

- `collections_followup`: candidate has `InvoicePastDue == "Yes"` or the top reason is overdue receivable.
- `renewal_save`: low tenure/month-to-month churn risk without receivables urgency.
- `technical_recovery`: support/SLA/usage health is the main driver.
- `nurture_monitor`: low probability and clean billing context.

Cohort checks:

- `past_due_shortlist_count`: requested candidates with `InvoicePastDue == "Yes"`.
- `low_tenure_shortlist_count`: requested candidates with tenure under 18 months.
- `average_probability_top5`: mean probability across the returned top five.

## Policy Code Mapping

Use these codes when the answer template includes matching policy-code fields:

- Weighted retention risk model: `RS-6`
- Posted billing snapshot ARR source: `REV-4`
- Clean support-ticket hygiene: `SUP-8`
- Collections-first action priority: `ACT-5`
- Older-bucket receivable trigger: `RCP-7`
- Exact legal-name CRM match: `CM-5`
- Close-date pipeline window: `PW-6`
- Follow up all older-overdue customers, including unlinked rows: `FS-4`
- Train/validate churn protocol: `MOD-7`
- Probability scale is 0 to 1 rounded to 3 decimals: `PRB-4`
- Rank only requested candidates: `DEP-5`
- Outreach action from the top operational risk: `OUT-2`
- Weighted board sort with deterministic tie-breaks: `BORD-4`
- Net exposure equals ARR at risk minus open expansion pipeline: `EXP-6`
- Prompt-provided due-date calendar: `CAL-5`
