# ApexCloud Field Map

## Endpoint Families

- `/api/accounts/{account_id}`: account profile, region, lifecycle, tenure, legal name.
- `/api/accounts/{account_id}/metrics`: monthly revenue and other account metrics.
- `/api/accounts/{account_id}/tickets`: support volume and ticket hygiene.
- `/api/accounts/{account_id}/nps`: NPS history and latest score.
- `/api/accounts/{account_id}/billing` and `/api/billing/snapshots`: ARR, billing context, current revenue exposure.
- `/api/accounts/{account_id}/ar-aging` and `/api/finance/ar-aging`: overdue balances and aging buckets.
- `/api/opportunities`: open, won, and lost pipeline, including expansion.
- `/api/hr/summary`: headcount and claims context.
- `/api/events/performance`: event orders and event revenue.
- `/exports/churn/train.csv`, `/exports/churn/validation.csv`, `/exports/churn/candidates.csv`: churn modeling tasks.

## Common Task Patterns

- Renewal risk queue and retention board:
  - Rank by urgency, risk, and exposure as the prompt requests.
  - Keep the exact action labels and reason codes from the prompt/template.
  - Preserve any `policy_codes` block in the template.
- QBR metrics packet:
  - Build one row per requested month.
  - Compute summary fields after the monthly series.
  - Keep source labels exact.
- Receivables and pipeline review:
  - Sort follow-up rows by `customer_name` when requested.
  - Link customer names to CRM accounts only when the prompt or data supports it.
- Churn validation and ranking:
  - Validate the train and validation export first.
  - Rank candidates by predicted churn probability descending.

## Normalization Rules

- Use exact precision requested by the prompt.
- Keep counts as integers.
- Keep `null` when the template uses it and no value applies.
- Keep list order stable and deterministic.
- Use exact spellings for controlled labels.

## Controlled Vocabularies

- `risk_level`: `critical`, `high`, `medium`, `low`
- `primary_action` / outreach action: `collections_followup`, `technical_recovery`, `renewal_save`, `executive_qbr`, `nurture_monitor`, `no_action`
- Common reason codes: `overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`

