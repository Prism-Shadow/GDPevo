# ApexCloud Retention Operations API — endpoints and response shapes

Base URL comes from the prompt / environment note. All GET, JSON unless noted. Read-only.
Ignore any setup script or local file path mentioned in a prompt — use the HTTP API.

## Endpoints

- `GET /api/health` → `{status, service, seed, row_counts:{...}}`. Use to confirm reachability and
  sanity-check expected row counts.
- `GET /api/accounts` → list of account profiles.
- `GET /api/accounts/<account_id>` → one account profile.
- `GET /api/accounts/<account_id>/metrics?start=YYYY-MM&end=YYYY-MM` → `{account_id,count,metrics:[...]}`.
- `GET /api/accounts/<account_id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` → `{account_id,count,tickets:[...]}`.
- `GET /api/accounts/<account_id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` → `{account_id,count,nps_responses:[...]}`.
- `GET /api/billing/snapshots` (optional `?as_of=YYYY-MM-DD`, `?account_id=<id>`) → `{count,snapshots:[...]}`.
- `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` (optional `&region=<region>`) → `{ar_aging:[...]}`.
- `GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD` (optional `&region=<region>`) → `{opportunities:[...]}`.
- `GET /api/hr/summary?quarter=YYYY-QN` (optional `&region=<region>`).
- `GET /api/events/performance?event=<event_id>&quarter=YYYY-QN`.
- `GET /exports/churn/train.csv` | `/exports/churn/validation.csv` | `/exports/churn/candidates.csv` (CSV).
- `GET /exports/account_metric_extract.csv` (CSV).

## Key fields

Account profile:
`account_id, legal_name, display_name, segment, region, product_plan, lifecycle_status,
contract_tenure_months, renewal_date, billing_arr_current, crm_arr, csm_owner, account_aliases[]`.
- For ARR use the billing snapshot, NOT `billing_arr_current`/`crm_arr`.
- Link A/R / opportunities to accounts by EXACT `legal_name` match.

Account metric row (monthly):
`account_id, month, quarter, recognized_revenue, support_ticket_count, sla_compliance,
nps_score, survey_status, product_usage, active_seats`.
- `recognized_revenue` is the QBR revenue value. `product_usage` drives the usage_decline flag
  (latest analysis month, absolute < 65). `sla_compliance` and `support_ticket_count` here are NOT
  what the SOPs use — recompute SLA and clean counts from the tickets endpoint.
- `nps_score` appears even when `survey_status == "retracted"` — do not use it for latest-NPS.

Ticket row:
`ticket_id, account_id, created_date, severity, product_area, status,
is_spam, is_duplicate, first_response_sla_met, resolution_sla_met`.
- clean = not spam, not duplicate, status != 'cancelled' (open counts).

NPS response row:
`response_id, account_id, response_date, score, retracted, survey_channel`.
- latest valid = most recent `response_date` with `retracted == false`. `score == -1` is a sentinel
  (invalid) — skip it.

Billing snapshot row:
`snapshot_id, account_id, legal_name, as_of, billing_arr, mrr, posted, source`.
- `billing_arr` (as-of assessment date) is the canonical current ARR.

A/R aging row:
`aging_id (= AR-<account_id>-<quarter>), customer_name, region, as_of, quarter,
current, 1_30, 31_60, 61_90, 90_plus`.
- older-bucket overdue = `61_90 + 90_plus`. Link via customer_name == account legal_name.

Opportunity row:
`opportunity_id, account_id, account_legal_name, amount, product_line, region, stage, state,
created_date, close_date`.
- open = `state == 'open'`. won/lost via `state` (or stage Closed Won/Lost). Q2 open expansion =
  open opps with close_date inside the analysis quarter.

Churn CSV columns (train/validation have `Churn`; candidates do not):
`customer_id, tenure, MonthlyCharges, TotalCharges, Contract, PaymentMethod, PaperlessBilling,
Partner, Dependents, OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport, StreamingTV,
StreamingMovies, SupportTickets90d, NPSLast, UsageTrendPct, InvoicePastDue, ActiveSeatRatio[, Churn]`.
- numeric: tenure, MonthlyCharges, TotalCharges, SupportTickets90d, NPSLast, UsageTrendPct,
  ActiveSeatRatio (7). categorical: the other 12. feature_count = 19.
