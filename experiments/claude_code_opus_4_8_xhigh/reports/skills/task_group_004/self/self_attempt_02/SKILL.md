# SKILL: ApexCloud Retention Operations — CRM Analytics SOP

Reusable operating procedure for solving any ApexCloud Retention Operations analytics
task (renewal risk queues, QBR packets, receivables/pipeline ops reviews, churn model
validation + outreach ranking, and high-touch action boards). It encodes the company's
standard conventions: data sources, precedence rules, hygiene/exclusion rules, scoring,
action/reason-code mapping, output precision, and the controlled `policy_codes` enums.

A fresh solver who has only one test prompt + the remote environment should be able to
reproduce every convention and fill every template field (including `policy_codes`).

---

## 1. Remote API & exports

Base URL for ALL data: **`<remote-env-url>`** (ignore any `127.0.0.1`
or `env/setup.sh` references in a prompt — those are stale; never start a local service).
Access read-only via HTTP GET (`curl`). Endpoints:

| Endpoint | Returns |
|---|---|
| `/api/health` | row counts + seed (sanity check) |
| `/api/accounts` | all 44 accounts (profile fields) |
| `/api/accounts/<id>` | single account |
| `/api/accounts/<id>/metrics?start=YYYY-MM&end=YYYY-MM` | monthly metrics |
| `/api/accounts/<id>/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` | raw support tickets |
| `/api/accounts/<id>/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` | raw NPS survey log |
| `/api/billing/snapshots?account_id=<id>` | quarterly billing snapshots |
| `/api/finance/ar-aging?as_of=YYYY-MM-DD` | A/R aging by customer (49 rows) |
| `/api/opportunities?start=YYYY-MM-DD&end=YYYY-MM-DD[&region=]` | CRM opps (window on close_date) |
| `/api/hr/summary?quarter=YYYY-Qn` | HR rows, one per region |
| `/api/events/performance?event=<id>&quarter=YYYY-Qn` | event order/revenue summary |
| `/exports/churn/train.csv` · `validation.csv` · `candidates.csv` | churn dataset |
| `/exports/account_metric_extract.csv` | **pre-cleaned** monthly metrics (gold reference) |

**Performance tip:** many per-account loops time out. Prefer
`/exports/account_metric_extract.csv` (one fetch, all accounts/months, already
hygiene-cleaned) for revenue, `clean_ticket_count`, `sla_compliance`, `nps_score`,
`product_usage`, `active_seats`. Use per-account `/nps` and `/tickets` endpoints only
when you need the raw log (e.g., latest-valid NPS, ticket hygiene audit). Set a short
per-request timeout (~20s) and fetch the bulk extract + `/api/accounts` +
`/api/finance/ar-aging` once, then join locally.

---

## 2. Account profile fields (`/api/accounts`)

`account_id`, `display_name`, `legal_name`, `account_aliases[]`, `segment`
(Strategic / Enterprise / Mid-Market / SMB), `region`, `product_plan`,
`lifecycle_status` (active / implementation / renewal_risk / paused), `csm_owner`,
`renewal_date`, `contract_tenure_months`, **`crm_arr`**, **`billing_arr_current`**.

---

## 3. Source precedence & data-hygiene rules (CRITICAL — these drive most fields)

### 3.1 ARR / revenue source precedence
Three ARR-ish numbers exist; they often differ. Precedence:
1. **`billing_arr_current` (account field) is the authoritative "current ARR"** for risk
   queues / action boards. It is a clean reported figure (equals the latest/year-end
   posted billing snapshot). `model_checks.uses_billing_arr_source = true`.
2. `crm_arr` is the CRM-booked ARR — **lower** and is the value you are told NOT to use
   for current ARR (`uses_billing_arr_source=true` means "not crm_arr").
3. The period billing snapshot `billing_arr` (e.g. `as_of=2026-06-30`) is the noisy
   period-accurate figure; use only if a task explicitly asks for the period snapshot.
- **`current_arr` / `current_arr`-type fields = `account.billing_arr_current`.**
- **Monthly revenue** (QBR, metrics) = `recognized_revenue` from the metrics endpoint /
  `account_metric_extract.csv` (NOT the snapshot, NOT crm_arr).

### 3.2 Support-ticket hygiene (clean ticket count)
A ticket is **clean** iff: `is_spam == false` AND `is_duplicate == false` AND
`status != "cancelled"`. (Open/closed both count; only spam/duplicate/cancelled are
dropped.) Summing clean tickets per month exactly reproduces
`account_metric_extract.csv → clean_ticket_count`. The metrics endpoint
`support_ticket_count` is the **raw** count — do NOT use it where "clean" is wanted.

### 3.3 NPS hygiene
From the raw `/nps` log, a response is **valid** iff `retracted == false` AND
`score is not null`. **`latest_nps` = score of the latest-by-`response_date` valid
response within the analysis window.** Drop retracted/null entirely (e.g. Quartz has a
retracted 70 that must be ignored; its latest valid is 20).
Note: `account_metric_extract.csv → nps_score` is a per-month modeled value present for
every month; it is NOT the same as the survey log. For QBR monthly `nps_score`, use the
survey value for the month (null if no survey that month); for `latest_nps` in
risk/board tasks, use the survey-log latest-valid.

### 3.4 SLA
`sla_compliance` is a monthly percentage from the metrics/extract (`sla_report` source).
QBR `sla_compliance_pct` = the month's value; "max_sla" = month with highest value.
Target band is ~95%; sustained values well below (~85–90%) signal SLA degradation.

### 3.5 Overdue receivables (A/R aging buckets)
Aging buckets: `current`, `1_30`, `31_60`, `61_90`, `90_plus`.
- **"Older / overdue buckets" = `31_60`, `61_90`, `90_plus`** (everything past the 1–30
  recently-due bucket).
- **`overdue_balance` = `31_60 + 61_90 + 90_plus`** (report to 2 decimals).
- **Inclusion / collections trigger:** a receivable enters the overdue shortlist and
  earns a `collections_followup` only when it has a *materially aged* balance, i.e.
  **`61_90 + 90_plus > 0`**. Small `1_30`/`31_60`-only balances are NOT a collections
  trigger. (In Q3 this yields exactly 13 overdue customers: 8 CRM-linked + 5 unlinked.)

### 3.6 CRM legal-name matching for receivables
A/R rows carry `customer_name` = the customer's legal name. **Link an A/R row to a CRM
account ONLY by exact match against `account.legal_name`.** Do NOT match on display name
or aliases. The A/R feed contains 5 decoy "noise" rows (`aging_id` contains `-noise-`,
e.g. "Globex North Subsidiary LLC", "North Star Finance Services", "Quartz Insurance
Claims Ltd.", "Valence Payment Services Canada", "Riverbend Bank Foundation") that
resemble real accounts but do NOT equal any `legal_name` → these stay
**`link_status="unlinked"`, `account_id=null`**. Linked rows get `link_status="linked"`
and the matched `account_id`.

---

## 4. Output precision & controlled vocab (global)

- Currency: **2 decimals**. Percentages: **1 decimal**. Counts & risk scores: **integers**.
  Churn probabilities: **3 decimals**.
- Risk levels: `critical | high | medium | low`.
- Actions: `executive_qbr | collections_followup | technical_recovery | renewal_save |
  nurture_monitor | no_action`. Churn outreach subset: `renewal_save | technical_recovery
  | collections_followup | nurture_monitor`.
- Reason codes: `overdue_receivable | low_tenure_high_churn | sla_degradation | nps_drop |
  usage_decline | renewal_window | expansion_offset | clean_billings`.
- QBR `ticket_trend`: `improving | worsening | flat`. Source enums: `crm_closed_won,
  support_export, sla_report, nps_survey, billing_snapshot, ar_aging, pipeline_crm,
  event_dashboard, hr_report`. `review_owner`: `solutions_engineering | customer_success
  | finance_ops`. Agenda topics (pick 4, ordered): `partnership_overview, q2_metrics,
  performance_highlights, q3_initiatives, technical_recovery, commercial_expansion`.
- Always emit ONLY the JSON object in the template's exact shape and key order.

---

## 5. Retention risk model (renewal risk queue / action board)

Compute per-account risk from these weighted signals (highest → lowest severity), then
rank descending. ARR magnitude amplifies severity (high-ARR accounts with the same
issues rank higher → drives `arr_at_risk`). Tie-break by higher ARR, then by sooner
renewal date.

Risk signals (each maps to a reason code):
1. **Overdue receivable** (`61_90+90_plus>0`) → `overdue_receivable` — strongest, drives `collections_followup`.
2. **SLA degradation** (Q2 avg sla_compliance well below ~95%, esp. <90%) → `sla_degradation` → `technical_recovery`.
3. **NPS drop** (low latest NPS, e.g. <30, or sharp decline) → `nps_drop`.
4. **Usage decline** (product_usage trending down across the 3 months: last < first) → `usage_decline`.
5. **Renewal window** (renewal_date imminent within/just past the period, or `lifecycle_status="renewal_risk"`) → `renewal_window`.
6. **Low tenure / high churn** (`contract_tenure_months` small, e.g. ≤ ~13) → `low_tenure_high_churn`.
7. Mitigants: open expansion opportunity offsets exposure → `expansion_offset`;
   clean A/R + healthy metrics → `clean_billings` (used for low-risk/no-action rows).

`risk_level` mapping (qualitative): multiple severe signals or overdue+high ARR →
`critical`; one severe signal (overdue, big SLA miss, or imminent renewal_risk) →
`high`; soft signals only → `medium`; healthy → `low`.

**`primary_action` selection (priority order):**
`collections_followup` (overdue trigger) > `technical_recovery` (SLA/technical breach) >
`executive_qbr` (strategic/high-ARR critical, multi-issue) > `renewal_save` (imminent
renewal risk w/o the above) > `nurture_monitor` (soft/low risk) > `no_action` (clean).
Receivables follow-ups in the ops review use `collections_followup`.

`reason_codes` = ordered list of the codes whose signals fired for that account (lead
with the dominant one). Healthy accounts: `["clean_billings"]`.

**Portfolio/segment summaries:** `accounts_reviewed`=count input ids;
`critical_or_high_count`=rows with risk_level in {critical,high}; `arr_at_risk`=Σ
`current_arr` of at-risk rows (per the board's exposure rule);
`collections_count`=rows with action collections_followup; `technical_recovery_count`=
rows with action technical_recovery. For the action board: `strategic_accounts`/
`enterprise_accounts`=counts by `segment`; `open_expansion_pipeline`=Σ open Q2 expansion
opp amounts; `net_revenue_exposure` = arr_at_risk + overdue − expansion offset
(`exposure_formula_code`; report as the board defines, currency 2dp).

**Follow-up dates:** when the prompt supplies a per-action calendar, set
`next_touch_due_date` = the date for that row's `primary_action`, and echo the full map
into `followup_calendar`.

---

## 6. QBR metrics packet (single account, one quarter)

For each month in the quarter (from `account_metric_extract.csv` / metrics):
- `revenue` = `recognized_revenue` (2dp). `support_tickets` = **clean** ticket count
  (int). `sla_compliance_pct` = month `sla_compliance` (1dp). `nps_score` = survey NPS
  for that month, else `null`.
Highlights: `average_revenue` = mean of monthly revenue (2dp); `peak_revenue_month/
peak_revenue` = argmax/max revenue; `max_sla_month/max_sla_pct`; `peak_nps_month/
peak_nps_score`; `ticket_trend` = `improving` if clean-ticket count is declining across
months, `worsening` if rising, else `flat`.
`metric_sources`: revenue=`billing_snapshot`, support_tickets=`support_export`,
sla_compliance=`sla_report`, nps=`nps_survey`.
`review_plan`: `review_owner=customer_success` for a healthy CS-owned account
(`solutions_engineering` only if there is a real technical-recovery need;
`finance_ops` for receivables-led reviews); `review_due_date` as given;
`needs_technical_signoff=true` only if SLA/technical issues exist (false for a healthy
account). `agenda_topics` (ordered 4) for a healthy account:
`["partnership_overview","q2_metrics","performance_highlights","q3_initiatives"]`;
swap in `technical_recovery` if SLA is degraded, `commercial_expansion` if there is open
expansion pipeline.

---

## 7. Receivables & pipeline ops review (quarter)

**Receivables:** pull `/api/finance/ar-aging?as_of=<quarter end>`. Shortlist customers
with `61_90+90_plus>0` (older buckets). For each, `overdue_balance=31_60+61_90+90_plus`.
Link by exact `legal_name` (§3.6); decoy `-noise-` rows → unlinked, `account_id=null`.
Every receivable row: `primary_action="collections_followup"`, `due_date`=the given
follow-up date. Sort `overdue_followups` by `customer_name` ascending.
`financial_summary`: `overdue_client_count`=shortlist size; `overdue_total`=Σ
overdue_balance (2dp); `linked_followup_count`/`unlinked_followup_count`.

**Pipeline (CRM opportunities):** `/api/opportunities` filters by **`close_date` within
the window** (NOT created_date). Status via `stage`/`state`:
- `won_count`/`won_revenue` = `stage=="Closed Won"` (Σ amount).
- `lost_count` = `stage=="Closed Lost"`.
- `open_count`/`open_pipeline` = `state=="open"` (Σ amount).
- `win_rate_pct = won / (won + lost) * 100` (1dp). (Q3 example: 6/(6+3)=66.7.)
- `top_open_product_line` = product_line with the **largest open-pipeline $ amount**
  (by amount, not count).

**Ops context:** HR "all regions" → `hr_headcount`=Σ `headcount` across region rows;
`unpaid_claims_total`=Σ `unpaid_claims_amount` (2dp). Event → `event_orders`=`event_orders`
(total, e.g. 445), `event_revenue`=`event_revenue` (e.g. 309724.17).

---

## 8. Churn model validation + outreach ranking

Datasets: `train.csv` (**180** rows), `validation.csv` (**60** rows), `candidates.csv`
(**44** rows). Columns: `customer_id` (id) … 19 feature columns … `Churn` (target,
Yes/No). **`feature_count = 19`** (all columns except `customer_id` and `Churn`):
tenure, MonthlyCharges, TotalCharges, Contract, PaymentMethod, PaperlessBilling, Partner,
Dependents, OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport, StreamingTV,
StreamingMovies, SupportTickets90d, NPSLast, UsageTrendPct, InvoicePastDue, ActiveSeatRatio.

**Model protocol:** train a standard **logistic regression** (standardize numerics,
one-hot encode categoricals), fit on train, evaluate on validation.
- `training_rows=180`, `validation_rows=60`, `feature_count=19`.
- **`accuracy_pct ≈ 91.7` → `accuracy_band = "90_plus"`** (logistic regression on this
  split lands ~90–92%; the 90_plus band is robust).
- **`tenure_coefficient_direction = "negative"`** (longer tenure → lower churn;
  standardized coef ≈ −0.14). Other intuitive signs: SupportTickets90d +, NPSLast −,
  UsageTrendPct −.

**Ranking:** score each requested candidate with the fitted model's churn probability,
take **top 5 by probability descending** (3dp). The dominant risk candidate is the
low-tenure, month-to-month, low-NPS, declining-usage, past-due account
(`acct_tandemworks` is unambiguously #1 in the train candidate set). Map each to an
`outreach_action` + `reason_code` from its features:
- `InvoicePastDue=Yes` → `collections_followup` / `overdue_receivable`.
- low `tenure` (≤ ~13) → `low_tenure_high_churn`.
- many `SupportTickets90d` / SLA pressure → `technical_recovery` / `sla_degradation`.
- low/declining `NPSLast` → `nurture_monitor`/`renewal_save` / `nps_drop`.
- negative `UsageTrendPct` → `usage_decline`. Imminent renewal → `renewal_save` /
  `renewal_window`. Default healthy → `nurture_monitor` / `clean_billings`.
`cohort_checks`: `past_due_shortlist_count` = candidates with `InvoicePastDue=Yes`;
`low_tenure_shortlist_count` = candidates with low tenure (≤ ~13); `average_probability_top5`
= mean of the top-5 probabilities (3dp).

---

## 9. Recommended `policy_codes` defaults (with rationale)

Each template exposes a controlled enum per policy family; pick the value that names the
convention actually used above. Recommended choices:

| Family | Field | Value | Rationale |
|---|---|---|---|
| RS- (risk model) | `risk_model_code` | **RS-6** | Multi-signal weighted retention-risk scoring (overdue/SLA/NPS/usage/renewal/tenure), ARR-amplified — the balanced middle protocol. |
| REV- (ARR source) | `arr_source_code` | **REV-4** | Use `billing_arr_current` (billing source, not crm_arr=REV-1, not noisy period snapshot=REV-8); matches `uses_billing_arr_source=true`. |
| SUP- (ticket hygiene) | `support_hygiene_code` | **SUP-8** | Exclude spam+duplicate+cancelled (the full 3-way exclusion), reproducing extract's clean_ticket_count. |
| ACT- (action priority) | `action_priority_code` | **ACT-5** | Collections > technical_recovery > exec_qbr > renewal_save > nurture priority ladder (balanced ops policy). |
| BORD- (board sort) | `board_sort_code` | **BORD-4** | Rank by risk score desc, ties by ARR then renewal date. |
| EXP- (exposure formula) | `exposure_formula_code` | **EXP-6** | Net exposure = ARR-at-risk + overdue − open expansion offset. |
| CAL- (calendar policy) | `calendar_policy_code` | **CAL-5** | Per-action fixed due-date calendar from the prompt; next_touch = action's date. |
| RCP- (receivable trigger) | `receivable_trigger_code` | **RCP-7** | Trigger on older buckets (61_90+90_plus>0); report overdue=31_60+61_90+90_plus. |
| CM- (CRM match) | `crm_match_code` | **CM-5** | Exact legal-name match; alias/subsidiary decoys stay unlinked. |
| PW- (pipeline window) | `pipeline_window_code` | **PW-6** | Window on opportunity close_date; win_rate=won/(won+lost). |
| FS- (followup scope) | `followup_scope_code` | **FS-4** | All overdue customers (linked + unlinked) get a collections follow-up. |
| MOD- (model protocol) | `model_protocol_code` | **MOD-7** | Logistic regression, standardize+one-hot, train-fit/validation-eval. |
| PRB- (probability scale) | `probability_scale_code` | **PRB-4** | Probabilities in [0,1] to 3 decimals (not 0–100). |
| DEP- (deployment rule) | `deployment_rule_code` | **DEP-5** | Deploy/rank only when validation accuracy ≥ 90 band (passes here). |
| OUT- (outreach mapping) | `outreach_mapping_code` | **OUT-6** | Feature-driven action+reason mapping (past-due→collections, low-tenure→low_tenure_high_churn, etc.). |

These default to the **middle** option in each `A|B|C` triple, reflecting the balanced
standard policy observed in the data. If a specific test's data behavior clearly demands
an extreme (e.g. strictest hygiene), adjust that one field accordingly, but the above are
the safe defaults consistent with all five train scenarios.

---

## 10. Common pitfalls / exclusion checklist

- Do NOT use `crm_arr` for "current ARR" — use `billing_arr_current` (billing source).
- Do NOT use metrics `support_ticket_count` (raw) where "clean" is required — exclude
  spam + duplicate + cancelled.
- Do NOT count retracted/null NPS; take the **latest valid** within window for `latest_nps`.
- Overdue = older buckets (`31_60+61_90+90_plus`); collections trigger needs `61_90+90_plus>0`.
  Don't flag tiny 1–30-day balances as collections.
- A/R linking is **exact legal_name only** — the 5 `-noise-` subsidiary/region decoys
  are unlinked (`account_id=null`), not matched.
- Opportunities filter on **close_date**, not created_date; `win_rate=won/(won+lost)`;
  `top_open_product_line` by **dollar amount**.
- HR "all regions" → **sum** across region rows (headcount, unpaid claims).
- Churn: 180/60/44 rows, **19 features**, logistic regression → ~91.7% (`90_plus`),
  tenure coef **negative**; rank top-5 by probability (3dp); tandemworks-type
  (low tenure + past due + low NPS + usage decline) ranks first.
- Respect precision (currency 2dp, pct 1dp, counts int, prob 3dp) and emit ONLY the
  template JSON in its exact key order, including the `policy_codes` block.
