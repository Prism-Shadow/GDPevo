# ApexCloud Workflow Reference

Use this reference after the skill triggers and the prompt identifies an ApexCloud Retention Operations report. It records reusable rules inferred from the staged examples without preserving any completed answer records.

## Endpoint Map

- `GET /api/accounts`: portfolio account profiles. Important fields: `account_id`, `legal_name`, `account_aliases`, `region`, `segment`, `lifecycle_status`, `renewal_date`, `contract_tenure_months`, `billing_arr_current`, `crm_arr`, `csm_owner`.
- `GET /api/accounts/{account_id}`: one account profile.
- `GET /api/accounts/{account_id}/metrics`: monthly account metrics. Important fields: `month`, `quarter`, `recognized_revenue`, `support_ticket_count`, `sla_compliance`, `nps_score`, `product_usage`, `active_seats`.
- `GET /api/accounts/{account_id}/tickets`: support tickets. Important fields: `created_date`, `status`, `is_duplicate`, `is_spam`, `first_response_sla_met`, `resolution_sla_met`, `severity`, `product_area`.
- `GET /api/accounts/{account_id}/nps`: NPS responses. Important fields: `response_date`, `score`, `retracted`.
- `GET /api/billing/snapshots`: posted ARR snapshots by `account_id` and `as_of`. Use this for current ARR outputs.
- `GET /api/finance/ar-aging`: A/R rows by `customer_name`, `as_of`, `quarter`, and aging buckets.
- `GET /api/opportunities`: opportunity rows by account, close date, amount, product line, stage, and state.
- `GET /api/hr/summary`: HR operating context by quarter and region.
- `GET /api/events/performance`: event context by quarter and event ID.
- `GET /exports/churn/train.csv`, `/validation.csv`, `/candidates.csv`: churn modeling exports.

Some staged environments expose account-specific billing or A/R routes in the allowed list but return 404. Fall back to the global billing snapshot and finance A/R endpoints and filter locally.

## Shared Calculations

- `clean_ticket_count`: count tickets in the inclusive date range where `is_duplicate` is false, `is_spam` is false, and `status` is not `cancelled`.
- Clean-ticket SLA compliance: among clean tickets, percentage where `first_response_sla_met` and `resolution_sla_met` are both true. Use `0.0` for a month with no clean tickets unless the prompt defines a different empty-case policy.
- Latest NPS: latest non-retracted NPS response in the date range. For QBR monthly rows, prefer the account metrics row's `nps_score`; fall back to the latest non-retracted response in that month if needed.
- Current ARR: posted billing snapshot `billing_arr` whose `as_of` equals the prompt's assessment or A/R date. If exact `as_of` is absent, use the latest posted snapshot before that date and call out the assumption only if the final format permits notes.
- Retention overdue balance: `61_90 + 90_plus` from the A/R row for the account's legal name and as-of date.
- Clean billings reason: use when the retention overdue balance is zero.
- Open expansion pipeline: sum `amount` for `state == "open"` opportunities with close dates inside the prompt date range.
- Renewal window: renewal date on or after the assessment date and no more than 90 days after it.
- Low-tenure churn signal: contract tenure of 18 months or less.
- Usage decline: current-period average product usage below the immediately preceding comparable period, or a clear start-to-end decline inside the requested period.
- NPS deterioration: current-period sentiment is materially worse than the prior comparable period or the latest score is low enough to be a primary customer-health concern.
- SLA degradation: any clean ticket misses first-response or resolution SLA, or the prompt asks to use monthly SLA metrics and a month is below target.

## QBR Metrics Packets

Build one row per requested month:

- `revenue`: monthly `recognized_revenue` from account metrics.
- `support_tickets`: clean tickets created in that month.
- `sla_compliance_pct`: clean-ticket SLA compliance for that month.
- `nps_score`: monthly metrics `nps_score`, with non-retracted NPS response fallback.

Highlights:

- `average_revenue`: arithmetic mean of monthly revenue.
- `peak_revenue_month` and `peak_revenue`: highest monthly revenue; choose the earliest month on ties.
- `max_sla_month` and `max_sla_pct`: highest clean-ticket SLA percentage; choose the earliest month on ties.
- `peak_nps_month` and `peak_nps_score`: highest monthly NPS; choose the earliest month on ties.
- `ticket_trend`: `improving` if last month clean tickets are fewer than first month, `worsening` if greater, otherwise `flat`.

Source labels:

- Revenue: `crm_closed_won`.
- Support tickets: `support_export`.
- SLA compliance: `sla_report`.
- NPS: `nps_survey`.

Review planning:

- Default `review_owner` to `customer_success` for QBR packets unless the prompt makes the report primarily technical or financial.
- Set `needs_technical_signoff` only for severe or unresolved technical health issues, not for every isolated SLA miss.
- Agenda topics should start with partnership/context and metrics, include `technical_recovery` when support/SLA health is part of the readout, and end with the next-period initiatives topic when offered by the enum vocabulary.

## Renewal Risk Queues And Retention Boards

Assemble per-account facts from account profile, billing snapshot, A/R aging, tickets, NPS, metrics, and opportunities. Use the reason code vocabulary from the prompt/template:

- `overdue_receivable`: older A/R balance is positive.
- `clean_billings`: older A/R balance is zero.
- `renewal_window`: renewal date is in the next 90 days from the assessment date.
- `low_tenure_high_churn`: tenure is 18 months or less.
- `sla_degradation`: clean ticket SLA misses or poor SLA metrics.
- `nps_drop`: weak or deteriorating customer sentiment.
- `usage_decline`: negative product usage trend.
- `expansion_offset`: open expansion pipeline or a meaningful commercial offset is present.

Recommended action priority:

1. `collections_followup` when older A/R is a major active risk.
2. `technical_recovery` when support, SLA, usage, or sentiment is the dominant non-collections risk.
3. `renewal_save` when renewal timing or low tenure is the dominant risk without collections.
4. `executive_qbr` for strategic or executive alignment work when the prompt includes that business context.
5. `nurture_monitor` for low but watchlisted risk.
6. `no_action` for low-risk accounts when the enum and board format allow it.

For retention boards, standard order is risk severity descending, then current billing ARR descending inside each severity, with ranks assigned after sorting. For risk queues, sort by the requested score or probability descending and return exactly the requested top N.

Useful risk-score heuristic when the prompt requires an integer score but does not specify a formula: combine the negative signals above, weight active receivables and renewal timing highest, cap at 100, and keep low-risk single-signal accounts below 30. Translate scores roughly as critical at 75 or higher, high at 50-74, medium at 30-49, and low below 30 unless the examples in the current task bundle indicate a stricter threshold.

Portfolio and segment summaries:

- `accounts_reviewed`: number of account IDs examined.
- `critical_or_high_count`: count returned accounts whose level is critical or high.
- `arr_at_risk`: sum current billing ARR for returned or board accounts that are not low/no-action, following the prompt's scope.
- `collections_count`, `technical_recovery_count`: count returned accounts by primary action.
- Strategic and enterprise segment counts use account profile `segment`.
- `open_expansion_pipeline`: sum open expansion pipeline in the requested period for board accounts.
- `net_revenue_exposure`: ARR at risk minus open expansion pipeline when the template asks for net exposure.

## Receivables And Pipeline Reviews

Start from A/R rows matching the prompt `as_of` date. Include a followup when `61_90 + 90_plus > 0`, set `overdue_balance` to that sum, and sort followups by `customer_name` ascending.

Linking:

- Link an A/R customer to a CRM account when normalized `customer_name` exactly matches the account `legal_name` or one of its aliases.
- Do not fuzzy-match subsidiaries, regions, or similarly named entities when the legal or alias text does not match after normalization.
- Use `linked` with the account ID when matched, otherwise `unlinked` with `account_id: null`.

Pipeline:

- Filter opportunities by close date inside the quarter's calendar date range.
- `won_count` and `won_revenue`: closed-won opportunities in the quarter.
- `lost_count`: closed-lost opportunities in the quarter.
- `open_count` and `open_pipeline`: open opportunities in the quarter.
- `win_rate_pct`: `won_count / (won_count + lost_count) * 100`, rounded to 1 decimal.
- `top_open_product_line`: product line with the largest summed open pipeline, tie-broken alphabetically.

Ops context:

- For "all regions" HR context, sum quarter rows across all regions for headcount and unpaid claims.
- For event context, select the row matching the requested quarter and `event_id`.

## Churn Export Validation And Outreach

Validation:

- Count train and validation rows from the CSVs.
- `feature_count` is the number of raw feature columns excluding `customer_id` and `Churn`.
- If no modeling stack is available, use a deterministic baseline for validation: predict the training-set majority class on validation rows. Report the resulting accuracy and band.
- Determine tenure direction from the training rows: if churned customers have lower average tenure than retained customers, the tenure coefficient direction is `negative`; if higher, `positive`; otherwise `zero`.

Candidate scoring:

- Rank only the candidate IDs requested by the prompt.
- A portable model should weigh short tenure, month-to-month contracts, electronic-check or weaker payment posture, past-due invoices, high support volume, low NPS, negative usage trend, and low active-seat ratio as churn risk.
- Calibrate probabilities consistently and round to 3 decimals. If the prompt cares more about ranking than statistical calibration, keep probabilities monotonic with the risk score and below 1.000.

Outreach mapping:

- Past-due candidate: `collections_followup` with `overdue_receivable`.
- Low-tenure month-to-month candidate: `renewal_save` with `low_tenure_high_churn`.
- High support/SLA burden or severe usage decline: `technical_recovery` with the matching support or usage reason.
- Otherwise: `nurture_monitor` with `clean_billings`.

Cohort checks:

- `past_due_shortlist_count`: requested candidates with `InvoicePastDue == "Yes"`.
- `low_tenure_shortlist_count`: requested candidates with tenure of 18 months or less.
- `average_probability_top5`: arithmetic mean of the top five rounded or unrounded probabilities, then round to 3 decimals according to the prompt.
