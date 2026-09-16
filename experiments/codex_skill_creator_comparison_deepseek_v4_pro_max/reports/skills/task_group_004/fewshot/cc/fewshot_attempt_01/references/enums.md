## Controlled Enumerations

Every output field with a constrained vocabulary must use exactly one value
from the lists below. The answer template is the authoritative source; use this
reference when the template is not available or for in-workflow reasoning.

### Risk levels

| Value | When to use |
|-------|------------|
| `critical` | Multiple severe signals: renewal imminent + low NPS + SLA failures + overdue receivables or usage decline. Risk score ≥ 75. |
| `high` | Two or more concerning signals: overdue, NPS drop, SLA degradation, or usage decline. Risk score 40–74. |
| `medium` | One moderate signal: SLA soft miss, mild NPS dip, or renewal within 90 days but otherwise healthy. Risk score 15–39. |
| `low` | At most one mild signal; account is generally healthy. Risk score < 15. |

### Primary actions

| Value | When to use |
|-------|------------|
| `collections_followup` | Overdue balance > 0 (any aging bucket beyond current). |
| `technical_recovery` | SLA compliance below 85% or significant SLA misses without overdue receivables. |
| `renewal_save` | Account is within the renewal window and risk level is high or critical but no overdue balance. |
| `executive_qbr` | Strategic/Enterprise account with expansion pipeline and no urgent risk issues. |
| `nurture_monitor` | Low risk, clean billings, stable usage — watch passively. |
| `no_action` | Very low risk, all signals nominal — no intervention needed. |

### Reason codes

| Value | When to flag |
|-------|------------|
| `renewal_window` | `renewal_date` is within ~90 days after the assessment date. |
| `overdue_receivable` | Overdue balance > 0 in the A/R aging for the as-of date. |
| `nps_drop` | Latest NPS dropped from the prior reading during the period, or latest NPS < 50. |
| `sla_degradation` | Any month in the period has SLA compliance below the threshold, or there is a declining SLA trend. |
| `usage_decline` | `product_usage` declined by more than a few percentage points over the period. |
| `low_tenure_high_churn` | `contract_tenure_months` ≤ 24. Short-tenure accounts are empirically higher churn risk. |
| `expansion_offset` | Account has an open Q2 (or current-quarter) opportunity with close_date in the analysis period. Mitigates risk. |
| `clean_billings` | Zero overdue balance, all invoices current for the as-of date. |

### Metric sources

| Value | Data origin |
|-------|------------|
| `crm_closed_won` | CRM closed-won opportunity revenue. |
| `support_export` | Support ticket system export. |
| `sla_report` | SLA compliance reporting dashboard. |
| `nps_survey` | NPS survey platform. |
| `billing_snapshot` | Quarterly billing snapshot. |
| `ar_aging` | Accounts receivable aging report. |
| `pipeline_crm` | CRM opportunity pipeline. |
| `event_dashboard` | Event performance dashboard. |
| `hr_report` | HR operations report. |

### Agenda topics (exactly 4 ordered)

| Value | Topic |
|-------|-------|
| `partnership_overview` | Account relationship and partnership summary. |
| `q2_metrics` | Quarterly metrics review. |
| `performance_highlights` | Key performance wins and highlights. |
| `q3_initiatives` | Planned Q3 initiatives and roadmap. |
| `technical_recovery` | Technical health and recovery plan. |
| `commercial_expansion` | Commercial expansion and growth opportunities. |

### Review owners

| Value | Domain |
|-------|--------|
| `solutions_engineering` | Technical signoff and solution architecture. |
| `customer_success` | Account health, QBR, relationship management. |
| `finance_ops` | Billing, receivables, revenue operations. |

### Ticket trend

| Value | Condition |
|-------|----------|
| `improving` | Clean ticket count decreases over the period. |
| `worsening` | Clean ticket count increases over the period. |
| `flat` | Clean ticket count is unchanged (±1) over the period. |

### Link status (A/R to CRM account)

| Value | Condition |
|-------|----------|
| `linked` | A/R `customer_name` matches an account `legal_name` or any `account_alias`. |
| `unlinked` | No account match found. account_id must be `null`. |

### Accuracy bands

| Value | Condition |
|-------|----------|
| `below_70` | accuracy < 70% |
| `70_to_79` | 70% ≤ accuracy < 80% |
| `80_to_89` | 80% ≤ accuracy < 90% |
| `90_plus` | accuracy ≥ 90% |

### Tenure coefficient direction

| Value | Meaning |
|-------|---------|
| `negative` | Higher tenure → lower churn probability (protective). |
| `positive` | Higher tenure → higher churn probability (unusual). |
| `zero` | No discernible relationship. |

### Outreach actions (churn ranking)

| Value | When to use |
|-------|------------|
| `collections_followup` | Candidate has `InvoicePastDue=Yes`. |
| `renewal_save` | Candidate flagged `low_tenure_high_churn`. |
| `nurture_monitor` | Low probability, clean billing. |
| `technical_recovery` | High support ticket count or SLA issues. |

### Policy code groups

These appear in `policy_codes` sub-objects. Selection rules are in
[rules.md](rules.md).

**Risk model**: `RS-2`, `RS-6`, `RS-9`
**ARR source**: `REV-1`, `REV-4`, `REV-8`
**Support hygiene**: `SUP-3`, `SUP-8`, `SUP-9`
**Action priority**: `ACT-1`, `ACT-5`, `ACT-7`
**Receivable trigger**: `RCP-4`, `RCP-7`, `RCP-9`
**CRM match**: `CM-2`, `CM-5`, `CM-8`
**Pipeline window**: `PW-3`, `PW-6`, `PW-9`
**Followup scope**: `FS-1`, `FS-4`, `FS-8`
**Model protocol**: `MOD-2`, `MOD-7`, `MOD-9`
**Probability scale**: `PRB-1`, `PRB-4`, `PRB-8`
**Deployment rule**: `DEP-3`, `DEP-5`, `DEP-9`
**Outreach mapping**: `OUT-2`, `OUT-6`, `OUT-8`
**Board sort**: `BORD-1`, `BORD-4`, `BORD-8`
**Exposure formula**: `EXP-2`, `EXP-6`, `EXP-9`
**Calendar policy**: `CAL-3`, `CAL-5`, `CAL-7`

### Risk score

Risk score is an integer between 0 and 100 computed from weighted signals. The
exact weighting is in [rules.md](rules.md). Higher scores indicate greater
renewal risk.
