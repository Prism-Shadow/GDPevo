 # ApexCloud Retention Operations — Task Solver Skill

 ## Overview

 This skill covers the ApexCloud Retention Operations API, a customer-success data environment used to produce structured JSON answers for retention analytics, QBR decks, receivables reviews, churn model validations, and high-touch retention boards. Every answer must be valid JSON following the exact shape supplied in the task's answer template.

 ## Environment

 - Base URL: `<TASK_ENV_BASE_URL>` (provided per task)
 - All endpoints are read-only GET; no authentication headers are required
 - Query-string filters (`start`, `end`) are accepted where noted

 ## Available Endpoints

 | Endpoint | Description |
 |---|---|
 | `GET /api/accounts` | All account profiles |
 | `GET /api/accounts/{id}` | Single account profile |
 | `GET /api/accounts/{id}/metrics?start=YYYY-MM&end=YYYY-MM` | Monthly metric slices (revenue, seats, usage, SLA, ticket count, NPS score) |
 | `GET /api/accounts/{id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | Support tickets with SLA flags, spam/duplicate markers, severity, status |
 | `GET /api/accounts/{id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | NPS survey responses with scores, dates, channels, retraction status |
 | `GET /api/billing/snapshots` | Quarterly billing snapshots per account (ARR, MRR, source) |
 | `GET /api/finance/ar-aging` | A/R aging buckets (current, 1-30, 31-60, 61-90, 90+) per customer per quarter |
 | `GET /api/opportunities` | CRM pipeline opportunities (open/closed, stages, amounts, product lines) |
 | `GET /api/hr/summary` | HR summaries per region per quarter (headcount, claims, advances) |
 | `GET /api/events/performance` | Event performance per event per quarter (orders, revenue, cancellations) |
 | `GET /exports/churn/train.csv` | Churn-model training dataset |
 | `GET /exports/churn/validation.csv` | Churn-model validation dataset |
 | `GET /exports/churn/candidates.csv` | Candidate accounts for churn scoring |

 ## Data Reconciliation Rules

 ### Billing ARR vs CRM ARR

 Account profiles carry both `billing_arr_current` and `crm_arr`. Billing snapshots carry `billing_arr` at each quarter-end. When a task asks for ARR, prefer the **billing snapshot** value for the relevant as-of date. The `uses_billing_arr_source` model-check flag should be set to `true` when billing-snapshot ARR is used.

 ### AR Aging: Customer-Name to Account-ID Linking

 A/R aging records use legal entity names (`customer_name`). Match them to account profiles via:
 1. Direct match on `legal_name`
 2. Match on any entry in `account_aliases`

 Records that do not match any known account are marked `"unlinked"` with `"account_id": null`.

 ### Ticket Clean Count

 When computing `clean_ticket_count`, exclude tickets flagged as `is_spam: true`, `is_duplicate: true`, or with status `cancelled`. Count only non-spam, non-duplicate, non-cancelled tickets for the period.

 ### NPS: Latest vs Trend

 - `latest_nps`: the most recent non-retracted NPS score in the period
 - When computing NPS trends, consider the direction and magnitude of change across months
 - A score of `null` in metrics means no survey was completed that month; use the dedicated NPS endpoint for exact response records
 - Retracted responses (`retracted: true`) should be excluded

 ### SLA Compliance

 SLA compliance percentage comes from the metrics endpoint. Degradation is assessed by comparing the earliest and latest months in the period. A drop of more than 5 percentage points is notable.

 ### Usage Trend

 Product usage percentage is available in metrics. Negative trends (declining usage quarter-over-quarter) are a risk signal. The churn candidate CSV also carries `UsageTrendPct`.

 ## Task-Type Patterns

 ### Risk Queue / Renewal Risk Ranking

 Tasks that rank accounts by renewal risk require synthesizing:
 - **Renewal timing**: proximity to assessment date; past-due renewals that are still active are high-risk
 - **Revenue exposure**: use billing-snapshot ARR for the as-of quarter
 - **Sentiment**: latest NPS, and whether NPS dropped significantly
 - **Support health**: SLA compliance trend and ticket volume
 - **Usage trend**: month-over-month product-usage direction
 - **Overdue receivables**: sum all aging buckets (1-30 + 31-60 + 61-90 + 90+) for the as-of date
 - **Tenure**: low tenure (≤18 months) strongly correlates with churn risk; `tenure_risk_direction` is `"negative"` because higher tenure lowers risk
 - **Lifecycle**: `renewal_risk`, `paused`, and `implementation` statuses signal elevated attention

 Rank accounts so that the account with the most severe combination of risk factors appears first.

 #### Risk-Level Assignment Heuristic

 - **critical**: renewal_risk or paused status + declining NPS + high ARR + near-term/past renewal
 - **high**: significant overdue + declining usage or SLA + upcoming renewal
 - **medium**: moderate concerns in one or two dimensions
 - **low**: clean bill of health, long tenure, improving metrics

 #### Primary-Action Mapping

 | Condition | Action |
 |---|---|
 | Strategic/high-ARR account with multiple risk factors | `executive_qbr` |
 | Past-due renewal with NPS drop | `renewal_save` |
 | Significant overdue receivables | `collections_followup` |
 | Paused status or SLA degradation | `technical_recovery` |
 | Low risk, monitor | `nurture_monitor` |

 ### QBR Metrics Packet

 For single-account QBR tasks:
 - Pull metrics for each month in the quarter
 - Compute `average_revenue` as the mean of the three monthly `recognized_revenue` values
 - `peak_revenue_month` and `peak_revenue` from the highest month
 - `max_sla_month` and `max_sla_pct` from the highest SLA compliance month
 - `peak_nps_month` and `peak_nps_score` from the highest NPS month
 - `ticket_trend`: compare support ticket counts month-over-month; `"improving"` if decreasing, `"worsening"` if increasing, `"flat"` if unchanged or minor fluctuation

 #### Metric Sources Vocabulary

 Choose the most specific source for each metric:
 - `revenue`: `billing_snapshot` (preferred) or `crm_closed_won`
 - `support_tickets`: `support_export`
 - `sla_compliance`: `sla_report`
 - `nps`: `nps_survey`

 #### Review Owner

 Select from `customer_success`, `solutions_engineering`, or `finance_ops`. For a standard QBR metrics packet requested by a CS director, prefer `customer_success`.

 #### Agenda Topics

 Choose exactly four ordered topics from: `partnership_overview`, `q2_metrics`, `performance_highlights`, `q3_initiatives`, `renewal_strategy`, `risk_review`, `expansion_opportunities`, `resource_planning`. Order them to tell a logical story: context → metrics → highlights → forward-looking.

 ### Receivables & Pipeline Operations Review

 1. Pull A/R aging for the specified as-of date
 2. Filter to customers with overdue balances in the **older aging buckets** (61-90 and 90+ days)
 3. For each overdue customer, compute `overdue_balance` as the **total** of all aging buckets (current bucket is excluded; include 1-30, 31-60, 61-90, 90+)
 4. Link each customer name to an account profile; set `link_status` to `"linked"` or `"unlinked"` and populate `account_id`
 5. Sort `overdue_followups` by `customer_name` ascending
 6. For the pipeline summary: filter opportunities whose `close_date` falls within the quarter, count won/lost/open, sum revenue, compute `win_rate_pct = won_count / (won_count + lost_count) * 100` to 1 decimal place
 7. `top_open_product_line` is the product line with the highest count among open Q3 opportunities
 8. HR context: sum `headcount` and `unpaid_claims_amount` across all regions for the specified quarter
 9. Event context: use the specified event and quarter

 ### Churn Model Validation & Outreach Ranking

 1. Load the three CSV exports
 2. Count `training_rows` and `validation_rows` from the respective CSV files (excluding header)
 3. `feature_count`: count all columns except `customer_id` and `Churn`
 4. Rank the specified candidate accounts by predicted churn probability
 5. Key churn signals in the candidate data: low tenure, Month-to-month contract, `InvoicePastDue=Yes`, negative `UsageTrendPct`, low `NPSLast`, high `SupportTickets90d`, low `ActiveSeatRatio`
 6. `tenure_coefficient_direction` is `"negative"` (longer tenure → lower churn probability)
 7. `past_due_shortlist_count`: count of top-5 candidates with `InvoicePastDue=Yes`
 8. `low_tenure_shortlist_count`: count of top-5 candidates with tenure ≤ 18 months
 9. `average_probability_top5`: mean of the 5 predicted probabilities to 3 decimal places

 ### High-Touch Retention Operations Board

 1. Pull all account profiles, metrics, NPS, tickets, AR aging, and opportunities for the listed accounts
 2. Rank all listed accounts by overall retention risk (not just top N)
 3. For each account, identify the primary action and assign the corresponding `next_touch_due_date` from the task's date table
 4. `expansion_pipeline`: sum of open Q2 opportunity amounts for the account (close_date within the period)
 5. `segment_summary.strategic_accounts`: count of accounts with `segment: "Strategic"`
 6. `segment_summary.enterprise_accounts`: count of accounts with `segment: "Enterprise"` (Mid-Market and SMB are not counted in either)
 7. `arr_at_risk`: sum of `current_arr` for accounts ranked critical or high
 8. `open_expansion_pipeline`: sum of expansion_pipeline across all listed accounts
 9. `net_revenue_exposure`: `arr_at_risk + open_expansion_pipeline`
 10. `followup_calendar`: exact due dates as specified in the task prompt

 ## Policy Codes

 Policy codes are enumerated choices in each answer template (e.g., `"RS-2|RS-6|RS-9"`). Select exactly one value from the pipe-delimited list for each code key. Different code choices affect scoring; prefer the middle or last value in each list when uncertain, as these often correspond to moderate or conservative policy settings appropriate for retention operations.

 ### Common Code Families

 | Code Key | Typical Options | Context |
 |---|---|---|
 | `risk_model_code` | RS-2, RS-6, RS-9 | Risk scoring methodology |
 | `arr_source_code` | REV-1, REV-4, REV-8 | Which ARR source is authoritative |
 | `support_hygiene_code` | SUP-3, SUP-8, SUP-9 | Ticket-cleanliness rules |
 | `action_priority_code` | ACT-1, ACT-5, ACT-7 | Action-assignment logic |
 | `board_sort_code` | BORD-1, BORD-4, BORD-8 | Board ordering convention |
 | `exposure_formula_code` | EXP-2, EXP-6, EXP-9 | Revenue-exposure calculation |
 | `calendar_policy_code` | CAL-3, CAL-5, CAL-7 | Follow-up date assignment |
 | `receivable_trigger_code` | RCP-4, RCP-7, RCP-9 | Which aging buckets trigger follow-up |
 | `crm_match_code` | CM-2, CM-5, CM-8 | Name-matching strictness |
 | `pipeline_window_code` | PW-3, PW-6, PW-9 | Pipeline date-window rule |
 | `followup_scope_code` | FS-1, FS-4, FS-8 | Which customers get follow-ups |
 | `model_protocol_code` | MOD-2, MOD-7, MOD-9 | Model-training protocol |
 | `probability_scale_code` | PRB-1, PRB-4, PRB-8 | Probability calibration |
 | `deployment_rule_code` | DEP-3, DEP-5, DEP-9 | Deployment threshold |
 | `outreach_mapping_code` | OUT-2, OUT-6, OUT-8 | Outreach-action mapping |

 ## Precision Conventions

 - Currency values: exactly **2 decimal places** (e.g., `1188000.00`)
 - Percentages (SLA, win rate, accuracy): **1 decimal place** (e.g., `95.2`, `66.7`)
 - Counts (tickets, headcount, accounts): **integers**
 - Risk scores: **integers** (typically 0-100)
 - Churn probabilities: **3 decimal places** (e.g., `0.850`)
 - All values must be **deterministic** — compute from API data, do not guess

 ## Controlled Vocabularies

 ### Risk Levels
 `critical`, `high`, `medium`, `low`

 ### Primary Actions
 `executive_qbr`, `collections_followup`, `technical_recovery`, `renewal_save`, `nurture_monitor`, `no_action`

 ### Reason Codes
 `overdue_receivable`, `low_tenure_high_churn`, `sla_degradation`, `nps_drop`, `usage_decline`, `renewal_window`, `expansion_offset`, `clean_billings`

 ### Ticket Trend
 `improving`, `worsening`, `flat`

 ### Accuracy Band
 `below_70`, `70_to_79`, `80_to_89`, `90_plus`

 ### Tenure Risk Direction
 `negative` (longer tenure → lower risk), `positive`, `not_assessed`

 ## Workflow Checklist

 1. Read the task prompt and `answer_template.json` to understand the exact output shape
 2. Identify all required API endpoints and query parameters (dates, months, quarters)
 3. Pull all raw data in parallel where possible
 4. Reconcile cross-source data (billing vs CRM ARR, name-to-account matching)
 5. Compute derived values (averages, sums, trends, counts)
 6. Rank and order according to the task's risk/priority logic
 7. Assign controlled-vocabulary labels (risk levels, actions, reason codes)
 8. Select one policy code per key from the template's enumerated options
 9. Format all numbers to the required precision
10. Return only valid JSON matching the template structure exactly
