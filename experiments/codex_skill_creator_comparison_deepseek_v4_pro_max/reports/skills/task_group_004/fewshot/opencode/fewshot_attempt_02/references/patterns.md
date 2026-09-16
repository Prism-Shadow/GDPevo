# Task Family Patterns

Each of the five task families follows a specific pipeline. Read the relevant section when the task prompt matches one of these patterns.

---

## 1. Renewal Risk Queue

**What it does:** Rank a set of accounts by renewal risk and produce a portfolio summary with risk signals, actions, and reason codes.

### Pipeline

1. **Pull account profiles** — Call `/api/accounts` (all) and filter to the specified account IDs. Keep `account_id`, `legal_name`, `region`, `segment`, `lifecycle_status`, `contract_tenure_months`, `renewal_date`, `billing_arr_current`, `crm_arr`.

2. **Pull billing snapshots** — Call `/api/billing/snapshots` (all). Filter to the specified account IDs and the assessment date (e.g. `as_of=2026-06-30`). The `billing_arr` from this snapshot is `current_arr`.

3. **Pull A/R aging** — Call `/api/finance/ar-aging` (all). Filter to the assessment quarter (e.g. `2026-Q2`). For each account, match `customer_name` to `legal_name` or `account_aliases`. Compute `overdue_balance = 61_90 + 90_plus`.

4. **Pull metrics** — For each account, call `/api/accounts/{id}/metrics?start=YYYY-MM&end=YYYY-MM`. Collect `recognized_revenue`, `sla_compliance`, `nps_score`, `product_usage` for each month.

5. **Pull tickets** — For each account, call `/api/accounts/{id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`. Compute `clean_ticket_count` by excluding spam, duplicates, and cancelled.

6. **Pull NPS** — For each account, call `/api/accounts/{id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`. Find the latest non-retracted response for `latest_nps`. Compare to prior NPS for drop detection.

7. **Compute risk signals** — For each account, determine which of the 8 reason codes apply (see vocabulary reference for trigger conditions).

8. **Score and rank** — Compute risk score using the `RS-6` model:
   - Start at 0.
   - Add 30 for `overdue_receivable`.
   - Add 25 for `nps_drop`.
   - Add 20 for `usage_decline`.
   - Add 15 for `sla_degradation`.
   - Add 10 for `low_tenure_high_churn`.
   - Add 10 for `renewal_window`.
   - Subtract 10 for `expansion_offset` (mitigating factor).
   - Subtract 5 for `clean_billings` (mitigating factor).
   - Cap at 100.
   - For accounts with both risk signals and mitigating factors, the score is the net of additions minus subtractions, floored at 0.

9. **Assign risk levels** — Based on the risk score bands.

10. **Assign primary actions** — Using the ACT-5 priority rules.

11. **Build portfolio summary** — Count accounts reviewed, critical+high count, sum ARR of critical+high accounts as `arr_at_risk`, count collections actions, count technical_recovery actions.

12. **Set model checks** — `uses_billing_arr_source: true` (because you used billing snapshots). `tenure_risk_direction`: check if lower-tenure accounts dominate the high-risk slots; set `"negative"` if they do, `"positive"` if higher-tenure dominates, `"not_assessed"` otherwise.

### Risk score worked example

An account with overdue_receivable (+30), nps_drop (+25), sla_degradation (+15), usage_decline (+20), renewal_window (+10), low_tenure (+10), and expansion_offset (-10): total = 100 (capped). Risk level = critical.

---

## 2. QBR Metrics Packet

**What it does:** Monthly metrics for one account with highlights, source attribution, review plan, and agenda.

### Pipeline

1. **Pull metrics** — Call `/api/accounts/{id}/metrics?start=YYYY-MM&end=YYYY-MM`. Each month becomes a `qbr_metrics` entry with `revenue` (from `recognized_revenue`), `support_tickets` (from the `/tickets` endpoint clean count), `sla_compliance_pct` (from `sla_compliance`), `nps_score` (from the `/nps` endpoint latest for that month, or from metrics `nps_score`).

2. **Pull tickets** — Call `/api/accounts/{id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD`. Count clean tickets per month by parsing `created_date`.

3. **Pull NPS** — Call `/api/accounts/{id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD`. Get the latest non-retracted score for each month. If a month has no NPS response, use the `nps_score` from metrics (which may be `null`).

4. **Compute highlights:**
   - `average_revenue`: mean of monthly revenue across the 3 months.
   - `peak_revenue_month` / `peak_revenue`: month with highest revenue.
   - `max_sla_month` / `max_sla_pct`: month with highest SLA compliance.
   - `peak_nps_month` / `peak_nps_score`: month with highest NPS score.
   - `ticket_trend`: compare first month to last month (improving if fewer, worsening if more, flat if same).

5. **Set metric sources:** All from the API endpoints used (see vocabulary).

6. **Set review plan:** `review_owner` based on the dominant signal (customer_success by default). `needs_technical_signoff: false` unless significant SLA issues exist.

7. **Set agenda topics:** Exactly 4 ordered topics. Default: `partnership_overview`, `q2_metrics`, `technical_recovery` (if SLA or usage issues), `q3_initiatives`. If no technical issues, replace `technical_recovery` with `commercial_expansion`.

---

## 3. Receivables and Pipeline Review

**What it does:** Cross-reference A/R aging with CRM accounts, summarize Q3 pipeline, and add HR/events context.

### Pipeline

1. **Pull A/R aging** — Call `/api/finance/ar-aging` (all). Filter to the target quarter. Keep records where `61_90 + 90_plus > 0` (overdue).

2. **Pull accounts** — Call `/api/accounts` (all). Build a lookup: for each account, collect `account_id`, `legal_name`, and `account_aliases`.

3. **Link A/R to accounts** — For each overdue A/R record, check if `customer_name` matches any account's `legal_name` exactly, or any entry in `account_aliases` (after stripping common suffixes like "LLC", "Inc.", "Ltd.", "PLC", "SA", "BV", "GmbH", "Pty Ltd.", "Pte. Ltd.", "KK"). If a match is found, set `link_status = "linked"` and `account_id` to the matched account ID. Otherwise, `link_status = "unlinked"` and `account_id = null`.

4. **Build financial summary** — Count total overdue clients, sum overdue balances, count linked and unlinked.

5. **Pull pipeline** — Call `/api/opportunities` (all). Filter to the target quarter's close dates. Count won (stage `Closed Won`), lost (`Closed Lost`), and open (everything else with `state = "open"`). Sum amounts. Compute win rate = won / (won + lost) as percentage to 1 decimal. Find the product line with the highest total open amount.

6. **Build overdue follow-ups** — For each overdue A/R record, create a follow-up entry with `customer_name`, `link_status`, `account_id`, `overdue_balance` (61_90 + 90_plus), `due_date` (from task prompt), `primary_action` (always `collections_followup` for receivables work). Sort by `customer_name` ascending.

7. **Pull HR context** — Call `/api/hr/summary` (all). Filter to the target quarter across all regions. Sum `headcount` and `unpaid_claims_amount`.

8. **Pull events context** — Call `/api/events/performance` (all). Filter to the specified event and quarter. Read `event_orders` and `event_revenue`.

9. **Set policy codes** — Use the defaults: `RCP-7`, `CM-5`, `PW-6` (for pipeline summary), `FS-4`.

---

## 4. Churn Model Validation and Outreach Ranking

**What it does:** Validate a churn model export, then rank candidates by predicted probability.

### Pipeline

1. **Pull and parse CSVs** — Download `/exports/churn/train.csv`, `/exports/churn/validation.csv`, `/exports/churn/candidates.csv`. Parse with a CSV reader.

2. **Model validation:**
   - `training_rows`: row count of train.csv (180).
   - `validation_rows`: row count of validation.csv (60).
   - `feature_count`: number of predictor columns (exclude `customer_id` and `Churn` from train/validation, or `customer_id` from candidates). That's 19 features: tenure, MonthlyCharges, TotalCharges, Contract, PaymentMethod, PaperlessBilling, Partner, Dependents, OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport, StreamingTV, StreamingMovies, SupportTickets90d, NPSLast, UsageTrendPct, InvoicePastDue, ActiveSeatRatio.
   - Train a logistic regression on train.csv predicting `Churn` from the 19 features. Evaluate accuracy on validation.csv.
   - `accuracy_pct`: percentage correct predictions on validation set, rounded to 1 decimal.
   - `accuracy_band`: based on accuracy_pct (see vocabulary).
   - `tenure_coefficient_direction`: extract the coefficient for `tenure` from the trained model. If negative → `"negative"`, if positive → `"positive"`, if zero/near-zero → `"zero"`.

3. **Score candidates:**
   - Filter candidates.csv to only the specified account IDs.
   - Use the trained model to predict churn probability for each.
   - Rank by descending probability, take top 5.

4. **Map outreach actions:**
   - For each ranked candidate, determine `outreach_action`:
     - If `InvoicePastDue == "Yes"` → `collections_followup`
     - Else if probability ≥ 0.030 → `renewal_save`
     - Else if probability ≥ 0.010 → `technical_recovery`
     - Else → `nurture_monitor`
   - Assign a single `reason_code`:
     - If `InvoicePastDue == "Yes"` → `overdue_receivable`
     - Else if tenure ≤ 24 → `low_tenure_high_churn`
     - Else → `clean_billings`

5. **Cohort checks:**
   - `past_due_shortlist_count`: count of top 5 where `InvoicePastDue == "Yes"`.
   - `low_tenure_shortlist_count`: count of top 5 where tenure ≤ 24.
   - `average_probability_top5`: mean of the top 5 predicted probabilities, rounded to 3 decimals.

6. **Set policy codes** — `MOD-7`, `PRB-4`, `DEP-5`, `OUT-2`.

### Important implementation note

The CSV exports use integer-encoded features (Contract, PaymentMethod, etc.) in the training data but use string values in the candidates CSV. You must encode string categorical features the same way before prediction. Verify the encoding by checking unique values in both train.csv and candidates.csv. The train.csv features are pre-encoded as integers; candidates.csv has string values like "Month-to-month", "Credit card", "Yes", "No", "No internet service" that need encoding.

The `Churn` column in train/validation is "Yes"/"No" strings.

---

## 5. High-Touch Retention Action Board

**What it does:** Full-board reconciliation of all accounts, ranked by risk with expansion pipeline and follow-up calendar.

### Pipeline

1. **Pull account profiles, billing snapshots, A/R aging, tickets, NPS, metrics** for each account — same as renewal risk queue pipeline steps 1-6.

2. **Pull opportunities** — Call `/api/opportunities` (all). For each account, sum `amount` for open opportunities (`state = "open"`) whose `close_date` falls within the analysis period. This is `expansion_pipeline`.

3. **Compute risk signals and score** — Same as renewal risk queue steps 7-8.

4. **Assign risk level, primary action, and next_touch_due_date:**
   - Use the due dates from the task prompt (mapped by action type).
   - For `no_action`, set `next_touch_due_date` to `null`.

5. **Sort the board** — By descending risk score (BORD-4).

6. **Build segment summary:**
   - `strategic_accounts`: count of accounts with `segment == "Strategic"`.
   - `enterprise_accounts`: count with `segment == "Enterprise"`. Mid-Market and SMB are not counted separately in the summary.
   - `arr_at_risk`: sum of ALL accounts' `current_arr` on the board (EXP-6).
   - `open_expansion_pipeline`: sum of all `expansion_pipeline` values.
   - `net_revenue_exposure`: `arr_at_risk` - `open_expansion_pipeline`.

7. **Set followup calendar** — From the task prompt's due dates.

8. **Set policy codes** — `RS-6`, `REV-4`, `SUP-8`, `ACT-5`, `BORD-4`, `EXP-6`, `CAL-5`.

### Example segment count breakdown

For the 8 accounts on a board, count Strategic and Enterprise segments from `/api/accounts`. Mid-Market and SMB accounts are not included in `strategic_accounts` or `enterprise_accounts`.
