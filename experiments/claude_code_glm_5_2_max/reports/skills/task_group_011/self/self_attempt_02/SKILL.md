# SKILL — Credit-Risk / Lending-Committee API Answering SOP

Self-evolved skill for task_group_011 credit-office evaluation. Distilled from reasoning
over 5 train tasks (Redwood rating migration, Lakeview allocation, Civic NC fire/EMS
segment posture, Summit watch-list stress, Harbor competing CRE) against the live
remote credit-office public REST API. **No gold answers were used** — this is the METHOD.

The environment is a shared remote credit office exposed only via a read-only JSON REST
API. Every task asks for a single committee-ready JSON object matching a per-task
`answer_template.json` (which doubles as the field/enum/precision contract). The job is
always: pull the right endpoints, re-derive a few quantified credit judgments from raw
loan/application/sector/benchmark fields using the **policy block**, then emit exact-shape
JSON with the right ordering, enums, and numeric precision.

---

## 0. Constants & conventions (apply to every task)

- API base: `<remote-env-url>` (from `environment_access.md`). Always GET, JSON,
  no auth. Pipe through `jq`. **Never** call `/api/judge` (none exists for you).
- Policy version: `credit_policy_v2025Q1`. Benchmark versions: FDIC `fdic_q4_2024`,
  NCUA `ncua_q1_2025`. Seed `11011`.
- Date canon: review/as-of date is `2025-03-31` (committee date).
- branch_id values are UPPERCASE (REDWOOD, LAKEVIEW, SUMMIT, HARBOR, …). Credit-union
  "branches" are also segment_ids (e.g. CIVIC_NC_FIRE_EMS).
- Rating scale: **integer, lower = better** (1 best … 8 worst observed). "Worst numeric
  rating" = the **max** integer.
- Numeric precision (from templates — obey exactly):
  - USD / money / exposure / balance → **2 decimals**.
  - Ratios (concentration %, NPA ratio, variance_ratio, delinquency ratio, LTV-as-ratio
    outputs) → **4 decimals** (these are fractions, e.g. 0.4695, NOT 46.95).
  - bps (variance_bps, policy_variance_bps) → **2 decimals**, **signed**
    (positive = adverse / branch worse than benchmark).
  - DSCR (base/stressed) → **2 decimals**. weighted_cdfi_score → **1 decimal**.
  - factor_score, loan_count, ratings, bps-from-NCUA-rows → **integer**.
- Ordering (obey per-field `ordering`):
  - loan_id, application_id, sector, action, reason_codes, conditions, trigger_id →
    **ascending string/alpha**.
  - final_rating, current_rating → **ascending integer**.
  - workout_queue → **descending exposure, then ascending loan_id**.
  - severe_bucket_counts → **ascending current_rating, then payment_status**.
- Output discipline: return ONLY a single JSON object. No narrative, no markdown fences,
  no trailing prose. Match `required_top_level_keys` exactly; do not add extra keys.

---

## 1. Remote API usage SOP

### Endpoint map (what each task section reads)

| Endpoint | Used for | Notes |
| --- | --- | --- |
| `GET /api/health` | sanity (table counts) | one-time liveness check |
| `GET /api/manifest` | benchmark versions, policy version, endpoint list | confirms `fdic_q4_2024` / `ncua_q1_2025` |
| `GET /api/policies` | **the rules** — risk-rating bands, CDFI factor scores, stress formulas, CRE weights, concentration policy | read FIRST and drive all derivation from it |
| `GET /api/branches` | all branches w/ `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`, `total_assets`, `state_code`, `institution_type`, `fdic_benchmark_set` | bank vs credit_union split |
| `GET /api/branches/{id}` | one branch | same fields as above |
| `GET /api/branches/{id}/metrics` | `total_loans_outstanding` (concentration/NPA **denominator**), `nonperforming_loans`, `delinquency_30_plus_pct`, allowance, charge-offs, deposits | optional `?quarter=2025Q1` |
| `GET /api/branches/{id}/loans` | per-loan `outstanding_balance` (exposure), `current_rating`, `dscr`, `ltv`, `debt_to_asset`, `fico`, `liquidity_months`, `payment_status`, `sector`, `loan_type`, `borrower_name`, `collateral_value`, `annual_debt_service`, `interest_rate` | filters: `?loan_type=`, `?payment_status=`, `?min_current_rating=` |
| `GET /api/branches/{id}/sector-exposures` | per-sector `current_exposure`, `limit_pct` (overrides branch default), `grandfathered` flag | sector totals **mix loan_types** — do NOT use for CRE-only exposure |
| `GET /api/branches/{id}/applications` | pending apps: `requested_amount`, `dscr`, `ltv`, `fico`, `debt_to_asset`, `liquidity_months`, `collateral_value`, `sector`, `loan_type` | filter `?loan_type=`; apps usually have null debt_to_asset/liquidity/payment_status |
| `GET /api/benchmarks/fdic/q4-2024` | 5 FDIC ratios (noncurrent + 30-89, by total / real-estate / C&D) | pick the metric whose universe+band matches your branch ratio |
| `GET /api/benchmarks/ncua/q1-2025` | per-state rows (incl `US` national) of `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct` | optional `?state_code=`; values are integers |
| `GET /api/credit-union-segments/{segment_id}` | CU segment: `peer_states`, `risk_tolerance`, `quarterly_capacity`, `current_outstanding`, `minimum_checklist`, `internal_context` (control_issue, recent_delinquency_bps, staffing_constraint, portfolio_yield_pct), `portfolio_focus`, `state_code` | drives train_003 |

### Calling habits
1. `GET /api/policies` first — it owns every threshold/formula. Re-derive from it; do not
   hard-code.
2. `GET /api/branches/{id}` + `/metrics?quarter=2025Q1` to anchor the branch.
3. Pull `/loans` (with the right `?min_current_rating=` or `?loan_type=` filter) and
   `/sector-exposures` and `/applications` as the task needs.
4. Pull the relevant benchmark (`/benchmarks/fdic/q4-2024` or `/benchmarks/ncua/q1-2025`).
5. For CU tasks: `/credit-union-segments/{segment_id}` + NCUA rows for the segment's
   `state_code`, its `peer_states`, and `US`.
6. Always pass `jq` to shape/verify; sum balances with `jq '[.[].outstanding_balance] | add'`.

---

## 2. Transferable business rules (INFERRED from policy + data)

### 2.1 Risk-rating re-derivation (train_001 Redwood, also feeds train_004)

From `/api/policies.risk_rating`:

**DSCR → rating (floor):** `>=1.5→3`, `>=1.25→4`, `>=1.05→5`, `>=1.0→6`, `<1.0→7`.
**LTV → rating (floor):** `<=0.65→3`, `<=0.75→4`, `<=0.85→5`, `<=1.0→6`, `>1.0→7`.
**Delinquency minimums (floor by payment_status):** `Current→null`,
`30 Days Past Due→4`, `60 Days Past Due→5`, `90+ Days Past Due→7`, `Nonaccrual→8`.

**Dominant-factor rule:** `final_rating = max( available factor ratings )` where the
available factors are the DSCR band, the LTV band, and the delinquency floor (Current
contributes no floor). When a loan has **zero** available factors (Current payment AND
no dscr AND no ltv), carry the `current_rating` forward unchanged.

- "Re-derive ratings for loans currently rated N or worse" → population = loans with
  `current_rating >= N` (use `/loans?min_current_rating=N`).
- `downgrade_notches = final_rating - current_rating`.
- **Material downgrade** threshold = `risk_rating.material_downgrade_notches` = **2**
  (i.e. `downgrade_notches >= 2`).
- `migration_from_current_rating_3` buckets ONLY loans whose `current_rating == 3`
  (NOT all regrade loans — just the current-3 cohort), grouped by `final_rating`,
  with ascending `loan_id` lists.
- `final_rating_exposure_totals` buckets the WHOLE regrade population by `final_rating`.

> **PITFALL — delinquency floors are "minimums":** a loan already rated worse than its
> delinquency floor (e.g. a 5-rated loan that is only 30-DPD, floor 4) would, under the
> literal `max(factors)` rule, *upgrade* to 4. The policy text supports the pure-factor
> max, but business logic of a downgrade review favors clamping with current:
> `final = max(current_rating, dscr_floor, ltv_floor, delinquency_floor)`. The two
> readings only diverge for loans rated worse than all their floors; for current-3 loans
> they always agree (downgrade). Decide per task; default to the literal policy max and
> flag upgrades explicitly. Verify migration totals don't silently drop a loan.

### 2.2 NPA & FDIC/NCUA variance (train_001, train_005)

**NPA exposure** = sum of `outstanding_balance` for loans with
`payment_status` ∈ {`90+ Days Past Due`, `Nonaccrual`} (the FDIC "noncurrent" definition:
90+ DPD plus nonaccrual). This **equals** `metrics.nonperforming_loans` — use that as a
cross-check (REDWOOD: loan-level Nonaccrual 1,725,000 == metrics 1,725,000).

**Denominator** = `metrics.total_loans_outstanding` (2025Q1) — **NOT `total_assets`**,
NOT the sum of sector exposures, NOT deposits. (REDWOOD 15,191,701.54; Harbor
14,933,688.02; Lakeview 14,334,094.87.)

```
branch_npa_ratio      = branch_npa_exposure / branch_total_loans          # 4dp
fdic_benchmark_ratio  = <chosen FDIC metric value>                        # 4dp
variance_ratio        = branch_npa_ratio - fdic_benchmark_ratio           # 4dp, signed
variance_bps          = variance_ratio * 10000                            # 2dp, signed (+ = adverse)
```

**Choosing the FDIC metric** (`npa_benchmark.benchmark_metric` enum): match the metric's
**universe + delinquency band** to the ratio you computed:
- `total_loans_noncurrent_pct` (0.0098) — broadest; default for a general bank branch
  whose NPA ratio is over **all** loans (90+/Nonaccrual).
- `total_real_estate_noncurrent_pct` (0.0121) — use when the branch ratio is over
  real-estate-secured loans only.
- `construction_development_noncurrent_pct` (0.0076) — C&D-heavy branch.
Available FDIC values: `total_loans_noncurrent_pct=0.0098`,
`total_real_estate_noncurrent_pct=0.0121`, `total_real_estate_30_89_pct=0.0051`,
`construction_development_noncurrent_pct=0.0076`, `construction_development_30_89_pct=0.0042`.
(REDWOOD NPA over all loans → `total_loans_noncurrent_pct`; Harbor CRE page uses
`total_real_estate_30_89_pct`.)

> **PITFALL — band/universe alignment:** the FDIC **`*_30_89_pct`** metrics cover the
> **30–89 DPD** band ONLY (`30 Days Past Due` + `60 Days Past Due`), EXCLUDING 90+ and
> Nonaccrual. The **`*_noncurrent_pct`** metrics cover 90+ DPD + Nonaccrual. Never compare
> a 30-89 branch ratio to a noncurrent benchmark or vice-versa. And never use
> `metrics.delinquency_30_plus_pct` as a stand-in — it is **all-loans 30+** (includes 90+
> & nonaccrual) and is a fraction of a different universe.

**FDIC real-estate 30-89 ratio (train_005 concentration block):**
```
branch_delinquency_ratio = (Σ balance of RE loans w/ payment_status in {30DPD, 60DPD})
                         / (Σ balance of RE loans)
fdic_benchmark_ratio     = 0.0051   # total_real_estate_30_89_pct
fdic_variance_ratio      = branch_delinquency_ratio - fdic_benchmark_ratio   # 4dp
fdic_variance_bps        = fdic_variance_ratio * 10000                        # 2dp, signed
```
"RE loans" universe = `loan_type` ∈ {`CRE`, `Residential Mortgage`} (FDIC total real
estate = 1-4 family + C&D + CRE + multifamily). SBA/Equipment loans secured by RE are a
judgment call; default to excluding them unless clearly RE-collateralized.

### 2.3 Capacity & concentration ceilings (train_002, train_005)

From `/api/policies.capacity_concentration`:
- `lending_capacity_field` = `branches.lending_capacity_q1` — the quarterly new-lending
  capacity (bank-retained). Sum of `approved_amount` (bank-retained portion) must not
  exceed it; breaches → `capacity_limit` / `participation_required` / `reduced_amount`.
- `single_sector_default_field` = `branches.sector_ceiling_pct`, BUT
  `branch_sector_override_table = sector_exposures` → **per-sector `limit_pct` from
  `/sector-exposures` overrides the branch default** (e.g. Lakeview Healthcare 0.19 vs
  default 0.21; Harbor Hospitality/Office 0.29 vs default 0.24).
- `allowed_mitigations` = `participation_required`, `reduced_amount`, `board_exception`.
- **Grandfathering:** `sector_exposures.grandfathered == 1` means existing over-ceiling
  exposure is grandfathered, but **new approvals may not worsen that sector** without
  mitigation. A new app in a grandfathered-over sector → `sector_breach` /
  `participation_required` / `decline`.

**Concentration denominator** = `metrics.total_loans_outstanding` (same as NPA —
**not total_assets**).

```
post_approval_pct (sector) = (existing_sector_exposure + approved_amount_in_sector)
                             / total_loans_outstanding        # 4dp
over_limit = post_approval_pct > limit_pct                     # boolean
cre_concentration           = existing_cre_exposure / total_loans_outstanding   # 4dp
policy_variance_bps         = (cre_concentration - cre_policy_limit_pct) * 10000 # 2dp signed
```
`existing_cre_exposure` = Σ `outstanding_balance` of loans with `loan_type == "CRE"`
(use `/loans?loan_type=CRE`). **Do not** sum sector-exposure rows for CRE — they mix
loan types (e.g. Harbor "Construction" sector includes an Equipment loan).

**Decision/concentration handling matrix (inferred):**
- Sector post-approval pct ≤ limit → `approve`.
- Post-approval pct > limit, mitigable (participation/reduction/board exception) →
  `conditional_approve` + mitigation, or `participation_required`.
- Post-approval pct > limit, unmitigable or grandfathered sector being worsened → `decline`
  with `sector_breach`.

### 2.4 CDFI-style risk classes & +200bp watch-list DSCR stress (train_004)

From `/api/policies.cdfi_factor_scores`:
- **Four factors only:** `debt_to_asset`, `fico`, `liquidity_months`, `ltv`.
  **DSCR is NOT a CDFI factor** (it feeds the stress test separately).
- Each factor maps to a score by band (debt_to_asset/ltv: 0/2/4/6; fico: 0/1/3/5;
  liquidity_months: 0/1/3/5). `factor_score` (integer) = sum of the four present factors.
- **Class by total score:** `Prime 0–5`, `Desirable 6–9`, `Satisfactory 10–13`,
  `Watch 14–18`, `Doubtful >=19`, `Projected Loss >=19 AND ltv>1.0`.

> **PITFALL — null CDFI factors:** most adverse loans have `fico=null` (and sometimes
> null dta/liquidity). Two readings:
> (a) **literal/zero:** null contributes 0 (factor not applicable). Tends to class severe
> loans as Desirable/Satisfactory — feels too lenient for a watch-list.
> (b) **conservative/worst-tier:** null scores the worst band (fico→5, dta→6,
> liquidity→5, ltv→6). Produces meaningful Doubtful/Projected-Loss classes for the worst
> credits (e.g. Summit SUM-LN-902 Nonaccrual LTV 1.18 → Projected Loss only under (b)).
> The policy is silent. **Lean (b) worst-tier for null factors in a watch-list context**
> (unknown risk = high risk), because `Projected Loss`/`projected_loss=true` only
> materializes that way; verify a couple of loans against the severity narrative.

**Watch-list DSCR stress** (train_004): use the LITERAL formula from
`/api/policies.stress`:
```
shock_label            = "+200bp"        # policy.stress.watch_list_parallel_shock
formula                = "stressed_dscr = dscr / (1 + 0.18)"
stressed_dscr          = base_dscr / 1.18
breach_threshold       = 1.00            # policy.stress.coverage_breach_threshold
breaches_threshold     = stressed_dscr < 1.00
```
Only run for loans where **DSCR is available** (skip nulls). `breach_loan_ids` = ascending
list of loan_ids with `breaches_threshold == true`.

> **PITFALL — "+200bp" label ≠ ÷1.02:** the parallel-shock *label* says +200bp but the
> policy's *coefficient* is `1.18`. Use the **formula string**, not the label. Do NOT
> compute `dscr×(1-0.02)` or `dscr/1.02`. (The apps/loans have null
> annual_debt_service/interest_rate, so you cannot re-derive DSCR from first principles
> anyway — the closed-form formula is authoritative.)

**Workout queue** (train_004): order `descending exposure, then ascending loan_id`.
`recommended_action` from the action enum graded by severity (see 2.7).
`projected_loss` (boolean) = `true` iff the loan's CDFI class is `Projected Loss`
(score>=19 AND ltv>1.0). `monitoring_cadence`: `monthly` for an adverse watch-list
(rating>=6 population), `quarterly`/`semiannual` only for milder books.

### 2.5 CRE weighted score & dual stress (train_005)

From `/api/policies.cre_weighted_score`:
- Weights (sum=1.0): `capacity 0.45`, `collateral_exposure 0.36`, `conditions 0.11`,
  `character 0.05`, `capital 0.03`.
- `weighted_cdfi_score` (1dp, **lower is better**) = Σ(weight × sub-score).
- `score_class`: `approve_quality` if score ≤ 2.0, `conditional` if ≤ 3.0, `weak` if > 3.0.

**Mapping the 5 C's to application fields (inferred — applications lack explicit C's):**
`capacity ← dscr`, `collateral_exposure ← ltv`, `character ← fico`, `capital ←
debt_to_asset`, `conditions ← qualitative/sector-stress`. Sub-score scale is not pinned:
likely the **risk-rating band (3–7)** from the corresponding threshold table for dscr/ltv,
and the CDFI fico/dta bands otherwise. Null sub-scores → 0 or worst-tier (same fork as
2.4). Because the class cutoffs (2.0/3.0) sit low, the rating-band (3–7) reading pushes
most apps to `weak`; the CDFI-band (0–5) reading is gentler. Pick one reading and apply
consistently; the **relative ranking between the two competing apps is robust either way**
(HAR-APP-901 dscr 1.47/ltv 0.68 beats HAR-APP-902 dscr 1.32/ltv 0.76 → 901 lower score).

**CRE dual stress (train_005 `stress` block):**
```
formula                      = "stressed_dscr = dscr * 0.85 / (1 + 0.18)"  # policy.stress.cre_dual_stress_formula
coverage_breach_threshold    = 1.00
stressed_dscr                = base_dscr * 0.85 / 1.18                     # 2dp
breaches_threshold           = stressed_dscr < 1.00
```
(0.85 = 15% NOI haircut; 1.18 = the same rate-shock coefficient as watch-list.)

### 2.6 Decline reason codes & decision enums (train_002, train_005)

**decision enum** (all decision fields): `approve`, `conditional_approve`, `decline`,
`defer`, `participation_required`.

**conditions enum** (train_002 per-app `conditions`): `participation_required`,
`reduced_amount`, `board_exception`, `sba_guaranty_required`, `startup_monitoring`,
`none`. (Note: `participation_required` is BOTH a decision and a condition.)

**concentration `handling` enum** (train_002): `approve`, `conditional_approve`,
`decline`, `participation_required`, `none`.

**reason_code enum** (decline_reasons / applications_compared reason_codes /
unselected_reason_codes): `capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`,
`low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`,
`policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`,
`ncua_peer_weakness`. **Always sort ascending alphabetically.**

**Inferred reason-code triggers:**
| code | trigger |
| --- | --- |
| `capacity_limit` | cumulative approved > `lending_capacity_q1` |
| `sector_breach` | post-approval sector pct > sector `limit_pct` (incl. worsening a grandfathered sector) |
| `weak_dscr` | dscr < 1.25 (severe < 1.0); also a *stressed* DSCR < 1.00 (train_005 unselected) |
| `high_ltv` | ltv > 0.85 (rating-5 band) |
| `low_fico` | fico < 580 |
| `underwater_collateral` | ltv > 1.0 |
| `recent_bankruptcy` | from borrower notes (not a numeric field) |
| `startup_risk` | startup/early-stage borrower (notes/loan_type) |
| `policy_floor_missing` | missing a required checklist/policy-minimum item |
| `documentation_gap` | missing docs → grounds for `defer` |
| `fdic_adverse_variance` | branch FDIC variance_bps > 0 (adverse) |
| `ncua_peer_weakness` | CU segment whose state/peer NCUA metrics are weaker (CU tasks) |

`unselected_reason_codes` (train_005) is restricted to the subset
`{sector_breach, weak_dscr, high_ltv, fdic_adverse_variance}`.

### 2.7 Watch-list action coverage & workout queues (train_001, train_004)

**`recommended_action` / coverage `action` enum** (note the hyphen):
`monitor`, `watchlist`, `special-assets`, `workout`, `partial_chargeoff_review`,
`legal_referral`.

**Inferred severity → action mapping** (grade by final_rating + payment_status):
| trigger | action |
| --- | --- |
| stable / final_rating ≤ 4, Current | `monitor` |
| final_rating 5 (Watch) | `watchlist` |
| final_rating 6 (Doubtful-ish) | `special-assets` |
| final_rating 7, or 90+ DPD | `workout` |
| Nonaccrual w/ loss indicators | `partial_chargeoff_review` |
| Nonaccrual + secured-impairment / ltv>1.0 / fraud | `legal_referral` |

**watch_list_action_coverage** (train_001): population = the **regrade population**
(loans `current_rating >= target_current_rating_min`), each assigned an action; the
`monitor` bucket holds the stable ones so the coverage sums to the whole regrade
population. `by_action` groups, ordered `ascending by action`, with ascending `loan_id`
lists. `top_problem_credit` = the single worst credit (lowest final_rating number? no —
**highest final_rating**, tie-break by exposure desc, then severity of payment_status);
its `recommended_action` uses the same enum.

> **PITFALL — regrade population vs watch-list vs severe buckets:** these are DIFFERENT
> populations. (a) Regrade population = `current_rating >= N` where N is the task's target
> (REDWOOD N=3, SUMMIT N=6). (b) `severe_bucket_counts` (train_004) groups the **adverse**
> population (rating>=6) by `(current_rating, payment_status)`. (c) Watch-list action
> coverage (train_001) covers the regrade population. Don't conflate them.

### 2.8 Credit-union segment posture (NCUA) — train_003

Driven by `/credit-union-segments/{segment_id}` + `/benchmarks/ncua/q1-2025` rows.

- `state_metrics` = the NCUA row for the segment's `state_code`, reported **as integers
  exactly** (`delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`).
- `peer_comparison.peer_states` = the segment's `peer_states`, sorted ascending (e.g.
  CIVIC → `[SC, TN, VA]`). `peer_median` = median of each metric across peer_states.
- `nc_vs_us` / `nc_vs_peer_median`: per-metric direction enum `higher`/`lower`/`equal`
  (NC value vs US / vs peer median).
- `controls.required_checklist_gates` = the segment's `minimum_checklist` set
  (CIVIC: `board_authorization, equipment_invoice, public_contract_or_tax_support,
  proof_of_insurance, ucc_or_title_lien`). Only add a template-enum gate if the segment
  data supports it (e.g. `fleet_replacement_plan` only for fleet/vehicle focus).
- `controls.added_operating_controls`: choose from the enum, mapped from
  `internal_context`:
  - `control_issue` about insurance binders → `pre_close_insurance_binder_verification`
  - staffing constraint / one senior underwriter → `senior_underwriter_second_review` +
    `lien_perfection_prior_to_funding`
  - external state delinquency > national → `quarterly_state_benchmark_monitoring` +
    `monthly_segment_delinquency_watch`
  - capacity pressure → `committee_exception_for_capacity_overrun`
- `escalation_triggers`: list all relevant conditions from the enum, each with an owner:
  - `segment_recent_delinquency_ge_90_bps` → `credit_risk_manager`
  - `missing_insurance_or_lien_exception` → `operations_control_manager`
  - `quarterly_capacity_exceeded_or_exception_requested` → `lending_committee_chair`
  - `state_delinquency_gap_widens_25_bps` → `credit_risk_manager`
  (trigger_id ascending; use T1/T2/… or numeric.)
- `interpretation`: derive from data —
  - `capacity_status`: `capacity_available` if `quarterly_capacity` not exhausted by
    `current_outstanding` trajectory; else `capacity_constrained` / `no_capacity`.
  - `external_risk_status`: compare segment state (`state_code`) vs `US` and vs all
    `peer_states` on `delinquency_bps` (primary) + others. `weaker_than_national_and_peers`
    if NC delinquency > US AND > peer median; `stronger_…` if lower than both;
    `mixed_…` otherwise.
  - `risk_tolerance`: take directly from segment's `risk_tolerance` field.
  - `committee_message`: tie to the combination — `capacity_available_but_external_risk_weaker`
    when capacity ok but state delinquency elevated; `pause_until_state_metrics_recover`
    when risk severe; `routine_approval_path_supported` when both clean.
  - `posture`: `continue_with_tighter_conditions` if capacity ok but external risk weaker
    + control issues (CIVIC case: NC delinq 79 > US 58 and > all peers; recent_delinquency
    86 bps < 90 trigger threshold so not paused); `continue_approving` if all clean;
    `temporarily_pause` if external risk severe / capacity gone.

> **PITFALL — `segment_recent_delinquency_ge_90_bps` threshold:** the segment's
> `internal_context.recent_delinquency_bps` (CIVIC 86) is BELOW 90, so that escalation
> trigger is **armed but not currently breached** — list it as a monitored trigger, do not
> report the segment as paused. Compare against 90, not against the state's 79.

---

## 3. Output field definitions & exact enums (consolidated)

All enums are closed — emit ONLY listed values. `payment_status` enum (used across tasks):
`Current`, `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`.

- **train_001** top keys: `branch_id, review_date, portfolio_regrade, npa_benchmark,
  material_downgrades, top_problem_credit`.
  - `portfolio_regrade`: `target_current_rating_min`, `target_loan_count`,
    `target_exposure`, `final_rating_exposure_totals` (asc final_rating),
    `migration_from_current_rating_3` (current-3 cohort, asc final_rating, loan_ids asc),
    `watch_list_action_coverage{covered_loan_count,covered_exposure,by_action}`.
  - `npa_benchmark`: `benchmark_version, benchmark_metric, branch_npa_exposure,
    branch_total_loans, branch_npa_ratio, fdic_benchmark_ratio, variance_ratio,
    variance_bps`.
  - `material_downgrades`: list (asc loan_id) of `{loan_id,current_rating,final_rating,
    downgrade_notches,exposure}`, downgrade_notches ≥ 2.
- **train_002** top keys: `branch_id, allocation, decisions, concentration_flags,
  decline_reasons, post_approval_concentrations`.
  - `allocation`: `lending_capacity_q1, gross_approved_amount,
    committed_capacity_amount, remaining_capacity, priority_ranking` (approved +
    conditional_approve app_ids, highest priority first).
  - `decisions`: asc application_id; `{application_id,decision,approved_amount,
    bank_capacity_used,conditions}`; money 2dp.
  - `concentration_flags`: sort by sector then application_id; `{sector,application_id,
    limit_pct,post_approval_pct,flag,handling}`; pct 4dp.
  - `decline_reasons`: `{app_id: [sorted reason_codes]}`.
  - `post_approval_concentrations`: asc sector; `{sector,exposure_after_approval,
    post_approval_pct,limit_pct,over_limit}`.
- **train_003** top keys: `segment_id, posture, state_metrics, peer_comparison, controls,
  escalation_triggers, interpretation` (enums in §2.8).
- **train_004** top keys: `branch_id, watch_list_summary, stress_results, workout_queue,
  severe_bucket_counts`.
  - `watch_list_summary`: `adverse_rating_min, adverse_loan_count, adverse_balance,
    risk_classes` (asc loan_id; `{loan_id,risk_class,factor_score}`),
    `monitoring_cadence`.
  - `stress_results`: `shock_label, breach_threshold, results` (asc loan_id, DSCR-only;
    `{loan_id,base_dscr,stressed_dscr,breaches_threshold}`), `breach_loan_ids` (asc).
  - `workout_queue`: desc exposure then asc loan_id; `{loan_id,exposure,risk_class,
    payment_status,recommended_action,projected_loss}`.
  - `severe_bucket_counts`: asc current_rating then payment_status; `{current_rating,
    payment_status,loan_count,exposure}`.
- **train_005** top keys: `branch_id, applications_compared, recommended_path, stress,
  concentration, conditions`.
  - `applications_compared`: asc application_id; `{application_id,weighted_cdfi_score,
    score_class,decision,reason_codes}` (score 1dp; reason_codes asc alpha).
  - `recommended_path`: `{selected_application_id,path,unselected_application_id,
    unselected_disposition,unselected_reason_codes}` (unselected_disposition ∈
    {decline,defer}; unselected_reason_codes ⊆ {sector_breach,weak_dscr,high_ltv,
    fdic_adverse_variance}, asc alpha).
  - `stress`: `formula, coverage_breach_threshold, results` (asc application_id;
    `{application_id,base_dscr,stressed_dscr,breaches_threshold}`).
  - `concentration`: `cre_policy_limit_pct, existing_cre_exposure,
    existing_cre_concentration, selected_post_approval_cre_concentration,
    selected_policy_variance_bps, fdic_benchmark_metric(=total_real_estate_30_89_pct),
    branch_delinquency_ratio, fdic_benchmark_ratio, fdic_variance_ratio,
    fdic_variance_bps`.
  - `conditions`: list (asc alpha) from `bank_retained_exposure_cap,
    committee_cre_exception, updated_appraisal_before_close,
    tenant_roll_and_lease_review, minimum_dscr_covenant_1_25,
    quarterly_financial_reporting, no_additional_cre_without_committee_review`.

---

## 4. Anticipated misjudgments & exclusion rules (checklist)

1. **Concentration/NPA denominator**: use `metrics.total_loans_outstanding` — never
   `total_assets`, never sum of `sector_exposures`, never `total_deposits`.
2. **CRE exposure**: sum `loan_type=="CRE"` loan balances from `/loans`, NOT sector rows
   (sectors mix Equipment/SBA/CRE).
3. **NPA exposure**: `90+ DPD + Nonaccrual` balances == `metrics.nonperforming_loans`
   (cross-check). Do not include 30/60 DPD.
4. **FDIC band alignment**: `*_noncurrent_pct` ↔ (90+ + Nonaccrual); `*_30_89_pct` ↔
   (30 DPD + 60 DPD only). Never mix. `metrics.delinquency_30_plus_pct` ≠ any FDIC metric.
5. **regrade vs watch-list vs severe buckets**: different populations — regrade =
   `current_rating >= task_min` (REDWOOD 3, SUMMIT 6); `migration_from_current_rating_3`
   = only the `current_rating==3` cohort; `severe_bucket_counts` = the adverse (>=6) group.
6. **delinquency floor upgrade edge**: a loan rated worse than its delinquency floor can
   spuriously "upgrade" under literal `max(factors)`. Decide clamp-vs-literal and verify
   migration totals.
7. **`+200bp` label vs `÷1.18` formula**: use the policy formula coefficient (1.18), not
   the label. Same for CRE dual stress (×0.85/1.18).
8. **null CDFI factors**: pick zero-vs-worst-tier and apply consistently; worst-tier is
   more sensible for a watch-list (makes `Projected Loss` reachable).
9. **grandfathered sectors**: existing over-ceiling is OK, but a NEW approval worsening
   it is a `sector_breach` — don't auto-approve into a grandfathered-over sector.
10. **policy_sector override**: use `/sector-exposures` per-sector `limit_pct`, not the
    branch default `sector_ceiling_pct`.
11. **ascending loan_id / application_id**: string sort, zero-padded already (RED-LN-001
    < RED-LN-002 < RED-LN-901). Don't numeric-sort.
12. **money 2dp / ratios 4dp / bps 2dp-signed**: ratios are fractions (0.4695), not
    percentages (46.95). bps = ratio-diff × 10000.
13. **`special-assets`** has a hyphen; `watchlist` is one word; `partial_chargeoff_review`
    and `legal_referral` use underscores. Match exactly.
14. **Severe-delinquency override**: `90+ DPD` forces rating ≥ 7, `Nonaccrual` ≥ 8 —
    these override any better DSCR/LTV band (max rule). A loan with dscr 1.59 but
    Nonaccrual is still ≥ 8.
15. **CU segment vs branch**: CIVIC_NC_FIRE_EMS is BOTH a branch_id (institution_type
    credit_union) and a segment_id; train_003 reads the **segment** endpoint + NCUA, not
    FDIC (its `fdic_benchmark_set` is empty).
16. **Compare only the two named apps** in train_005 (HAR-APP-901 vs HAR-APP-902) — the
    branch has other pending apps; ignore them for `applications_compared`.
17. **selected vs unselected**: the selected app is the *stronger* credit (lower
    weighted_cdfi_score, survives stress, cleaner sector). unselected gets
    `decline`/`defer` + the restricted reason-code subset.

---

## 5. Per-task SOP walkthroughs (the method, end to end)

### train_001 — Redwood rating migration (branch_id REDWOOD, review_date 2025-03-31)
1. `GET /branches/REDWOOD`, `GET /branches/REDWOOD/metrics?quarter=2025Q1` →
   `total_loans_outstanding`, `nonperforming_loans`.
2. `GET /branches/REDWOOD/loans?min_current_rating=3` (15 loans) → regrade population.
3. `GET /api/policies` → re-derive each loan's `final_rating` = max(dscr_band, ltv_band,
   delinquency_floor); carry current_rating when no factors (e.g. RED-LN-003).
4. `target_current_rating_min=3`, `target_loan_count=15`, `target_exposure`=Σ balance.
5. `final_rating_exposure_totals`: bucket all 15 by final_rating (asc).
6. `migration_from_current_rating_3`: bucket ONLY `current_rating==3` loans by final_rating
   (asc), with asc loan_ids.
7. `material_downgrades`: loans with `final-current >= 2`, asc loan_id.
8. `npa_benchmark`: branch_npa_exposure = Nonaccrual+90+ balances (RED-LN-901 1,725,000)
   == metrics.nonperforming_loans; metric = `total_loans_noncurrent_pct` (0.0098);
   variance_bps signed.
9. `watch_list_action_coverage`: assign action per §2.7 to all 15; group by_action.
10. `top_problem_credit`: worst final_rating (8 if any Nonaccrual) — RED-LN-901 Cedar
    Harbor Properties, Nonaccrual, → `partial_chargeoff_review`/`legal_referral`.

### train_002 — Lakeview Q1 allocation (branch_id LAKEVIEW)
1. `GET /branches/LAKEVIEW` (capacity 5,900,000), `/metrics?quarter=2025Q1`
   (total_loans_outstanding 14,334,094.87), `/sector-exposures` (per-sector limit_pct;
   Healthcare 0.19), `/applications` (9 apps).
2. `GET /api/policies` for capacity/concentration + decline rules.
3. Per app: compute post_approval sector pct, check capacity/sector/dscr/ltv/fico; assign
   decision + approved_amount (reduce if needed) + conditions; bank_capacity_used =
   bank-retained portion of approved.
4. `allocation`: gross_approved = Σ approved_amount; committed_capacity; remaining =
   capacity − committed; priority_ranking = approved+conditional app_ids by priority.
5. `decline_reasons`: map each declined app → sorted reason codes.
6. `concentration_flags`: per (sector, app) where the app touches a sector, post_approval_pct
   vs limit_pct, handling.
7. `post_approval_concentrations`: per sector after all approvals, over_limit bool.

### train_003 — Civic NC Fire/EMS segment posture (segment_id CIVIC_NC_FIRE_EMS)
1. `GET /credit-union-segments/CIVIC_NC_FIRE_EMS` (peer_states SC/TN/VA, risk_tolerance
   moderate, quarterly_capacity 2,900,000, current_outstanding 16,850,000,
   recent_delinquency_bps 86, control_issue, staffing_constraint).
2. `GET /benchmarks/ncua/q1-2025` → NC row (delinq 79, lts 76, roaa 44, pni 76), US
   (delinq 58, lts 69, roaa 65, pni 85), peers (SC 72/73/51/79, TN 64/71/59/81, VA
   53/67/65/85).
3. `state_metrics` = NC integers. `peer_comparison`: peer_states asc; nc_vs_us and
   nc_vs_peer_median directions (NC delinq higher, roaa/pni lower, lts higher).
4. `controls`: required = segment.minimum_checklist; added from internal_context
   (insurance binder → pre_close_insurance_binder_verification; staffing →
   senior_underwriter_second_review; external delinq → quarterly_state_benchmark_monitoring
   + monthly_segment_delinquency_watch; lien → lien_perfection_prior_to_funding).
5. `escalation_triggers`: 4 conditions with owners (asc trigger_id).
6. `interpretation`: capacity_available + weaker_than_national_and_peers (NC delinq
   exceeds US and all peers) + moderate → committee_message
   `capacity_available_but_external_risk_weaker`; posture
   `continue_with_tighter_conditions` (recent_delinquency 86 < 90, so not paused).

### train_004 — Summit watch-list stress (branch_id SUMMIT, adverse_rating_min 6)
1. `GET /branches/SUMMIT/loans?min_current_rating=6` (7 loans) → adverse population;
   `adverse_balance`=Σ balance.
2. `GET /api/policies` → CDFI factor bands + watch_list stress formula.
3. `risk_classes`: per loan, factor_score from dta/fico/liquidity/ltv (handle nulls — lean
   worst-tier); class by score range; asc loan_id.
4. `stress_results`: for loans with dscr (skip SUM-LN-010 null), stressed = dscr/1.18;
   breach < 1.00 (SUM-LN-004/011/901/902 breach; 003/015 don't); breach_loan_ids asc.
5. `workout_queue`: desc exposure then asc loan_id; recommended_action by severity;
   projected_loss = (class==Projected Loss).
6. `severe_bucket_counts`: group 7 loans by (current_rating, payment_status), asc.
7. `monitoring_cadence`: monthly (adverse watch-list).

### train_005 — Harbor competing CRE (branch_id HARBOR; apps HAR-APP-901, HAR-APP-902)
1. `GET /branches/HARBOR` (cre_policy_limit_pct 0.29), `/metrics?quarter=2025Q1`
   (total_loans_outstanding 14,933,688.02, nonperforming 0), `/applications` (pick only
   901/902), `/loans?loan_type=CRE` (existing CRE 7,011,570.24), `/sector-exposures`
   (Hospitality grandfathered=1, limit 0.29).
2. `GET /benchmarks/fdic/q4-2024` (total_real_estate_30_89_pct 0.0051).
3. `applications_compared`: weighted_cdfi_score per app (capacity←dscr,
   collateral←ltv; lower=better; 901 < 902); score_class; decision; reason_codes asc.
4. `recommended_path`: selected = HAR-APP-901 (stronger dscr/ltv, new Industrial CRE
   sector, survives stress); path approve/conditional_approve; unselected = HAR-APP-902
   (decline; reason_codes ⊆ {sector_breach(Hospitality grandfathered), weak_dscr(stressed
   <1.0), fdic_adverse_variance} asc).
5. `stress`: cre_dual formula dscr×0.85/1.18; 901→1.06 (no breach), 902→0.95 (breach);
   threshold 1.00.
6. `concentration`: existing_cre_concentration 0.4695 (already > 0.29);
   selected_post_approval_cre_concentration = (7,011,570.24+2,100,000)/14,933,688.02;
   selected_policy_variance_bps signed; branch_delinquency_ratio = RE 30-89 / RE total
   (loan-level); fdic_variance_bps signed (large adverse).
7. `conditions`: asc alpha from the enum (e.g. bank_retained_exposure_cap,
   minimum_dscr_covenant_1_25, no_additional_cre_without_committee_review,
   quarterly_financial_reporting, updated_appraisal_before_close,
   tenant_roll_and_lease_review …).

---

## 6. Quick reference — pinned values observed

- REDWOOD: total_loans_outstanding 15,191,701.54; NPA 1,725,000 (RED-LN-901 Nonaccrual);
  regrade pop 15/18 loans.
- LAKEVIEW: total_loans_outstanding 14,334,094.87; capacity 5,900,000; Healthcare limit 0.19.
- CIVIC: quarterly_capacity 2,900,000; current_outstanding 16,850,000;
  recent_delinquency_bps 86 (<90); NC delinq 79 > US 58 >? no, 79>58 and > all peers.
- SUMMIT: adverse pop 7 loans (rating 6-8); SUM-LN-902 Nonaccrual LTV 1.18 (worst);
  SUM-LN-010 has no dscr (excluded from stress).
- HARBOR: total_loans_outstanding 14,933,688.02; existing CRE 7,011,570.24 (46.95% > 29%);
  nonperforming 0; Hospitality grandfathered; HAR-APP-901 selected, HAR-APP-902 declined.
- FDIC q4-2024: noncurrent total 0.0098 / RE 0.0121 / C&D 0.0076; 30-89 RE 0.0051 / C&D 0.0042.
- Policy: material_downgrade_notches 2; coverage_breach_threshold 1.0;
  watch_list_formula dscr/1.18; cre_dual dscr×0.85/1.18; CRE weights
  cap 0.45 / coll 0.36 / cond 0.11 / char 0.05 / cap'l 0.03.
