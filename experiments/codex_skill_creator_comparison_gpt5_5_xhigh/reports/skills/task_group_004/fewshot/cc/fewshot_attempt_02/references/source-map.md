# ApexCloud Source Map

This file summarizes the live sources that appear across the staged examples.

## Account-centric sources
- `/api/accounts` returns the account catalog.
- `/api/accounts/{account_id}` returns profile fields such as `account_id`, `display_name`, `legal_name`, `account_aliases`, `segment`, `region`, `lifecycle_status`, `renewal_date`, `contract_tenure_months`, `billing_arr_current`, `crm_arr`, `csm_owner`, and `product_plan`.
- `/api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM` returns monthly rows with `recognized_revenue`, `support_ticket_count`, `sla_compliance`, `nps_score`, `active_seats`, `product_usage`, and `survey_status`.
- `/api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` returns ticket rows with `created_date`, `severity`, `status`, `first_response_sla_met`, `resolution_sla_met`, `is_duplicate`, `is_spam`, and `product_area`.
- `/api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` returns NPS responses with `score` and `retracted`.

## Billing and receivables sources
- `/api/billing/snapshots` returns snapshot rows with `as_of`, `billing_arr`, `mrr`, `posted`, `legal_name`, `account_id`, and `source`.
- `/api/finance/ar-aging` returns aging rows with `customer_name`, `as_of`, `current`, `1_30`, `31_60`, `61_90`, and `90_plus`. Link them to CRM accounts through the account catalog rather than assuming every A/R row exposes an account_id.

## Commercial and ops sources
- `/api/opportunities` returns opportunity rows with `account_id`, `account_legal_name`, `amount`, `stage`, `state`, `close_date`, `created_date`, `product_line`, and `region`.
- `/api/hr/summary` returns quarter and region rows with `headcount`, `unpaid_claims_amount`, `unpaid_claims_count`, `attendance_rate`, `open_advances_amount`, and `open_advances_count`.
- `/api/events/performance` returns event rows with `event_id`, `quarter`, `event_orders`, `event_revenue`, `completed_orders`, `cancelled_orders`, `pending_orders`, `product_revenue`, and `refunded_orders`.

## Churn exports
- `/exports/churn/train.csv` and `/exports/churn/validation.csv` include the `Churn` label.
- `/exports/churn/candidates.csv` has the same feature columns without `Churn`.
- The common feature columns are `tenure`, `MonthlyCharges`, `TotalCharges`, `Contract`, `PaymentMethod`, `PaperlessBilling`, `Partner`, `Dependents`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `SupportTickets90d`, `NPSLast`, `UsageTrendPct`, `InvoicePastDue`, and `ActiveSeatRatio`.

## Calculation rules
- Use the billing snapshot at the prompt's as-of date for current ARR unless the prompt explicitly says otherwise.
- Treat overdue balance as `61_90 + 90_plus`.
- Treat clean ticket count as tickets where `is_duplicate == false` and `is_spam == false`.
- Treat SLA compliance as the percent of clean tickets where `first_response_sla_met == true`.
- Treat monthly revenue as `recognized_revenue`.
- Treat ticket trend as the direction of clean ticket volume from the first requested month to the last.
- Treat `arr_at_risk` as the sum of current ARR for the reported at-risk or actionable subset named by the summary field.
- Treat `net_revenue_exposure` as `arr_at_risk - open_expansion_pipeline` when both fields are present.
- Treat win rate as won divided by won plus lost, excluding open opportunities from the denominator.
- Treat the churn feature count as the number of feature columns excluding `customer_id` and `Churn`.
- When linking A/R to accounts, prefer `account_id`, then normalized legal names, then aliases.
