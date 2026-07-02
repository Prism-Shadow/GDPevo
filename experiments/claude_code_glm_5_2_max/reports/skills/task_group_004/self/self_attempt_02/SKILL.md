# ApexCloud Retention Operations — CRM Retention Analytics Skill

Self-evolved skill for the ApexCloud Retention Operations API. Covers the five
training archetypes: (1) renewal-risk queue, (2) QBR metrics packet,
(3) receivables + pipeline operations review, (4) churn-model validation +
outreach ranking, (5) high-touch retention action board. Conventions below are
inferred from live API data shapes and answer templates only — no gold answers.

Base URL is read from `ENV_URL.txt` (e.g. `<remote-env-url>`). Prompts
may reference `http://127.0.0.1:8074`; ALWAYS use the ENV_URL host, never the
127.0.0.1 placeholder.

---

## 0. Endpoint inventory & usage

| Endpoint | Returns | Key params / gotcha |
|---|---|---|
| `GET /api/health` | service liveness | use to confirm reachability |
| `GET /api/accounts` | `{accounts:[…], count}` (44 accounts) | list of all CRM accounts |
| `GET /api/accounts/<id>` | single account profile | authoritative for segment, region, tenure, renewal_date, legal_name, aliases, lifecycle_status |
| `GET /api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM` | monthly metrics: recognized_revenue, sla_compliance, support_ticket_count, nps_score, product_usage, active_seats, survey_status | `survey_status` ∈ {completed, missing, retracted} |
| `GET /api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | support tickets with spam/duplicate/cancelled flags | filter window is on created_date |
| `GET /api/accounts/<id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | NPS responses with `retracted` flag + score | filter window on response_date |
| `GET /api/billing/snapshots` | `{snapshots:[…], count}` quarterly posted ARR/MRR | one snapshot per account per quarter (as_of 03-31/06-30/09-30/12-31) |
| `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` | `{ar_aging:[…], count}` customer aging buckets | keyed by `customer_name` (= legal entity), NOT account_id |
| `GET /api/opportunities?start&end&region` | CRM opps | start/end filter on **close_date** (not created_date) |
| `GET /api/hr/summary?quarter&region` | HR ops summary per region | **`region=all` returns 0 rows — OMIT region to get all regions** |
| `GET /api/events/performance?event&quarter` | event order/revenue totals | includes cancelled/refunded/pending sub-counts |
| `GET /exports/churn/train.csv` | 180 rows, 19 features + Churn | telco-style churn dataset |
| `GET /exports/churn/validation.csv` | 60 rows, same schema | held-out validation |
| `GET /exports/churn/candidates.csv` | 44 rows, NO Churn column | score these for outreach |
| `GET /exports/account_metric_extract.csv` | 528 rows pre-cleaned per account/month | includes pre-computed `clean_ticket_count` (confirms cleaning rule) |

**"All regions" rule:** for both `/api/opportunities` and `/api/hr/summary`,
"all regions" = call WITHOUT the `region` parameter. Passing `region=all`
returns zero HR rows.

---

## 1. Data hygiene rules (crisp, verifiable — apply always)

### Support tickets → `clean_ticket_count`
A ticket is **clean** iff ALL of:
- `is_spam == false`
- `is_duplicate == false`
- `status != "cancelled"` (status enum: closed / open / cancelled)
`clean_ticket_count` = count of clean tickets in the analysis window.
Spam, duplicate, and cancelled tickets are excluded from counts AND from
SLA-miss / severity (P1/P2) computations.

### NPS
- Ignore `retracted == true` responses.
- Ignore **invalid** scores: `score < 0` (a `-1` sentinel exists in the data)
  and treat null/missing as invalid. Valid range effectively 0–100.
- `latest_nps` (single value) = score of the most recent valid (non-retracted,
  valid-range) NPS response in the window by `response_date`. If none, use `0`.
- Per-month NPS (QBR): use `metrics.nps_score` for that month, but set to `null`
  when `metrics.survey_status` ∈ {missing, retracted}.

### Receivables (A/R)
- `overdue_balance = 61_90 + 90_plus` (the OLDER aging buckets only).
  The `current`, `1_30`, `31_60` buckets are NOT overdue.
- A customer is an "overdue follow-up" iff `overdue_balance > 0`.
- `overdue_total` (financial summary) = sum of `overdue_balance` across overdue
  customers.

### Revenue / ARR
- **ARR source = posted billing snapshots, NOT CRM.** `account.crm_arr` is
  STALE (often differs from billing). `account.billing_arr_current` equals the
  latest (Q4 / as_of=2026-12-31) snapshot — also wrong for point-in-time.
- `current_arr` for an assessment date D = `billing_arr` from the snapshot with
  `as_of == D` and `posted == true` (all snapshots are posted, but filter
  defensively). If no exact-date snapshot, use the latest snapshot with
  `as_of <= D`.
- Monthly "revenue" (QBR `recognized_revenue`) comes from the metrics endpoint,
  not the billing snapshot MRR.

---

## 2. CRM matching rule (receivables → accounts)

Match an A/R `customer_name` to a CRM account by **exact equality** against
`account.legal_name` ONLY.
- Subsidiaries and aliases are **NOT linked** even when the name closely
  resembles an alias. Examples observed: "Globex North Subsidiary LLC",
  "North Star Finance Services", "Quartz Insurance Claims Ltd.",
  "Valence Payment Services Canada" → all UNLINKED (their alias-like names do
  not equal any `legal_name`).
- Linked → `link_status="linked"`, `account_id` set.
- Unlinked → `link_status="unlinked"`, `account_id = null`.
- Sort `overdue_followups` by `customer_name` ascending.

---

## 3. Pipeline / opportunity rules

Window = opportunities whose `close_date` ∈ [start, end] (endpoint filters on
close_date). Outcome classification by `stage`:
- **Closed Won** (`state="closed"`) → won
- **Closed Lost** (`state="closed"`) → lost
- All other stages (Discovery, Prospecting, Proposal, Negotiation;
  `state="open"`) → **open**

Derived fields:
- `won_count`, `lost_count`, `open_count`
- `won_revenue` = Σ amount of Closed Won
- `open_pipeline` = Σ amount of open opps (this is "expansion pipeline")
- `win_rate_pct` = `won / (won + lost) * 100`, rounded 1dp (0 if denominator 0)
- `top_open_product_line` = most frequent `product_line` among open opps
  (product_lines: AI Assist, Core Retention, Data Cloud, Workflow Plus)

---

## 4. Risk scoring & ranking (renewal-risk queue + action board)

### Risk signals → reason_codes (assign all that apply)
| reason_code | trigger (inferred) |
|---|---|
| `overdue_receivable` | `overdue_balance > 0` |
| `low_tenure_high_churn` | `contract_tenure_months < 18` |
| `sla_degradation` | avg `sla_compliance` < 90, OR any clean-ticket SLA miss (`first_response_sla_met`/`resolution_sla_met` false), OR any P1/P2 clean ticket |
| `nps_drop` | `latest_nps < 40` (low) — also flag strong negative NPS trend |
| `usage_decline` | product_usage trend (Jun−Apr) < 0 |
| `renewal_window` | `renewal_date` within ~90 days of assessment date, or already due/overdue relative to assessment date |
| `expansion_offset` | open expansion pipeline > 0 (MITIGANT — reduces risk) |
| `clean_billings` | no overdue AND no SLA/NPS/usage issues (low-risk positive indicator) |

### Risk score (best-inference additive rubric, integer, cap 0–100)
Start 0. Add: `+25` overdue_receivable; `+20` low_tenure_high_churn;
`+15` sla_degradation; `+15` nps_drop; `+10` usage_decline; `+20`
renewal_window; `+10` lifecycle_status=="renewal_risk"; `+10` segment in
{Strategic, Enterprise} when other risks present. Subtract `−15`
expansion_offset (floor 0). Weights are inferred — the authoritative rule is
the RANKING below, not the absolute score.

### Risk level thresholds (inferred)
`score >= 75 → critical`; `>= 55 → high`; `>= 35 → medium`; else `low`.

### Ranking rule (authoritative, deterministic)
Sort by **risk_score DESC, then current_arr DESC, then account_id ASC**.
- Task-001 returns top 5 of the reviewed 8.
- Task-005 returns ALL listed accounts in this order (rank 1..N).

### Action precedence (derived from follow-up-calendar due-date order)
Apply the first that matches:
1. `overdue_receivable` → **`collections_followup`**
2. `sla_degradation` or `usage_decline` → **`technical_recovery`**
3. `renewal_window` → **`renewal_save`**
4. Strategic/Enterprise critical account with mixed signals → **`executive_qbr`**
5. otherwise → **`nurture_monitor`** (task-001 also allows `no_action` for
   very-low risk)

This precedence mirrors the calendar urgency:
collections (most urgent) > technical_recovery > renewal_save > executive_qbr >
nurture_monitor.

### `next_touch_due_date`
Use the due date mapped to the account's `primary_action` from the prompt's
follow-up calendar (task-005 gives explicit dates per action).

### Net revenue exposure (task-005)
Per account: `net_exposure = current_arr + overdue_balance − open_expansion_pipeline`.
Aggregate `segment_summary.net_revenue_exposure` = Σ current_arr
(at-risk accounts) + Σ overdue_balance − Σ open_expansion_pipeline.

---

## 5. Churn model validation & outreach ranking (task-004)

### Dataset
- training_rows = 180, validation_rows = 60, candidates = 44 (top-5 returned
  from the prompt's requested subset).
- 19 features (exclude `customer_id` and label `Churn`):
  tenure, MonthlyCharges, TotalCharges, Contract, PaymentMethod,
  PaperlessBilling, Partner, Dependents, OnlineSecurity, OnlineBackup,
  DeviceProtection, TechSupport, StreamingTV, StreamingMovies,
  SupportTickets90d, NPSLast, UsageTrendPct, InvoicePastDue, ActiveSeatRatio.
- Label `Churn` ∈ {Yes, No}. Encode Yes=1, No=0.

### Model (deterministic)
Fit **`GradientBoostingClassifier(random_state=0)`** (fully deterministic,
stable across seeds; rs=0/1/42 all give the same validation accuracy here).
One-hot encode categorical features; numeric features as-is.
- `accuracy_pct` = `round(accuracy_score(val_true, val_pred) * 100, 1)`.
- `accuracy_band` thresholds: `<70 → below_70`; `70–79.9 → 70_to_79`;
  `80–89.9 → 80_to_89`; `>=90 → 90_plus`. (GB yields ~88.3 → `80_to_89`;
  RandomForest(100,rs=0) yields ~93.3 → `90_plus` — prefer GB as the
  canonical "deterministic classifier".)
- `tenure_coefficient_direction`: compute Pearson correlation of `tenure` vs
  `Churn` on the training set (or the logistic-regression coefficient sign on
  standardized features). Observed corr ≈ −0.06, LR coef ≈ −0.14 →
  **`negative`** (lower tenure ⇒ higher churn risk). Use `zero` only if
  |corr| < 1e-6.

### Candidate ranking
- Score the prompt's requested candidate subset (intersect candidates.csv
  `customer_id` with the listed account_ids) with `predict_proba[:,1]`.
- `predicted_churn_probability` = round to 3dp.
- Rank by **probability DESC, then customer_id ASC**. Return top 5.
- `outreach_action` mapping (inferred): high prob + overdue
  (InvoicePastDue=Yes) → `renewal_save`; high prob + low tenure
  (`low_tenure_high_churn`) → `technical_recovery`; overdue-receivable signal
  → `collections_followup`; lower prob → `nurture_monitor`. Map `reason_code`
  to the dominant churn driver: InvoicePastDue=Yes→`overdue_receivable`;
  tenure<18→`low_tenure_high_churn`; SupportTickets90d high→`sla_degradation`;
  NPSLast low→`nps_drop`; UsageTrendPct<0→`usage_decline`.

### Cohort checks
- `past_due_shortlist_count` = # shortlisted candidates with
  `InvoicePastDue == "Yes"`.
- `low_tenure_shortlist_count` = # shortlisted candidates with `tenure < 18`.
- `average_probability_top5` = mean predicted proba of the returned top 5,
  rounded to a precision consistent with the template (treat as 1dp pct-style
  unless template dictates otherwise — template shows `0.0`, use 1dp).

---

## 6. QBR metrics packet (task-002)

Per month (Apr/May/Jun) → `qbr_metrics[]`:
- `revenue` = `metrics.recognized_revenue` (2dp)
- `support_tickets` = `metrics.support_ticket_count` (int)
- `sla_compliance_pct` = `metrics.sla_compliance` (1dp)
- `nps_score` = `metrics.nps_score` (int) or `null` when survey_status ∈
  {missing, retracted}

`highlights`:
- `average_revenue` = mean of 3 monthly revenues (2dp)
- `peak_revenue_month` / `peak_revenue` = month with max revenue
- `max_sla_month` / `max_sla_pct` = month with max sla (1dp)
- `peak_nps_month` / `peak_nps_score` = month with max valid nps (null if none)
- `ticket_trend` ∈ {improving, worsening, flat}: from monthly ticket counts;
  decreasing → `improving`, increasing → `worsening`, equal → `flat`

`metric_sources` (system-of-record enum — fixed mapping):
- revenue → `billing_snapshot`
- support_tickets → `support_export`
- sla_compliance → `sla_report`
- nps → `nps_survey`

`review_plan`:
- `review_owner` ∈ {solutions_engineering, customer_success, finance_ops}.
  QBR owned by CS → `customer_success`.
- `review_due_date` = date given in template/prompt (e.g. 2026-07-22).
- `needs_technical_signoff` = true if any clean-ticket P1/P2 OR any clean-ticket
  SLA miss exists in the quarter (engineering must sign off recovery).

`agenda_topics`: exactly 4 ordered enums from {partnership_overview,
q2_metrics, performance_highlights, q3_initiatives, technical_recovery,
commercial_expansion}. Default healthy-account agenda =
[partnership_overview, q2_metrics, performance_highlights, q3_initiatives].
If technical issues (P1/P2 or SLA miss) → replace q3_initiatives with
`technical_recovery`. If material open expansion pipeline exists → it
informationally supports `commercial_expansion`, but only when no technical
issue displaces the slot.

---

## 7. Operations-review context (task-003 `ops_context`)

From HR summary across all regions (omit region param):
- `hr_headcount` = Σ `headcount` across all regions
- `unpaid_claims_total` = Σ `unpaid_claims_amount` across all regions (2dp)

From `/api/events/performance?event=apex_connect&quarter=2026-Q3`:
- `event_orders` = `event_orders` field (total, incl. completed/cancelled/
  pending/refunded)
- `event_revenue` = `event_revenue` field (2dp)
(Do NOT subtract cancelled/refunded unless the prompt asks for "net/confirmed"
orders — here use the headline totals.)

---

## 8. Precision & output conventions (apply to every archetype)

- **Currency** → 2 decimals.
- **Percentage** → 1 decimal.
- **Counts, risk scores** → integers.
- **Churn probability** → 3 decimals.
- **Dates** → `YYYY-MM-DD`; months → `YYYY-MM`.
- **Nullables**: `nps_score` null when missing/retracted; `account_id` null for
  unlinked receivables; `peak_nps_score` null when no valid NPS.
- Booleans as JSON `true`/`false`.
- Return **only** JSON matching the template's top-level keys and field names
  verbatim (controlled enums only).

---

## 9. Policy codes (best inference — NO gold available)

Each `policy_codes` field in a template lists pipe-separated OPTIONS (e.g.
`"RS-2|RS-6|RS-9"`). The answer must emit the **single** code representing the
policy actually applied. Exact code→rule mapping cannot be confirmed without
gold; below is the rule each field encodes and the best-inferred selection.
**Treat code values as uncertain; the rule text is the reliable part.**

### Task-001 / Task-005 (shared)
| field | rule encoded | best-inferred code |
|---|---|---|
| `risk_model_code` (RS-2\|RS-6\|RS-9) | composite risk rubric using billing-ARR + tenure + SLA + NPS + usage + overdue + renewal-window − expansion | RS-6 (mid/standard composite) — inferred |
| `arr_source_code` (REV-1\|REV-4\|REV-8) | ARR sourced from posted billing snapshot as-of-date (CRM ARR rejected as stale) | inferred: the option denoting "billing_snapshot posted" |
| `support_hygiene_code` (SUP-3\|SUP-8\|SUP-9) | clean tickets exclude spam + duplicate + cancelled | inferred: the strict-triage option |
| `action_priority_code` (ACT-1\|ACT-5\|ACT-7) | action precedence collections > technical > renewal > exec > nurture, by due-date urgency | inferred: the precedence option |
| `board_sort_code` (BORD-1\|BORD-4\|BORD-8) [task-005] | sort score DESC, arr DESC, account_id ASC | inferred: the multi-key sort option |
| `exposure_formula_code` (EXP-2\|EXP-6\|EXP-9) [task-005] | net_exposure = arr + overdue − open_expansion_pipeline | inferred: the net-of-expansion option |
| `calendar_policy_code` (CAL-3\|CAL-5\|CAL-7) [task-005] | next-touch due date = action→calendar lookup | inferred: the calendar-driven option |

### Task-003
| field | rule encoded | best-inferred code |
|---|---|---|
| `receivable_trigger_code` (RCP-4\|RCP-7\|RCP-9) | overdue = 61_90 + 90_plus (older buckets) | inferred: older-buckets option |
| `crm_match_code` (CM-2\|CM-5\|CM-8) | exact legal_name match; subsidiaries/aliases NOT linked | inferred: exact-match option |
| `pipeline_window_code` (PW-3\|PW-6\|PW-9) | pipeline window = close_date in [start,end] | inferred: close-date-window option |
| `followup_scope_code` (FS-1\|FS-4\|FS-8) | single collections_followup action + fixed due date per overdue customer | inferred: single-action-fixed-date option |

### Task-004
| field | rule encoded | best-inferred code |
|---|---|---|
| `model_protocol_code` (MOD-2\|MOD-7\|MOD-9) | deterministic GB classifier (random_state=0), train/val split as exported | inferred: deterministic-GB option |
| `probability_scale_code` (PRB-1\|PRB-4\|PRB-8) | predict_proba[:,1], report 3dp | inferred: 3dp-proba option |
| `deployment_rule_code` (DEP-3\|DEP-5\|DEP-9) | rank by proba DESC + customer_id ASC tiebreak | inferred: proba-rank option |
| `outreach_mapping_code` (OUT-2\|OUT-6\|OUT-8) | outreach_action ← dominant churn driver | inferred: driver-mapped option |

When unsure, prefer the option whose documented semantics match the rule above.

---

## 10. Per-archetype output field definitions (from templates)

### Task-001 `renewal_risk_queue`
- `risk_accounts[]`: rank, account_id, risk_score(int), risk_level
  (critical|high|medium|low), primary_action
  (executive_qbr|collections_followup|technical_recovery|renewal_save|nurture_monitor|no_action),
  current_arr(2dp), latest_nps(int), clean_ticket_count(int),
  overdue_balance(2dp), reason_codes (subset of the 8 codes).
- `portfolio_summary`: accounts_reviewed(=N reviewed),
  critical_or_high_count, arr_at_risk(Σ current_arr of critical+high),
  collections_count, technical_recovery_count.
- `model_checks`: uses_billing_arr_source=true, tenure_risk_direction
  (negative|positive|not_assessed) → `negative`.

### Task-002 `qbr_metrics_packet`
See §6. Output keys: `qbr_metrics[]`, `highlights`, `metric_sources`,
`review_plan`, `agenda_topics` (exactly 4).

### Task-003 `receivables_pipeline_review`
- `financial_summary`: overdue_client_count, overdue_total(2dp),
  linked_followup_count, unlinked_followup_count.
- `pipeline_summary`: won_count, won_revenue(2dp), lost_count, open_count,
  open_pipeline(2dp), win_rate_pct(1dp), top_open_product_line.
- `overdue_followups[]` (sorted customer_name asc): customer_name,
  link_status(linked|unlinked), account_id(nullable), overdue_balance(2dp),
  due_date("2026-10-15"), primary_action("collections_followup").
- `ops_context`: hr_headcount, unpaid_claims_total(2dp), event_orders(int),
  event_revenue(2dp).

### Task-004 `churn_model_validation`
- `model_validation`: training_rows(180), validation_rows(60),
  feature_count(19), accuracy_pct(1dp), accuracy_band, tenure_coefficient_direction(negative).
- `risk_ranking[]`: rank, customer_id, predicted_churn_probability(3dp),
  outreach_action, reason_code.
- `cohort_checks`: past_due_shortlist_count, low_tenure_shortlist_count,
  average_probability_top5.
- `model_policy_codes`: see §9.

### Task-005 `retention_action_board`
- `action_board[]`: rank, account_id, risk_level, primary_action,
  current_arr(2dp), expansion_pipeline(2dp), overdue_balance(2dp),
  next_touch_due_date, reason_codes[].
- `segment_summary`: strategic_accounts, enterprise_accounts, arr_at_risk(2dp),
  open_expansion_pipeline(2dp), net_revenue_exposure(2dp).
- `followup_calendar`: {collections_followup, technical_recovery,
  renewal_save, executive_qbr, nurture_monitor} → each its due date.
- `policy_codes`: see §9.

---

## 11. Reproducible SOP (apply per task)

1. Read `ENV_URL.txt`; set `$BASE`. Hit `/api/health` to confirm.
2. Fetch `/api/accounts` once (build `legal_name→account_id`, alias index,
   profile lookups). Cache.
3. For each listed account: fetch metrics (start/end months), tickets
   (start/end dates), nps (start/end dates). Apply hygiene (§1).
4. Fetch `/api/billing/snapshots`; index by `(account_id, as_of)`. Pull ARR at
   the assessment date. Do NOT use `crm_arr` or `billing_arr_current`.
5. Fetch `/api/finance/ar-aging?as_of=<as-of>`; compute
   `overdue_balance = 61_90 + 90_plus`; match to CRM by exact legal_name (§2).
6. Fetch `/api/opportunities?start&end` (omit region for "all"); classify
   won/lost/open by stage; compute pipeline summary + per-account open
   expansion pipeline (§3).
7. (Task-003) Fetch HR (omit region) + events for ops context (§7).
8. (Task-004) Download the 3 churn CSVs; fit GB(random_state=0); validate;
   score requested candidate subset; rank proba DESC (§5).
9. Compute risk score + reason_codes + action (§4); rank by
   score DESC, arr DESC, account_id ASC.
10. Apply precision rules (§8); assemble JSON matching the template exactly;
    emit ONLY JSON.

### Common pitfalls
- Using `crm_arr` or `billing_arr_current` instead of the point-in-time posted
  snapshot → wrong ARR.
- Counting spam/duplicate/cancelled tickets in `clean_ticket_count` or SLA
  stats.
- Including retracted or `-1` NPS scores.
- Treating `1_30`/`31_60` as overdue (only `61_90 + 90_plus`).
- Linking receivables via aliases/subsidiaries (only exact legal_name).
- Passing `region=all` to HR (returns empty — omit region).
- Using created_date instead of close_date for the pipeline window.
- Forgetting NPS nullables / unlinked account_id null.
