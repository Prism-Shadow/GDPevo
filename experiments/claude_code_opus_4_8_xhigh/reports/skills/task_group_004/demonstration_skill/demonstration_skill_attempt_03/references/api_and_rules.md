# ApexCloud API field maps, examples, and policy-code cheat-sheet

Read this when you need the exact shape of a response, to confirm a threshold, or to
copy a worked calculation. Base URL is in the prompt (typically
`http://127.0.0.1:8074`). All endpoints are HTTP GET, JSON unless noted. Read-only.

## Table of contents
1. Endpoints and key fields
2. Worked examples (the rules in numbers)
3. Reason-code trigger evidence table
4. Policy-code cheat-sheet (which value per family)
5. Curl/Python recipes

---

## 1. Endpoints and key fields

- `GET /api/health` — `row_counts`, `seed`. Sanity check the service.
- `GET /api/accounts` and `GET /api/accounts/<id>` — account profile. Fields:
  `account_id`, `display_name`, `legal_name`, `account_aliases[]`, `segment`
  (Strategic / Enterprise / Mid-Market / SMB), `region`, `product_plan`,
  `lifecycle_status` (active, implementation, renewal_risk, paused, …),
  `contract_tenure_months`, `renewal_date`, `csm_owner`,
  `billing_arr_current` (rounded plan ARR — DO NOT use as current ARR),
  `crm_arr` (CRM figure — DO NOT use as current ARR).
- `GET /api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM` — **months** not dates.
  Per month: `recognized_revenue`, `support_ticket_count` (RAW, includes spam/dup/
  cancelled), `sla_compliance` (a reported %, NOT the basis for `sla_degradation`),
  `nps_score`, `product_usage`, `active_seats`, `survey_status`, `quarter`.
- `GET /api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` — per ticket:
  `ticket_id`, `created_date`, `status` (open/closed/cancelled), `is_spam`,
  `is_duplicate`, `severity`, `product_area`, `first_response_sla_met`,
  `resolution_sla_met`.
- `GET /api/accounts/<id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` — per response:
  `response_id`, `response_date`, `score`, `retracted`, `survey_channel`.
- `GET /api/billing/snapshots?account_id=<id>&as_of=YYYY-MM-DD` — `snapshots[]`:
  `snapshot_id`, `as_of`, `billing_arr` (← current ARR source), `mrr`, `posted`,
  `legal_name`, `source`. With `&as_of=` the API returns the single latest posted
  snapshot at/before that date. All seed snapshots are `posted:true`.
- `GET /api/finance/ar-aging?as_of=YYYY-MM-DD` (optional `&region=`) — `ar_aging[]`:
  `aging_id`, `customer_name`, `region`, `quarter`, `as_of`, buckets `current`,
  `1_30`, `31_60`, `61_90`, `90_plus`. Linked rows: `aging_id = AR-<account_id>-<Q>`;
  noise rows: `aging_id = AR-noise-...`.
- `GET /api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD` (optional `&region=`) —
  `opportunities[]`: `opportunity_id`, `account_id`, `account_legal_name`, `amount`,
  `stage` (Prospecting/Discovery/Proposal/Negotiation/Closed Won/Closed Lost),
  `state` (open / closed), `product_line`, `close_date`, `created_date`, `region`.
  won = stage "Closed Won"; lost = stage "Closed Lost"; open = state "open".
- `GET /api/hr/summary?quarter=YYYY-QN` (optional `&region=`) — `hr_summary[]` per
  region: `headcount`, `unpaid_claims_amount`, `unpaid_claims_count`,
  `open_advances_amount`, `attendance_rate`, `leave_liability_hours`,
  `high_absence_employees`. "All regions" = sum across the returned rows.
- `GET /api/events/performance?event=<id>&quarter=YYYY-QN` — `event_performance[]`:
  `event_orders`, `event_revenue`, `product_revenue`, `completed_orders`,
  `cancelled_orders`, `refunded_orders`, `pending_orders`.
- CSV exports: `/exports/churn/train.csv`, `/exports/churn/validation.csv`,
  `/exports/churn/candidates.csv`, `/exports/account_metric_extract.csv`.
  Churn columns: `customer_id, tenure, MonthlyCharges, TotalCharges, Contract,
  PaymentMethod, PaperlessBilling, Partner, Dependents, OnlineSecurity, OnlineBackup,
  DeviceProtection, TechSupport, StreamingTV, StreamingMovies, SupportTickets90d,
  NPSLast, UsageTrendPct, InvoicePastDue, ActiveSeatRatio, Churn`. Features = 19
  (all columns minus `customer_id` and target `Churn`). candidates.csv has no `Churn`.

---

## 2. Worked examples (the rules in numbers)

### Current ARR (billing snapshot, as_of 2026-06-30)
`acct_northstar_finance` snapshots: 2026-03-31→1449511.67, **2026-06-30→1416439.47**,
2026-09-30→1419678.82, 2026-12-31→1425000.00. With `as_of=2026-06-30` →
`current_arr = 1416439.47`. The account record's `billing_arr_current` is 1425000.0 and
`crm_arr` is 1268250.0 — both **wrong** for current ARR.

### Clean ticket count (window 2026-04-01..06-30)
Filter `is_spam==false & is_duplicate==false & status!="cancelled"`. Verified:
northstar_finance 13, polaris_health 14, northstar_retail 14, arcstone 12,
summit_grid 4. (Raw counts and "no-cancelled-exclusion" counts are higher — e.g.
northstar_finance raw 15, spam+dup-only filter 14, full filter 13.)

### Latest NPS (window, retracted excluded, most recent date)
northstar_finance: 2026-04-21→17, 2026-06-06→39 ⇒ **39**. arcstone:
05-01→48, 05-25→-1, 06-22→65 ⇒ **65**. Always take the latest `response_date`, not the
max score, not the first.

### Overdue balance (61_90 + 90_plus)
globex_north (as_of 2026-09-30): 1_30=…, 31_60=1981.19, 61_90=17925.98,
90_plus=3003.77 ⇒ overdue = 17925.98+3003.77 = **20929.75**. Summing from 1_30 (29085.54)
or from 31_60 (22910.94) is wrong.

### Receivables review (Q3, as_of 2026-09-30) — reproduced exactly
13 overdue clients, total 190312.41; 8 linked, 5 unlinked. Linked rows carry
`AR-acct_*` aging_ids (e.g. Globex North Holdings LLC → acct_globex_north); noise rows
like `AR-noise-globex-north-subsidiary-...` are unlinked with `account_id: null`.
Sort by `customer_name` ascending.

### Pipeline (Q3 opportunities) — reproduced exactly
won_count 6 (stage Closed Won), won_revenue 193720.31, lost_count 3 (Closed Lost),
open_count 25 (state open), open_pipeline 3043511.10, win_rate 66.7%,
top_open_product_line "Data Cloud" (largest open amount total).

### Ops context (Q3, all regions) — reproduced exactly
hr_headcount = 134+103+78+62 = 377. unpaid_claims_total =
28761.44+11853.87+35321.41+16913.67 = 92850.39. event_orders 445, event_revenue
309724.17 (apex_connect).

### QBR (globex_north, Q2) — reproduced exactly
revenue (recognized_revenue) 95756.67 / 98509.22 / 105156.27 → avg 99807.39, peak
2026-06. clean tickets 4 / 4 / 1 (June raw is 3 but two are duplicates) → ticket_trend
improving. sla_compliance_pct (clean-ticket first_response %) 100.0 / 75.0 / 100.0.
nps 45 / 61 / 56, peak 2026-05=61. metric_sources fixed
(crm_closed_won, support_export, sla_report, nps_survey). review_owner customer_success,
needs_technical_signoff false. agenda
[partnership_overview, q2_metrics, technical_recovery, q3_initiatives].

### Action board (Q2, as_of 2026-06-30) — reproduced exactly
strategic_accounts 3, enterprise_accounts 5 (by segment). arr_at_risk 5736227.46 =
sum of current_arr for all accounts EXCEPT the two low/no_action ones (bayside_bio,
apexia). open_expansion_pipeline 976490.66 = sum of open Q2 opp amounts (quartz
793202.42 + valence 64483.34 + bayside 118804.90). net_revenue_exposure =
5736227.46 − 976490.66 = 4759736.80.

### Renewal queue arr_at_risk (contrast)
Top-5 with critical/high = northstar_finance(critical,1416439.47) +
polaris_health(high,705648.74) + northstar_retail(high,237281.77) = **2359369.98**.
Only critical+high count here — NOT all reviewed, NOT medium/low.

### Churn cohort_checks over the top-5
Top-5 were tandemworks(0.102), northstar_finance(0.039), northstar_retail(0.032),
globex_north(0.001), valence(0.001). past_due_shortlist_count = 1 (only tandemworks has
PastDue=Yes among the top-5; quartz also has PastDue but is NOT in the top-5).
low_tenure_shortlist_count = 3 (tandemworks 7, NF 12, NR 13; all < 18).
average_probability_top5 = (0.102+0.039+0.032+0.001+0.001)/5 = 0.035.

---

## 3. Reason-code trigger evidence table (15+ accounts, verified)

Fires / does-not-fire boundaries observed in the training accounts:

- `renewal_window`: FIRES at days_to_renewal 41,52,56,58,75 (future, <=90). NOT at
  149,160,162 (too far) or any negative (past). ⇒ `0 < days_to_renewal <= 90`.
- `low_tenure_high_churn`: FIRES tenure 7,12,13. NOT 20,31,46,56,65,66,69,70,71,72,76.
  ⇒ `tenure < 18`.
- `usage_decline`: FIRES when min monthly product_usage is 52.77, 56.41, 56.43, 60.85.
  NOT when min is 66.17, 68.53, 71.82, 75.24, 81.02 (even with a downward slope). ⇒
  absolute floor `min(product_usage) < ~65`, NOT a delta.
- `nps_drop`: FIRES latest 18,20,29,34,39 (all <40) and apexia latest 47 with in-window
  drop 66→47 (=19). NOT 46(drop5),53,53,64,64,65,71. ⇒ `latest<40 OR drop>=~15`.
- `sla_degradation`: FIRES for every account with >=1 clean ticket SLA miss
  (first_response or resolution). The ONLY non-fire was apexia with 100% on both flags.
  Higher metrics `sla_compliance` does not prevent firing (summit fires at 96.5% metric
  SLA; apexia does not fire at 94% metric SLA). ⇒ per-ticket flags, not the metric %.
- `expansion_offset`: FIRES when open expansion pipeline > 0 (action board). On the
  renewal queue it is used for an at-risk account WITH open pipeline (e.g.
  northstar_finance) while clean low-risk accounts get `clean_billings` instead.
- `clean_billings`: positive note for accounts with `overdue_balance == 0` and no
  receivable problem; appears on otherwise-low-risk accounts without an expansion story.

Risk levels by score: critical >=80, high 50-79, medium 30-49, low <30 (scores are
integers, multiples of 5, clamped 0–100). Same reason-code set can yield slightly
different scores because severity is continuous — rank reliably by score desc, ARR
desc as tie-break.

---

## 4. Policy-code cheat-sheet

Pick the value below; it is the same for every task in that family. (The answer
template lists three options per code; choose the matching one.)

Renewal Risk Queue & Action Board (shared core):
- `risk_model_code = RS-6`  (six-signal risk model)
- `arr_source_code = REV-4` (latest posted billing snapshot)
- `support_hygiene_code = SUP-8` (exclude spam + duplicate + cancelled)
- `action_priority_code = ACT-5` (overdue→tech→renewal→exec→nurture ladder)

Action Board additional:
- `board_sort_code = BORD-4`   (severity desc, then ARR desc)
- `exposure_formula_code = EXP-6` (net = arr_at_risk − open_expansion_pipeline)
- `calendar_policy_code = CAL-5` (per-action follow-up due dates from the prompt)

Receivables & Pipeline Review:
- `receivable_trigger_code = RCP-7` (overdue = 61_90 + 90_plus buckets)
- `crm_match_code = CM-5`           (link via AR-<account_id> aging_id)
- `pipeline_window_code = PW-6`     (quarter close-date window)
- `followup_scope_code = FS-4`      (all overdue clients, linked + unlinked)

Churn Validation & Ranking:
- `model_protocol_code = MOD-7`     (train/validation split protocol)
- `probability_scale_code = PRB-4`  (probabilities 3 decimals)
- `deployment_rule_code = DEP-5`    (top-5 outreach shortlist)
- `outreach_mapping_code = OUT-2`   (past-due→collections, low-tenure→renewal_save, else nurture)

QBR has no policy_codes block; its provenance lives in `metric_sources`
(crm_closed_won, support_export, sla_report, nps_survey).

If you ever applied a *different* rule than the canonical one above, match the
policy_code option to what you actually did — the code must describe the real method.

---

## 5. Curl/Python recipes

```bash
BASE=http://127.0.0.1:8074
curl -s "$BASE/api/health"
curl -s "$BASE/api/accounts/acct_globex_north/metrics?start=2026-04&end=2026-06"
curl -s "$BASE/api/billing/snapshots?account_id=acct_globex_north&as_of=2026-06-30"
curl -s "$BASE/api/finance/ar-aging?as_of=2026-06-30"
curl -s "$BASE/exports/churn/candidates.csv"
```

Current ARR:
```python
s = get(f"{BASE}/api/billing/snapshots?account_id={aid}&as_of={asof}")["snapshots"]
current_arr = round(s[0]["billing_arr"], 2) if s else 0.0   # &as_of returns the one snapshot
```

Clean tickets + sla_degradation:
```python
t = get(f"{BASE}/api/accounts/{aid}/tickets?start={s}&end={e}")["tickets"]
clean = [x for x in t if not x["is_spam"] and not x["is_duplicate"] and x["status"] != "cancelled"]
clean_count = len(clean)
sla_degradation = any((not x["first_response_sla_met"]) or (not x["resolution_sla_met"]) for x in clean)
sla_pct = round(100.0 * sum(x["first_response_sla_met"] for x in clean) / len(clean), 1) if clean else None
```

Latest NPS:
```python
n = get(f"{BASE}/api/accounts/{aid}/nps?start={s}&end={e}")["nps_responses"]
valid = sorted([x for x in n if not x["retracted"]], key=lambda x: x["response_date"])
latest_nps = valid[-1]["score"] if valid else None
```

Overdue balance + linking:
```python
import re
rows = get(f"{BASE}/api/finance/ar-aging?as_of={asof}")["ar_aging"]
for r in rows:
    overdue = round(r["61_90"] + r["90_plus"], 2)
    m = re.match(r"AR-(acct_[a-z_]+)-", r["aging_id"])
    linked = bool(m) and m.group(1) in real_account_ids
```
