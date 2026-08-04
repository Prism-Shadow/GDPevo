# Deterministic precision rules

 Apply these rules to every numeric field in the output JSON. Use Python's built-in `round()` for consistency.

 ## Currency (USD)

 - **Precision**: 2 decimal places.
 - **Examples**: `1416439.47`, `0.00`, `8773.03`
 - **Fields**: `current_arr`, `overdue_balance`, `arr_at_risk`, `revenue`, `average_revenue`, `peak_revenue`, `overdue_total`, `won_revenue`, `open_pipeline`, `unpaid_claims_total`, `event_revenue`, `expansion_pipeline`, `net_revenue_exposure`, `last_invoice_amount`, and any other monetary field.

 ## Percentages

 - **Precision**: 1 decimal place.
 - **Examples**: `93.3`, `100.0`, `66.7`
 - **Fields**: `sla_compliance_pct`, `accuracy_pct`, `win_rate_pct`, `license_utilization_pct`, and any other percentage field.

 ## Counts

 - **Precision**: integer (0 decimal places).
 - **Examples**: `13`, `0`, `180`
 - **Fields**: `risk_score`, `clean_ticket_count`, `accounts_reviewed`, `critical_or_high_count`, `collections_count`, `technical_recovery_count`, `support_tickets`, `nps_score`, `overdue_client_count`, `linked_followup_count`, `unlinked_followup_count`, `won_count`, `lost_count`, `open_count`, `training_rows`, `validation_rows`, `feature_count`, `hr_headcount`, `event_orders`, `past_due_shortlist_count`, `low_tenure_shortlist_count`, `strategic_accounts`, `enterprise_accounts`, and any other count field.

 ## Churn probability

 - **Precision**: 3 decimal places (task-specific; apply only when the churn model task type is in use).
 - **Examples**: `0.102`, `0.039`, `0.001`
 - **Fields**: `predicted_churn_probability`, `average_probability_top5`.

 ## Rounding method

 Use Python's `round(x, n)` which rounds ties to the nearest even number (banker's rounding). This is deterministic and reproducible across runs.

 ## Null handling

 - Use `null` (JSON null, not the string "null") only for fields where the answer template explicitly shows `null` as a valid value (e.g., `nps_score: null`, `next_touch_due_date: null`, `account_id: null`).
 - For numeric fields that are genuinely unavailable, prefer `0` or `0.0` / `0.00` depending on the type, unless the template shows `null`.
