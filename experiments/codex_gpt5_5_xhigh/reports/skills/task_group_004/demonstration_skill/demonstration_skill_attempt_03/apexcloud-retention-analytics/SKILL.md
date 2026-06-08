---
name: apexcloud-retention-analytics
description: Use for ApexCloud CRM retention analytics tasks that call the ApexCloud Retention Operations API and must return strict JSON for renewal risk queues, QBR metrics packets, receivables and pipeline reviews, churn validation/ranking, or high-touch retention action boards. Captures reusable endpoint usage, source-of-truth choices, data hygiene rules, controlled enum mappings, policy-code conventions, and output formatting pitfalls.
---

# ApexCloud Retention Analytics

## Core Workflow

1. Read the task prompt and answer template first. Preserve the template's top-level keys, nested field names, nullability, list lengths, enum vocabularies, and requested sort order.
2. Use only the API base URL and public endpoint families provided in the current prompt. Do not reuse ports or paths from prior examples if the current task gives different ones.
3. Filter every source by the prompt's account IDs, region, months, date range, quarter, as-of date, and candidate shortlist. Treat date ranges as inclusive.
4. Compute from raw API data, then round only final values: currency to 2 decimals, percentages to 1 decimal, churn probabilities to 3 decimals, counts and risk scores as integers.
5. Return JSON only. Do not include explanations, markdown, comments, extra keys, or enum values outside the template.

## API Source Map

- Account profile: `/api/accounts` and `/api/accounts/<account_id>` provide canonical `account_id`, names/aliases, region, segment, lifecycle status, renewal date, tenure, CRM ARR, and current billing ARR hints.
- Monthly metrics: `/api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM` provides recognized revenue, product usage, active seats, monthly NPS status, and coarse support/SLA metrics.
- Tickets: `/api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` is the source for clean support counts and ticket-level SLA calculations.
- NPS: `/api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` is the source for latest, peak, and valid survey scores.
- A/R aging: `/api/finance/ar-aging` with the prompt's as-of date is the source for receivables, collections triggers, and CRM matching.
- Opportunities: `/api/opportunities` filtered by close date, state/stage, account, region, and product line is the source for open expansion pipeline and Q3 pipeline summaries.
- HR and events: `/api/hr/summary` and `/api/events/performance` provide operations context; sum across regions only when the prompt says all regions.
- Churn exports: `/exports/churn/train.csv`, `/exports/churn/validation.csv`, and `/exports/churn/candidates.csv` support validation metrics and candidate ranking.

## Data Hygiene

- Use `account_id` as the canonical CRM key. Use legal names and aliases only to match external A/R customer names back to CRM accounts.
- For A/R matching, normalize case, punctuation, and common suffixes, but stay conservative: exact legal-name or alias matches are linked; subsidiaries, foundations, regional variants, and near-lookalike noise remain unlinked with `account_id: null`.
- For overdue receivables, use only older buckets: `overdue_balance = 61_90 + 90_plus`. Do not include `current`, `1_30`, or `31_60` in overdue balances or older-bucket follow-up triggers.
- Mark `clean_billings` when older-bucket overdue balance is zero, even if current or younger aging buckets are nonzero.
- Clean tickets exclude spam, duplicates, and cancelled tickets. Open and closed tickets can count if they are otherwise clean.
- Compute ticket SLA compliance from clean tickets where both `first_response_sla_met` and `resolution_sla_met` are true. Prefer ticket-level calculations over summary metric fields when a support count or SLA health field depends on hygiene.
- Exclude retracted NPS responses. For latest NPS, choose the most recent non-retracted response in the period; ignore missing monthly NPS placeholders.
- Use billing snapshot/current billing ARR for `current_arr`, exposure, and `uses_billing_arr_source`; do not use `crm_arr` when a billing source is available. Use monthly `recognized_revenue` for QBR revenue, not ARR.

## QBR Packets

- Build one metric row per requested month, in month order.
- `revenue`: monthly `recognized_revenue`.
- `support_tickets`: clean ticket count for that month, not the raw metric support count if hygiene changes it.
- `sla_compliance_pct`: clean tickets meeting both SLA flags divided by clean tickets; use the template's fallback if there are no clean tickets.
- `nps_score`: valid monthly NPS score from NPS responses or completed monthly metrics; keep template null behavior for missing scores.
- `average_revenue`: arithmetic average across requested months.
- Peak/max fields use the highest value; when tied, pick the earliest month.
- `ticket_trend`: compare first and last monthly clean ticket counts: decreasing is `improving`, increasing is `worsening`, otherwise `flat`.
- QBR source enums usually map as: revenue `crm_closed_won`, support tickets `support_export`, SLA `sla_report`, NPS `nps_survey`.
- Agenda topics must be controlled enum strings. Start with partnership/metrics topics, include technical recovery when support or SLA needs discussion, include commercial expansion when pipeline is a central finding, and end with next-quarter initiatives when requested.

## Retention Risk And Action Boards

- Risk evidence comes from renewal timing, billing ARR/current exposure, NPS health, clean support/SLA health, usage trend, older-bucket receivables, tenure, lifecycle status, and expansion pipeline.
- Use these reason codes exactly when supported by data: `overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`.
- `renewal_window`: renewal date falls inside or near the prompt's retention window.
- `nps_drop`: latest valid NPS is materially low or sentiment worsened versus the relevant baseline.
- `usage_decline`: product usage, active seat ratio, or candidate `UsageTrendPct` declines over the requested period.
- `low_tenure_high_churn`: short tenure, month-to-month/weak contract context, or churn model features indicate early-life risk.
- `expansion_offset`: open expansion opportunity in the requested close-date window; it can reduce net exposure but is still a reason code when present.
- If a numeric risk score is required, keep it integer and capped at 100. Typical level bands are `critical` at 80+, `high` at 50-79, `medium` at 30-49, and `low` below 30 unless the prompt defines otherwise.
- Primary action precedence: older-bucket overdue balance -> `collections_followup`; severe support/SLA/usage/NPS problem -> `technical_recovery`; near renewal without collections lead -> `renewal_save` or `executive_qbr`; stable watchlist -> `nurture_monitor`; healthy/no follow-up -> `no_action`.
- For action-board calendars, map each primary action to the prompt's due date. Use `null` for `next_touch_due_date` when `primary_action` is `no_action`.
- Rank queues by risk score/level first, then current ARR or exposure as a tie-breaker. For a "standard retention board order", sort from critical to low action priority, then by exposure within comparable risk groups.
- Portfolio summaries count the accounts reviewed from the prompt, not just accounts returned. Action counts count returned/output rows unless the template says portfolio-wide.
- `arr_at_risk` is normally the sum of current ARR for risk-bearing accounts in scope, such as critical/high accounts for risk queues or non-low/action accounts for action boards.
- `open_expansion_pipeline` is the sum of open opportunities in the requested close-date window. `net_revenue_exposure = arr_at_risk - open_expansion_pipeline`.

## Receivables, Pipeline, HR, And Events

- Receivables follow-ups include every customer with older-bucket overdue balance greater than zero, linked or unlinked, sorted by `customer_name` ascending.
- `overdue_client_count` counts these older-bucket customers; `overdue_total` sums their `61_90 + 90_plus` balances.
- `linked_followup_count` and `unlinked_followup_count` split follow-ups by conservative CRM match result.
- For pipeline summaries, filter opportunities by prompt close-date window. Count closed won and closed lost by stage/state, count open opportunities by `state: open`, and sum open pipeline amounts.
- `win_rate_pct = won_count / (won_count + lost_count) * 100`; do not include open opportunities in the denominator.
- `top_open_product_line` is the product line with the highest total open pipeline in the filtered window.
- HR context for all regions sums headcount and unpaid claims amounts. Event context uses the requested event and quarter fields directly.

## Churn Export Tasks

- Count rows directly from CSV data rows: `training_rows`, `validation_rows`, and candidate rows after filtering to the prompt's shortlist.
- `feature_count` is the number of input feature columns before one-hot expansion: exclude `customer_id` and the target `Churn`.
- Train only on `train.csv`; use `validation.csv` only for validation accuracy and checks. Never train on validation or candidate rows.
- Encode categorical features consistently across train, validation, and candidates. Use a deterministic regularized binary classifier unless the prompt specifies a different model; report validation accuracy at the model's class threshold.
- `tenure_coefficient_direction` is the sign of the fitted tenure effect: lower tenure increasing churn risk means `negative`.
- Churn probabilities are decimals from 0 to 1, rounded to 3 places, not percentages. Rank only the candidate accounts requested by the prompt.
- `past_due_shortlist_count` counts top-ranked candidates with past-due invoice/older A/R evidence. `low_tenure_shortlist_count` counts top-ranked candidates with short-tenure risk. `average_probability_top5` averages the top five probabilities.
- Outreach mapping mirrors retention actions: past due -> `collections_followup` with `overdue_receivable`; low tenure/high modeled risk near renewal -> `renewal_save` with `low_tenure_high_churn`; technical/SLA/usage pain -> `technical_recovery`; clean low-risk accounts -> `nurture_monitor` with `clean_billings`.

## Policy Code Conventions

When the template asks for policy code choices and the data follows the standard ApexCloud conventions, use these controlled codes:

- `risk_model_code`: `RS-6` for multi-factor retention risk using renewal, ARR, sentiment, support, usage, receivables, tenure, lifecycle, and expansion context.
- `arr_source_code`: `REV-4` for billing/current ARR source of truth.
- `support_hygiene_code`: `SUP-8` for clean-ticket support hygiene.
- `action_priority_code`: `ACT-5` for collections-first, technical-recovery-next action priority.
- `board_sort_code`: `BORD-4` for standard risk/action board ordering.
- `exposure_formula_code`: `EXP-6` for net exposure as ARR at risk minus open expansion pipeline.
- `calendar_policy_code`: `CAL-5` for prompt-specified follow-up date mapping by action.
- `receivable_trigger_code`: `RCP-7` for older-bucket A/R trigger.
- `crm_match_code`: `CM-5` for conservative legal-name/alias CRM matching.
- `pipeline_window_code`: `PW-6` for close-date-window pipeline filtering.
- `followup_scope_code`: `FS-4` for linked and unlinked older-bucket receivables follow-up scope.
- `model_protocol_code`: `MOD-7` for train/validation/candidate export protocol.
- `probability_scale_code`: `PRB-4` for 0-to-1 probability decimals.
- `deployment_rule_code`: `DEP-5` for ranking only the requested candidate shortlist.
- `outreach_mapping_code`: `OUT-2` for risk-driver-to-outreach-action mapping.

## Final JSON Checks

- Verify exact object counts: top N means exactly N; action boards may require all input accounts.
- Verify sort order after rounding has not changed.
- Verify all enum strings match the template exactly.
- Preserve numeric types as numbers and nullable fields as `null`, not empty strings, unless the template explicitly uses strings.
- Recompute summary fields from the final included rows and stated portfolio scope before returning.
