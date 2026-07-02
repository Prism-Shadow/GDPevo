# Skill — Credit-Risk / Lending-Committee Answer Generation (task_group_011)

Transferable method for producing committee-ready JSON answers against the
shared credit-office public REST API. Distilled from five fully-worked train
tasks (Redwood regrade, Lakeview allocation, Civic NC segment posture, Summit
watch-list, Harbor competing-CRE) and cross-checked against live API data.

## 0. Environment & ground rules

- Base URL: `<remote-env-url>`. Read-only GET only. No auth.
- Always start by reading `/api/policies` (the single source of credit rules:
  risk-rating thresholds, CDFI factor scores, CRE weighted score, stress
  formulas, capacity/concentration policy) and `/api/manifest` (versions).
- Never call `/api/judge` (no test-time judge; it is not part of the public
  surface). Do not read any local `env/` source.
- Pipe responses through `jq` to inspect and project fields.
- Latest quarter of branch metrics is `2025Q1` (the second array element on
  these branches is `2024Q4`). Use the latest quarter unless a prompt names a
  quarter. `review_date` / as-of date in prompts is `2025-03-31`.
- Policy version is `credit_policy_v2025Q1`. FDIC set `fdic_q4_2024`; NCUA
  `ncua_q1_2025`.

## 1. API SOP — endpoints and how each answer section uses them

| Endpoint | Used for | Key query params |
| --- | --- | --- |
| `GET /api/policies` | every task — rating tables, stress formulas, score weights, capacity rules | none |
| `GET /api/manifest` | versions to populate `benchmark_version` strings | none |
| `GET /api/branches` | branch roster; `?institution_type=credit_union` filters CU segments | none |
| `GET /api/branches/{id}` | capacity (`lending_capacity_q1`), `sector_ceiling_pct`, `cre_policy_limit_pct`, `state_code`, `total_assets`, `fdic_benchmark_set` | none |
| `GET /api/branches/{id}/metrics` | `total_loans_outstanding`, `nonperforming_loans`, `delinquency_30_plus_pct`, allowances (latest quarter array element) | `?quarter=` |
| `GET /api/branches/{id}/loans` | loan-level regrade inputs: `dscr`, `ltv`, `debt_to_asset`, `fico`, `liquidity_months`, `payment_status`, `outstanding_balance`, `current_rating`, `sector`, `loan_type`, `borrower_name` | `?loan_type=`, `?payment_status=`, `?min_current_rating=` |
| `GET /api/branches/{id}/sector-exposures` | per-sector `current_exposure` and per-sector `limit_pct` (overrides `sector_ceiling_pct`); `grandfathered` flag | none |
| `GET /api/branches/{id}/applications` | pending applications: `requested_amount`, `dscr`, `ltv`, `fico`, `years_in_business`, `sba_guaranty_pct`, `bankruptcy_months_ago`, `documentation_complete`, `co_guarantor_strength`, `total_debt`, `total_assets`, `sector`, `loan_type` | `?loan_type=` |
| `GET /api/benchmarks/fdic/q4-2024` | five FDIC ratios (noncurrent + 30-89, by total / real-estate / construction) | none |
| `GET /api/benchmarks/ncua/q1-2025` | all state + `US` rows; `?state_code=` returns one row | `?state_code=` |
| `GET /api/credit-union-segments/{segment_id}` | CU segment: `state_code`, `peer_states`, `minimum_checklist`, `risk_tolerance`, `quarterly_capacity`, `current_outstanding`, `internal_context` | none |

`branch_id` values are uppercase (`REDWOOD`, `LAKEVIEW`, `SUMMIT`, `HARBOR`,
uppercase bank branch ids plus credit-union segment ids, which also appear in `/api/branches`
with `institution_type=credit_union`.

## 2. Cross-cutting business rules

### 2.1 Risk-rating re-derivation (dominant-factor / worst-notch rule)

Policy `risk_rating.dominant_factor_rule`: the final re-derived rating is the
**worst (highest) numeric rating** from the available DSCR, LTV/collateral, and
delinquency factors. Compute each factor's rating, then take the max.

**DSCR thresholds** (`risk_rating.dscr_thresholds`, `min` is inclusive lower bound):
- `dscr >= 1.5` → 3
- `dscr >= 1.25` → 4
- `dscr >= 1.05` → 5
- `dscr >= 1.0` → 6
- `dscr < 1.0` → 7
- `dscr` null/missing → factor contributes nothing (skip it).

**LTV thresholds** (`risk_rating.ltv_thresholds`, `max` inclusive upper bound):
- `ltv <= 0.65` → 3
- `ltv <= 0.75` → 4
- `ltv <= 0.85` → 5
- `ltv <= 1.0` → 6
- `ltv > 1.0` → 7

**Delinquency minimums** (`risk_rating.delinquency_minimums`) — a hard floor:
- `Current` → no floor (null)
- `30 Days Past Due` → at least 4
- `60 Days Past Due` → at least 5
- `90+ Days Past Due` → at least 7
- `Nonaccrual` → at least 8

`final_rating = max(dscr_rating*, ltv_rating*, delinquency_floor*)`. Example
verified on REDWOOD: `RED-LN-002` (dscr 1.49→4, ltv 1.0219→7, 60 DPD→5) ⇒
final 7 (current 4, downgrade 3).

**Population filter:** regrade population = loans with
`current_rating >= target_current_rating_min` (e.g. Redwood `>=3`). Pull with
`/api/branches/{id}/loans?min_current_rating=3`. This is NOT the watch-list
follow-up population (see 2.7).

**Material downgrade:** `material_downgrade_notches = 2`. A loan is a material
downgrade iff `current_rating - final_rating <= -2` (i.e. worsened by ≥2
notches). Only downgrades (final > current) by ≥2 notches are listed; list is
ordered ascending by `loan_id`.

### 2.2 NPA & FDIC/NCUA variance

**NPA variance (bank branches):** use branch metrics latest quarter.
- `branch_npa_exposure` = `metrics.nonperforming_loans` (cross-check: sum of
  `outstanding_balance` where `payment_status == "Nonaccrual"`; the two agree).
- `branch_total_loans` = `metrics.total_loans_outstanding`.
- `branch_npa_ratio = round(branch_npa_exposure / branch_total_loans, 4)`.
- `fdic_benchmark_ratio` = the chosen FDIC metric value (a decimal ratio, e.g.
  0.0098).
- `variance_ratio = round(npa_exposure/total_loans - fdic_ratio, 4)` (positive
  = branch worse than benchmark).
- `variance_bps = round((npa_exposure/total_loans - fdic_ratio) * 10000, 2)`,
  computed from the **unrounded** ratio (Redwood: 1037.49, not 1037.00).
- `benchmark_version = "fdic_q4_2024"`.

**FDIC metric choice** (`npa_benchmark.benchmark_metric` enum):
`total_loans_noncurrent_pct`, `total_real_estate_noncurrent_pct`,
`construction_development_noncurrent_pct`. Choose by branch/portfolio focus:
general branch NPA review → `total_loans_noncurrent_pct`; CRE-heavy →
`total_real_estate_noncurrent_pct`; construction-heavy →
`construction_development_noncurrent_pct`. The benchmark value comes from the
matching field of `/api/benchmarks/fdic/q4-2024`.

**CRE/FDIC delinquency variance (Harbor-style CRE decision):** here the variance
pairs the branch `delinquency_30_plus_pct` (from metrics) against the FDIC
`total_real_estate_30_89_pct` benchmark (template-hardcoded for that task).
- `branch_delinquency_ratio` = `metrics.delinquency_30_plus_pct` (e.g. 0.2853).
- `fdic_benchmark_ratio` = FDIC `total_real_estate_30_89_pct` (e.g. 0.0051).
- `fdic_variance_ratio = round(branch - fdic, 4)`; `fdic_variance_bps =
  round((branch - fdic) * 10000, 2)` (e.g. 2802.0). Sign: positive = branch
  under-performs benchmark.

**NCUA peer comparison (credit-union segment tasks):**
- Fetch `/api/benchmarks/ncua/q1-2025` (all rows, includes `US`).
- `state_metrics` = the segment `state_code` row; `benchmark_version =
  "ncua_q1_2025"`. Values are integers exactly as reported
  (`delinquency_bps`, `loan_to_share_pct`, `roaa_bps`,
  `positive_net_income_pct`).
- Peer states come from the **segment JSON** `peer_states` (e.g. `["SC","TN","VA"]`),
  already ascending; do not invent peers. Compute the **median** of the peer
  states' values per metric.
- `nc_vs_us` and `nc_vs_peer_median`: direction per metric ∈
  `{"higher","lower","equal"}` (substitute the segment's state code for "nc").
  Example: NC delinquency_bps 79 vs US 58 → `higher`; NC roaa_bps 44 vs peer
  median 59 → `lower`.

### 2.3 Capacity & concentration ceilings

**Lending capacity** (from `branches.lending_capacity_q1`):
- `gross_approved_amount` = Σ `approved_amount` over all `approve` +
  `conditional_approve` decisions (full approved principal, including amounts
  that are later participated / SBA-guaranteed).
- `committed_capacity_amount` = Σ `bank_capacity_used` over the same decisions
  (the bank's at-risk retained exposure, after mitigation).
- `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`.

**bank_capacity_used by decision type:**
- `approve` → `approved_amount` (full retention).
- `conditional_approve` + `sba_guaranty_required` →
  `approved_amount * (1 - sba_guaranty_pct)`. Verified: LAK-APP-902,
  approved 840,000 × (1 − 0.75) = 210,000.
- `conditional_approve` + `participation_required` → bank-retained amount sized
  so the affected sector sits at its `limit_pct` against the pro-forma book
  (total_loans_outstanding + committed bank-retained capacity); the excess is
  participated out. Verified: LAK-APP-901 retained 1,508,113.31 =
  `0.19 × (total_loans_outstanding + committed_capacity) − existing_healthcare`.

**Sector concentration limits:** `limit_pct` comes from each
`sector-exposures` row (per-sector override); default is
`branches.sector_ceiling_pct` when a sector is not listed. CRE-wide ceiling =
`branches.cre_policy_limit_pct`. Mitigations allowed by policy:
`participation_required`, `reduced_amount`, `board_exception`. Grandfathering:
existing over-ceiling exposure may be grandfathered, but a new approval may not
*worsen* that sector without mitigation.

**Existing CRE exposure (Harbor-style):** `existing_cre_exposure` = Σ
`outstanding_balance` of loans with `loan_type == "CRE"` (equivalently the sum
of CRE sector exposures). `existing_cre_concentration =
round(existing_cre_exposure / total_loans_outstanding, 4)`.
`selected_post_approval_cre_concentration = round((existing_cre_exposure +
selected_requested_amount) / (total_loans_outstanding +
selected_requested_amount), 4)` — **both numerator and denominator grow by the
new principal**. `selected_policy_variance_bps = round((post_unrounded -
cre_policy_limit_pct) * 10000, 2)` (Harbor: 0.5349 − 0.29 ⇒ 2449.15 bps).

**CRITICAL denominator rule:** concentration denominators use
`metrics.total_loans_outstanding` (e.g. 14,334,094.87 for Lakeview), **never**
`branches.total_assets` (which is ~25× larger and would make every ratio
trivially tiny).

**post_approval_concentrations (reporting section):**
- `exposure_after_approval` = existing sector exposure + Σ **full**
  `approved_amount` of approve/conditional apps in that sector (use approved
  principal, not bank_capacity_used).
- denominator = `total_loans_outstanding + gross_approved_amount` (pro-forma
  book including all newly approved principal). Verified on all four Lakeview
  sectors: Construction 3,934,283.26 / 18,908,348.32 = 0.2081, etc.
- `post_approval_pct = round(exposure_after_approval / denom, 4)`.
- `over_limit = post_approval_pct > limit_pct` (boolean).

**concentration_flags:** for each approve/conditional app whose sector is at or
near its ceiling, report `sector`, `application_id`, `limit_pct`,
`post_approval_pct` (4dp), `flag` (true when the deal breaches/near-breaches
the sector limit on a committed-capacity basis), `handling` ∈
`{approve, conditional_approve, decline, participation_required, none}`. Sort
by sector then application_id.

### 2.4 CDFI factor scores & risk classes (watch-list)

CDFI factor score = sum of four sub-scores (lower = better); **null/missing
factors score 0**.
- `ltv`: `<0.40`→0, `0.40–0.60`→2, `0.60–0.80`→4, `>0.80`→6
- `fico`: `>720`→0, `680–720`→1, `580–679`→3, `<580`→5 (null→0)
- `debt_to_asset`: `<0.40`→0, `0.40–0.60`→2, `0.60–0.80`→4, `>0.80`→6 (null→0)
- `liquidity_months`: `>12`→0, `6–12`→1, `3–6`→3, `<3`→5 (null→0)

Verified: SUM-LN-003 (ltv 0.9511→6, fico null→0, dta 0.3579→0, liq 11.6→1) ⇒
factor_score 7 ⇒ Desirable. SUM-LN-902 (ltv 1.18→6, dta 0.88→6, liq 1.6→5) ⇒
17.

**Risk class from factor_score** (`policies.cdfi_factor_scores.classes`):
- `Prime`: 0–5
- `Desirable`: 6–9
- `Satisfactory`: 10–13
- `Watch`: 14–18
- `Doubtful`: ≥19
- `Projected Loss`: ≥19 **and** ltv > 1.0

**Severe-delinquency override:** a loan with `payment_status == "Nonaccrual"`
is classed **`Projected Loss`** regardless of its factor score (it overrides the
score-range mapping). Verified on SUM-LN-902 (factor 17, Nonaccrual ⇒ Projected
Loss). `90+ Days Past Due` does **not** override — SUM-LN-011/015 stay at their
score-derived class.

### 2.5 +200bp DSCR stress (watch-list) and CRE dual stress

From `policies.stress`:
- `watch_list_parallel_shock = "+200bp"` ⇒ `shock_label = "+200bp"`.
- **Watch-list formula:** `stressed_dscr = dscr / (1 + 0.18)` =
  `dscr / 1.18`. Verified: SUM-LN-003 1.59/1.18 = 1.35; SUM-LN-004 1.01/1.18 =
  0.86.
- **CRE dual-stress formula** (`cre_dual_stress_formula`):
  `stressed_dscr = dscr * 0.85 / (1 + 0.18)` = `dscr * 0.85 / 1.18`. Verified:
  HAR-APP-901 1.47×0.85/1.18 = 1.06; HAR-APP-902 1.32×0.85/1.18 = 0.95.
  Report `formula` as the compact expression, e.g. `"dscr * 0.85 / 1.18"`.
- `coverage_breach_threshold = 1.0`. `breaches_threshold = stressed_dscr <
  1.0` (i.e. stressed < 1.0). Use strict `<` (Harbor 901 stressed 1.06 ⇒ false;
  902 stressed 0.95 ⇒ true).
- Stress results include **only loans with DSCR available** (skip null-dscr
  loans such as SUM-LN-010). DSCR values round to 2dp.
- `breach_loan_ids` = ascending loan_id list of loans whose stressed DSCR
  breaches.

### 2.6 Decline reason codes & decision enums

**Decision enum:** `approve`, `conditional_approve`, `decline`, `defer`,
`participation_required` (used as a per-application `decision` and as the
selected `path`).

**Conditions enum:** `participation_required`, `reduced_amount`,
`board_exception`, `sba_guaranty_required`, `startup_monitoring`, `none`.
Approve ⇒ `["none"]`; conditional_approve lists the mitigations in effect.

**Decline reason codes** (assign to declined apps; sorted ascending
alphabetically in output):
- `high_ltv` — ltv elevated past the 0.80 boundary (borderline) on an app
  declined for compounding weakness; clearly high when ltv > 0.85.
- `weak_dscr` — base DSCR < 1.25 (when DSCR applicable). In CRE-decision
  contexts, `weak_dscr` is instead triggered by **stressed DSCR < 1.0** (the
  coverage breach) — verified: HAR-APP-902 (stressed 0.95) gets `weak_dscr`,
  HAR-APP-901 (stressed 1.06) does not.
- `low_fico` — `fico < 580`.
- `recent_bankruptcy` — `bankruptcy_months_ago` not null and `< 24` months.
- `startup_risk` — `years_in_business < 2`.
- `sector_breach` — the app's sector post-approval concentration breaches (or
  would breach) `limit_pct` without mitigation.
- `capacity_limit` — the app is credit-acceptable but cannot be funded within
  remaining lending capacity after higher-priority approvals (e.g. LAK-APP-006:
  ltv 0.7749, fico 668 — passes credit, declined only on capacity).
- `fdic_adverse_variance` — branch FDIC delinquency materially exceeds
  benchmark (applies to all apps at an under-performing branch in a CRE
  decision; both Harbor apps carry it).
- `ncua_peer_weakness` — credit-union segment's state is weaker than national
  and peer median.
- `underwater_collateral`, `policy_floor_missing`, `documentation_gap` — use
  when collateral/value, policy floor, or documentation gaps are the binding
  weakness (`documentation_complete == 0` ⇒ `documentation_gap`).

**Decision logic (transferable):**
- `approve` — passes every credit test (ltv ≤ 0.85 band, dscr ≥ 1.25 where
  applicable, fico ≥ 580, no recent bankruptcy, years ≥ 2, documentation
  complete) AND fits capacity and sector ceilings. `approved_amount` =
  `requested_amount`; `bank_capacity_used = approved_amount`.
- `conditional_approve` — credit-acceptable but needs a mitigation:
  `participation_required` (sector near ceiling), `sba_guaranty_required`
  (startup risk partly offset by SBA guaranty), `startup_monitoring`,
  `reduced_amount`, or `board_exception`.
- `decline` — compounding credit weaknesses (e.g. high_ltv + weak_dscr; or
  low_fico + recent_bankruptcy) or `capacity_limit`.
- `defer` — for a competing-credit scenario, the weaker credit that is not
  selected but not outright declined (remediation possible). `unselected_disposition`
  ∈ `{decline, defer}`.

### 2.7 Watch-list action coverage & workout queues

**Watch-list action coverage (regrade tasks, e.g. Redwood):** covers the subset
of the regrade population whose **final (re-derived) rating ≥ 6**. Loans
regraded to ≤ 5 are dropped from follow-up (they are no longer adverse).
`covered_loan_count` / `covered_exposure` = Σ over final ≥ 6. Group `by_action`,
each action sorted ascending alphabetically; `loan_ids` ascending.

**Action mapping by final_rating** (Redwood pattern):
- final `8` (Nonaccrual) → `partial_chargeoff_review`
- final `7` → `special_assets`
- final `6` → `watchlist`

**Workout queue (watch-list tasks, e.g. Summit):** includes **all** adverse
loans (`current_rating >= adverse_rating_min`), each assigned a
`recommended_action` based on a payment-status-first cascade, then risk class.
Sort the queue **descending by exposure, then ascending loan_id**.

**Action cascade (verified on Summit):**
1. `Nonaccrual` → `partial_chargeoff_review` (`projected_loss = true`)
2. `90+ Days Past Due` → `special_assets` (`projected_loss = false`)
3. `Current` + class `Watch` → `special_assets`
4. `Current` + class `Desirable` → `watchlist`
5. (`Current` + `Prime`/mild → `monitor`; `Doubtful`/`Projected Loss` current →
   `workout` — extend by analogy for unseen buckets.)

**watch_list_summary:**
- `adverse_rating_min` = the threshold from the prompt (e.g. 6).
- `adverse_loan_count` = count of loans with `current_rating >= adverse_rating_min`.
- `adverse_balance` = Σ `outstanding_balance` of those loans (verified:
  Summit 7,675,179.41).
- `risk_classes` = one row per adverse loan, sorted ascending `loan_id`, with
  `factor_score` (integer) and `risk_class` (with Nonaccrual ⇒ `Projected Loss`
  override).
- `monitoring_cadence` = `monthly` for an adverse watch-list.

**stress_results:** all DSCR-bearing adverse loans, ascending loan_id, with
`base_dscr`, `stressed_dscr = base/1.18` (2dp), `breaches_threshold`.
`breach_loan_ids` ascending.

**severe_bucket_counts:** group adverse loans by `(current_rating,
payment_status)`, sorted ascending `current_rating` then payment_status. Note
payment_status ascending is **string-ascending**, so `"90+ Days Past Due"`
sorts before `"Current"` (digit `9` < `C`), and `"Current"` before
`"Nonaccrual"`. `loan_count` and `exposure` (Σ outstanding_balance) per bucket.

## 3. Per-task archetypes & method

### A. Rating-migration review (Redwood)
1. `GET /api/policies`, `/api/branches/REDWOOD`, `/api/branches/REDWOOD/loans?min_current_rating=3`,
   `/api/branches/REDWOOD/metrics`, `/api/benchmarks/fdic/q4-2024`.
2. Re-derive `final_rating` per loan (2.1). Build `final_rating_exposure_totals`
   (all target loans, ascending final_rating — count + Σ exposure) and
   `migration_from_current_rating_3` (only loans whose current_rating == 3,
   grouped by final_rating, with ascending `loan_ids`).
3. `watch_list_action_coverage` over final ≥ 6 (2.7).
4. `npa_benchmark` (2.2) with `total_loans_noncurrent_pct`.
5. `material_downgrades` = loans with `final - current >= 2` notches worsening,
   ascending loan_id.
6. `top_problem_credit` = the worst final_rating loan (prefer Nonaccrual / highest
   final / largest exposure); include `borrower_name`, `payment_status`,
   `recommended_action`.

### B. Quarterly allocation package (Lakeview)
1. `GET /api/branches/LAKEVIEW`, `/applications`, `/sector-exposures`,
   `/metrics`, `/api/policies`.
2. Decide each application (2.6); compute `approved_amount` and
   `bank_capacity_used` per decision (2.3). Decisions sorted ascending
   `application_id`.
3. Aggregate `allocation` (2.3); `priority_ranking` = approved + conditional
   application_ids, highest committee funding priority first (strategic/stronger
   credits lead).
4. `concentration_flags` per near-ceiling conditional app (2.3).
5. `decline_reasons` map (only declined apps) with sorted reason-code lists.
6. `post_approval_concentrations` for every sector touched by an approval
   (reporting denominator = total_loans_outstanding + gross_approved_amount;
   2.3), sorted ascending sector.

### C. Credit-union segment posture (Civic NC)
1. `GET /api/credit-union-segments/{segment_id}`, `/api/policies`,
   `/api/benchmarks/ncua/q1-2025`, `/api/manifest`.
2. `state_metrics` from the segment `state_code` NCUA row (integer values);
   `benchmark_version = "ncua_q1_2025"`.
3. `peer_comparison`: `peer_states` from segment (ascending); direction vs `US`
   row and vs **median** of peer rows (2.2), each ∈ {higher, lower, equal}.
4. `posture` from capacity vs external risk: capacity available + external risk
   weaker ⇒ `continue_with_tighter_conditions`; capacity constrained ⇒
   `temporarily_pause`; external risk strong ⇒ `continue_approving`.
5. `controls.required_checklist_gates` = segment `minimum_checklist`;
   `added_operating_controls` = the standard tighter set (pre-close insurance
   binder verification, lien perfection prior to funding, senior underwriter
   second review, quarterly state benchmark monitoring, monthly segment
   delinquency watch); include `committee_exception_for_capacity_overrun` only
   when capacity is constrained.
6. `escalation_triggers`: ascending `trigger_id` (ET001 delinquency ≥ 90 bps →
   `credit_risk_manager`; ET002 missing insurance/lien exception →
   `operations_control_manager`; ET003 quarterly capacity exceeded/exception →
   `lending_committee_chair`). Condition/owner enums only.
7. `interpretation`: derive `capacity_status`, `external_risk_status`,
   `risk_tolerance` (from segment), and the matching `committee_message`.

### D. Watch-list stress packet (Summit)
1. `GET /api/branches/SUMMIT`, `/api/branches/SUMMIT/loans?min_current_rating=6`,
   `/api/policies`.
2. `watch_list_summary` (2.7): factor scores, risk classes (Nonaccrual ⇒
   Projected Loss), `adverse_balance`, `monitoring_cadence = monthly`.
3. `stress_results` (2.5): `+200bp`, `dscr/1.18`, threshold 1.0, DSCR-bearing
   loans only.
4. `workout_queue` (2.7): all adverse loans, action cascade, descending exposure
   then ascending loan_id.
5. `severe_bucket_counts` (2.7) with the string-ascending payment_status order.

### E. Competing CRE decision (Harbor)
1. `GET /api/branches/HARBOR`, `/metrics`, `/loans?loan_type=CRE`,
   `/sector-exposures`, `/applications`, `/api/policies`,
   `/api/benchmarks/fdic/q4-2024`.
2. For each competing CRE app compute `weighted_cdfi_score` (1dp, lower better)
   using `cre_weighted_score` weights (capacity 0.45, collateral_exposure 0.36,
   conditions 0.11, character 0.05, capital 0.03) — capacity (DSCR) and
   collateral (LTV) carry 81% of the weight; map to `score_class`
   (`approve_quality` ≤ 2.0, `conditional` ≤ 3.0, `weak` > 3.0).
3. `stress` (2.5 CRE dual): `formula = "dscr * 0.85 / 1.18"`, threshold 1.0.
   `weak_dscr` reason fires when stressed < 1.0.
4. `concentration` (2.2/2.3): existing & post-approval CRE concentration vs
   `cre_policy_limit_pct`; FDIC variance vs `total_real_estate_30_89_pct`.
5. `applications_compared` (ascending application_id): each with score, class,
   decision, sorted reason_codes. Reasons include `fdic_adverse_variance` and
   `sector_breach` (both apps at an under-performing, CRE-heavy branch) plus
   `weak_dscr` only for the stressed-breach app.
6. `recommended_path`: select the **lower** (better) weighted score app; its
   `decision` becomes `path`. `unselected_disposition` ∈ `{decline, defer}`;
   unselected reason_codes ascending.
7. `conditions`: for a `participation_required` selected CRE path, the full set
   (all 7 enum values), sorted ascending alphabetically:
   bank_retained_exposure_cap, committee_cre_exception,
   minimum_dscr_covenant_1_25, no_additional_cre_without_committee_review,
   quarterly_financial_reporting, tenant_roll_and_lease_review,
   updated_appraisal_before_close.

## 4. Output field definitions & exact enums (consolidated)

- `payment_status`: `Current`, `30 Days Past Due`, `60 Days Past Due`,
  `90+ Days Past Due`, `Nonaccrual`.
- `recommended_action` / watch-list `action`: `monitor`, `watchlist`,
  `special_assets` (underscore — this is the spelling used by both the Redwood
  and Summit templates and their gold answers), `workout`,
  `partial_chargeoff_review`, `legal_referral`. Still copy the exact token from
  the task's `answer_template.json` enum in case a future template differs.
- `decision`: `approve`, `conditional_approve`, `decline`, `defer`,
  `participation_required`.
- `conditions`: `participation_required`, `reduced_amount`, `board_exception`,
  `sba_guaranty_required`, `startup_monitoring`, `none`.
- `handling`: `approve`, `conditional_approve`, `decline`,
  `participation_required`, `none`.
- `risk_class`: `Prime`, `Desirable`, `Satisfactory`, `Watch`, `Doubtful`,
  `Projected Loss`.
- `score_class`: `approve_quality`, `conditional`, `weak`.
- `posture`: `continue_approving`, `continue_with_tighter_conditions`,
  `temporarily_pause`.
- `capacity_status`: `capacity_available`, `capacity_constrained`,
  `no_capacity`.
- `external_risk_status`: `stronger_than_national_and_peers`,
  `mixed_vs_national_and_peers`, `weaker_than_national_and_peers`.
- `risk_tolerance`: `restrained`, `moderate`, `expansive`.
- `committee_message` (segment): `capacity_available_but_external_risk_weaker`,
  `pause_until_state_metrics_recover`, `routine_approval_path_supported`.
- `unselected_disposition`: `decline`, `defer`.
- Decline `reason_code` set: `capacity_limit`, `sector_breach`, `weak_dscr`,
  `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`,
  `underwater_collateral`, `policy_floor_missing`, `documentation_gap`,
  `fdic_adverse_variance`, `ncua_peer_weakness`.

**Ordering rules (apply unless the template says otherwise):**
- lists of loans/applications/actions: ascending `loan_id` / `application_id`;
- `final_rating` ascending; `sector` ascending; `action`/condition/reason-code
  ascending alphabetically; `trigger_id` ascending;
- `material_downgrades` ascending `loan_id`; `workout_queue` **descending**
  exposure then ascending `loan_id`; `severe_bucket_counts` ascending
  `current_rating` then string-ascending `payment_status`;
- `priority_ranking`: highest priority first (approved + conditional only);
- numeric lists inside objects follow the `ordering` field in the template.

## 5. Numeric conventions

- Money / exposure / balance: **2 decimals** USD (e.g. 1725000.00).
- Ratios (concentration, NPA, FDIC variance, post_approval_pct, limit_pct):
  **4 decimals** as a ratio (0.1897, not 18.97%).
- `variance_bps` / `*_variance_bps` / `policy_variance_bps`: **2 decimals**,
  **signed** (positive = branch/app worse than benchmark/policy); computed from
  the **unrounded** ratio difference × 10000.
- `dscr` / `base_dscr` / `stressed_dscr`: **2 decimals**.
- `weighted_cdfi_score`: **1 decimal** (lower is better).
- `factor_score`, ratings, counts, bps-in-state-metrics: integers.
- Percentages in policy/templates are ratios (0.19), never percent integers.
- Round only at output; keep unrounded intermediates for variance_bps so the bps
  figure stays consistent with the rounded ratio (Redwood 0.1135 ratio but
  1037.49 bps, not 1037.00).

## 6. Common misjudgments & exclusion rules

1. **Regrade population ≠ watch-list coverage.** Regrade population =
   `current_rating >= target_current_rating_min`. Watch-list action coverage =
   subset with **re-derived final_rating ≥ 6**. Do not list final ≤ 5 loans in
   coverage, and do not use current_rating to decide coverage.
2. **Severe-delinquency override is Nonaccrual only.** Nonaccrual ⇒
   `Projected Loss` regardless of factor_score. `90+ Days Past Due` does **not**
   override the score-derived class (SUM-LN-011/015 stay Desirable).
3. **Concentration denominator = `total_loans_outstanding`, not `total_assets`.**
   `total_assets` is ~25–35× larger and yields trivially small ratios. Always
   pull `total_loans_outstanding` from `metrics` (latest quarter).
4. **Pro-forma denominator grows with new principal.** For
   `post_approval_concentrations` the denominator = `total_loans_outstanding +
   gross_approved_amount`; for CRE `selected_post_approval_cre_concentration`
   both numerator and denominator grow by the selected `requested_amount`.
   Keep numerator and denominator consistent.
5. **`approved_amount` is always full principal; `bank_capacity_used` is the
   reduced, retained figure.** SBA-guaranty ⇒ `approved × (1 −
   sba_guaranty_pct)`; participation ⇒ sized to sector limit. Never substitute
   `bank_capacity_used` into `gross_approved_amount` or sector
   `exposure_after_approval`.
6. **`variance_bps` uses the unrounded ratio.** Recompute from the raw
   `exposure/total` fraction before multiplying by 10000, then round to 2dp.
   This avoids the 0.5–1 bps drift that matching judges penalize.
7. **Stress excludes null-DSCR loans.** `stress_results` lists only loans with a
   DSCR; null-dscr loans (often Consumer/Equipment) still appear in
   `risk_classes` and `workout_queue`.
8. **Material downgrade threshold is 2 notches.** Include only loans worsened by
   ≥ 2 (`final - current >= 2`). Single-notch downgrades are not "material".
9. **`benchmark_metric` choice tracks portfolio focus.** General NPA review ⇒
   `total_loans_noncurrent_pct`; CRE decision task ⇒
   `total_real_estate_30_89_pct` paired with `delinquency_30_plus_pct`. Do not
   mix a noncurrent metric with a 30-89 branch figure.
10. **Payment-status ordering is string-ascending, not severity-ascending.**
    `"90+ Days Past Due"` < `"Current"` < `"Nonaccrual"` because `'9' < 'C'`.
    In `severe_bucket_counts`, a rating-7 "90+ DPD" bucket sorts before a
    rating-7 "Current" bucket.
11. **`top_problem_credit` should be the genuinely worst credit** (highest
    final_rating, prefer Nonaccrual, then largest exposure), not the largest
    balance regardless of rating.
12. **Selection in a competing-credit task = lower weighted score.** The
    selected app is the one with the **lower** `weighted_cdfi_score` (better
    quality); its `decision` becomes the `path`; the other is
    `defer`/`decline`.
13. **Always honor the exact enum spelling in the target `answer_template.json`.**
    The action enum is consistently `special_assets` (underscore) across the
    train templates and gold answers; still verify against the target template's
    `allowed_values` rather than assuming.
14. **Do not invent peer states or benchmark versions.** Peer states come from
    the segment JSON; benchmark versions come from `/api/manifest`. Use only the
    enum choices and identifiers the template allows.

## 7. End-to-end execution checklist

1. Read the prompt; fix the `branch_id` / `segment_id`, as-of date, and which
   answer_template to mirror.
2. `GET /api/policies` and `/api/manifest` first; cache the rating tables,
   stress formulas, score weights, and benchmark versions.
3. Pull the branch, metrics (latest quarter), loans (`?min_current_rating=` as
   needed), sector-exposures, applications, and the relevant benchmark
   (FDIC and/or NCUA all-rows).
4. Re-derive ratings / scores / stresses with the rules above; never trust the
   stored `current_rating` as the final answer.
5. Assemble the JSON exactly matching the template's `required_top_level_keys`
   and per-section `required_keys`, applying ordering and precision rules.
6. Emit only valid JSON — no narrative outside the object. Money 2dp, ratios 4dp,
   bps 2dp signed, scores 1dp, DSCR 2dp.
