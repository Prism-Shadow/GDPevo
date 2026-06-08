---
name: apexcloud-retention-analytics
description: Use this skill whenever a task asks for ApexCloud CRM, ApexCloud Retention Operations API, renewal risk, retention action boards, QBR metrics packets, receivables and pipeline reviews, or churn export validation. It guides API collection, source precedence, controlled labels, ranking, precision, and JSON-only output for ApexCloud customer success and retention analytics.
---

# ApexCloud Retention Analytics

Use this skill to produce deterministic JSON analytics from the ApexCloud Retention Operations API. The recurring work is to reconcile account profiles, account metrics, support tickets, NPS, billing/ARR, A/R aging, opportunities, HR/event context, and churn CSV exports into the exact answer template supplied by the task.

## Operating Rules

1. Read the task prompt and `input/payloads/answer_template.json` before computing anything. The template is the contract: preserve all requested top-level keys, nested keys, enum vocabularies, nullability, and list shapes.
2. Use only the account IDs, candidates, regions, periods, dates, and endpoint families named by the active task. Do not expand the cohort unless the prompt asks for all accounts or all regions.
3. Return JSON only. Use numbers as numbers, not strings. Round only final values: currency to 2 decimals, percentages to 1 decimal, probabilities to 3 decimals, counts and ranks as integers.
4. Controlled labels must exactly match the template vocabulary. Do not invent synonyms such as `save_play`, `finance_followup`, or `tech_recovery`.
5. If prompt prose lists fewer top-level keys than the template, keep the template keys. In these tasks, `policy_codes` may appear in the template even when the prompt summary omits it.

## API Usage

Use the API base URL explicitly allowed by the current task or controlling instruction. In evaluation harnesses, a proxy base such as `http://127.0.0.1:8066` can supersede a historical port embedded in sample prompts.

Common public endpoints:

- `GET /api/accounts` for CRM account records and legal names.
- `GET /api/accounts/<account_id>` for profile fields such as `legal_name`, `region`, `segment`, `renewal_date`, `contract_tenure_months`, `lifecycle_status`, `crm_arr`, and account-level billing fallback fields.
- `GET /api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM` for monthly `recognized_revenue`, `product_usage`, active seats, and coarse metric snapshots.
- `GET /api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` for support ticket truth, ticket hygiene, and SLA compliance.
- `GET /api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` for dated NPS responses.
- `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` for A/R buckets.
- `GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD` for pipeline and expansion opportunities by close date.
- `GET /api/hr/summary?quarter=YYYY-QN` for regional HR operations context.
- `GET /api/events/performance?event=<event_id>&quarter=YYYY-QN` for event order and revenue context.
- `GET /exports/churn/train.csv`, `/exports/churn/validation.csv`, and `/exports/churn/candidates.csv` for churn modeling tasks.

If a prompt exposes a billing snapshot endpoint, use it as the authoritative source for current ARR. If not, account profile billing fields are a fallback and `crm_arr` is a last resort. Do not use `recognized_revenue` as ARR.

## Source Precedence And Hygiene

- Current ARR: prefer billing snapshot current ARR, then account billing ARR fallback, then CRM ARR only when no billing source exists. Policy code `REV-4` corresponds to using the billing ARR source.
- Revenue in QBR monthly packets: use `metrics[].recognized_revenue`, not ARR.
- Clean support tickets: exclude tickets where `is_duplicate` is true, `is_spam` is true, or `status` is `cancelled`. Include real open and closed tickets.
- Monthly support ticket counts: count clean tickets by `created_date` month. Do not rely on `metrics.support_ticket_count` when ticket-level data is available.
- SLA compliance: among clean tickets, a ticket is SLA-clean only when both `first_response_sla_met` and `resolution_sla_met` are true. Monthly SLA percent is SLA-clean tickets divided by clean tickets.
- NPS: use non-retracted NPS responses sorted by `response_date`. Latest NPS is the latest valid response. Monthly NPS comes from the valid response in that month when present; use `null` only if the template permits missing values.
- Product usage trend: compare the first and last months in the requested period, or use `UsageTrendPct` from churn exports when the task is explicitly export-based.
- A/R overdue balance for retention and receivables work: use older buckets `61_90 + 90_plus`. Do not include `current`, `1_30`, or `31_60` unless the prompt explicitly defines overdue differently.
- CRM matching for A/R customers: link only customers that are actual CRM accounts, normally by exact legal name. Do not fuzzy-link subsidiaries, foundations, country variants, or near-matches just because they resemble an account alias.

## Risk And Action Rules

Reason codes:

- `overdue_receivable`: older A/R bucket balance is greater than zero.
- `renewal_window`: renewal date falls inside the task's renewal window, usually within about 90 days after the assessment date or inside the requested period.
- `nps_drop`: latest valid NPS is poor or materially worse than earlier period sentiment.
- `sla_degradation`: any meaningful clean-ticket SLA miss, or low clean-ticket SLA compliance.
- `usage_decline`: product usage or active-seat trend declines over the requested months.
- `low_tenure_high_churn`: short-tenure and high-churn profile, especially month-to-month or low-tenure accounts in churn exports.
- `expansion_offset`: account has open expansion pipeline in the requested close-date window.
- `clean_billings`: no older overdue A/R balance; include only when the template's reason vocabulary includes it and it helps explain a lower-risk account.

When a `risk_score` is required, use a consistent 0-100 additive score, cap at 100, and make the drivers explainable through reason codes. Weight overdue receivables, renewal timing, poor NPS, SLA degradation, and usage decline most heavily; use low tenure and lifecycle context as secondary risk; treat expansion pipeline as an exposure offset, not a reason to ignore risk.

Risk levels should follow the score or overall severity consistently:

- `critical`: acute multi-factor risk, usually high exposure plus urgent renewal, sentiment/support, or receivables pressure.
- `high`: clear material risk with several drivers or one severe driver.
- `medium`: actionable risk but less urgent or lower exposure.
- `low`: monitor-only or hygiene/contextual risk.

Primary action priority:

- `collections_followup`: use when older overdue receivables exist.
- `technical_recovery`: use for SLA, support, usage, or product-health recovery when receivables do not dominate.
- `renewal_save`: use for renewal-window or low-tenure churn risk without collections priority.
- `executive_qbr`: use for high-value strategic accounts where executive alignment is the best next move.
- `nurture_monitor`: use for low-risk accounts that still need observation.
- `no_action`: use only when the template allows it and no follow-up is warranted.

For retention action boards, standard board order is severity descending, then revenue exposure descending within the same severity, with ranks assigned after sorting. For top-risk lists, sort by risk score descending. For churn candidate lists, sort by predicted churn probability descending.

## Receivables, Pipeline, HR, And Event Reviews

- Receivables follow-ups start from A/R customers with `61_90 + 90_plus > 0`. `overdue_balance` is that older-bucket sum.
- Sort `overdue_followups` by `customer_name` ascending when requested.
- `link_status` is `linked` only when the A/R customer maps to an actual CRM account. Use `account_id: null` for unlinked customers.
- Pipeline windows are based on opportunity `close_date`, not created date.
- `won_count` and `won_revenue` use closed-won opportunities in the window. `lost_count` uses closed-lost opportunities. `open_count` and `open_pipeline` use opportunities with `state: open`.
- `win_rate_pct = won_count / (won_count + lost_count) * 100`; if there are no closed won/lost opportunities, report 0.0 unless the prompt says otherwise.
- `top_open_product_line` is the product line with the largest summed open pipeline, not necessarily the highest count.
- HR all-region context sums regional `headcount` and `unpaid_claims_amount`.
- Event context uses the requested event and quarter fields directly, commonly `event_orders` and `event_revenue`.

## QBR Metrics Packets

For each requested month:

- `revenue`: monthly `recognized_revenue`.
- `support_tickets`: clean ticket count for that month.
- `sla_compliance_pct`: clean-ticket SLA percent for that month.
- `nps_score`: valid NPS response score for that month.

Highlights:

- `average_revenue`: average of monthly revenue values.
- `peak_revenue_month` and `peak_revenue`: max monthly revenue.
- `max_sla_month` and `max_sla_pct`: max monthly clean-ticket SLA percent; break ties by earliest month unless the prompt says otherwise.
- `peak_nps_month` and `peak_nps_score`: max valid monthly NPS; break ties by earliest month.
- `ticket_trend`: `improving` if clean tickets decline from first to last month, `worsening` if they rise, else `flat`.

Metric source enums commonly map to:

- revenue: `crm_closed_won` for recognized-revenue CRM metrics unless the prompt asks for billing.
- support_tickets: `support_export`.
- sla_compliance: `sla_report`.
- nps: `nps_survey`.

## Churn Export Validation

For churn CSV tasks:

1. Load train, validation, and candidate CSVs from the public export endpoints.
2. `training_rows` and `validation_rows` are data row counts.
3. `feature_count` excludes `customer_id` and the target column such as `Churn`.
4. Train a deterministic logistic classifier or equivalent reproducible binary model from train.csv. One-hot encode categorical columns; keep numeric columns numeric; apply the same preprocessing to validation and candidates.
5. `accuracy_pct` is validation classification accuracy times 100, rounded to 1 decimal. Use a 0.5 probability threshold unless the task says otherwise.
6. `tenure_coefficient_direction` is the sign of the trained tenure feature coefficient: `negative`, `positive`, or `zero`.
7. Candidate `predicted_churn_probability` is a 0-1 probability rounded to 3 decimals, not a percent.
8. Rank only the requested candidate IDs, even if the candidate export contains more rows.

Outreach mapping for churn candidates should be driven by the most salient driver: overdue receivable -> `collections_followup`; low tenure or renewal timing -> `renewal_save`; SLA/usage/support health -> `technical_recovery`; clean billing and very low probability -> `nurture_monitor`.

## Common Field Meanings

- `current_arr`: current annual recurring revenue from billing-preferred ARR source.
- `latest_nps`: latest non-retracted NPS response in the analysis period.
- `clean_ticket_count`: number of non-duplicate, non-spam, non-cancelled tickets in the analysis period.
- `overdue_balance`: older A/R balance, normally `61_90 + 90_plus`.
- `arr_at_risk`: sum current ARR for accounts classified as critical, high, or medium risk, or the task's explicitly defined at-risk cohort.
- `open_expansion_pipeline`: sum open expansion opportunity amounts in the requested window.
- `net_revenue_exposure`: `arr_at_risk - open_expansion_pipeline` when the template asks for an exposure formula.
- `collections_count`: count accounts or follow-ups whose primary action is `collections_followup`, depending on the surrounding object.
- `technical_recovery_count`: count accounts whose primary action is `technical_recovery`.

## Policy Code Conventions

When the template offers these policy-code enums and the prompt does not define different policies, use the standard ApexCloud choices:

- `risk_model_code`: `RS-6`
- `arr_source_code`: `REV-4`
- `support_hygiene_code`: `SUP-8`
- `action_priority_code`: `ACT-5`
- `board_sort_code`: `BORD-4`
- `exposure_formula_code`: `EXP-6`
- `calendar_policy_code`: `CAL-5`
- `receivable_trigger_code`: `RCP-7`
- `crm_match_code`: `CM-5`
- `pipeline_window_code`: `PW-6`
- `followup_scope_code`: `FS-4`
- `model_protocol_code`: `MOD-7`
- `probability_scale_code`: `PRB-4`
- `deployment_rule_code`: `DEP-5`
- `outreach_mapping_code`: `OUT-2`

## Final QA Checklist

- The output parses as one JSON object and contains no markdown.
- All lists have exactly the requested length and rank/order.
- All enum values match the template exactly.
- All calculations use the requested date/month/quarter windows.
- Ticket counts and SLA use clean ticket logic.
- A/R overdue balances use older buckets only.
- CRM matching avoids fuzzy-linking noise entities.
- ARR uses billing-preferred source, not CRM ARR or monthly revenue.
- Rounding is applied only at final output precision.
