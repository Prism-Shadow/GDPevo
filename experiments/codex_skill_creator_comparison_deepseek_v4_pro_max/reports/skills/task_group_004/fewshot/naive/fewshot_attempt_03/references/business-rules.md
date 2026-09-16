# Business Rules

## Risk factor severity ordering

Risk factors contribute to the overall risk score and level in roughly this order of severity:

1. `overdue_receivable` -- strongest signal; indicates immediate financial exposure.
2. `renewal_window` -- important timing signal; amplifies all other risks.
3. `nps_drop` -- strong sentiment signal; often precedes churn.
4. `sla_degradation` -- operational health indicator; erodes trust.
5. `usage_decline` -- product stickiness indicator; leading churn indicator.
6. `low_tenure_high_churn` -- statistical risk factor from churn model.
7. `expansion_offset` -- mitigating factor; reduces net risk.
8. `clean_billings` -- positive signal; indicates financial discipline.

When multiple reason codes are present, the risk score should increase with both the number and severity of codes. A single `overdue_receivable` plus `renewal_window` is typically `high`; adding `nps_drop` and `sla_degradation` moves it toward `critical`.

## Primary action selection logic

Use this decision tree to select the primary action:

1. If `overdue_receivable` is present and the overdue balance is material (non-zero): `collections_followup`.
2. Else if the account has `sla_degradation` or `usage_decline` as the dominant signal (no overdue, but operational issues): `technical_recovery`.
3. Else if the account is in a `renewal_window` with elevated risk (low tenure, NPS drop, or multiple signals): `renewal_save`.
4. Else if the account is strategic/enterprise with complex multi-signal issues: `executive_qbr`.
5. Else if risk is low with `clean_billings`: `nurture_monitor`.
6. Else if risk is minimal and no active issues: `no_action`.

When `overdue_receivable` co-occurs with technical issues, prioritize collections. Collections risk is financial and time-sensitive; technical recovery can follow.

## Portfolio and segment aggregations

- `arr_at_risk`: sum of `current_arr` for all accounts with `risk_level` of `critical` or `high`.
- `collections_count`: count of accounts where `primary_action` is `collections_followup`.
- `technical_recovery_count`: count of accounts where `primary_action` is `technical_recovery`.
- `critical_or_high_count`: count of accounts with `risk_level` in (`critical`, `high`).
- `net_revenue_exposure`: `arr_at_risk` minus `open_expansion_pipeline` for the portfolio. This represents the net dollar exposure after accounting for potential expansion offsets.

## Segment classification

Accounts have a `segment` field from the API. Map it as:
- `strategic_accounts`: count of accounts with segment value matching "Strategic".
- `enterprise_accounts`: count of accounts with segment value matching "Enterprise".
These counts should sum to the total accounts reviewed when only those two segments are present.

## Ticket trend computation

Compare the ticket count from the first month in the analysis period to the ticket count from the last month:
- If last-month count < first-month count: `improving`.
- If last-month count > first-month count: `worsening`.
- If equal: `flat`.

## NPS analysis

- `latest_nps`: use the most recent NPS survey score within the analysis period for the account.
- To detect an `nps_drop`: compare the latest score against the earliest score in the period. A drop of roughly 10 or more points qualifies.
- For QBR highlights, `peak_nps_score` and `peak_nps_month` refer to the highest NPS score observed across the period.

## SLA compliance

- Source: ticket data from `/api/accounts/{id}/tickets`. Each ticket has SLA breach information.
- Compute `clean_ticket_count` as the number of tickets with no SLA breach within the period.
- Compute `sla_compliance_pct` per month: (tickets without SLA breach / total tickets) * 100, rounded to 1 decimal.
- For risk assessment: `sla_degradation` applies when SLA compliance drops below 100% in the recent period or when tickets with breaches are present.

## Usage trend

- Source: monthly metrics from `/api/accounts/{id}/metrics`. Look for a decline in usage-related fields across the months in the analysis period.
- `usage_decline` applies when usage metrics show a clear downward trajectory.

## CRM account linking for A/R

When cross-referencing `/api/finance/ar-aging` customers with `/api/accounts`:

1. Fetch both lists in full.
2. For each A/R customer, normalize the name: lowercase, strip extra whitespace, remove common suffixes like "Inc.", "LLC", "Ltd.", "Corp.", "Group".
3. Compare against normalized CRM account names.
4. A match is `linked` when the normalized names share a significant token overlap (e.g., "north star finance services" and "northstar finance group inc." share the tokens "north" and "star" and "finance"). Use substring matching and token-set overlap.
5. When linked, populate `account_id` with the CRM account's `id`. When unlinked, set `account_id` to `null`.

## Churn model validation

When working with churn CSV exports:

1. Parse with pandas: `pd.read_csv(url)` for each export.
2. `training_rows`: length of train.csv DataFrame.
3. `validation_rows`: length of validation.csv DataFrame.
4. `feature_count`: number of columns in train.csv minus the label column (`churn`) and any ID or prediction columns. Count all remaining columns that represent model features.
5. `accuracy_pct`: compute from validation.csv by comparing the `prediction` column to the `churn` label column. `accuracy = (correct / total) * 100`, rounded to 1 decimal.
6. `tenure_coefficient_direction`: inspect the data relationship between tenure and churn. If churn rate is higher for low-tenure accounts, the direction is `negative` (tenure inversely related to churn). This is the standard expectation.
7. For candidate ranking: sort `candidates.csv` by `predicted_churn_probability` descending, take the top N, and map each to an outreach action based on the account context.

## Pipeline aggregation

When computing pipeline summary from `/api/opportunities`:

1. Filter opportunities by the relevant period (close_date within the analysis range).
2. `won_count` and `won_revenue`: opportunities with stage `closed_won`. `won_revenue` is the sum of their amounts.
3. `lost_count`: opportunities with stage `closed_lost`.
4. `open_count` and `open_pipeline`: opportunities with stage values other than `closed_won` or `closed_lost`. `open_pipeline` is the sum of their amounts.
5. `win_rate_pct`: `won_count / (won_count + lost_count) * 100`, rounded to 1 decimal.
6. `top_open_product_line`: the `product_line` with the highest total `amount` among open opportunities. In case of ties, select the first alphabetically.

## Calendar due dates

When the prompt provides per-action due dates (e.g., `collections_followup: 2026-07-15`, `technical_recovery: 2026-07-18`), use those exact dates. When a prompt provides a single due date for all overdue items (e.g., "Follow-up due date: 2026-10-15"), propagate that date to every overdue followup entry. For `no_action` accounts, set `next_touch_due_date` to `null`.
