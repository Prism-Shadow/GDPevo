# apex-retention-ops — ApexCloud Retention Operations SOP

Executable skill for CRM retention-analytics tasks against the ApexCloud
Retention Operations API. Covers five task archetypes: renewal risk queue,
QBR metrics packet, receivables + pipeline operations review, churn model
validation + outreach ranking, and the high-touch retention operations board.

All conventions below were reverse-engineered from the live API schemas and
the train answer templates (self-evolution: no gold answers were used). Where
an exact policy value could not be confirmed, the field name + governing rule
are stated so a solver applies the right policy.

---

## 0. Environment

- Base URL: read `ENV_URL.txt` (a single remote URL; do NOT hard-code the
  `127.0.0.1:8074` shown inside some prompt bodies — that is a placeholder).
- Never call `/api/judge`.
- Always start with `GET /api/health` — it returns the authoritative row counts
  and confirms the service is live and which seed is active.

### Endpoint catalog

| Endpoint | Params | Returns |
|---|---|---|
| `GET /api/health` | — | service status + row counts |
| `GET /api/accounts` | — | `accounts[]` (44): profile + `crm_arr`, `billing_arr_current`, `contract_tenure_months`, `renewal_date`, `segment`, `region`, `lifecycle_status`, `legal_name`, `account_aliases` |
| `GET /api/accounts/<id>` | — | single account profile |
| `GET /api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM` | month range | monthly `metrics[]`: `month`, `quarter`, `recognized_revenue`, `support_ticket_count` (RAW, see §2), `sla_compliance`, `nps_score`, `product_usage`, `active_seats`, `survey_status` |
| `GET /api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | date range | `tickets[]`: `ticket_id`, `created_date`, `product_area`, `severity`, `status`, `first_response_sla_met`, `resolution_sla_met`, `is_spam`, `is_duplicate` |
| `GET /api/accounts/<id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | date range | `nps_responses[]`: `response_id`, `response_date`, `score`, `survey_channel`, `retracted` |
| `GET /api/billing/snapshots` | — | `snapshots[]` (176 = 44 accts × 4 quarters): `account_id`, `legal_name`, `as_of` (quarter-end YYYY-MM-DD), `billing_arr`, `mrr`, `posted`, `source` |
| `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` | as_of date | `ar_aging[]` (~49): `customer_name` (legal name, NO account_id), `as_of`, `quarter`, `region`, `current`, `1_30`, `31_60`, `61_90`, `90_plus` |
| `GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD&region=` | date range, optional region | `opportunities[]`: `opportunity_id`, `account_id`, `account_legal_name`, `amount`, `close_date`, `created_date`, `product_line`, `region`, `stage`, `state` |
| `GET /api/hr/summary?quarter=YYYY-Qn` | quarter (OMIT region for "all regions") | `hr_summary[]`: `quarter`, `region`, `headcount`, `attendance_rate`, `high_absence_employees`, `leave_liability_hours`, `open_advances_amount/count`, `unpaid_claims_amount/count` |
| `GET /api/events/performance?event=&quarter=` | event id, quarter | `event_performance[]`: `event_id`, `quarter`, `event_orders`, `completed_orders`, `cancelled_orders`, `pending_orders`, `refunded_orders`, `event_revenue`, `product_revenue` |
| `GET /exports/churn/train.csv` | — | 180 rows × 21 cols (incl `customer_id`, target `Churn`) |
| `GET /exports/churn/validation.csv` | — | 60 rows × 21 cols (incl target) |
| `GET /exports/churn/candidates.csv` | — | 44 rows × 20 cols (NO `Churn` column; `customer_id` == account_id) |
| `GET /exports/account_metric_extract.csv` | — | 528 rows (44 accts × 12 months): `recognized_revenue`, `clean_ticket_count`, `sla_compliance`, `nps_score`, `product_usage`, `active_seats` |

### Endpoint gotchas
- **HR "all regions":** omit the `region` param entirely. `region=all` returns
  an empty list. Each quarter has 4 regional rows (North America, EMEA, APAC,
  LATAM); aggregate by summing the rows for the quarter.
- **A/R aging has no `account_id`:** it only carries `customer_name` (a legal
  name). Linking to CRM is by exact legal-name match (§3).
- **Opportunities `region=all`/omitted:** returns all regions.

---

## 1. Precision & formatting (apply to every task)

- Currency: 2 decimals.
- Percentages: 1 decimal.
- Counts: integers.
- Risk scores: integers.
- Probabilities (churn): 3 decimals.
- Dates: `YYYY-MM-DD` (per-month keys use `YYYY-MM`).
- Rounding: round half-up at the final aggregated value, not per intermediate.
- Output: the task JSON only — no prose, no markdown. Match the answer
  template's top-level keys and field names exactly. Use the controlled enum
  values verbatim; never invent labels.

---

## 2. Data-hygiene rules (apply universally)

### 2a. ARR — use posted billing snapshots, NOT CRM ARR
- `crm_arr` on the account profile is **stale**; `billing_arr_current` is the
  latest (newest quarter-end) snapshot value and is **not** the as-of value.
- **`current_arr` (for any as-of date) = the billing snapshot whose `as_of`
  equals the assessment date AND `posted == true`.** All snapshots are posted.
  Quarter-end `as_of` values are `2026-03-31`, `2026-06-30`, `2026-09-30`,
  `2026-12-31`. For assessment `2026-06-30` use the snapshot with
  `as_of == 2026-06-30`; for `2026-09-30` use `as_of == 2026-09-30`.
- Per-account snapshot id pattern: `BILL-<account_id>-<YYYY>-Q<n>`.
- `arr_source_code` convention = "ARR is sourced from posted billing snapshots
  as of the assessment date; CRM account ARR is treated as stale."

### 2b. Support tickets — clean before counting
- A ticket is **clean** iff `is_spam == false` AND `is_duplicate == false` AND
  `status != "cancelled"`. Exclude spam, duplicate, and cancelled rows.
- IMPORTANT nuance: the `/metrics` endpoint's `support_ticket_count` is the
  **RAW** monthly count (includes duplicates/spam). The
  `account_metric_extract.csv` `clean_ticket_count` is the **CLEAN** monthly
  count. For any reported ticket total/per-month, use the **clean** count.
- Canonical recipe: pull `/api/accounts/<id>/tickets?start&end` for the window,
  filter to clean rows, then aggregate (per-month for QBR; total over window
  for the risk-queue `clean_ticket_count` field). The extract CSV is a
  pre-cleaned convenience that matches this.
- `support_hygiene_code` convention = "exclude spam, duplicate, and cancelled
  tickets before counting."

### 2c. NPS — ignore retracted responses
- A response is valid iff `retracted == false`. Treat `retracted == true` as
  an invalid/retracted response and drop it.
- `latest_nps` (over a window) = the `score` of the most recent (max
  `response_date`) **non-retracted** response in the window.
- Monthly `nps_score` (from `/metrics` / extract) already reflects valid
  responses per month and is safe to use per-month.

### 2d. Receivables — overdue = 61–90 + 90+ buckets
- `overdue_balance = ar_aging["61_90"] + ar_aging["90_plus"]`.
- The `current`, `1_30`, and `31_60` buckets are **not** overdue.
- A customer is an "overdue client" iff `overdue_balance > 0` (i.e. either
  older bucket is non-zero).
- `overdue_total` = Σ `overdue_balance` across all overdue clients.

### 2e. CRM match — exact legal name only
- `ar_aging.customer_name` links to a CRM account iff it **exactly equals**
  the account's `legal_name`. Set `link_status="linked"` and `account_id` to
  the matched id; otherwise `link_status="unlinked"` and `account_id=null`.
- Do **not** link subsidiaries, aliases, or regional variants. Examples of
  NON-matches (must be unlinked): a name containing "Subsidiary", a hyphen/
  space variant ("North Star" vs "Northstar"), a country suffix variant
  ("...Services Canada" vs "...Services LLC"), or a "Foundation" variant.
- `crm_match_code` convention = "exact legal-name match only; subsidiaries and
  aliases are similar but not linked."

### 2f. Pipeline — window by close_date; stages vs outcomes
- Window opportunities by `close_date` within the analysis date range.
- **Outcomes** (terminal, `state=="closed"`): `Closed Won`, `Closed Lost`.
- **Open** (`state=="open"`): `Discovery`, `Prospecting`, `Proposal`,
  `Negotiation` (any stage that is not Closed Won / Closed Lost).
- `won_count` / `won_revenue` = Closed Won opps in window (count / Σ amount).
- `lost_count` = Closed Lost opps in window.
- `open_count` / `open_pipeline` = open opps in window (count / Σ amount).
- `win_rate_pct = 100 * won_count / (won_count + lost_count)` (1dp; 0.0 if
  denominator is 0).
- `top_open_product_line` = product line with the largest Σ open `amount`.
- Per-account `expansion_pipeline` = Σ `amount` of open opps for that account
  with `close_date` in the window.
- `pipeline_window_code` convention = "opportunities are windowed by
  close_date; Closed Won and Closed Lost are outcomes, all other stages are
  open."

---

## 3. Retention-risk scoring & ranking (risk queue / board)

### 3a. Risk score (integer, 0–100) — inferred points model
The exact policy score is not provided in gold; derive it deterministically as
a 0–100 integer that increases with churn/retention risk. Use this additive
model, summing, then clipping to [0,100]:

| Signal (as-of assessment date, over the 3-month window) | Points |
|---|---|
| `overdue_balance > 0` (receivables overdue) | +25 |
| `renewal_date` within next 90 days of assessment date (renewal window) | +20 |
| `lifecycle_status` in {`renewal_risk`, `paused`} | +15 |
| latest non-retracted `nps_score` < 30 (detractor) | +15 |
| product usage trend negative over the window (`product_usage` slope < 0, or `UsageTrendPct < 0`) | +15 |
| SLA degradation: window mean `sla_compliance` < 92, or rising clean-ticket count | +10 |
| low tenure: `contract_tenure_months` < 12 | +10 |
| open expansion pipeline present for the account | −10 (offsets risk) |

(Thresholds are inferred from the data distributions; the *direction* of each
contribution is the load-bearing part. Document the rule, recompute per
account.) Output `risk_score` as the rounded integer.

### 3b. Risk level bands (inferred)
- `critical`: score ≥ 60
- `high`: 40–59
- `medium`: 20–39
- `low`: < 20

### 3c. Ranking / board sort
Rank the shortlist by:
1. `risk_score` **descending**
2. `current_arr` **descending** (tie-break)
3. `account_id` **ascending** (final tie-break)

`board_sort_code` convention = "rank by risk_score desc, then current_arr
desc, then account_id asc."

### 3d. Net revenue exposure
- Per account: `net_exposure = current_arr + overdue_balance − expansion_pipeline` (clip at 0 minimum is not required; report raw).
- Segment `net_revenue_exposure` = Σ per-account `net_exposure` over the
  reviewed accounts (or over critical+high accounts; be consistent and state
  the scope). Recommended: Σ over all reviewed board accounts.
- `arr_at_risk` (segment) = Σ `current_arr` over accounts with risk_level in
  {critical, high}.
- `exposure_formula_code` convention = "net exposure = current_arr + overdue − open_expansion_pipeline."

---

## 4. Action / reason-code dictionaries (controlled enums)

### Reason codes (apply across risk queue, board, churn shortlist)
`overdue_receivable` | `low_tenure_high_churn` | `sla_degradation` | `nps_drop`
| `usage_decline` | `renewal_window` | `expansion_offset` | `clean_billings`

Assign reason codes (array for risk-queue/board; single primary for churn)
by checking signals in this priority order; attach every code whose signal
fires (risk-queue/board), or the first that fires (churn):
1. `overdue_receivable` — `overdue_balance > 0`
2. `low_tenure_high_churn` — `contract_tenure_months < 12`
3. `sla_degradation` — mean `sla_compliance < 92` over window
4. `nps_drop` — latest non-retracted NPS < 30, or NPS fell > 10 pts MoM
5. `usage_decline` — product-usage slope negative / `UsageTrendPct < 0`
6. `renewal_window` — `renewal_date` within 90 days of assessment
7. `expansion_offset` — open expansion pipeline > 0 (risk mitigated)
8. `clean_billings` — no receivables overdue and current bucket only (healthy)

### Primary actions (controlled enum)
`collections_followup` | `technical_recovery` | `renewal_save` |
`executive_qbr` | `nurture_monitor` | `no_action`

Action-mapping rule (first match wins), based on the account's top reason:
- `overdue_receivable` → `collections_followup`
- `sla_degradation` or `usage_decline` → `technical_recovery`
- `low_tenure_high_churn` or `renewal_window` or `nps_drop` → `renewal_save`
- high-ARR strategic/enterprise at critical risk without a more specific
  driver → `executive_qbr`
- `expansion_offset` or `clean_billings` (low risk) → `nurture_monitor`
- no signal / very low risk → `no_action`

`action_priority_code` convention = "map primary action from the dominant
risk reason in the priority order above."

### Follow-up calendar (per-action due dates)
When the task supplies explicit due dates per action (board tasks), emit them
verbatim in `followup_calendar` keyed by action. `calendar_policy_code`
convention = "each action has a deterministic follow-up due date supplied by
the task; echo as given."
- `collections_followup`, `technical_recovery`, `renewal_save`,
  `executive_qbr`, `nurture_monitor` — use the dates stated in the prompt.

---

## 5. Per-archetype SOPs

### 5A. Renewal Risk Queue (task 001 shape)
Top-level keys: `risk_accounts`, `portfolio_summary`, `model_checks`,
`policy_codes`.

1. For each of the prompt's account_ids, fetch profile, metrics (3 months),
   tickets (window), NPS (window), billing snapshot (as_of = assessment
   date), and ar-aging (as_of = assessment date).
2. Per account compute: `current_arr` (§2a), `overdue_balance` (§2d),
   `clean_ticket_count` = total clean tickets in window (§2b), `latest_nps`
   (§2c), plus risk score/level, primary_action, reason_codes (§3, §4).
3. `risk_accounts`: top 5 by the ranking rule (§3c). Each object: `rank`,
   `account_id`, `risk_score` (int), `risk_level`, `primary_action`,
   `current_arr` (2dp), `latest_nps` (int), `clean_ticket_count` (int),
   `overdue_balance` (2dp), `reason_codes` (array).
4. `portfolio_summary`: `accounts_reviewed` (full set size, e.g. 8),
   `critical_or_high_count`, `arr_at_risk` (2dp), `collections_count`
   (accounts whose primary_action == collections_followup),
   `technical_recovery_count`.
5. `model_checks`: `uses_billing_arr_source` = **true** (ARR from posted
   billing snapshots, §2a); `tenure_risk_direction` = **negative** (low
   tenure increases churn risk — consistent with the churn-model tenure
   coefficient, §7).
6. `policy_codes`: `risk_model_code`, `arr_source_code`,
   `support_hygiene_code`, `action_priority_code` (§8).

### 5B. QBR Metrics Packet (task 002 shape, single account)
Top-level keys: `qbr_metrics`, `highlights`, `metric_sources`, `review_plan`,
`agenda_topics`.

1. Fetch `/metrics?start&end` for the 3 months (and/or the extract CSV).
2. `qbr_metrics[]` one object per month: `month` (`YYYY-MM`),
   `revenue` = `recognized_revenue` (2dp), `support_tickets` = **clean**
   ticket count for that month (§2b), `sla_compliance_pct` = `sla_compliance`
   (1dp), `nps_score` = `nps_score` (int, null if no valid response that
   month).
3. `highlights`: `average_revenue` (mean of monthly revenue, 2dp),
   `peak_revenue_month` + `peak_revenue` (max monthly revenue),
   `max_sla_month` + `max_sla_pct` (max monthly sla_compliance, 1dp),
   `peak_nps_month` + `peak_nps_score` (max monthly nps_score),
   `ticket_trend` ∈ {`improving`,`worsening`,`flat`} from the slope of the
   monthly **clean** ticket counts (fewer tickets over time = `improving`;
   more = `worsening`; ~flat = `flat`).
4. `metric_sources` (provenance declaration, one enum each):
   `revenue` = `billing_snapshot`, `support_tickets` = `support_export`,
   `sla_compliance` = `sla_report`, `nps` = `nps_survey`.
5. `review_plan`: `review_owner` ∈ {`solutions_engineering`,`customer_success`,
   `finance_ops`} — default `customer_success` for a QBR (use
   `solutions_engineering` if SLA/technical risk dominates, `finance_ops` if
   receivables dominate); `review_due_date` (from prompt, e.g. 2026-07-22);
   `needs_technical_signoff` = true if mean `sla_compliance < 92` or
   technical-recovery driver, else false.
6. `agenda_topics`: exactly **four** ordered enums from
   {`partnership_overview`,`q2_metrics`,`performance_highlights`,
   `q3_initiatives`,`technical_recovery`,`commercial_expansion`}. Default
   deck: [`partnership_overview`, `q2_metrics`, `performance_highlights`,
   `q3_initiatives`]; swap in `technical_recovery` when SLA degraded, and/or
   `commercial_expansion` when the account has open expansion pipeline.
7. Precision: revenue 2dp, pct 1dp, counts int.

### 5C. Q3 Receivables & Pipeline Operations Review (task 003 shape)
Top-level keys: `financial_summary`, `pipeline_summary`, `overdue_followups`,
`ops_context`, `policy_codes`.

1. `GET /api/finance/ar-aging?as_of=2026-09-30`.
2. Overdue clients = records with `61_90 + 90_plus > 0` (§2d).
3. `GET /api/accounts`; build `legal_name → account_id` map.
4. For each overdue client, set `link_status` + `account_id` by exact
   legal-name match (§2e). `overdue_followups[]` object: `customer_name`,
   `link_status`, `account_id` (null if unlinked), `overdue_balance` (2dp),
   `due_date` (= the prompt's follow-up date, e.g. 2026-10-15),
   `primary_action` = `collections_followup`. **Sort by `customer_name`
   ascending.**
5. `financial_summary`: `overdue_client_count`, `overdue_total` (2dp),
   `linked_followup_count`, `unlinked_followup_count`.
6. `pipeline_summary` from `GET /api/opportunities?start=2026-07-01&end=2026-09-30`
   (§2f): `won_count`, `won_revenue` (2dp), `lost_count`, `open_count`,
   `open_pipeline` (2dp), `win_rate_pct` (1dp), `top_open_product_line`.
7. `ops_context`:
   - `hr_headcount` = Σ `headcount` across all regional rows for the quarter
     (call `/api/hr/summary?quarter=2026-Q3` **without** a region param; 4
     regions).
   - `unpaid_claims_total` = Σ `unpaid_claims_amount` across those rows (2dp).
   - `event_orders` = `event_orders` from
     `/api/events/performance?event=apex_connect&quarter=2026-Q3`.
   - `event_revenue` = `event_revenue` (2dp).
8. `policy_codes`: `receivable_trigger_code`, `crm_match_code`,
   `pipeline_window_code`, `followup_scope_code` (§8).
   - `receivable_trigger_code` convention = "overdue = 61_90 + 90_plus
     older aging buckets; current/1_30/31_60 are not overdue."
   - `followup_scope_code` convention = "every overdue client gets a
     collections_followup action with the prompt's due date; sort by
     customer_name asc."

### 5D. Churn Model Validation & Outreach Ranking (task 004 shape)
Top-level keys: `model_validation`, `risk_ranking`, `cohort_checks`,
`model_policy_codes`.

1. Download `train.csv`, `validation.csv`, `candidates.csv`.
2. **Structural fields (recompute from headers, do not hard-code):**
   - `training_rows` = row count of train.csv (**180**).
   - `validation_rows` = row count of validation.csv (**60**).
   - `feature_count` = (columns − `customer_id` − `Churn`) = **19**.
3. **Deterministic model recipe** (reproduce exactly):
   - Target `y = (Churn == "Yes")`.
   - Features = all columns except `customer_id` and `Churn` (19 features).
   - Numeric features: `tenure, MonthlyCharges, TotalCharges,
     SupportTickets90d, NPSLast, UsageTrendPct, ActiveSeatRatio`.
   - Categorical features: `Contract, PaymentMethod, PaperlessBilling,
     Partner, Dependents, OnlineSecurity, OnlineBackup, DeviceProtection,
     TechSupport, StreamingTV, StreamingMovies`.
   - Preprocessing: `ColumnTransformer` with `StandardScaler` on numeric +
     `OneHotEncoder(handle_unknown="ignore")` on categorical.
   - Estimator: `LogisticRegression(max_iter=3000, random_state=42)` with
     **default** `class_weight` (do NOT use `class_weight="balanced"` — it
     over-predicts positives and drops accuracy into the 70–79 band).
   - Fit on train, predict on validation.
4. `model_validation`:
   - `accuracy_pct` = validation accuracy ×100 (1dp).
   - `accuracy_band` ∈ {`below_70`,`70_to_79`,`80_to_89`,`90_plus`} from
     `accuracy_pct`. With the recipe above the band is **`90_plus`** (expected
     ~91.7%); if a solver's environment differs, recompute and report the
     band that results — the band is whatever the deterministic recipe
     produces.
   - `tenure_coefficient_direction` = sign of the fitted `tenure` coefficient
     on the standardized scale. With the recipe it is **`negative`** (low
     tenure → higher churn). Possible values: `negative`/`positive`/`zero`.
5. `risk_ranking` (top 5 of the prompt's candidate subset):
   - Enrich each candidate row (`customer_id` == account_id) with account
     context: `renewal_date` (renewal window), open expansion pipeline
     (`expansion_offset`), overdue balance (`overdue_receivable`), NPS
     (`nps_drop`), usage trend (`usage_decline` via `UsageTrendPct`).
   - `predicted_churn_probability` = `predict_proba`[:,1] (3dp).
   - Rank candidates by probability **descending**; take top 5. Tie-break:
     `customer_id` ascending.
   - Each object: `rank`, `customer_id`, `predicted_churn_probability` (3dp),
     `outreach_action` ∈ {`renewal_save`,`technical_recovery`,
     `collections_followup`,`nurture_monitor`}, `reason_code` (single, from
     §4 priority — first signal that fires).
   - `outreach_action` mapping = same as §4 (overdue→collections_followup;
     sla/usage→technical_recovery; low-tenure/renewal-window/nps→renewal_save;
     expansion_offset/clean→nurture_monitor).
6. `cohort_checks`:
   - `past_due_shortlist_count` = count of top-5 with `InvoicePastDue == "Yes"`.
   - `low_tenure_shortlist_count` = count of top-5 with `tenure < 12`
     (inferred threshold; the rule = "low tenure is a churn driver").
   - `average_probability_top5` = mean of the top-5 probabilities (3dp).
7. `model_policy_codes`: `model_protocol_code`, `probability_scale_code`,
   `deployment_rule_code`, `outreach_mapping_code` (§8).
   - `model_protocol_code` convention = "standardized logistic regression,
     default class_weight, random_state=42, reproducible."
   - `probability_scale_code` convention = "predict_proba churn class to 3dp."
   - `outreach_mapping_code` convention = "outreach action mapped from the
     dominant risk reason (collections/technical/renewal/nurture)."

### 5E. High-Touch Retention Operations Board (task 005 shape)
Top-level keys: `action_board`, `segment_summary`, `followup_calendar`,
`policy_codes`.

1. For each of the prompt's account_ids (return **all**, not just top N),
   compute §3 fields: `current_arr`, `overdue_balance`, `expansion_pipeline`
   (Σ open opp amounts in window per account), risk score/level,
   primary_action, reason_codes.
2. `action_board[]` (all accounts, ranked by §3c): `rank`, `account_id`,
   `risk_level`, `primary_action`, `current_arr` (2dp),
   `expansion_pipeline` (2dp), `overdue_balance` (2dp), `next_touch_due_date`
   (the due date for this account's `primary_action` from the prompt's
   per-action calendar), `reason_codes` (array).
3. `segment_summary`:
   - `strategic_accounts` = count of board accounts with `segment ==
     "Strategic"`.
   - `enterprise_accounts` = count with `segment == "Enterprise"`.
   - `arr_at_risk` = Σ `current_arr` over critical+high accounts (2dp).
   - `open_expansion_pipeline` = Σ `expansion_pipeline` over board accounts
     (2dp).
   - `net_revenue_exposure` = Σ (current_arr + overdue_balance −
     expansion_pipeline) over board accounts (2dp).
4. `followup_calendar`: echo the prompt's per-action due dates keyed by
   action (`collections_followup`, `technical_recovery`, `renewal_save`,
   `executive_qbr`, `nurture_monitor`).
5. `policy_codes`: `risk_model_code`, `arr_source_code`,
   `support_hygiene_code`, `action_priority_code`, `board_sort_code`,
   `exposure_formula_code`, `calendar_policy_code` (§8).

---

## 6. Reason-code quick-reference by data test

| Code | Fires when |
|---|---|
| `overdue_receivable` | ar_aging overdue (61_90+90_plus) > 0, or candidate `InvoicePastDue == "Yes"` |
| `low_tenure_high_churn` | `contract_tenure_months < 12` (or candidate `tenure < 12`) |
| `sla_degradation` | window mean `sla_compliance < 92`, or SLA-met rate degraded |
| `nps_drop` | latest non-retracted NPS < 30, or MoM NPS drop > 10 |
| `usage_decline` | product-usage slope < 0 over window, or `UsageTrendPct < 0` |
| `renewal_window` | `renewal_date` within 90 days after assessment date |
| `expansion_offset` | open expansion pipeline > 0 (risk mitigation) |
| `clean_billings` | no overdue, current bucket only — healthy |

---

## 7. Tenure risk direction (cross-task consistency)
- The churn logistic-regression `tenure` coefficient is **negative** (low
  tenure → higher churn probability). Report `tenure_coefficient_direction =
  negative` in the churn task, and `tenure_risk_direction = negative` in the
  risk-queue `model_checks`. Low tenure is a churn/risk driver everywhere.

---

## 8. Policy-code reference (inferred convention labels)

The answer templates show each `policy_codes` field as a pipe-joined candidate
code set (e.g. `"RS-2|RS-6|RS-9"`). These are convention reference strings:
emit the code(s) that correspond to the policy actually applied, using the
rule stated below for each field. The governing rule (not the literal code) is
what a solver must apply; codes below are the documented candidate sets.

**Task 001 / 005 (risk board):**
- `risk_model_code` (`RS-2|RS-6|RS-9`) — the retention-risk scoring model
  applied (§3a model: overdue + renewal-window + lifecycle + NPS + usage + SLA
  + tenure, expansion offset).
- `arr_source_code` (`REV-1|REV-4|REV-8`) — ARR sourced from posted billing
  snapshots as of the assessment date; CRM ARR is stale (§2a).
- `support_hygiene_code` (`SUP-3|SUP-8|SUP-9`) — exclude spam, duplicate,
  cancelled tickets before counting (§2b).
- `action_priority_code` (`ACT-1|ACT-5|ACT-7`) — primary action mapped from
  the dominant risk reason in priority order (§4).
- `board_sort_code` (`BORD-1|BORD-4|BORD-8`) — rank by risk_score desc, then
  current_arr desc, then account_id asc (§3c).
- `exposure_formula_code` (`EXP-2|EXP-6|EXP-9`) — net exposure = current_arr +
  overdue − open_expansion_pipeline (§3d).
- `calendar_policy_code` (`CAL-3|CAL-5|CAL-7`) — per-action deterministic
  follow-up due dates supplied by the task (§4).

**Task 003 (receivables/pipeline):**
- `receivable_trigger_code` (`RCP-4|RCP-7|RCP-9`) — overdue = 61_90 + 90_plus
  older buckets (§2d).
- `crm_match_code` (`CM-2|CM-5|CM-8`) — exact legal-name match; subsidiaries/
  aliases not linked (§2e).
- `pipeline_window_code` (`PW-3|PW-6|PW-9`) — window by close_date; Closed
  Won/Lost are outcomes, other stages open (§2f).
- `followup_scope_code` (`FS-1|FS-4|FS-8`) — every overdue client gets a
  collections_followup action with the prompt's due date, sorted by
  customer_name asc (§5C).

**Task 004 (churn):**
- `model_protocol_code` (`MOD-2|MOD-7|MOD-9`) — standardized logistic
  regression, default class_weight, random_state=42 (§5D).
- `probability_scale_code` (`PRB-1|PRB-4|PRB-8`) — churn-class
  `predict_proba` to 3 decimals.
- `deployment_rule_code` (`DEP-3|DEP-5|DEP-9`) — rank candidates by predicted
  churn probability desc; take top 5.
- `outreach_mapping_code` (`OUT-2|OUT-6|OUT-8`) — outreach action mapped from
  dominant risk reason (§4).

> Note: the exact single-code selection within each set is not confirmable
> without gold answers. A solver should emit the code consistent with the
> stated rule; if the platform expects the full pipe-joined reference string
> verbatim, prefer echoing the template's reference string. The rule text is
> the authoritative specification.

---

## 9. Common pitfalls (do not do these)
- Using `crm_arr` or `billing_arr_current` instead of the snapshot whose
  `as_of` equals the assessment date.
- Using the raw `/metrics` `support_ticket_count` as a "clean" count (it
  includes duplicates/spam) — use the cleaned count.
- Linking ar-aging customers to CRM by alias/subsidiary/fuzzy match — use
  exact legal-name equality only.
- Including `current` / `1_30` / `31_60` in overdue — overdue is the two
  older buckets only.
- Passing `region=all` to HR (returns empty) — omit the param for all regions.
- Using `class_weight="balanced"` in the churn logistic regression (collapses
  accuracy to the 70–79 band) — use default class_weight.
- Windowing opportunities by `created_date` instead of `close_date`.
- Omitting the tie-breaks in board ranking (score, then current_arr, then
  account_id).
- Forgetting to drop retracted NPS responses when computing latest NPS.
