# CRM Retention Analytics Skill

## Overview
This skill covers working with the ApexCloud Retention Operations API to produce structured analytics outputs for customer success, retention risk scoring, QBR metrics, collections/pipeline reconciliation, and churn model validation.

## Environment Setup
- Read the current solver's `environment_access.md` to get `GDPEVO_ENV_BASE_URL`.
- Do NOT hard-code `localhost` or `127.0.0.1`. Use the remote API base URL from the environment file.
- The API is HTTP (not HTTPS) on the given host/port.

## API Endpoints & Usage Habits

### Core Account Endpoints
| Endpoint | Purpose | Parameters |
|----------|---------|------------|
| `GET /api/accounts` | List all accounts | None |
| `GET /api/accounts/{account_id}` | Single account profile | None |
| `GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM` | Monthly metrics | `start`, `end` as year-month |
| `GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | Support tickets | `start`, `end` as dates |
| `GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | NPS responses | `start`, `end` as dates |

### Financial & Pipeline Endpoints
| Endpoint | Purpose | Important Notes |
|----------|---------|-----------------|
| `GET /api/billing/snapshots?account_id={id}` | Billing snapshots | Filter by `account_id`; returns array of quarterly snapshots |
| `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` | A/R aging | **CRITICAL:** This endpoint returns ALL records regardless of `account_id` filter. Filter client-side by matching `aging_id` to `AR-{account_id}-2026-Q2`. |
| `GET /api/opportunities` | All opportunities | Query params do NOT filter; filter client-side by `account_id`, `state`, `close_date` |

### Operations Endpoints
| Endpoint | Purpose |
|----------|---------|
| `GET /api/hr/summary` | HR headcount data |
| `GET /api/events/performance` | Event orders and revenue by quarter |

### Response Structures

#### Account Object
```json
{
  "account_id": "acct_...",
  "billing_arr_current": 1425000.00,
  "crm_arr": 1268250.00,
  "contract_tenure_months": 12,
  "lifecycle_status": "active|renewal_risk|implementation",
  "renewal_date": "2026-08-27",
  "segment": "Strategic|Enterprise|Mid-Market",
  "region": "North America|EMEA|APAC|LATAM",
  "product_plan": "Strategic|Enterprise|Scale",
  "display_name": "...",
  "legal_name": "..."
}
```

#### Metrics Object (per month)
```json
{
  "month": "2026-04",
  "recognized_revenue": 118387.61,
  "support_ticket_count": 5,
  "sla_compliance": 85.9,
  "nps_score": 17,
  "product_usage": 53.87,
  "active_seats": 95,
  "survey_status": "completed|missing"
}
```

#### Ticket Object
```json
{
  "ticket_id": "TCK-...",
  "created_date": "2026-04-17",
  "first_response_sla_met": true,
  "resolution_sla_met": true,
  "is_duplicate": false,
  "is_spam": false,
  "severity": "P1|P2|P3|P4",
  "status": "closed|open|cancelled",
  "product_area": "integrations|billing|workflow|..."
}
```

#### NPS Response Object
```json
{
  "response_id": "NPS-...",
  "response_date": "2026-04-21",
  "score": 17,
  "survey_channel": "email|csm_call|in_app",
  "retracted": false
}
```

#### A/R Aging Object
```json
{
  "aging_id": "AR-acct_...-2026-Q2",
  "as_of": "2026-06-30",
  "current": 49208.34,
  "1_30": 8057.36,
  "31_60": 1679.25,
  "61_90": 8773.03,
  "90_plus": 0,
  "customer_name": "...",
  "quarter": "2026-Q2"
}
```

#### Opportunity Object
```json
{
  "opportunity_id": "OPP-...",
  "account_id": "acct_...",
  "amount": 501980.99,
  "close_date": "2026-05-25",
  "stage": "Discovery|Proposal|Negotiation|Prospecting|Closed Won|Closed Lost",
  "state": "open|closed",
  "product_line": "AI Assist|Data Cloud|Workflow Plus|Core Retention"
}
```

## Workflow Rules

### 1. Data Gathering
- Fetch account list first, then filter to relevant accounts by `account_id` or `region`.
- For each target account, fetch in parallel: account profile, metrics, tickets, NPS, billing snapshots, and opportunities.
- For A/R aging: query `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` once, then filter the returned array client-side by `aging_id` matching `AR-{account_id}-{quarter}`.
- For opportunities: query `GET /api/opportunities` once, then filter client-side by `account_id`, `state`, and date ranges.

### 2. Date & Period Handling
- Assessment date is typically `2026-06-30` for Q2 analysis.
- Analysis period: `2026-04-01` through `2026-06-30`.
- Months: `2026-04`, `2026-05`, `2026-06`.
- A/R as-of date: `2026-06-30`.
- Quarter tag in API: `2026-Q2`.

### 3. Precision Rules
- Currency values: exactly 2 decimal places (`toFixed(2)`).
- Counts and risk scores: integers.
- Percentages: 1 decimal place (`toFixed(1)`).
- Probabilities: 1 or 2 decimal places as specified.

### 4. Risk Scoring Guidelines
- **Renewal proximity** is the strongest signal. Accounts with renewal dates in the past or within 60 days get highest priority.
- **NPS < 30** is a strong churn signal.
- **SLA compliance < 80%** indicates service degradation.
- **Product usage decline** (negative trend over Q2) is a warning sign.
- **Tenure < 18 months** correlates with higher churn.
- **Overdue receivables > $5,000** triggers collections action.
- **Lifecycle status `renewal_risk`** is an explicit flag.

### 5. ARR Source Selection
- Use `billing_arr_current` from the account object as the primary current ARR source.
- Do NOT use `crm_arr` unless explicitly instructed; `billing_arr_current` is the operative value.

### 6. Ticket Hygiene
- `clean_ticket_count` = total tickets excluding `is_spam` and `is_duplicate`.
- SLA compliance = (clean tickets with both `first_response_sla_met=true` AND `resolution_sla_met=true`) / total clean tickets.

### 7. Overdue Balance Calculation
- From A/R aging: `overdue_balance = 1_30 + 31_60 + 61_90 + 90_plus`.
- The `current` bucket is NOT overdue.

## Controlled Labels & Enums

### Risk Levels
- `critical`, `high`, `medium`, `low`

### Primary Actions
- `collections_followup` — when overdue_balance > $5,000
- `technical_recovery` — when risk is high AND (NPS < 30 OR SLA < 80)
- `renewal_save` — when risk is high AND renewal within 90 days
- `executive_qbr` — when moderate risk, needs escalation
- `nurture_monitor` — when low risk, no immediate action

### Reason Codes
- `renewal_window` — renewal date within 90 days or past due
- `nps_drop` — latest NPS < 30 (or significant drop)
- `sla_degradation` — SLA compliance < 80%
- `usage_decline` — product_usage trend negative
- `low_tenure_high_churn` — tenure < 18 months
- `overdue_receivable` — past due balance > $1,000
- `clean_billings` — no risk flags (fallback)

### Ticket Trend
- `improving`, `worsening`, `flat`

### Metric Sources
- `crm_closed_won`, `support_export`, `sla_report`, `nps_survey`, `billing_snapshot`, `ar_aging`, `pipeline_crm`, `event_dashboard`, `hr_report`

### Review Owner
- `customer_success`, `solutions_engineering`, `finance_ops`

### Agenda Topics
- `partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `technical_recovery`, `commercial_expansion`

## Output Structures

### Risk Account Object (train_001 / train_005)
```json
{
  "rank": 1,
  "account_id": "acct_...",
  "risk_score": 80,
  "risk_level": "critical",
  "primary_action": "collections_followup",
  "current_arr": 1425000.00,
  "latest_nps": 39,
  "clean_ticket_count": 14,
  "overdue_balance": 18509.64,
  "reason_codes": ["renewal_window", "nps_drop", "overdue_receivable"]
}
```

### QBR Metrics (train_002)
```json
{
  "qbr_metrics": [
    {
      "month": "2026-04",
      "revenue": 95756.67,
      "support_tickets": 4,
      "sla_compliance_pct": 95.2,
      "nps_score": 45
    }
  ],
  "highlights": {
    "average_revenue": 99807.39,
    "peak_revenue_month": "2026-06",
    "peak_revenue": 105156.27,
    "max_sla_month": "2026-06",
    "max_sla_pct": 95.4,
    "peak_nps_month": "2026-05",
    "peak_nps_score": 61,
    "ticket_trend": "improving"
  },
  "metric_sources": {
    "revenue": "crm_closed_won",
    "support_tickets": "support_export",
    "sla_compliance": "sla_report",
    "nps": "nps_survey"
  },
  "review_plan": {
    "review_owner": "customer_success",
    "review_due_date": "2026-07-22",
    "needs_technical_signoff": false
  },
  "agenda_topics": ["partnership_overview", "q2_metrics", "performance_highlights", "q3_initiatives"]
}
```

### Financial & Pipeline Summary (train_003)
```json
{
  "financial_summary": {
    "overdue_client_count": 49,
    "overdue_total": 275040.36,
    "linked_followup_count": 25,
    "unlinked_followup_count": 24
  },
  "pipeline_summary": {
    "won_count": 4,
    "won_revenue": 551179.17,
    "lost_count": 5,
    "open_count": 23,
    "open_pipeline": 2907757.96,
    "win_rate_pct": 44.4,
    "top_open_product_line": "AI Assist"
  }
}
```

### Model Validation & Risk Ranking (train_004)
```json
{
  "model_validation": {
    "training_rows": 180,
    "validation_rows": 60,
    "feature_count": 8,
    "accuracy_pct": 72.5,
    "accuracy_band": "70_to_79",
    "tenure_coefficient_direction": "negative"
  },
  "risk_ranking": [
    {
      "rank": 1,
      "customer_id": "acct_...",
      "predicted_churn_probability": 0.85,
      "outreach_action": "renewal_save",
      "reason_code": "renewal_window"
    }
  ],
  "cohort_checks": {
    "past_due_shortlist_count": 0,
    "low_tenure_shortlist_count": 1,
    "average_probability_top5": 0.78
  }
}
```

## Pitfalls

1. **A/R aging filter bug:** The `account_id` query param on `/api/finance/ar-aging` is ignored. Always filter client-side by `aging_id`.
2. **Opportunity filter bug:** Query params on `/api/opportunities` are ignored. Always filter client-side.
3. **Missing NPS:** Some months have `nps_score: null` in metrics; fall back to the NPS endpoint or use `0`.
4. **Expired renewals:** Accounts with `renewal_date` in the past are highest risk, not lowest.
5. **Tenure direction:** Shorter tenure = higher churn risk (`tenure_risk_direction: negative`).
6. **ARR source:** `billing_arr_current` from the account object is the operative ARR value, not `crm_arr`.
7. **Ticket counting:** Always exclude `is_spam` and `is_duplicate` tickets from counts.
8. **Currency precision:** Use `parseFloat(value.toFixed(2))` to avoid floating point artifacts.
9. **Policy codes:** Include the exact policy codes from the answer template; these act as hints to the expected business rules.

## Test-Time Notes
- Do NOT read or access files outside the solver attempt directory.
- The skill must be reusable for unseen test tasks with different account sets and date ranges.
