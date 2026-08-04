 # ApexCloud Retention Operations Skill

 ## Overview

 This skill provides the reusable operating rules for completing structured retention-operations tasks against the ApexCloud Retention Operations API. The API is hosted at a task-specific base URL provided through an environment variable. All endpoints are read-only GET requests returning JSON (or CSV for export paths). Tasks require querying multiple endpoints, cross-referencing data, and producing a deterministic JSON response that matches a supplied answer template.

 ## Task Execution Workflow

 Execute every task in this order:

 1. **Read the answer template.** The template file (typically at `input/payloads/answer_template.json`) defines the exact JSON shape, controlled enum values, and precision rules that the output must satisfy. Every key, array structure, and enum option in the template constrains the output.

 2. **Extract task parameters.** From the prompt identify: target account IDs, the assessment date, the analysis period (dates or months), the A/R as-of date, the quarter, any regional filters, and which endpoint families are mentioned or implied.

 3. **Plan the API call sequence.** Determine which endpoints to hit, in what order, and what query string parameters each needs. Prefer breadth-first: gather all account profiles, then enrich each with metrics, tickets, NPS, billing, and A/R aging in parallel where possible.

 4. **Execute API calls against `<TASK_ENV_BASE_URL>`.** Use the base URL from the environment variable appended with the endpoint path. Add query parameters for date filtering as specified below.

 5. **Compute derived fields.** Calculate risk scores, aggregates, win rates, averages, and other computed fields from raw API responses according to business logic described in the task.

 6. **Populate the answer JSON.** Fill every field in the template using API data and computed values. Use only the controlled enum values listed in the template or this skill. Select one value from each pipe-delimited policy code placeholder.

 7. **Validate precision.** Confirm all currency fields have exactly 2 decimal places, percentages have exactly 1 decimal place, counts and scores are integers, and churn probabilities (when applicable) have exactly 3 decimal places.

 8. **Return only the JSON object.** No markdown fences, no explanatory text — only the populated JSON.

 ## API Reference

 ### Base URL

 The API base URL is injected at `<TASK_ENV_BASE_URL>`. Read it from the environment as `$TASK_ENV_BASE_URL` or the equivalent variable name used in the task shell. Append the endpoint path directly (e.g., `${TASK_ENV_BASE_URL}/api/accounts`).

 ### Authentication

 No authentication headers are required. All endpoints are publicly accessible GET requests.

 ### Endpoints

 | Endpoint | Returns | Query Parameters |
 |---|---|---|
 | `GET /api/accounts` | All account profiles | none |
 | `GET /api/accounts/{account_id}` | Single account profile | none |
 | `GET /api/accounts/{account_id}/metrics` | Monthly usage metrics for one account | `?start=YYYY-MM&end=YYYY-MM` |
 | `GET /api/accounts/{account_id}/tickets` | Support tickets for one account | `?start=YYYY-MM-DD&end=YYYY-MM-DD` |
 | `GET /api/accounts/{account_id}/nps` | NPS survey responses for one account | `?start=YYYY-MM-DD&end=YYYY-MM-DD` |
 | `GET /api/accounts/{account_id}/billing` | Billing records for one account | none |
 | `GET /api/accounts/{account_id}/ar-aging` | A/R aging for one account | `?as_of=YYYY-MM-DD` |
 | `GET /api/billing/snapshots` | Billing snapshots across accounts | none |
 | `GET /api/finance/ar-aging` | Finance-level A/R aging across all accounts | `?as_of=YYYY-MM-DD` |
 | `GET /api/opportunities` | CRM pipeline opportunities | `?start=YYYY-MM-DD&end=YYYY-MM-DD` |
 | `GET /api/hr/summary` | HR headcount and claims | `?quarter=YYYY-QN` |
 | `GET /api/events/performance` | Event orders and revenue | `?event=event_name&quarter=YYYY-QN` or `?quarter=YYYY-QN` |

 ### Export Endpoints (CSV)

 | Endpoint | Returns |
 |---|---|
 | `GET /exports/churn/train.csv` | Churn model training data |
 | `GET /exports/churn/validation.csv` | Churn model validation data |
 | `GET /exports/churn/candidates.csv` | Candidate accounts for churn prediction |
 | `GET /exports/account_metric_extract.csv` | Account metric extract |

 ### Query Parameter Conventions

 - **Month range:** `?start=YYYY-MM&end=YYYY-MM` (inclusive)
 - **Date range:** `?start=YYYY-MM-DD&end=YYYY-MM-DD` (inclusive)
 - **A/R as-of:** `?as_of=YYYY-MM-DD`
 - **Quarter:** `?quarter=YYYY-QN` (e.g., `2026-Q2`)
 - **Event filter:** `?event=event_name&quarter=YYYY-QN`

 ## Data Model

 ### Account Profile (`/api/accounts`, `/api/accounts/{account_id}`)

 Each account object typically includes: `account_id`, `account_name` (or `legal_name`), `region`, `segment` (strategic, enterprise, mid_market, smb), `tenure_months`, `current_arr`, `renewal_date`, `lifecycle_stage`, and `csm_owner`.

 ### Account Metrics (`/api/accounts/{account_id}/metrics`)

 Monthly metrics objects with: `month` (YYYY-MM), `revenue`, `active_users`, `storage_gb`, `compute_hours`, `api_calls`, `sla_compliance_pct`.

 ### Support Tickets (`/api/accounts/{account_id}/tickets`)

 Ticket objects with: `ticket_id`, `created_date`, `resolved_date`, `severity` (P1-P4), `status` (open, resolved, closed), `category`, `sla_breach` (boolean).

 ### NPS (`/api/accounts/{account_id}/nps`)

 Survey objects with: `survey_date`, `nps_score` (integer 0-10), `respondent_role`, `comments`.

 ### Billing (`/api/accounts/{account_id}/billing`, `/api/billing/snapshots`)

 Billing records with: `month`, `billed_amount`, `paid_amount`, `outstanding`, `invoice_date`, `due_date`.

 ### A/R Aging (`/api/accounts/{account_id}/ar-aging`, `/api/finance/ar-aging`)

 Aging records with: `customer_name`, `account_id` (nullable), `current`, `aging_1_30`, `aging_31_60`, `aging_61_90`, `aging_90_plus`, `total_overdue`.

 ### Opportunities (`/api/opportunities`)

 Pipeline objects with: `opportunity_id`, `account_id`, `product_line`, `amount`, `stage`, `close_date`, `status` (won, lost, open).

 ### HR Summary (`/api/hr/summary`)

 Returns: `headcount`, `unpaid_claims_total`, plus supporting detail.

 ### Events (`/api/events/performance`)

 Returns: `orders`, `revenue`, plus event metadata.

 ### Churn Exports (CSV)

 The churn CSVs contain rows with features including tenure, usage metrics, support counts, NPS, billing data, and a `churned` label column (in train/validation sets). Parse CSV with a standard parser; treat the first row as headers.

 ## Controlled Vocabularies

 Use only these enum values when populating output fields. Do not invent new values. The answer template for each task will list the applicable subset; prefer values that appear in the template.

 ### Risk Levels

 `critical`, `high`, `medium`, `low`

 Sorting priority: critical first, then high, then medium, then low. Within the same level, sort by risk score descending.

 ### Primary Actions / Outreach Actions

 `executive_qbr` — Schedule an executive business review for high-value at-risk accounts.
 `collections_followup` — Pursue overdue receivables; used when overdue_balance is material.
 `technical_recovery` — Engage solutions engineering for accounts with SLA degradation or technical debt.
 `renewal_save` — Immediate intervention on accounts approaching renewal with negative signals.
 `nurture_monitor` — Watch and engage periodically; accounts with moderate or unclear risk.
 `no_action` — Account is healthy; no intervention needed.

 ### Reason Codes

 `overdue_receivable` — Account has material overdue balance in A/R aging.
 `low_tenure_high_churn` — Account tenure is below the churn-risk threshold identified in the model.
 `sla_degradation` — SLA compliance has dropped below acceptable threshold during the period.
 `nps_drop` — NPS score declined materially from prior periods or is negative.
 `usage_decline` — Product usage metrics (active users, compute, storage) show downward trend.
 `renewal_window` — Account renewal date falls within the near-term window (within 90 days of assessment).
 `expansion_offset` — Open expansion pipeline partially offsets risk; account has growth potential.
 `clean_billings` — Billing history is clean with no overdue amounts or payment issues.

 ### Metric Sources

 `crm_closed_won` — Revenue from CRM won opportunities.
 `support_export` — Support ticket counts from the ticketing system.
 `sla_report` — SLA compliance percentages from the SLA reporting module.
 `nps_survey` — NPS scores from survey responses.
 `billing_snapshot` — Revenue or billing data from billing snapshots.
 `ar_aging` — Receivables data from the A/R aging report.
 `pipeline_crm` — Pipeline data from CRM opportunities.
 `event_dashboard` — Event data from the events performance endpoint.
 `hr_report` — HR data from the HR summary endpoint.

 ### Ticket Trend

 `improving` — Ticket volume decreased over the period.
 `worsening` — Ticket volume increased over the period.
 `flat` — Ticket volume stayed within 10% of the starting value.

 ### Review Owner

 `solutions_engineering` — Technical signoff required.
 `customer_success` — CSM-led review.
 `finance_ops` — Finance and operations-led review.

 ### Agenda Topics

 `partnership_overview`, `q2_metrics`, `q3_metrics`, `performance_highlights`, `q3_initiatives`, `q4_initiatives`, `technical_deep_dive`, `expansion_strategy`, `risk_review`, `renewal_pipeline`, `collections_status`, `support_health`, `product_roadmap`, `executive_alignment`

 ### Accuracy Bands (Churn Model)

 `below_70`, `70_to_79`, `80_to_89`, `90_plus`

 ### Tenure Coefficient Direction

 `negative` — Longer tenure lowers churn probability.
 `positive` — Longer tenure raises churn probability.
 `zero` — Tenure has no detectable effect.
 `not_assessed` — Not evaluated (used outside churn model context).

 ### Link Status

 `linked` — A/R customer matched to a CRM account.
 `unlinked` — A/R customer not found in CRM accounts.

 ### Segment

 `strategic`, `enterprise`, `mid_market`, `smb`

 ## Precision Rules

 Apply these formatting rules to every output field:

 | Data Type | Format | Example |
 |---|---|---|
 | Currency (ARR, revenue, balances, pipeline) | 2 decimal places | `125000.00` |
 | Percentages (win rates, SLA, accuracy) | 1 decimal place | `87.3` |
 | Counts (tickets, accounts, headcount) | Integer | `42` |
 | Risk scores | Integer | `85` |
 | Churn probabilities | 3 decimal places | `0.734` |

 When computing aggregates:
 - Sum currency values with full precision before rounding to 2 decimals.
 - Compute percentages from raw counts, then round to 1 decimal.
 - Average churn probabilities from raw values, then round to 3 decimals.

 ## Business Logic Rules

 ### Risk Score Calculation

 Risk scoring should consider these factors, weighted by relevance to the task context:

 1. **Overdue receivables:** High overdue balance increases risk.
 2. **Tenure:** Low tenure (< 12 months) correlates with higher churn risk.
 3. **SLA health:** Degrading SLA compliance indicates technical dissatisfaction.
 4. **NPS trend:** Declining or negative NPS signals customer sentiment risk.
 5. **Usage trend:** Declining product usage (users, compute, storage) suggests disengagement.
 6. **Renewal proximity:** Accounts renewing within 90 days have elevated urgency.
 7. **Expansion pipeline:** Open expansion opportunities partially offset risk.

 ### ARR Sourcing

 When determining current ARR for an account:
 - Prefer the `current_arr` field from the account profile endpoint.
 - Fall back to the most recent billing snapshot amount.
 - If both are available, prefer the account profile value and set `uses_billing_arr_source` accordingly.

 ### Clean Ticket Count

 Count only tickets where `status` is `resolved` or `closed` during the analysis period. Exclude open tickets. Count each ticket once (by `ticket_id`).

 ### Churn Model Validation

 When validating churn exports:
 - `training_rows`: row count of train.csv (excluding header).
 - `validation_rows`: row count of validation.csv (excluding header).
 - `feature_count`: number of feature columns (exclude the label/target column and any ID column).
 - `accuracy_pct`: model accuracy computed from the validation set by comparing predicted vs actual labels. Use the training data to fit a simple logistic regression model and evaluate on the validation set. Round to 1 decimal.
 - `accuracy_band`: map accuracy_pct to the appropriate band.
 - `tenure_coefficient_direction`: examine the sign of the tenure feature's learned coefficient.

 For ranking candidates, use the fitted model to predict churn probability for each candidate row in candidates.csv, then sort descending and take the top 5.

 ### CRM-to-A/R Account Linking

 When reconciling finance A/R data with CRM accounts:
 - Match A/R `customer_name` to CRM `account_name` (or `legal_name`) using case-insensitive substring matching.
 - If a match is found, set `link_status` to `linked` and populate `account_id`.
 - If no match, set `link_status` to `unlinked` and leave `account_id` as null.

 ### Retention Board Order

 The standard retention board order sorts accounts by:
 1. Risk level (critical > high > medium > low)
 2. Within same level: overdue balance descending, then ARR descending
 3. Assign consecutive ranks starting at 1

 If the task says "return all accounts" include every specified account. If it says "top N" include only the first N.

 ### Net Revenue Exposure

 `net_revenue_exposure = arr_at_risk - open_expansion_pipeline`

 When expansion pipeline exceeds ARR at risk, net revenue exposure may be negative.

 ## Policy Codes

 Answer templates contain `policy_codes` objects with pipe-delimited placeholder values (e.g., `"RS-2|RS-6|RS-9"`). These represent code families; each task may require different codes. When populating:

 - Select exactly **one** code from each pipe-delimited group.
 - The selection should be informed by the API data and business logic applied in the task.
 - Common code families across tasks include:

 | Code Family | Prefix | Context |
 |---|---|---|
 | Risk model | `RS-` | Which risk-scoring methodology was applied |
 | ARR source | `REV-` | Which revenue data source was primary |
 | Support hygiene | `SUP-` | Which support metric was used |
 | Action priority | `ACT-` | Which action-prioritization rule was applied |
 | Receivable trigger | `RCP-` | Which A/R threshold triggered follow-up |
 | CRM match | `CM-` | Which matching strategy linked A/R to CRM |
 | Pipeline window | `PW-` | Which pipeline date window was used |
 | Followup scope | `FS-` | Which accounts were included in follow-ups |
 | Model protocol | `MOD-` | Which modeling approach was used |
 | Probability scale | `PRB-` | How probabilities were calibrated |
 | Deployment rule | `DEP-` | Which deployment rule was applied |
 | Outreach mapping | `OUT-` | How risk maps to outreach actions |
 | Board sort | `BORD-` | Which sort order the board uses |
 | Exposure formula | `EXP-` | How net revenue exposure is calculated |
 | Calendar policy | `CAL-` | Which follow-up calendar was applied |

 ## Sorting Conventions

 Follow the sorting instruction stated in the task prompt. Common conventions:

 - **Risk ranking:** By risk score descending (highest risk first).
 - **Customer name:** Alphabetical ascending (A-Z), case-insensitive.
 - **Churn probability:** Descending (highest probability first).
 - **Standard board order:** Risk level descending, then overdue balance descending, then ARR descending.
 - **Monthly metrics:** Chronological by month ascending.

 ## Error Handling

 - If an API endpoint returns a non-2xx status, retry once after a 500ms delay. If it still fails, use `0` or `null` for the affected fields and note the failure in an output note if the template has a notes or errors field; otherwise, proceed with zero values.
 - If an account_id in the task list does not appear in the API response, skip that account and adjust `accounts_reviewed` accordingly.
 - If a date-filtered endpoint returns an empty array, treat all metrics/counts for that account as zero for the period.

 ## Output Rules

 - Return **only** the populated JSON object.
 - Do not wrap the JSON in markdown code fences.
 - Do not include comments, explanations, or conversational text.
 - The JSON must be valid and parseable by a standard JSON parser.
 - All required keys from the answer template must be present, even if their values are zero or empty.
