# SKILL — Credit-Risk / Lending-Committee Decision Packets (task_group_011)

A self-contained SOP for producing committee-ready JSON answers against the
shared **credit-office public REST API**. Distilled from reasoning through five
training archetypes (Redwood rating-migration, Lakeview allocation, Civic CU
segment posture, Summit watch-list stress, Harbor competing-CRE). No gold
answers used — this is the *method*, not the answers.

---

## 0. Environment & ground rules

- Base URL: `<remote-env-url>`  (remote; no local `env/` source, no DB).
- Read-only: **GET only**. No auth. Never call `/api/judge`.
- Always JSON. Pipe through `jq`. Health: `GET /api/health`. Catalog: `GET /api/manifest`.
- Policy version: `credit_policy_v2025Q1` (fetch `GET /api/policies` once — it holds
  every numeric rule below). Benchmark versions: FDIC `fdic_q4_2024`, NCUA `ncua_q1_2025`.
- Generated/committee date = `2025-03-31` (use as `review_date` / packet date).
- Every answer must conform to that task's `input/payloads/answer_template.json`.
  Enums and orderings there are **strict** — do not invent values.

---

## 1. Remote API usage SOP — endpoints, keys, query params

| Endpoint | Returns | Key fields / gotchas |
|---|---|---|
| `GET /api/health` | status + record counts | sanity check |
| `GET /api/manifest` | versions, seed `11011`, endpoint list | generated_at `2025-03-31T00:00:00Z` |
| `GET /api/policies` | ALL business rules (see §2) | single object; cache it |
| `GET /api/branches` | branch_id list (also returns CU segment ids) | branch ids are UPPERCASE |
| `GET /api/branches/{id}` | one branch | `cre_policy_limit_pct`, `sector_ceiling_pct`, `lending_capacity_q1`, `state_code`, `institution_type`, `total_assets`. **`total_loans_outstanding` is NOT here** (null) — get from `/metrics` |
| `GET /api/branches/{id}/metrics` | **LIST by quarter** | take `[0]` (latest = `2025Q1`). Fields: `nonperforming_loans`, `total_loans_outstanding`, `delinquency_30_plus_pct`, `allowance_for_loan_losses`, `net_charge_offs`, `total_deposits`, `quarter` |
| `GET /api/branches/{id}/loans` | loans | `?loan_type=`, `?payment_status=`, `?min_current_rating=`. Loan fields: `loan_id`, `current_rating`, `payment_status`, `dscr`(nullable), `ltv`(nullable), `debt_to_asset`(nullable), `fico`(nullable), `liquidity_months`(nullable), `outstanding_balance`, `sector`, `loan_type`, `borrower_name`, `collateral_value`, `annual_debt_service` |
| `GET /api/branches/{id}/sector-exposures` | sector rows | fields are `sector`, `current_exposure`, `limit_pct`, `grandfathered` (0/1) — **NOT** `exposure`/`outstanding_balance`/`balance` |
| `GET /api/branches/{id}/applications` | pending apps | optional `?loan_type=`. Fields: `application_id`, `loan_type`, `requested_amount`, `dscr`(nullable), `ltv`, `fico`(nullable), `sector`, `bankruptcy_months_ago`, `documentation_complete`, `years_in_business`, `sba_guaranty_pct`, `purpose`, `proposed_rate`, `total_debt`, `total_assets` |
| `GET /api/benchmarks/fdic/q4-2024` | FDIC ratios | `total_loans_noncurrent_pct`=0.0098, `total_real_estate_noncurrent_pct`=0.0121, `total_real_estate_30_89_pct`=0.0051, `construction_development_noncurrent_pct`=0.0076, `construction_development_30_89_pct`=0.0042 |
| `GET /api/benchmarks/ncua/q1-2025` | NCUA rows | optional `?state_code=NC`. Row fields: `state_code`, `delinquency_bps`, `loan_to_share_pct`, `positive_net_income_pct`, `roaa_bps`. Always returns a `rows[]` array even for a single state |
| `GET /api/credit-union-segments/{id}` | CU segment | `segment_id`, `segment_name`, `state_code`, `current_outstanding`, `quarterly_capacity`, `risk_tolerance`, `peer_states[]`, `minimum_checklist[]`, `internal_context{recent_delinquency_bps, staffing_constraint, control_issue}`, `portfolio_focus[]`, `notes` |

### Query-param semantics (critical)
- `?min_current_rating=N` → returns loans with **`current_rating >= N`** (rating scale:
  **3 = best, 8 = worst**; higher = worse). This is an inclusive lower bound on a
  "worse-or-equal" scale.
- `?loan_type=` exact match (e.g. `CRE`, `C%26I` → URL-encode `&` as `%26`).
- `?payment_status=` exact match (spaces → `%20`).
- `?state_code=` 2-letter, returns `rows[]` with one element.

### Which endpoint feeds which answer section
- **Redwood (001)**: `/branches/REDWOOD` + `/branches/REDWOOD/loans?min_current_rating=3` + `/metrics`[0] + `/policies` + `/benchmarks/fdic/q4-2024`.
- **Lakeview (002)**: `/branches/LAKEVIEW` + `/applications` + `/sector-exposures` + `/metrics`[0] + `/policies`.
- **Civic (003)**: `/credit-union-segments/CIVIC_NC_FIRE_EMS` + `/benchmarks/ncua/q1-2025` (all rows + `?state_code=NC`) + `/policies`.
- **Summit (004)**: `/branches/SUMMIT` + `/loans?min_current_rating=6` + `/metrics`[0] + `/policies`.
- **Harbor (005)**: `/branches/HARBOR` + `/applications?loan_type=CRE` + `/sector-exposures` + `/loans` + `/metrics`[0] + `/policies` + `/benchmarks/fdic/q4-2024`.

---

## 2. Universal business rules (from `GET /api/policies`)

### 2.1 Risk-rating re-derivation (`risk_rating`)
Final re-derived rating = **worst (highest numeric)** of the available factor-derived
ratings. Rating scale 3 (best) → 8 (worst).

- **DSCR → rating**: `dscr >= 1.5 → 3`; `>= 1.25 → 4`; `>= 1.05 → 5`; `>= 1.0 → 6`; `< 1.0 → 7`.
- **LTV → rating**: `ltv <= 0.65 → 3`; `<= 0.75 → 4`; `<= 0.85 → 5`; `<= 1.0 → 6`; `> 1.0 → 7`.
- **Delinquency minimum (hard floor)**: `Current → none`; `30 DPD → 4`; `60 DPD → 5`; `90+ DPD → 7`; `Nonaccrual → 8`.
- **Dominant-factor rule**: `final_rating = max( current_rating, dscr_rating(if DSCR), ltv_rating(if LTV), delinquency_floor(if status has one) )`.
  Treat `current_rating` itself as a floor so re-derivation **only downgrades or holds**,
  never spuriously upgrades (a Current loan with strong DSCR stays; a 30-DPD loan at 5 is not
  upgraded to 4 just because the delinquency floor is 4). When DSCR/LTV are null, that factor
  is simply omitted.
- **Severe-delinquency override**: `90+ DPD → 7` and `Nonaccrual → 8` are mandatory floors that
  override even a strong DSCR (e.g. a Nonaccrual loan with DSCR 1.55 lands at 8, not 5).
- **Material downgrade**: `final_rating - current_rating >= risk_rating.material_downgrade_notches` (= **2**). Only these go in `material_downgrades`.

### 2.2 Stress formulas (`stress`)
- `coverage_breach_threshold` = **1.0** (breach when `stressed_dscr < 1.0`).
- **Watch-list (Summit)**: `stressed_dscr = dscr / (1 + 0.18)` → `dscr / 1.18`. Shock label `+200bp`.
- **CRE dual stress (Harbor)**: `stressed_dscr = dscr * 0.85 / (1 + 0.18)` → `dscr * 0.72034`.
- Only loans/apps **with a non-null DSCR** appear in `stress_results`. Loans with null DSCR
  are excluded from the stress list (but stay in watch-list/workout). `breaches_threshold` is boolean.
- `breach_loan_ids` = the subset where `stressed_dscr < 1.0`, **ascending loan_id**.

### 2.3 CDFI factor scoring & risk classes (`cdfi_factor_scores`)
Sum available factor subscores (each 0–6) → `factor_score` (integer). **Skip null factors**
(do not add a max penalty for missing data).

| Factor | bands → score |
|---|---|
| `ltv` | `<0.40→0`, `0.40–0.60→2`, `0.60–0.80→4`, `>0.80→6` |
| `debt_to_asset` | `<0.40→0`, `0.40–0.60→2`, `0.60–0.80→4`, `>0.80→6` |
| `fico` | `>720→0`, `680–720→1`, `580–679→3`, `<580→5` |
| `liquidity_months` | `>12→0`, `6–12→1`, `3–6→3`, `<3→5` |

`risk_class` from `factor_score`:
- `Prime` 0–5 · `Desirable` 6–9 · `Satisfactory` 10–13 · `Watch` 14–18
- `Doubtful` `>=19` · `Projected Loss` `>=19 AND ltv > 1.0`.

`projected_loss` (workout_queue boolean) = true iff the loan's `risk_class == "Projected Loss"`
(i.e. `factor_score >= 19` **and** `ltv > 1.0`). Apply the rule literally even for Nonaccrual
loans that don't meet both conditions.

### 2.4 CRE weighted score (`cre_weighted_score`) — Harbor
Five-C weights: `capacity 0.45`, `collateral_exposure 0.36`, `conditions 0.11`,
`character 0.05`, `capital 0.03` (sum 1.0). Map app/loan factors to the C's (collateral_exposure←ltv,
character←fico, capital←debt_to_asset, capacity/conditions←DSCR/sector-specific). Multiply each C's
factor score by its weight and sum → `weighted_cdfi_score` (1 dp, **lower is better**).
- `score_class`: `approve_quality` if `<= 2.0`; `conditional` if `<= 3.0`; `weak` if `> 3.0`.
- The app with the **lower** weighted score (better DSCR + lower LTV) is the stronger credit.

### 2.5 Capacity & concentration (`capacity_concentration`)
- Q1 lending capacity = `branches.lending_capacity_q1` (USD).
- Single-sector default ceiling = `branches.sector_ceiling_pct` (0.21–0.24). Per-sector overrides
  live in `/sector-exposures` (`limit_pct`); CRE-related sectors carry `limit_pct = cre_policy_limit_pct` (0.29 at HARBOR).
- CRE policy limit = `branches.cre_policy_limit_pct` (the field name — **not** `cre_limit_pct`).
- **Concentration denominator = `/metrics[0].total_loans_outstanding`** (NOT `total_assets`, NOT branch sum of balances). Critical pitfall.
- `post_approval_pct = (sector current_exposure + approved app amount in that sector) / total_loans_outstanding`, 4 dp.
- `over_limit` / sector `flag` = `post_approval_pct > limit_pct`.
- **Grandfathering**: existing over-ceiling exposure may stay (grandfathered=1), but **new approvals
  may not worsen** that sector without a mitigation. Allowed mitigations: `participation_required`,
  `reduced_amount`, `board_exception`. Non-mitigated breaches → decline or participation_required.

### 2.6 Decline reason codes & decision enums
Decline reason-code enum (12): `capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`,
`low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`,
`documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`. Sort ascending alphabetically.

Decision enum (5): `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`.

Task-002 conditions enum (6): `participation_required`, `reduced_amount`, `board_exception`,
`sba_guaranty_required`, `startup_monitoring`, `none`. (Use `none` for clean approvals.)

Decision heuristics (Lakeview): `approve` if DSCR≥1.25, LTV≤0.85, fico≥680, no sector breach,
documentation_complete, within capacity; `conditional_approve` / `reduced_amount` when capacity-tight
or LTV high but creditable; `decline` for DSCR<1.0, LTV>1.0, recent bankruptcy, sector breach w/o mitigation,
documentation gap; `defer` for missing documentation that is curable; `participation_required` /
`sba_guaranty_required` for SBA loans or capacity overruns.

### 2.7 Watch-list action coverage & workout queue (action enum, 6)
`monitor`, `watchlist`, `special-assets`, `workout`, `partial_chargeoff_review`, `legal_referral`.

Action mapping by final risk:
- Current / held rating, factor Watch-or-better → `monitor` or `watchlist`.
- Substandard (final 6) → `watchlist`/`special-assets`.
- 90+ DPD / final 7 → `special-assets`/`workout`.
- Nonaccrual / final 8 → `legal_referral` (or `partial_chargeoff_review` if projected loss).

Workout queue (`workout_queue`) ordering: **descending `exposure`, then ascending `loan_id`**.
Watch-list action coverage (`watch_list_action_coverage`) is grouped `by_action` ascending by action,
each with loan_count, exposure, ascending loan_ids.

---

## 3. Field-name & data-source gotchas (verified against live data)

1. `/metrics` is a **list** — index `[0]` for the current quarter. Field is `total_loans_outstanding`,
   branch record's same-named field is **null**.
2. Branch CRE field = **`cre_policy_limit_pct`** (0.29 Harbor). Do not query `cre_limit_pct`.
3. `/sector-exposures` balance field = **`current_exposure`**; ceiling field = **`limit_pct`**
   (per-sector, may equal sector_ceiling_pct or cre_policy_limit_pct); `grandfathered` is 0/1.
4. Loans/applications carry many **nullable** factor fields (`dscr`, `ltv`, `fico`, `debt_to_asset`,
   `liquidity_months`). Always null-check before scoring; null DSCR ⇒ exclude from stress list.
5. `loan_type` `C&I` must be URL-encoded `C%26I` when passed as a query param.
6. NCUA endpoint always returns `{benchmark_version, rows:[...]}` — even `?state_code=NC` gives a
   1-element `rows[]`. Do not assume a flat object.
7. Rating scale direction: **higher current_rating = worse**. `min_current_rating=3` = "3 or worse"
   (the whole regrade review set); `min_current_rating=6` = "adverse/watch-list" (Summit).
8. `nonperforming_loans` (NPA exposure) is a USD field in `/metrics`; it is **not** a count.
   `nonperforming_loans` at REDWOOD (1,725,000.00) equals the Nonaccrual loan balance — confirms NPA
   exposure comes from the metrics row, not a hand recount.

---

## 4. Per-task output field map & orderings

### Task 001 — Redwood rating migration  (`review_date = 2025-03-31`)
Top-level: `branch_id, review_date, portfolio_regrade, npa_benchmark, material_downgrades, top_problem_credit`.

`portfolio_regrade`:
- `target_current_rating_min` = 3 (the `min_current_rating` used).
- `target_loan_count` / `target_exposure` = count and 2-dp USD sum of the **rating>=3** population.
- `final_rating_exposure_totals`: **all** regrade loans grouped by `final_rating` (asc), with `loan_count`, `exposure`.
- `migration_from_current_rating_3`: **only loans whose `current_rating == 3`** (literal 3 — subset, not the whole population!), grouped by `final_rating` (asc), each row `{final_rating, loan_count, exposure, loan_ids(asc)}`. **Common trap:** do not use the whole >=3 population here.
- `watch_list_action_coverage`: `{covered_loan_count, covered_exposure, by_action[]}` — the downgraded loans needing follow-up, bucketed by the §2.7 action enum (asc by action).

`npa_benchmark`:
- `benchmark_version` = "fdic_q4_2024".
- `benchmark_metric` ∈ {`total_loans_noncurrent_pct`, `total_real_estate_noncurrent_pct`, `construction_development_noncurrent_pct`}. For Redwood (general bank) use `total_loans_noncurrent_pct` = 0.0098.
- `branch_npa_exposure` = `metrics[0].nonperforming_loans`; `branch_total_loans` = `metrics[0].total_loans_outstanding`.
- `branch_npa_ratio` = npa_exposure / total_loans (4dp); `fdic_benchmark_ratio` = 0.0098 (4dp).
- `variance_ratio` = branch_npa_ratio − fdic_benchmark_ratio (4dp, **signed**).
- `variance_bps` = variance_ratio × 10000 (2dp, signed; positive = adverse).

`material_downgrades`: loans where `final_rating − current_rating >= 2`, asc by `loan_id`; each
`{loan_id, current_rating, final_rating, downgrade_notches, exposure}`.

`top_problem_credit`: the single worst credit — pick by severe delinquency (Nonaccrual/90+), then
largest exposure, then largest downgrade. `{loan_id, borrower_name, exposure, current_rating,
final_rating, payment_status(enum), recommended_action(enum)}`. (REDWOOD: the Nonaccrual CRE loan
whose balance equals `nonperforming_loans` is the natural pick.)

### Task 002 — Lakeview allocation
Top-level: `branch_id, allocation, decisions, concentration_flags, decline_reasons, post_approval_concentrations`.

`allocation`: `lending_capacity_q1` (branch), `gross_approved_amount` (sum of approve+conditional approved_amounts),
`committed_capacity_amount`, `remaining_capacity` = capacity − committed, `priority_ranking`
(application_ids **highest priority first**, approve+conditional only).

`decisions`: asc by `application_id`; each `{application_id, decision(enum), approved_amount(2dp),
bank_capacity_used(2dp), conditions(enum)}`. Declined apps → `approved_amount` 0.00; `bank_capacity_used` 0.00.

`concentration_flags`: asc by `(sector, application_id)`; each `{sector, application_id, limit_pct(4dp),
post_approval_pct(4dp), flag, handling(enum)}`. `handling`: approve/conditional_approve/decline/participation_required/none.

`decline_reasons`: object mapping each **declined** application_id → sorted list of reason codes (§2.6 enum).

`post_approval_concentrations`: asc by sector; `{sector, exposure_after_approval(2dp), post_approval_pct(4dp),
limit_pct(4dp), over_limit(bool)}`. Denominator = `total_loans_outstanding`.

### Task 003 — Civic CU segment posture
Use NCUA rows for NC, US, and peer states (`segment.peer_states` = [SC, TN, VA]).

`state_metrics`: `state_code`="NC", `benchmark_version`="ncua_q1_2025", and the four NC integer values
exactly as reported (delinquency_bps=79, loan_to_share_pct=76, roaa_bps=44, positive_net_income_pct=76).

`peer_comparison`: `peer_states` asc ([SC,TN,VA]); `nc_vs_us` and `nc_vs_peer_median` each =
`{delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct}` with values `higher|lower|equal`
(direction of NC vs comparator). Peer median = median of the 3 peer-state values per metric.
- NC vs US: delinquency higher, loan_to_share higher, roaa lower, positive_net_income lower.
- NC vs peer median: delinquency higher, loan_to_share higher, roaa lower, positive_net_income lower.

`controls.required_checklist_gates` = segment's `minimum_checklist` (board_authorization,
equipment_invoice, public_contract_or_tax_support, proof_of_insurance, ucc_or_title_lien — note
fleet_replacement_plan & payer_contract_summary are allowed by the template but NOT in this segment's
checklist, so omit them). `added_operating_controls` chosen from the template set to address the
segment's `internal_context` (insurance-binder control_issue → pre_close_insurance_binder_verification;
staffing_constraint → senior_underwriter_second_review; external risk → quarterly_state_benchmark_monitoring,
monthly_segment_delinquency_watch, lien_perfection_prior_to_funding).

`escalation_triggers`: asc by `trigger_id`; each `{trigger_id, condition, owner}` using the condition &
owner enums. Standing set of 4 triggers with owners among credit_risk_manager / operations_control_manager /
lending_committee_chair (`segment_recent_delinquency_ge_90_bps` → note NC bps 79 & segment recent 86 are
both < 90, so it is a *standing* trigger, not currently breached).

`interpretation`: `capacity_status`=capacity_available (segment `quarterly_capacity` 2.9M, notes say
available); `external_risk_status`=weaker_than_national_and_peers; `risk_tolerance`=moderate (from segment);
`committee_message`=capacity_available_but_external_risk_weaker. `posture`=continue_with_tighter_conditions.

### Task 004 — Summit watch-list stress
Top-level: `branch_id, watch_list_summary, stress_results, workout_queue, severe_bucket_counts`.

`watch_list_summary`:
- `adverse_rating_min` = 6 (the requested threshold; adverse = `current_rating >= 6`).
- `adverse_loan_count`, `adverse_balance` (2dp) over the rating>=6 set.
- `risk_classes`: asc by `loan_id`; each `{loan_id, risk_class(enum §2.3), factor_score}`.
- `monitoring_cadence` ∈ {monthly, quarterly, semiannual} — pick by worst risk class present
  (Nonaccrual/Projected-Loss → monthly; otherwise quarterly).

`stress_results`: `shock_label` ("+200bp"/"watch_list_+200bp"), `breach_threshold`=1.0,
`results` asc by `loan_id` **for loans with DSCR only**: `{loan_id, base_dscr(2dp), stressed_dscr(2dp),
breaches_threshold(bool)}` using `stressed_dscr = dscr/1.18`. `breach_loan_ids` asc.

`workout_queue`: asc/desc by **exposure desc, then loan_id asc**: `{loan_id, exposure(2dp), risk_class,
payment_status(enum), recommended_action(enum §2.7), projected_loss(bool)}`. Includes all adverse loans
(even those without DSCR).

`severe_bucket_counts`: asc by `(current_rating, payment_status)`; each
`{current_rating, payment_status, loan_count, exposure}` summarizing the adverse population.

### Task 005 — Harbor competing-CRE
`applications_compared` = the two competing CRE apps (the larger `9xx`-series sentinel apps,
e.g. HAR-APP-901 / HAR-APP-902), asc by `application_id`. Each `{application_id, weighted_cdfi_score(1dp),
score_class(enum), decision(enum), reason_codes(sorted)}`.

`recommended_path`: `{selected_application_id, path(enum), unselected_application_id,
unselected_disposition ∈ {decline, defer}, unselected_reason_codes(sorted, restricted to
sector_breach/weak_dscr/high_ltv/fdic_adverse_variance)}`. Select = lower weighted score (survives
the dual stress `stressed_dscr = dscr*0.85/1.18 >= 1.0`); the unselected typically breaches stress
and/or sector.

`stress`: `formula` ("cre_dual_stress"/"stressed_dscr = dscr * 0.85 / (1 + 0.18)"),
`coverage_breach_threshold`=1.0, `results` asc by application_id: `{application_id, base_dscr(2dp),
stressed_dscr(2dp), breaches_threshold(bool)}`.

`concentration`: `cre_policy_limit_pct`(4dp = branch.cre_policy_limit_pct), `existing_cre_exposure`(2dp
= sum of CRE-sector `current_exposure`; CRE sectors are those whose `limit_pct` == cre_policy_limit_pct),
`existing_cre_concentration`(4dp = exposure/total_loans_outstanding),
`selected_post_approval_cre_concentration`(4dp = (existing + selected requested_amount)/total_loans_outstanding),
`selected_policy_variance_bps`(2dp signed = (post − limit)×10000),
`fdic_benchmark_metric`=`total_real_estate_30_89_pct`, `branch_delinquency_ratio`(4dp, branch analog of that metric — derive from metrics/loans), `fdic_benchmark_ratio`=0.0051(4dp),
`fdic_variance_ratio`(4dp signed = branch − benchmark), `fdic_variance_bps`(2dp signed = ratio×10000).

`conditions`: subset of the 7 allowed enum values, asc alphabetically (bank_retained_exposure_cap,
committee_cre_exception, updated_appraisal_before_close, tenant_roll_and_lease_review,
minimum_dscr_covenant_1_25, quarterly_financial_reporting, no_additional_cre_without_committee_review).

---

## 5. Numeric conventions

- **Money / USD**: round to **2 decimals**. Sum balances/exposures with 2-dp rounding at the end.
- **Ratios / concentrations / percentages expressed as ratios**: **4 decimals** (e.g. 0.1135).
- **Basis-point variances**: **2 decimals**, **signed** (positive = adverse / over-limit).
  `variance_bps = (branch_ratio − benchmark_ratio) × 10000`.
- **DSCR (base & stressed)**: 2 decimals. **weighted_cdfi_score**: 1 decimal (lower better).
- **Counts, ratings, factor_score**: integers.
- **breach / over_limit / projected_loss**: JSON booleans (`true`/`false`).
- Always honour the precision stated in each template field — it is checked.

---

## 6. Anticipated misjudgments & exclusion rules

1. **Regrade population vs watch-list.** Redwood regrades `current_rating >= 3` (min_current_rating=3);
   Summit watch-list is `current_rating >= 6`. Don't confuse the two thresholds. Within Redwood,
   `target_current_rating_min=3` covers almost the whole book; the *migration* block is the
   `current_rating == 3` subset only.
2. **Severe-delinquency override.** 90+ DPD forces ≥7, Nonaccrual forces 8, even if DSCR is strong.
   Don't let a good DSCR "rescue" a Nonaccrual.
3. **No spurious upgrades.** `final = max(current, factors)` — re-derivation only downgrades/holds.
   Do not upgrade a 5 to 4 because only the 30-DPD floor (4) is available.
4. **Concentration denominator.** Always `total_loans_outstanding` from `/metrics[0]`. Never `total_assets`
   (the branch record's, ~5× larger) — that would shrink every concentration % and hide breaches.
5. **NPA exposure source.** Use `metrics[0].nonperforming_loans` (USD), not a manual count, not total_assets.
6. **Stress-list DSCR filter.** Loans with null DSCR are excluded from `stress_results` but still appear in
   `workout_queue` / `watch_list_summary`. Don't drop them from the portfolio.
7. **`final_rating_exposure_totals` vs `migration_from_current_rating_3`.** Former = all rating>=3 loans by
   final_rating; latter = only current_rating==3 loans by final_rating (and includes `loan_ids`).
8. **Orderings.** `ascending loan_id` is **string** sort ("RED-LN-001" < "RED-LN-011" < "RED-LN-015" <
   "RED-LN-901"). `workout_queue` is exposure-desc then loan_id-asc. `applications_compared`,
   `material_downgrades`, `risk_classes`, `breach_loan_ids`, `severe_bucket_counts`,
   `post_approval_concentrations` — each has its own stated ordering; follow the template literally.
9. **Reason-code lists** sorted ascending alphabetically; `unselected_reason_codes` is restricted to the
   4-value subset, not the full 12.
10. **CRE sectors.** Identify CRE sectors as those whose `/sector-exposures` `limit_pct` equals
    `cre_policy_limit_pct` (0.29), not by name heuristics. Respect `grandfathered` — don't worsen a
    grandfathered over-ceiling sector without a mitigation.
11. **NCUA shape.** Always `.rows[]`; a `?state_code=` call returns a 1-element rows array, not a flat object.
12. **`benchmark_metric` choice.** Match the FDIC metric to the branch/sector mix: general bank NPA review →
    `total_loans_noncurrent_pct`; CRE delinquency variance (Harbor) → `total_real_estate_30_89_pct`;
    construction-heavy → construction metrics. The template enum pins Harbor to `total_real_estate_30_89_pct`.
13. **Two competing apps, not all CRE apps.** Harbor has several CRE-typed applications; the "competing"
    pair is the two large `9xx`-series sentinel apps. Confirm via amounts / the prompt's "two CRE requests".
14. **`score_class` thresholds use `<=`** (approve_quality ≤2.0, conditional ≤3.0, weak >3.0). Lower
    weighted score is better; pick the lower score as selected.
15. **`recent_bankruptcy`** trigger: years_in_business small + `bankruptcy_months_ago` present →
    `recent_bankruptcy`/`startup_risk`. `low_fico` only when fico is non-null and below band.
    `documentation_gap` only when `documentation_complete` is false.

---

## 7. Step-by-step derivation SOP (apply per task)

1. **Read the prompt** → identify branch_id / segment_id, the threshold param (`min_current_rating`),
   and which benchmark (FDIC vs NCUA) applies. Open the answer_template; list every required key, enum,
   and ordering.
2. **Fetch** `/api/policies` once. Fetch `/api/branches/{id}`, `/api/branches/{id}/metrics` (take `[0]`),
   the relevant loans/applications/sector-exposures with the right `?` filter, and the benchmark.
3. **Derive per-field** using §2 rules. Compute factor-derived ratings, stress DSCRs, factors scores,
   concentrations, and variances with the exact formulas and precisions in §5.
4. **Filter & group** with the exact subset rules (regrade pop vs migration subset; DSCR-only stress list;
   adverse rating>=6; decline-only reason map; competing-pair apps).
5. **Sort** each list to the template's ordering (string asc loan_id; exposure-desc; alpha asc reason codes;
   asc by final_rating / sector / trigger_id / application_id).
6. **Round** to the field's precision (money 2dp, ratios 4dp, bps 2dp signed, scores 1dp).
7. **Emit** a single JSON object with exactly the required top-level keys and per-item keys; omit extras.
8. **Self-check** against §6 pitfalls before finishing: denominator? NPA source? override applied? no
   upgrade? enum exact? ordering literal? precision honoured?
