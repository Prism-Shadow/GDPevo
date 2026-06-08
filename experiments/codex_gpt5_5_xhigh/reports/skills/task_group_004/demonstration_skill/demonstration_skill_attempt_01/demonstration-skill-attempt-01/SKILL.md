---
name: demonstration-skill-attempt-01
description: Build ApexCloud CRM retention analytics outputs from the ApexCloud Retention Operations API and strict JSON answer templates. Use for tasks involving renewal risk queues, QBR metrics packets, receivables and pipeline operations reviews, churn model validation, candidate outreach ranking, high-touch retention action boards, or any ApexCloud CRM retention workflow requiring controlled labels, policy codes, deterministic rounding, and JSON-only output.
---

# ApexCloud Retention Analytics

## Core Workflow

1. Read the user prompt and the provided answer template first. Treat the template as authoritative for top-level keys, nested fields, nullability, enum vocabulary, and whether policy-code blocks must be returned.
2. Use only the account IDs, date ranges, months, regions, quarters, events, and due dates requested by the prompt. Do not add extra accounts unless the prompt asks for an all-region/all-customer summary.
3. Query the ApexCloud Retention Operations API using the base URL from the current prompt or harness. In this eval family, a shared proxy may be provided at `http://127.0.0.1:8066` even when prompt text references the original local service port.
4. Reconcile data by stable identifiers first: `account_id` for CRM/account/metrics/tickets/NPS/opportunities, exact CRM account or legal customer name for A/R matching, and explicit event or quarter parameters for operations context.
5. Calculate fields from source data, then sort, rank, round, and validate against the template. Return one JSON object only, with no Markdown, comments, or explanatory text.

## API Usage

Use endpoint families named in the prompt. Common ApexCloud public endpoints include:

- `/api/accounts` for CRM account lists, profiles, legal names, regions, segments, renewal dates, lifecycle, and matching context.
- `/api/accounts/<account_id>` for one account profile.
- `/api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM` for monthly revenue, usage, health, and other account metrics.
- `/api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` for support volume and SLA health.
- `/api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` for sentiment surveys.
- Account billing snapshot endpoints, when named, for current ARR. Prefer billing snapshots over CRM revenue for `current_arr`.
- `/api/finance/ar-aging` for receivables as of an A/R date. Use query parameters from the prompt when available.
- `/api/opportunities` for CRM pipeline, opportunity status, close dates, product line, amount, and account linkage.
- `/api/hr/summary` for quarter/region HR operations context.
- `/api/events/performance` for named event performance context.
- `/exports/churn/train.csv`, `/exports/churn/validation.csv`, and `/exports/churn/candidates.csv` for churn model validation and candidate ranking tasks.

When an endpoint returns linked records or source metadata, use those links instead of fuzzy inference. If an endpoint has more rows than requested, filter locally to the prompt's account list and inclusive date/month window.

## Source Rules

- `current_arr`: use the latest relevant billing snapshot as the authoritative ARR source. Do not substitute monthly CRM revenue unless the template explicitly asks for revenue metrics.
- `revenue` in QBR month rows: use account monthly metrics or CRM closed-won/revenue data for that month, not A/R balances.
- `support_tickets` and `clean_ticket_count`: count customer-relevant tickets inside the requested date window. Exclude duplicates, tests, spam, cancellations, or non-customer noise when flags/statuses identify them.
- `sla_compliance_pct`: calculate from clean tickets with SLA outcome fields. If there are no eligible tickets, follow the template's zero/null convention.
- `latest_nps`: use the latest survey in the requested window. Monthly QBR NPS uses that month's survey value; use `null` only when the template permits and no survey exists.
- `overdue_balance`: use overdue A/R aging buckets, excluding current/not-due amounts. For older-bucket receivables tasks, include customers with a positive older-bucket balance.
- `expansion_pipeline`: sum open expansion opportunities for the account whose close dates fall inside the requested opportunity window.
- `pipeline_summary`: filter opportunities to the requested quarter/date range. Count won, lost, and open separately. Calculate `win_rate_pct` as `won_count / (won_count + lost_count) * 100`, excluding open opportunities.
- `top_open_product_line`: choose the product line with the largest open pipeline amount; break ties deterministically by name.
- HR/event fields: use the requested quarter, region scope, event identifier, and source totals directly.

## Risk Signals

Use reason codes only from the template vocabulary.

- `overdue_receivable`: positive overdue A/R balance in the requested as-of snapshot.
- `renewal_window`: renewal date falls in or near the prompt's renewal/action window.
- `nps_drop`: sentiment worsens materially or latest NPS is low relative to earlier window data.
- `sla_degradation`: SLA compliance declines, breaches target, or has repeated unresolved support health issues.
- `usage_decline`: product usage or adoption declines across the requested months.
- `low_tenure_high_churn`: low tenure is associated with higher churn risk in the model or lifecycle context.
- `expansion_offset`: open expansion pipeline exists and can partially offset revenue exposure.
- `clean_billings`: no overdue balance for the requested A/R snapshot.

For `risk_score`, use an API-provided/model score if present. Otherwise use a deterministic additive score from the above signals, with overdue receivables, renewal timing, SLA degradation, NPS decline, usage decline, and low-tenure churn risk increasing score, and expansion offset reducing net exposure but still reported as a reason. Clamp scores to integers from 0 to 100. Map levels consistently: `critical` for the highest-risk tier, then `high`, `medium`, and `low`.

## Action Rules

Use the template's controlled action labels exactly.

- `collections_followup`: choose when overdue receivables are present and the task is not explicitly overriding action priority.
- `technical_recovery`: choose for SLA degradation, support health problems, NPS deterioration, or usage decline when no collections action has priority.
- `renewal_save`: choose for near-term renewal exposure without collections priority and without stronger technical recovery indicators.
- `executive_qbr`: choose for strategic QBR/escalation contexts where executive alignment is the main next step.
- `nurture_monitor`: choose for low-risk watchlist accounts or clean-billing churn candidates with no urgent recovery action.
- `no_action`: use only when the template allows it and there is no follow-up action due.

For follow-up calendars, map `next_touch_due_date` from the action-specific dates in the prompt. Use `null` for `no_action` when the template permits.

## Output Patterns

### Renewal Risk Queues

- Rank only the requested accounts and return exactly the requested count, usually top 5.
- Sort by `risk_score` descending, then by ARR exposure descending, then by `account_id` for ties.
- `portfolio_summary.accounts_reviewed` is the number of requested accounts reviewed.
- `critical_or_high_count` counts returned or in-scope accounts at `critical` or `high`, matching the prompt/template convention.
- `arr_at_risk` sums `current_arr` for critical/high accounts, not all accounts.
- `collections_count` and `technical_recovery_count` count returned accounts by `primary_action`.
- `model_checks.uses_billing_arr_source` should be true when `current_arr` came from billing snapshots.
- `model_checks.tenure_risk_direction` is `negative` when shorter tenure indicates higher churn risk, `positive` when longer tenure indicates higher risk, and `not_assessed` when tenure was not evaluated.

### QBR Metrics Packets

- Return one row per requested month, in month order.
- `average_revenue` is the arithmetic mean of monthly revenue values.
- `peak_revenue_month`, `max_sla_month`, and `peak_nps_month` use the earliest month on ties.
- `ticket_trend` is `improving` when ticket counts decline over the period, `worsening` when they rise, and `flat` otherwise.
- Metric source labels should match the source family: `crm_closed_won` or monthly metrics for revenue, `support_export` for tickets, `sla_report` for SLA, and `nps_survey` for NPS.
- Set `needs_technical_signoff` true when SLA/support/usage issues require technical recovery; otherwise false.
- Pick exactly the requested number of agenda topics, ordered from relationship framing and metrics to recovery/expansion and next-period planning.

### Receivables And Pipeline Reviews

- Start from A/R customers with positive older-bucket overdue balances.
- Link a receivable to CRM only when the customer is a CRM account by exact account linkage or exact legal-name match. Do not treat subsidiaries, foundations, regional entities, or merely similar names as linked without an explicit CRM link.
- Use `link_status` values `linked` or `unlinked`; set `account_id` to `null` for unlinked customers.
- Sort `overdue_followups` by `customer_name` ascending unless the prompt says otherwise.
- `financial_summary.overdue_client_count` counts follow-up customers; `overdue_total` sums their overdue balances.
- `linked_followup_count` and `unlinked_followup_count` count the follow-up rows by link status.
- `primary_action` for receivables follow-ups is normally `collections_followup`.

### Churn Model Validation And Candidate Ranking

- Load train, validation, and candidate CSVs from the export endpoints.
- Count `training_rows` and `validation_rows` directly after normal parsing.
- `feature_count` is the number of model feature columns, excluding IDs, labels/targets, split markers, and prediction/output columns.
- If validation rows include predictions, compute accuracy from those predictions. If not, fit a deterministic model from train features and evaluate the validation set using a fixed threshold, usually 0.5.
- Express `accuracy_pct` to 1 decimal and map `accuracy_band` to `below_70`, `70_to_79`, `80_to_89`, or `90_plus`.
- Determine `tenure_coefficient_direction` from the model coefficient or documented feature contribution for tenure: `negative`, `positive`, or `zero`.
- Rank only prompt-specified candidates by `predicted_churn_probability` descending. Use 3 decimal places for probabilities and sequential ranks after filtering.
- Map outreach by the strongest driver: overdue balance to `collections_followup`, renewal/low-tenure churn risk to `renewal_save`, SLA/NPS/usage degradation to `technical_recovery`, otherwise `nurture_monitor`.
- `past_due_shortlist_count` and `low_tenure_shortlist_count` count the requested candidate shortlist, not the entire candidate export, unless the prompt explicitly asks for all candidates.
- `average_probability_top5` is the arithmetic mean of the returned top 5 probabilities.

### Retention Action Boards

- Return all requested accounts in standard board order: risk severity descending, current ARR descending within severity, then `account_id` for deterministic ties.
- `arr_at_risk` sums ARR for accounts with an active risk action, excluding `no_action` accounts.
- `open_expansion_pipeline` sums open expansion pipeline across the board scope, including lower-risk accounts if they have open expansion.
- `net_revenue_exposure` equals `arr_at_risk - open_expansion_pipeline`.
- Count segment summary fields from CRM account profile segments for the requested board accounts.
- Fill `followup_calendar` exactly from prompt-provided action due dates.

## Policy Codes

When the template includes policy-code fields and the prompt does not define a different policy, use the standard ApexCloud conventions implied by the calculations:

- `risk_model_code`: `RS-6` for balanced multi-factor retention risk.
- `arr_source_code`: `REV-4` for billing-snapshot ARR.
- `support_hygiene_code`: `SUP-8` for clean customer-ticket counting.
- `action_priority_code`: `ACT-5` for collections, technical, renewal, executive, nurture/no-action priority.
- `board_sort_code`: `BORD-4` for risk severity then ARR ordering.
- `exposure_formula_code`: `EXP-6` for ARR at risk minus expansion pipeline.
- `calendar_policy_code`: `CAL-5` for prompt-specified action calendars.
- `receivable_trigger_code`: `RCP-7` for older-bucket overdue receivable triggers.
- `crm_match_code`: `CM-5` for strict CRM linkage or exact legal-name matching.
- `pipeline_window_code`: `PW-6` for opportunity close dates inside the requested quarter/window.
- `followup_scope_code`: `FS-4` for all older-bucket overdue follow-up customers.
- `model_protocol_code`: `MOD-7` for train/validation/candidate export validation.
- `probability_scale_code`: `PRB-4` for 0.000 to 1.000 churn probabilities.
- `deployment_rule_code`: `DEP-5` for ranked top-candidate deployment.
- `outreach_mapping_code`: `OUT-2` for driver-based outreach action mapping.

## Formatting And Hygiene

- Return valid JSON only. Do not wrap it in Markdown.
- Preserve all fields from the answer template, including policy blocks even if the prose prompt omits them.
- Use integers for counts, ranks, and risk scores.
- Use 2 decimals for currency, 1 decimal for percentages, and 3 decimals for churn probabilities unless the prompt says otherwise.
- Use JSON `null` for missing nullable values and `0` or `0.0` only when the template expects a numeric zero.
- Keep enum strings exactly as shown in the template. Do not invent labels or change case.
- Treat date ranges and month ranges as inclusive.
- Recompute totals from the rounded or source values consistently; avoid double-counting linked records, duplicate tickets, or repeated A/R rows.
- After sorting, assign ranks sequentially starting at 1.
- Do not include training examples, hidden test data, or account-specific answer dumps in any derived output.
