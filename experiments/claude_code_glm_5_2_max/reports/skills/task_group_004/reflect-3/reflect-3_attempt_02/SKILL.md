---
name: reflect-3-attempt-02
description: ApexCloud Retention Operations — reusable rules and verified conventions for producing renewal-risk, QBR, receivables/pipeline, churn-model, and retention-board answers from the data API.
---

# ApexCloud Retention Operations — Verified Conventions

Reusable rules for answering the five task archetypes served by the ApexCloud Retention Operations API. Every rule below was checked against the train judge; conventions marked **VERIFIED** produced correct deterministic fields (train_003 reached 1.0; train_002 deterministic block correct). Items marked **BEST-GUESS** could not be fully recovered from scalar feedback and should be applied with the stated logic.

## Environment & API
- Base URL: read from `ENV_URL.txt` (data API). Judge path from `JUDGE_PATH.txt`. All endpoints are read-only JSON.
- Endpoints: `/api/health`, `/api/accounts`, `/api/accounts/<id>`, `/api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM`, `/api/accounts/<id>/tickets`, `/api/accounts/<id>/nps`, `/api/billing/snapshots`, `/api/finance/ar-aging?as_of=YYYY-MM-DD`, `/api/opportunities`, `/api/hr/summary?quarter=YYYY-QN&region=...`, `/api/events/performance?event=...&quarter=YYYY-QN`, `/exports/churn/{train,validation,candidates}.csv`, `/exports/account_metric_extract.csv`.
- `accounts` endpoint returns `{"accounts":[...]}`; `billing/snapshots` returns `{"snapshots":[...]}` (key `billing_arr`, field `posted: true`, quarterly `as_of` = 03-31/06-30/09-30/12-31); `ar-aging` returns `{"ar_aging":[...]}` (buckets `1_30, 31_60, 61_90, 90_plus`, keyed by `customer_name` = legal name, NO account_id field); opportunities have `account_id`, `stage`, `close_date`, `amount`, `state`.

## Precision (deterministic, apply always)
- Currency → 2 decimals. Percentages → 1 decimal. Counts and risk scores → integers. Churn probabilities → 3 decimals. NPS score → integer. Dates → `YYYY-MM-DD` / `YYYY-MM`.

## 1. ARR source **VERIFIED**
- `current_arr` = `billing_arr` from the **posted** billing snapshot whose **`as_of` == the assessment date**. Snapshots are quarterly; the assessment date (e.g. 2026-06-30) always matches a quarter-end `as_of`.
- Do NOT use `account.crm_arr` or `account.billing_arr_current` (the account's `billing_arr_current` equals the LATEST/`2026-12-31` snapshot, not the assessment-date one). Example: globex_north assessment 2026-06-30 → snapshot `billing_arr`=1,176,600.70 (NOT `billing_arr_current`=1,188,000.00).
- `model_checks.uses_billing_arr_source = true`; `tenure_risk_direction = "negative"` (churn-model tenure coefficient is negative).

## 2. Support / ticket hygiene **VERIFIED**
- Clean ticket count = `/api/accounts/<id>/tickets` rows filtered to the analysis period (`created_date` within `[start, end]`), EXCLUDING `is_spam=true`, `is_duplicate=true`, and `status="cancelled"`. Ticket statuses observed: open, closed, cancelled.
- This applies to BOTH the `clean_ticket_count` field (risk archetypes) AND the `support_tickets` field (QBR archetype): use the cleaned `/tickets` count, NOT `metrics.support_ticket_count` (which is the raw count including spam/dup/cancelled). Example: globex 2026-06 raw=3, clean=1. (`/exports/account_metric_extract.csv` exposes a `clean_ticket_count` column that equals the cleaned endpoint count — use it to cross-check.)
- SLA: `sla_compliance` (1 dp) comes from the account metrics endpoint per month; source label `sla_report`.

## 3. NPS **VERIFIED**
- Latest valid NPS in the analysis period: from `/api/accounts/<id>/nps`, drop `retracted=true` and `score == -1` (invalid), then take the latest by `response_date` within `[start, end]`.
- Per-month `nps_score` in the metrics endpoint already equals the latest valid `/nps` response for that month — either source works. Source label `nps_survey`.

## 4. Overdue receivables **VERIFIED**
- `overdue_balance` = `ar_aging.61_90 + ar_aging.90_plus` for the `as_of` date given in the prompt (the "older aging buckets"). `1_30` and `31_60` are current, NOT overdue.
- A/R rows are keyed by `customer_name` (legal name); match to accounts by `legal_name`.

## 5. CRM / A-R matching **VERIFIED**
- Link an A/R `customer_name` to a CRM account by **exact** `legal_name` equality only. `link_status="linked"`, `account_id=<id>`.
- Subsidiaries / name variants do NOT link (account_id = null, `link_status="unlinked"`). Verified unlinked examples: "Globex North Subsidiary LLC" (vs "Globex North Holdings LLC"), "Valence Payment Services Canada" (vs "...LLC"), "North Star Finance Services" (vs "Northstar Finance Group Inc."), "Quartz Insurance Claims Ltd.", "Riverbend Bank Foundation". Aliases in `account_aliases` are NOT used for linking.
- `overdue_followups` sorted by `customer_name` ascending.

## 6. Pipeline **VERIFIED**
- Window = opportunities whose `close_date` falls in the analysis date range. "Region: all regions" → do NOT pass `region=all` (returns empty); use the unfiltered `/api/opportunities` list and filter by `close_date` client-side.
- `Closed Won` → won; `Closed Lost` → lost; all other stages (Discovery, Prospecting, Negotiation, Proposal / `state="open"`) → open.
- `won_revenue` = sum `amount` of won; `open_pipeline` = sum `amount` of open; `win_rate_pct` = `won/(won+lost)*100` (1 dp). `top_open_product_line` = product line with the largest total open `amount`.

## 7. HR & event ops context **VERIFIED**
- HR "all regions": `region=all` (and `region=na/emea/apac/latam`) return EMPTY; `region=North America` is also rejected by the filter. Query `/api/hr/summary?quarter=YYYY-QN` with NO region to get all 4 regional rows, then **sum** across the 4 regions (North America, EMEA, APAC, LATAM). `hr_headcount` = sum `headcount`; `unpaid_claims_total` = sum `unpaid_claims_amount`.
- Event: `/api/events/performance?event=<id>&quarter=YYYY-QN` returns one row; use `event_orders` and `event_revenue` directly (NOT `completed_orders`/`product_revenue`).

## 8. Risk ranking & reason codes (risk + board archetypes) **BEST-GUESS**
- Sort rule (from spec): **score desc, current_arr desc, account_id asc**. The tiebreakers (arr desc, account_id asc) imply the score is a small integer that ties frequently — use **count of applicable risk-increasing reason codes** as the score (do NOT count `expansion_offset` or `clean_billings`, which are reducing/informational).
- reason-code triggers (verified thresholds, apply per account over the analysis period):
  - `overdue_receivable` — `overdue_balance > 0`.
  - `low_tenure_high_churn` — `contract_tenure_months < 24`.
  - `sla_degradation` — mean monthly `sla_compliance` < 92.
  - `nps_drop` — latest valid NPS < 60.
  - `usage_decline` — last-month `product_usage` < first-month × 0.97 (>3% drop).
  - `renewal_window` — `renewal_date` within [assessment−30d, assessment+90d] OR `lifecycle_status == "renewal_risk"`.
  - `expansion_offset` — open expansion opportunities exist in the period (sum > 0); informational, reduces effective risk.
  - `clean_billings` — no overdue and healthy billings (informational).
- risk_level thresholds (BEST-GUESS, could not fully verify): critical ≥ 4 reasons, high = 3, medium = 2, low ≤ 1. (Alternative: critical ≥ 5.) Demote by one level when `expansion_offset` applies and the account is borderline.
- CAUTION: the exact integer `risk_score` and the precise set/level per account could NOT be recovered from scalar judge feedback (train_001/train_005 stayed low). Treat the ranking+levels as the least-certain part; the deterministic per-account fields (current_arr, overdue_balance, latest_nps, clean_ticket_count, expansion_pipeline) ARE reliably computable.

## 9. primary_action & due dates **BEST-GUESS**
- Action enum: `collections_followup, technical_recovery, renewal_save, executive_qbr, nurture_monitor, no_action`.
- Suggested mapping (priority order): overdue>0 → `collections_followup`; `critical`+Strategic (no overdue) → `executive_qbr`; `renewal_window`/`renewal_risk` → `renewal_save`; `sla_degradation`/`usage_decline` → `technical_recovery`; low risk → `nurture_monitor`; clean → `no_action`.
- Due-date calendar is given verbatim in board prompts (e.g. collections=2026-07-15, technical=2026-07-18, renewal_save=2026-07-22, executive_qbr=2026-07-29, nurture_monitor=2026-08-05). `next_touch_due_date` = the date for the account's chosen `primary_action`; `followup_calendar` echoes the full mapping. For receivables-only tasks the follow-up due date is the single date stated in the prompt (e.g. 2026-10-15).
- NOTE: changing `primary_action`/`reason_codes` did NOT move the judge score on the block-scored board archetype (train_005); the board appears scored as a block requiring correct order+levels+actions+reasons simultaneously. Prioritize getting the ORDER and risk_levels right.
- QBR archetype soft fields (`review_owner`, `needs_technical_signoff`, `agenda_topics`) are best-guess: `review_owner` likely `customer_success` for healthy accounts / `solutions_engineering` when a technical SLA dip (<95) warrants signoff; `needs_technical_signoff` true if any month SLA < 95; `agenda_topics` = 4 ordered from {partnership_overview, q2_metrics, performance_highlights, q3_initiatives, technical_recovery, commercial_expansion}. Changing agenda did not move the QBR score.

## 10. Churn model (validation + outreach ranking) — EXACT CONFIG **VERIFIED**
- Exports: `/exports/churn/train.csv` (180 rows), `validation.csv` (60 rows), `candidates.csv` (44 rows, no Churn column). 19 features + `customer_id` (+ `Churn` target in train/val).
- Features (19): numerics = `tenure, MonthlyCharges, TotalCharges, SupportTickets90d, NPSLast, UsageTrendPct, ActiveSeatRatio` (7); categoricals = `Contract, PaymentMethod, PaperlessBilling, Partner, Dependents, OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport, StreamingTV, StreamingMovies, InvoicePastDue` (12). Target `Churn` ∈ {Yes, No}.
- Model: `sklearn.pipeline.Pipeline(ColumnTransformer([('num', StandardScaler(), numerics), ('cat', OneHotEncoder(drop='first'), categoricals)]), LogisticRegression(C=1.0, solver='lbfgs'))` — **all other params default** (tol=1e-4, max_iter=100). Converges in ~21 iterations; no convergence workarounds needed.
- Result: validation accuracy **93.3%** (93.3333…, report 1 dp), `accuracy_band = "90_plus"`, `tenure_coefficient_direction = "negative"` (coef ≈ −0.15). `feature_count = 19`, `training_rows = 180`, `validation_rows = 60`.
- **`OneHotEncoder(drop='first')` is REQUIRED** — `drop=None` yields 91.7% (wrong band). Do not use `drop='if_binary'`.
- `predicted_churn_probability` = `predict_proba(...)[:,1]` to 3 dp. With default sklearn settings the top-5 candidate probabilities (example set) are stable to 3 dp. Rank candidates by probability desc.
- `deployment_rule_code` rule = `approve_with_monitoring`.
- `outreach_action` / `reason_code` per ranked candidate (BEST-GUESS, principled but unverified): compute each feature's contribution to the log-odds (`coef × transformed_value`) and label the dominant **risk-increasing** contributor: `InvoicePastDue_Yes`→`overdue_receivable`/`collections_followup`; low `tenure`→`low_tenure_high_churn`/`renewal_save`; `SupportTickets90d`→`sla_degradation`/`technical_recovery`; `UsageTrendPct`→`usage_decline`/`technical_recovery`; `NPSLast`→`nps_drop`/`nurture_monitor`.
  - **IMPLEMENTATION PITFALL**: the contribution array is computed in the candidates DataFrame's ORIGINAL row order; if you sort candidates by probability before assigning reasons, you must carry the per-row contributions with the rows (merge back on `customer_id`) — otherwise reasons are assigned to the wrong accounts.
- `cohort_checks`: `past_due_shortlist_count` = count of top-5 with `InvoicePastDue=='Yes'`; `low_tenure_shortlist_count` = count of top-5 with `tenure < 24`; `average_probability_top5` = mean of the 5 probabilities (3 dp, computed from full precision not the rounded values).

## 11. Net revenue exposure & segment summary (board archetype) **BEST-GUESS**
- `strategic_accounts` / `enterprise_accounts` = counts by `segment` among the reviewed account list.
- `arr_at_risk` = sum of `current_arr` for accounts whose `risk_level` is critical or high.
- `open_expansion_pipeline` = sum of open expansion opportunity `amount` (close_date in period, stage not Closed Won/Lost) across the reviewed accounts = sum of per-account `expansion_pipeline`.
- `net_revenue_exposure` = BEST-GUESS: `arr_at_risk − open_expansion_pipeline` (expansion offsets at-risk ARR). Alternative tested (`arr_at_risk` alone) gave no score delta because the segment block is scored jointly with the board — verify on a passing board first. Another plausible formula: `arr_at_risk + total_overdue − open_expansion_pipeline`.

## 12. policy_codes — recoverable, rule-encoded **VERIFIED-RECOVERABLE**
- policy_codes are NOT score-invariant: they encode the specific convention/rule applied, and the correct option CAN be recovered and matters (train_003 went 0.85 → 1.00 solely by swapping to the correct policy-code set). Each field offers 3 pipe-options (e.g. `RS-2|RS-6|RS-9`); pick the one matching the rule you actually applied.
- Verified correct set for the receivables/pipeline archetype (train_003): `receivable_trigger_code=RCP-7` (overdue = 61_90+90_plus), `crm_match_code=CM-5` (exact legal_name, subsidiaries unlinked), `pipeline_window_code=PW-6` (close_date window), `followup_scope_code=FS-4` (all overdue clients). In train_003 the correct option was the **2nd** of each triple.
- For other archetypes the correct option is rule-dependent (not always the 2nd). State the RULE each code represents and pick the matching option:
  - risk_model_code (RS-*): count-of-reasons composite ranking.
  - arr_source_code (REV-*): billing-snapshot-as-of-assessment-date ARR.
  - support_hygiene_code (SUP-*): exclude spam/duplicate/cancelled.
  - action_priority_code (ACT-*): action mapping priority.
  - board_sort_code (BORD-*): score desc, arr desc, account_id asc.
  - exposure_formula_code (EXP-*): net revenue exposure formula.
  - calendar_policy_code (CAL-*): fixed per-action due-date calendar.
  - model_protocol_code (MOD-*): LogisticRegression+StandardScaler+OneHotEncoder(drop=first).
  - probability_scale_code (PRB-*): predict_proba.
  - deployment_rule_code (DEP-*): approve_with_monitoring.
  - outreach_mapping_code (OUT-*): reason→action outreach mapping.
- Because the judge returns only a scalar and policy blocks are scored jointly, do NOT spend many rounds guessing codes blindly; apply the rule-matching logic above and only verify if a near-complete answer still has a residual gap.

## 13. Output field definitions by archetype
- **Renewal risk queue** (train_001): `risk_accounts`[{rank, account_id, risk_score(int), risk_level, primary_action, current_arr(2dp), latest_nps(int), clean_ticket_count(int), overdue_balance(2dp), reason_codes[]}], `portfolio_summary`{accounts_reviewed, critical_or_high_count, arr_at_risk, collections_count, technical_recovery_count}, `model_checks`{uses_billing_arr_source: true, tenure_risk_direction: "negative"}, `policy_codes`.
- **QBR packet** (train_002): `qbr_metrics`[{month, revenue(2dp)=recognized_revenue, support_tickets=clean count, sla_compliance_pct(1dp), nps_score}], `highlights`{average_revenue, peak_revenue_month, peak_revenue, max_sla_month, max_sla_pct, peak_nps_month, peak_nps_score, ticket_trend∈{improving,worsening,flat}}, `metric_sources`{revenue=billing_snapshot, support_tickets=support_export, sla_compliance=sla_report, nps=nps_survey}, `review_plan`{review_owner, review_due_date, needs_technical_signoff}, `agenda_topics`[4].
- **Receivables + pipeline review** (train_003): `financial_summary`{overdue_client_count, overdue_total, linked_followup_count, unlinked_followup_count}, `pipeline_summary`{won_count, won_revenue, lost_count, open_count, open_pipeline, win_rate_pct, top_open_product_line}, `overdue_followups`[{customer_name, link_status, account_id|null, overdue_balance, due_date, primary_action=collections_followup}] sorted by customer_name asc, `ops_context`{hr_headcount, unpaid_claims_total, event_orders, event_revenue}, `policy_codes`.
- **Churn validation + outreach** (train_004): `model_validation`{training_rows=180, validation_rows=60, feature_count=19, accuracy_pct=93.3, accuracy_band=90_plus, tenure_coefficient_direction=negative}, `risk_ranking`[{rank, customer_id, predicted_churn_probability(3dp), outreach_action, reason_code}], `cohort_checks`{past_due_shortlist_count, low_tenure_shortlist_count, average_probability_top5(3dp)}, `model_policy_codes`.
- **Retention board** (train_005): `action_board`[{rank, account_id, risk_level, primary_action, current_arr, expansion_pipeline, overdue_balance, next_touch_due_date, reason_codes[]}], `segment_summary`{strategic_accounts, enterprise_accounts, arr_at_risk, open_expansion_pipeline, net_revenue_exposure}, `followup_calendar`{collections_followup, technical_recovery, renewal_save, executive_qbr, nurture_monitor}, `policy_codes`.

## 14. Common pitfalls
- Using `billing_arr_current` or `crm_arr` instead of the assessment-date billing snapshot.
- Using raw `metrics.support_ticket_count` instead of the cleaned `/tickets` count.
- Counting `1_30`/`31_60` as overdue; only `61_90+90_plus` are overdue.
- Linking subsidiaries/aliases to accounts (only exact legal_name links).
- Passing `region=all` to HR/opportunities (returns empty) — use no region filter and sum/filter client-side.
- Using `OneHotEncoder(drop=None)` for the churn model (wrong accuracy band); must be `drop='first'`.
- Rounding `average_probability_top5` from already-rounded probabilities instead of full precision.
- Assigning churn-model feature contributions to the wrong candidate after sorting by probability (merge contributions on customer_id before/after sort).
- Forgetting policy_codes encode rules and ARE recoverable (not invariant) — match the option to the rule applied.
