# ApexCloud Retention Operations — CRM Retention Analytics Skill

Self-evolved, transferable SOP for the ApexCloud Retention Operations API. Encodes endpoint schemas, data-hygiene rules, ARR-source selection, pipeline semantics, a deterministic renewal-risk scoring rubric, the reproducible churn-model recipe, ranking/precision rules, per-archetype output contracts, and inferred policy-code conventions. No gold answers are stored; every rule is derived from the live API and answer-template shapes so it generalizes to held-out task variants.

## 0. Environment & base URL

- Base URL lives in `scratch/skill_generation/self_attempt_03/ENV_URL.txt`. Read it at run time; the host/port may change between evals. (The file is JSON-encoded text; parse the URL with `json.loads` or strip quotes/escapes, e.g. `<remote-env-url>`.)
- Every task hardcodes `http://127.0.0.1:8074` in its prompt as a default — IGNORE that literal; always use the URL from `ENV_URL.txt`. If the prompt gives a different assessment date / month set / account list, those task-specific values override the examples here.
- Call with `curl`. Most endpoints wrap results in an object: `{"accounts":[...]}`, `{"metrics":[...]}`, `{"tickets":[...],"count":N}`, `{"nps_responses":[...],"count":N}`, `{"snapshots":[...]}`, `{"ar_aging":[...]}`, `{"opportunities":[...]}`, `{"count":N,"hr_summary":[...]}`, `{"count":N,"event_performance":[...]}`. Always index the wrapper key, not the top-level list.
- `/api/health` returns per-resource row counts (useful to sanity-check export sizes): accounts 44, billing_snapshots 176, ar_aging 196, opportunities 114, support_tickets 1595, nps_responses 451, hr_summary 16, event_performance 20, churn_train 180, churn_validation 60, churn_candidates 44, account_metric_extract 528.

## 1. Endpoint schema reference (verified)

### /api/accounts  and  /api/accounts/<account_id>
`{"accounts":[{account_id, legal_name, display_name, account_aliases[], segment, region, product_plan, lifecycle_status, csm_owner, renewal_date (YYYY-MM-DD), contract_tenure_months (int), crm_arr (STALE — do not use), billing_arr_current (year-end snapshot value — do not use for assessment-date ARR)}]}`
- `segment` ∈ {Strategic, Enterprise, Mid-Market, SMB}. `region` ∈ {North America, EMEA, APAC, LATAM}. `lifecycle_status` typically "active". `renewal_date` is the contract renewal date used for renewal-window scoring.

### /api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM
`{"metrics":[{account_id, month (YYYY-MM), quarter (YYYY-QN), recognized_revenue (currency), support_ticket_count (int), sla_compliance (pct, 0-100), nps_score (int or sentinel), survey_status (completed|missing|retracted), product_usage (pct), active_seats (int)}], "count":N}`
- This is the canonical monthly source for revenue, SLA, usage, seats. `nps_score` here is only trustworthy when `survey_status == "completed"`; for `missing`/`retracted` treat NPS as absent (null).
- `recognized_revenue` is monthly recognized revenue (currency). For a quarter, sum the 3 months; for average, divide by 3.

### /api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD
`{"tickets":[{ticket_id, account_id, created_date, status (closed|open|cancelled), severity (P1-P4), product_area, first_response_sla_met (bool), resolution_sla_met (bool), is_spam (bool), is_duplicate (bool)}], "count":N}`
- Hygiene fields: `is_spam`, `is_duplicate`, `status` (see §3).

### /api/accounts/<id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD
`{"nps_responses":[{response_id, account_id, response_date, score (int; valid 0-100, sentinels e.g. -8 appear), survey_channel (email|in_app|csm_call), retracted (bool)}], "count":N}`
- Hygiene: ignore `retracted == true` and any `score` outside [0,100] (§3). For "latest NPS" use the most recent valid response by `response_date` within the window.

### /api/billing/snapshots
`{"snapshots":[{snapshot_id, account_id, as_of (YYYY-MM-DD, quarter-end), billing_arr (currency), mrr (currency), legal_name, posted (bool), source ("billing_snapshot")}]}`
- 4 `as_of` values exist, one per quarter-end: 2026-03-31, 2026-06-30, 2026-09-30, 2026-12-31. All are `posted=true`.
- This is the AUTHORITATIVE ARR source (§3).

### /api/finance/ar-aging?as_of=YYYY-MM-DD
`{"ar_aging":[{aging_id, customer_name, as_of, quarter, region, current, 1_30, 31_60, 61_90, 90_plus}]}`
- `customer_name` corresponds to a billing legal name (NOT always a CRM account — see CRM-match rule §3).
- `overdue_balance = 61_90 + 90_plus`. (current/1_30/31_60 are not overdue.)
- Filter by `as_of` exactly equal to the assessment date.

### /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD&region=...
`{"opportunities":[{opportunity_id, account_id, account_legal_name, region, stage, state (open|closed), amount (currency), close_date, created_date, product_line}]}`
- `stage` ∈ {Prospecting, Discovery, Proposal, Negotiation, Closed Won, Closed Lost}. `state` mirrors outcome.
- The `start`/`end` query window filters on `close_date`.
- `region` is optional; omit to get all regions (do not pass `region=all` — see HR pitfall; the opportunities endpoint returns all when region omitted).

### /api/hr/summary?quarter=YYYY-QN&region=<Region>
`{"count":N,"hr_summary":[{region, quarter, headcount, high_absence_employees, attendance_rate, leave_liability_hours, open_advances_count, open_advances_amount, unpaid_claims_count, unpaid_claims_amount}]}`
- `region=all` returns `{"count":0,"hr_summary":[]}`. For "all regions" you MUST query the 4 regions (North America, EMEA, APAC, LATAM) and SUM the numeric columns (headcount, unpaid_claims_amount, etc.).

### /api/events/performance?event=<id>&quarter=YYYY-QN
`{"count":N,"event_performance":[{event_id, quarter, event_orders, completed_orders, pending_orders, cancelled_orders, refunded_orders, event_revenue, product_revenue}]}`
- `event_orders` is total orders; `event_revenue` is total revenue. For ops_context use `event_orders` and `event_revenue`.

### Exports (CSV)
- `/exports/churn/train.csv` — 180 rows, 21 cols: `customer_id` + 19 features + `Churn` (target, Yes/No).
- `/exports/churn/validation.csv` — 60 rows, same 21 cols.
- `/exports/churn/candidates.csv` — 44 rows, 20 cols (`customer_id` + 19 features, NO `Churn`). `customer_id` equals the account_id (e.g. `acct_globex_north`).
- `/exports/account_metric_extract.csv` — 528 rows (44 accts × 12 months): `account_id, legal_name, segment, region, month, recognized_revenue, clean_ticket_count, sla_compliance, nps_score, product_usage, active_seats`. Bulk alternative to per-account `/metrics` (note: `clean_ticket_count` is pre-cleaned here).
- Churn feature schema: numeric = `tenure, MonthlyCharges, TotalCharges, SupportTickets90d, NPSLast, UsageTrendPct, ActiveSeatRatio`. categorical = `Contract (Month-to-month|One year|Two year), PaymentMethod (Bank transfer|Credit card|Electronic check|Mailed check), PaperlessBilling, Partner, Dependents, OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport, StreamingTV, StreamingMovies, InvoicePastDue` (all Yes/No).

## 2. Common parameters & date conventions

- Assessment date: the "as of" date (e.g. 2026-06-30). It drives: billing-snapshot `as_of` selection, AR `as_of`, and the end of the analysis window.
- Analysis period: a date range (e.g. 2026-04-01..2026-06-30) and a month list (e.g. 2026-04, 2026-05, 2026-06). Pass months to `/metrics?start=...&end=...` and dates to `/tickets`, `/nps`.
- Quarter labels: 2026-Q2 = Apr-Jun, 2026-Q3 = Jul-Sep. Billing snapshot `as_of` for Q2 = 2026-06-30, Q3 = 2026-09-30.
- Each task lists the exact `account_id`s to review — never review all accounts; filter strictly to the listed set.

## 3. Data-hygiene & source-selection rules (load-bearing)

1. **Clean support tickets** = exclude any ticket where `is_spam == true` OR `is_duplicate == true` OR `status == "cancelled"`. Keep `open` and `closed`. `clean_ticket_count` = count after exclusion. (P1/P2 severities are still "clean" — they are severity, not hygiene.)
2. **Valid NPS** = ignore responses where `retracted == true` OR `score` not in [0,100]. For per-month NPS from `/metrics`, only use `nps_score` when `survey_status == "completed"`; else null. For "latest NPS", take the most recent valid `/nps` response by `response_date` within the window. If none, the value is null/absent (template int may show 0; use 0 only as a placeholder when truly no data — prefer the actual latest valid score).
3. **ARR source = posted billing snapshot whose `as_of` equals the assessment date.** `account.billing_arr_current` is the year-end (2026-12-31) snapshot value and is WRONG for a mid-year assessment date. `account.crm_arr` is stale (e.g. Globex North: crm_arr 1,057,320 vs snapshot-as-of-2026-06-30 1,176,600.70 vs billing_arr_current 1,188,000). Always pull `/api/billing/snapshots`, filter `as_of == <assessment date>` and `posted == true`, and use `billing_arr`. This drives `uses_billing_arr_source = true` in model_checks.
4. **Overdue receivable** = `61_90 + 90_plus` from AR aging at the assessment `as_of`. `current`, `1_30`, `31_60` are NOT overdue. If an account has no AR row (not a debtor) overdue = 0.0.
5. **CRM match = exact `legal_name` match only.** AR `customer_name` is linked to a CRM account ONLY when it exactly equals an account's `legal_name` (→ `link_status: "linked"`, `account_id` set). Subsidiaries, aliases, and near-matches (e.g. "Globex North Subsidiary LLC", "Valence Payment Services Canada", "North Star Finance Services") are NOT linked → `link_status: "unlinked"`, `account_id: null`. Do not fuzzy-match against `account_aliases`.

## 4. Pipeline (opportunities) rules

1. Window = `close_date` within [start, end] (the `/api/opportunities?start&end` filter already applies this).
2. Outcomes: `stage == "Closed Won"` → won; `stage == "Closed Lost"` → lost; all other stages (Prospecting/Discovery/Proposal/Negotiation) → open. `state` corroborates ("open" vs "closed") but classify by `stage`.
3. `won_count`, `won_revenue` (sum amount of Closed Won), `lost_count`, `open_count`, `open_pipeline` (sum amount of open). `win_rate_pct = won_count / (won_count + lost_count) * 100`, 1 dp. (Open opportunities are excluded from the win-rate denominator.)
4. `top_open_product_line` = the product_line with the most open opportunities (count); tie-break by product_line name ascending.
5. Expansion pipeline per account (for retention boards) = sum of `amount` for that account's OPEN opportunities with `close_date` in the analysis window.

## 5. Renewal-risk scoring rubric (deterministic, integer 0-100)

Apply to each reviewed account. All inputs are fetched per §1-3 using the task's assessment date and analysis window.

`current_arr` = billing-snapshot `billing_arr` at the assessment `as_of`. `avg_sla` = mean of `sla_compliance` across the window months. `usage_delta` = last-month `product_usage` − first-month `product_usage` in the window. `latest_nps` = most recent valid NPS score in window. `nps_drop` = first valid − last valid NPS in window (positive = decline). `overdue` = 61_90+90_plus. `tenure` = `contract_tenure_months`. `renewal_days` = (renewal_date − assessment_date) in days (negative = lapsed).

| Component | Condition | Points |
|---|---|---|
| A. Renewal window (0-20) | renewal_days <= 30 (incl. lapsed) | 20 |
| | 31-60 | 15 |
| | 61-90 | 10 |
| | 91-180 | 4 |
| | >180 | 0 |
| B. Overdue receivable (0-20) | overdue > 0 | 20 |
| | overdue == 0 | 0 |
| C. NPS sentiment (0-15) | latest_nps < 30 | 15 |
| | 30 <= latest_nps < 50 | 8 |
| | else if nps_drop >= 15 (declined 15+) | 7 |
| | else | 0 |
| D. Support/SLA health (0-15) | avg_sla < 90 | 15 |
| | 90 <= avg_sla < 93 | 8 |
| | else | 0 |
| | + P1/P2 severity count >= 3 | +5 |
| | + clean_ticket_count >= 12 | +3 |
| | (cap D at 15) | |
| E. Usage trend (0-15) | usage_delta <= -5 | 15 |
| | -5 < usage_delta <= -2 | 8 |
| | -2 < usage_delta <= 0 | 3 |
| | usage_delta > 0 | 0 |
| F. Tenure (0-15) | tenure < 18 | 15 |
| | 18 <= tenure < 36 | 8 |
| | 36 <= tenure < 60 | 4 |
| | tenure >= 60 | 0 |

`risk_score` = round(A+B+C+D+E+F) to an integer (0-100).

**Risk level bands:** `>= 70` critical · `50-69` high · `30-49` medium · `< 30` low.

**Reason codes** — include every triggered flag:
- `overdue_receivable` — overdue > 0
- `low_tenure_high_churn` — tenure < 18
- `sla_degradation` — avg_sla < 90 OR P1/P2 count >= 3
- `nps_drop` — latest_nps < 30 OR nps_drop >= 15
- `usage_decline` — usage_delta <= -2
- `renewal_window` — renewal_days <= 90 (incl. lapsed)
- `expansion_offset` — account has open expansion pipeline in window (mitigating)
- `clean_billings` — overdue == 0 AND no other risk flags triggered

**Primary action** (first match wins, priority order):
1. `renewal_save` — renewal_days <= 30 (incl. lapsed)
2. `collections_followup` — overdue > 0
3. `technical_recovery` — avg_sla < 90 OR usage_delta <= -5 OR P1/P2 >= 3
4. `executive_qbr` — risk_level in {critical, high} AND segment in {Strategic, Enterprise}
5. `nurture_monitor` — risk_level == low
6. `no_action` — otherwise (clean billings, no flags)
(For the receivables task the overdue action is always `collections_followup`.)

**Ranking tie-break (load-bearing):** sort by `risk_score` DESC, then `current_arr` DESC, then `account_id` ASC. Return the top N requested (e.g. top 5). For full-boards, return all reviewed accounts in this order with rank 1..N.

## 6. Exposure formulas

- `arr_at_risk` = sum of `current_arr` over reviewed accounts whose `risk_level != low` (low-risk accounts are EXCLUDED from exposure).
- `open_expansion_pipeline` = sum of OPEN opportunity `amount` (close_date in window) for the reviewed accounts.
- `net_revenue_exposure` = `arr_at_risk` − `open_expansion_pipeline` (may be reduced by expansion; floor at 0 only if the task implies non-negative — otherwise report the signed difference).
- Receivables `overdue_total` = sum of `(61_90 + 90_plus)` over all overdue AR clients (linked + unlinked).

## 7. Churn model recipe (fully reproducible)

Goal (task 004): validate the churn exports and rank a candidate shortlist by predicted churn probability.

**Inputs:** `/exports/churn/train.csv` (180 rows), `/exports/churn/validation.csv` (60 rows), `/exports/churn/candidates.csv` (44 rows). Target = `Churn` (Yes/No). Features = all columns except `customer_id` and `Churn` → **19 features**.

**Preprocessing (sklearn `ColumnTransformer`):**
- numeric features `['tenure','MonthlyCharges','TotalCharges','SupportTickets90d','NPSLast','UsageTrendPct','ActiveSeatRatio']` → `StandardScaler()`.
- categorical features `['Contract','PaymentMethod','PaperlessBilling','Partner','Dependents','OnlineSecurity','OnlineBackup','DeviceProtection','TechSupport','StreamingTV','StreamingMovies','InvoicePastDue']` → `OneHotEncoder(drop='first', handle_unknown='ignore')`.
- Coerce numeric columns with `pd.to_numeric(errors='coerce')`; the shipped data has no NaNs in numeric columns, so no imputation is required (if a future variant introduces NaNs, impute with training-set median inside the pipeline).

**Model:** `LogisticRegression(C=1.0, solver='lbfgs', max_iter=1000)` inside a `Pipeline([('pre', ColumnTransformer), ('lr', LogisticRegression)])`. Fit on train. This is deterministic (no random_state needed for lbfgs).

**Verification (reproduced):** validation accuracy = **93.3%** (56/60) → `accuracy_band = "90_plus"`. Tenure coefficient ≈ −0.15 → `tenure_coefficient_direction = "negative"` (lower tenure ⇒ higher churn risk).

**Candidate ranking (task 004):** filter `candidates.csv` to the task's shortlist `customer_id`s, `predict_proba` the positive class, sort by probability DESC, return top 5. `predicted_churn_probability` = 3 decimals.

**Candidate outreach_action mapping** (first match, priority):
1. `InvoicePastDue == "Yes"` → `collections_followup` (reason `overdue_receivable`)
2. `tenure < 12` → `renewal_save` (reason `low_tenure_high_churn`)
3. `SupportTickets90d >= 5` or `NPSLast < 30` → `technical_recovery` (reason `sla_degradation` / `nps_drop`)
4. `UsageTrendPct < 0` → still `technical_recovery` (reason `usage_decline`) if not already mapped
5. otherwise `nurture_monitor` (reason `clean_billings`)

**cohort_checks:**
- `past_due_shortlist_count` = #shortlist candidates with `InvoicePastDue == "Yes"`.
- `low_tenure_shortlist_count` = #shortlist candidates with `tenure < 12`.
- `average_probability_top5` = mean of the 5 returned probabilities (3 decimals).

**deployment_rule_code** represents `approve_with_monitoring` (model meets the 90_plus accuracy bar and tenure coefficient is directionally correct, so deploy behind monitoring — not full auto-action).

Reproducible reference implementation:
```python
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
tr=pd.read_csv('train.csv'); va=pd.read_csv('validation.csv'); ca=pd.read_csv('candidates.csv')
num=['tenure','MonthlyCharges','TotalCharges','SupportTickets90d','NPSLast','UsageTrendPct','ActiveSeatRatio']
feat=[c for c in tr.columns if c not in ('customer_id','Churn')]
cat=[c for c in feat if c not in num]
for df in (tr,va,ca):
    for c in num: df[c]=pd.to_numeric(df[c],errors='coerce')
    for c in cat: df[c]=df[c].astype(str)
pre=ColumnTransformer([('num',StandardScaler(),num),
                       ('cat',OneHotEncoder(drop='first',handle_unknown='ignore'),cat)])
mdl=Pipeline([('pre',pre),('lr',LogisticRegression(C=1.0,solver='lbfgs',max_iter=1000))])
mdl.fit(tr[feat],(tr['Churn'].str.strip()=='Yes').astype(int))
pred=mdl.predict(va[feat]); acc=accuracy_score((va['Churn'].str.strip()=='Yes').astype(int),pred)
# acc -> 0.933 ; tenure coef (mdl.named_steps['lr'].coef_[0][feature_names=='num__tenure']) -> negative
sub=ca[ca['customer_id'].isin(SHORTLIST)].copy()
sub['p']=mdl.predict_proba(sub[feat])[:,1]
ranked=sub.sort_values('p',ascending=False).head(5)
```

## 8. Precision & output rules

- Currency: 2 decimals (float). Percentages: 1 decimal. Counts & scores: integers. Probabilities: 3 decimals.
- Dates: `YYYY-MM-DD` or `YYYY-MM` / `YYYY-QN` exactly as the task specifies.
- Return ONLY the JSON object matching the answer-template keys (plus the `policy_codes` block when present). Preserve key order and nesting. Use the controlled enum values verbatim (do not invent new enums).
- `null` is valid for NPS when no valid survey in window (QBR monthly `nps_score`) and for `account_id` on unlinked receivables.

## 9. Per-archetype output contracts (inferred from templates)

### Archetype A — Renewal Risk Queue (task 001)
```
risk_accounts[] (top 5): {rank, account_id, risk_score (int), risk_level, primary_action,
  current_arr (2dp), latest_nps (int), clean_ticket_count (int), overdue_balance (2dp), reason_codes[]}
portfolio_summary: {accounts_reviewed (int=N reviewed), critical_or_high_count (int, over reviewed set),
  arr_at_risk (2dp, excludes low-risk), collections_count (int, overdue>0), technical_recovery_count (int)}
model_checks: {uses_billing_arr_source: true, tenure_risk_direction: "negative"}
policy_codes: {risk_model_code, arr_source_code, support_hygiene_code, action_priority_code}
```
- `critical_or_high_count`, `arr_at_risk`, `collections_count`, `technical_recovery_count` are computed over the FULL reviewed set, not just the top-5 returned.

### Archetype B — QBR Metrics Packet (task 002)
```
qbr_metrics[] (one per month, 3 entries): {month (YYYY-MM), revenue (2dp, =recognized_revenue),
  support_tickets (int, =support_ticket_count from metrics), sla_compliance_pct (1dp, =sla_compliance),
  nps_score (int when survey_status completed else null)}
highlights: {average_revenue (2dp, mean of 3 months), peak_revenue_month, peak_revenue (2dp),
  max_sla_month, max_sla_pct (1dp), peak_nps_month, peak_nps_score (int or null), ticket_trend (improving|worsening|flat)}
metric_sources: {revenue, support_tickets, sla_compliance, nps} each = source enum
review_plan: {review_owner (solutions_engineering|customer_success|finance_ops), review_due_date, needs_technical_signoff (bool)}
agenda_topics[] exactly 4 ordered from: partnership_overview, q2_metrics, performance_highlights,
  q3_initiatives, technical_recovery, commercial_expansion
```
- `ticket_trend`: compare support_tickets across the 3 months (last vs first): last < first → `improving`; last > first → `worsening`; equal → `flat`.
- Source enum vocabulary: `crm_closed_won, support_export, sla_report, nps_survey, billing_snapshot, ar_aging, pipeline_crm, event_dashboard, hr_report`. Map each metric to the source it came from: revenue→`billing_snapshot` (or recognized_revenue from metrics which derives from billing), support_tickets→`support_export`, sla→`sla_report`, nps→`nps_survey`.
- `review_owner`: choose by dominant risk theme — finance/overdue issues → `finance_ops`; technical/SLA issues → `solutions_engineering`; otherwise `customer_success`.
- `review_due_date`: use the value in the prompt/template (e.g. 2026-07-22 = assessment + ~3 weeks).
- `needs_technical_signoff`: true if SLA degradation or usage decline is present; else false.

### Archetype C — Receivables & Pipeline Ops Review (task 003)
```
financial_summary: {overdue_client_count (int, #AR clients with 61_90+90_plus>0),
  overdue_total (2dp, sum of overdue across all overdue clients), linked_followup_count (int),
  unlinked_followup_count (int)}
pipeline_summary: {won_count, won_revenue (2dp), lost_count, open_count, open_pipeline (2dp),
  win_rate_pct (1dp), top_open_product_line (str)}
overdue_followups[] sorted by customer_name ASC: {customer_name, link_status (linked|unlinked),
  account_id (str or null), overdue_balance (2dp, =61_90+90_plus), due_date (from prompt), primary_action ("collections_followup")}
ops_context: {hr_headcount (int, sum of 4 regions), unpaid_claims_total (2dp, sum of unpaid_claims_amount over 4 regions),
  event_orders (int), event_revenue (2dp)}
policy_codes: {receivable_trigger_code, crm_match_code, pipeline_window_code, followup_scope_code}
```
- HR "all regions": query the 4 regions separately and sum `headcount` and `unpaid_claims_amount` (`region=all` returns empty).
- Event: `/api/events/performance?event=apex_connect&quarter=2026-Q3` → `event_orders`, `event_revenue`.
- `overdue_client_count`, `overdue_total`, and the followup counts cover ALL overdue AR clients (linked + unlinked). `linked_followup_count` = # with exact legal-name match; `unlinked_followup_count` = the rest.

### Archetype D — Churn Model Validation & Outreach Ranking (task 004)
```
model_validation: {training_rows: 180, validation_rows: 60, feature_count: 19, accuracy_pct: 93.3,
  accuracy_band: "90_plus", tenure_coefficient_direction: "negative"}
risk_ranking[] (top 5): {rank, customer_id, predicted_churn_probability (3dp), outreach_action, reason_code}
cohort_checks: {past_due_shortlist_count (int), low_tenure_shortlist_count (int), average_probability_top5 (3dp)}
model_policy_codes: {model_protocol_code, probability_scale_code, deployment_rule_code, outreach_mapping_code}
```

### Archetype E — High-Touch Retention Operations Board (task 005)
```
action_board[] (all reviewed, ranked): {rank, account_id, risk_level, primary_action, current_arr (2dp),
  expansion_pipeline (2dp, open opp amount in window for that account), overdue_balance (2dp),
  next_touch_due_date (from followup_calendar by the account's primary_action), reason_codes[]}
segment_summary: {strategic_accounts (int, #Strategic in reviewed set), enterprise_accounts (int, #Enterprise),
  arr_at_risk (2dp, excludes low-risk), open_expansion_pipeline (2dp, sum over reviewed),
  net_revenue_exposure (2dp, = arr_at_risk - open_expansion_pipeline)}
followup_calendar: {collections_followup, technical_recovery, renewal_save, executive_qbr, nurture_monitor}
  each = the due date for that action (from the prompt's per-action dates)
policy_codes: {risk_model_code, arr_source_code, support_hygiene_code, action_priority_code,
  board_sort_code, exposure_formula_code, calendar_policy_code}
```
- `next_touch_due_date` per account = `followup_calendar[<the account's primary_action>]`.
- The board includes ALL reviewed accounts (not just top 5), ranked 1..N.

## 10. Policy-code conventions (inferred; no gold)

Each `*_code` field is a pipe-joined string of the code(s) for the rules that apply to that task (`PREFIX-N`, e.g. `RS-2|RS-6|RS-9`). Codes are domain-prefixed; the number identifies a specific rule. Select the codes whose rules match the methodology you applied and join with `|` (keep order stable: ascending by number). Inferred registry:

**risk_model_code (RS-)** — risk scoring rules:
- `RS-2` = score from additive weighted components (renewal + overdue + NPS + support + usage + tenure), 0-100.
- `RS-6` = risk_level banding from score (>=70 critical, 50-69 high, 30-49 medium, <30 low).
- `RS-9` = ranking tie-break (score desc, current_arr desc, account_id asc).

**arr_source_code (REV-)** — ARR source selection:
- `REV-1` = use posted billing snapshot as authoritative ARR.
- `REV-4` = select snapshot whose as_of == assessment date (not billing_arr_current year-end).
- `REV-8` = crm_arr is stale and excluded from ARR.

**support_hygiene_code (SUP-)** — ticket hygiene:
- `SUP-3` = exclude is_spam and is_duplicate tickets.
- `SUP-8` = exclude status=cancelled tickets.
- `SUP-9` = P1/P2 severity counts toward technical-recovery risk (not hygiene exclusion).

**action_priority_code (ACT-)** — action priority:
- `ACT-1` = renewal_save first when renewal imminent (<=30d/lapsed).
- `ACT-5` = collections_followup when overdue>0.
- `ACT-7` = executive_qbr for high/critical Strategic/Enterprise; nurture_monitor for low.

**board_sort_code (BORD-)** — board ordering (archetype E):
- `BORD-1` = full board ranked by risk score then current_arr then account_id.
- `BORD-4` = next_touch_due_date derived per-action from followup_calendar.
- `BORD-8` = segment_summary counts Strategic/Enterprise; exposure excludes low-risk.

**exposure_formula_code (EXP-)** — exposure math:
- `EXP-2` = arr_at_risk excludes low-risk accounts.
- `EXP-6` = open_expansion_pipeline from open opps in close_date window.
- `EXP-9` = net_revenue_exposure = arr_at_risk - open_expansion_pipeline.

**calendar_policy_code (CAL-)** — followup calendar:
- `CAL-3` = per-action due dates sourced from prompt.
- `CAL-5` = each account's next_touch_due_date = calendar[primary_action].
- `CAL-7` = deterministic date assignment (no scheduling heuristics).

**receivable_trigger_code (RCP-)**:
- `RCP-4` = overdue trigger = 61_90 + 90_plus > 0 (older buckets only).
- `RCP-7` = overdue_balance reported at 2dp.
- `RCP-9` = followup due date uniform per prompt (e.g. 2026-10-15).

**crm_match_code (CM-)**:
- `CM-2` = link by exact legal_name equality only.
- `CM-5` = subsidiaries/aliases/near-matches are unlinked (account_id null).
- `CM-8` = linked vs unlinked counts reported separately.

**pipeline_window_code (PW-)**:
- `PW-3` = window filters on close_date.
- `PW-6` = outcomes by stage (Closed Won/Lost; others open).
- `PW-9` = win_rate = won/(won+lost); open excluded from denominator.

**followup_scope_code (FS-)**:
- `FS-1` = all overdue AR clients followed up (linked + unlinked).
- `FS-4` = overdue_followups sorted by customer_name asc.
- `FS-8` = primary_action for receivables = collections_followup.

**model_protocol_code (MOD-)**:
- `MOD-2` = LogisticRegression(C=1.0, lbfgs) + StandardScaler + OneHotEncoder(drop='first').
- `MOD-7` = train on churn_train (180), validate on churn_validation (60), 19 features.
- `MOD-9` = deterministic (no random_state); reproducible.

**probability_scale_code (PRB-)**:
- `PRB-1` = predict_proba positive class for ranking.
- `PRB-4` = rank by probability desc.
- `PRB-8` = report probability at 3 decimals.

**deployment_rule_code (DEP-)**:
- `DEP-3` = accuracy band 90_plus meets deployment threshold.
- `DEP-5` = tenure coefficient directionally correct (negative).
- `DEP-9` = deployment decision = approve_with_monitoring.

**outreach_mapping_code (OUT-)**:
- `OUT-2` = outreach_action mapped from candidate features (InvoicePastDue → collections, tenure → renewal_save, etc.).
- `OUT-6` = reason_code mapped from the same dominant feature.
- `OUT-8` = cohort_checks count past-due and low-tenure shortlist members.

## 11. Execution checklist (apply per task)

1. Read `ENV_URL.txt`; set BASE. Read the prompt for assessment date, analysis window/months, A/R as-of, region, account list, and any per-action due dates. Parse the answer template to lock the exact output keys and enums.
2. Fetch `/api/accounts` once; build `account_id -> account` and `legal_name -> account_id` maps. Fetch `/api/billing/snapshots` once; index by `(account_id, as_of==assessment_date)` for `current_arr`.
3. For each reviewed account: fetch `/metrics` (window months), `/tickets` (window dates), `/nps` (window dates). Fetch `/api/finance/ar-aging?as_of=<assessment>` once; map `legal_name -> overdue`.
4. Apply hygiene (§3): clean tickets (excl spam/dup/cancelled), valid NPS (excl retracted/out-of-range). Compute signals and the risk score (§5) for retention archetypes; compute exposure (§6) for boards.
5. For pipeline archetypes: fetch `/api/opportunities?start&end`; classify by stage (§4).
6. For receivables archetypes: enumerate overdue AR clients, exact-match to CRM legal_name (§3.5), sort by customer_name asc.
7. For HR "all regions": sum the 4 regional rows. For events: query the named event + quarter.
8. For the churn archetype: run the §7 recipe exactly; rank shortlist by probability desc, 3dp.
9. Round to required precision (§8). Assemble the JSON matching the template (§9), including the `policy_codes` block with the inferred codes for the rules applied (§10).
10. Sanity-check: `uses_billing_arr_source=true`, `tenure_risk_direction="negative"`, `feature_count=19`, `accuracy_band="90_plus"`, ranking tie-break = score desc / current_arr desc / account_id asc.

## 12. Pitfalls & gotchas

- Do NOT use `crm_arr` or `billing_arr_current` for assessment-date ARR — use the billing snapshot whose `as_of` equals the assessment date.
- `region=all` and `region=ALL` return empty for HR — always sum the 4 named regions (North America, EMEA, APAC, LATAM). URL-encode the space in "North America" (`North%20America`).
- CRM link is EXACT legal_name only; do not match aliases or subsidiaries.
- Overdue = `61_90 + 90_plus` only (not current/1_30/31_60).
- Win-rate denominator = won + lost (open excluded); classify outcomes by `stage`, corroborated by `state`.
- Clean tickets exclude `cancelled` status (open and closed both count as clean). Spam/duplicate flags are independent of status.
- NPS validity: exclude `retracted` AND out-of-range scores; metrics `nps_score` only when `survey_status == completed`.
- Churn model: keep `customer_id` out of features (it's an identifier); keep `Churn` out (it's the target). OneHotEncoder must use `drop='first'` and `handle_unknown='ignore'` to match the 93.3% result.
- `top_open_product_line` is by COUNT of open opps (not by revenue).
- Enum values are controlled — never invent new risk levels / actions / reason codes / source enums; use exactly the template vocabulary.
- The prompt's `http://127.0.0.1:8074` URL is a placeholder — always use the ENV_URL host.
