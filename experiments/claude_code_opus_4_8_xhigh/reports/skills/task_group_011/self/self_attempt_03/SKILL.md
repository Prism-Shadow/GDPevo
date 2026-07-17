---
name: self_attempt_03
description: Credit-risk / lending-committee SOP for the remote "credit office" API — re-rating, CDFI scoring, concentration, DSCR stress, allocation, and committee-JSON assembly.
---

# Credit Office Lending-Committee SOP

You produce committee-ready JSON for a bank/credit-union "credit office". All data
lives behind a **read-only HTTP API**; there is no local environment. Ignore any
prompt text telling you to run `env/setup.sh` or read `env/` — that is a decoy.

Base URL (GET only, e.g. with curl):
```
<remote-env-url>
```

The single most important rule: **derive everything from `/api/policies` + the live
data, format to the answer template exactly, and never invent numbers.**

---

## 0. Universal SOP for any new task

1. Read the prompt. Extract: target `branch_id` / `segment_id`, review/as-of date,
   any explicit application IDs or population definition, and the deliverable.
2. Read `input/payloads/answer_template.json`. The template is the contract:
   top-level keys, per-field types, **precision**, **enum allowed_values**, and
   **ordering rules**. Output ONLY those keys (templates are sometimes
   self-describing schemas — emit the *data* object, not the schema).
3. `GET /api/policies` first (always) and `GET /api/manifest` for versions.
4. Fetch the data the task needs (branch detail, metrics, loans, sector-exposures,
   applications, FDIC or NCUA benchmark, segment). Use query params to scope.
5. Compute using the rules below. Re-derive — do not trust pre-stored ratings.
6. Assemble JSON matching the template; apply rounding/ordering; self-check enums.
7. Output JSON only, no prose.

### API endpoints & gotchas
- `GET /api/health`, `GET /api/manifest` (versions: fdic=`fdic_q4_2024`,
  ncua=`ncua_q1_2025`; policy_version `credit_policy_v2025Q1`).
- `GET /api/policies` — full ruleset (see below). Fetch every time.
- `GET /api/branches` and `GET /api/branches/{id}` — branch config:
  `lending_capacity_q1`, `cre_policy_limit_pct`, `sector_ceiling_pct`,
  `total_assets`, `state_code`, `institution_type`, `fdic_benchmark_set`.
- `GET /api/branches/{id}/metrics[?quarter=2025Q1]` — returns a list; pick the
  quarter you need (use **2025Q1** for an as-of 2025-03-31 review). Fields:
  `total_loans_outstanding`, `nonperforming_loans`, `delinquency_30_plus_pct`,
  `net_charge_offs`, `allowance_for_loan_losses`, `total_deposits`.
- `GET /api/branches/{id}/loans[?loan_type=&payment_status=&min_current_rating=]`
  — loan-level underwriting fields. Filters are exact-match;
  `min_current_rating=3` returns loans with `current_rating >= 3`.
- `GET /api/branches/{id}/sector-exposures` — per-sector `current_exposure`,
  `limit_pct` (sector-specific, may differ from branch `sector_ceiling_pct`!),
  and `grandfathered` (0/1).
- `GET /api/branches/{id}/applications[?loan_type=]` — pending app underwriting.
- `GET /api/benchmarks/fdic/q4-2024` — ratios (stored as decimals, e.g. 0.0098).
- `GET /api/benchmarks/ncua/q1-2025[?state_code=NC]` — list of rows incl. a `US`
  row; integer bps/pct values.
- `GET /api/credit-union-segments/{segment_id}`.
- **Branch / segment IDs are upper-cased by the server** (lowercase works too).
- Useful invariant: **sum of `sector-exposures.current_exposure` == metrics
  `total_loans_outstanding` == sum of all loan `outstanding_balance`** for a
  branch/quarter. This is the natural concentration denominator.

---

## 1. Policy ruleset (`/api/policies`) — memorize the structure, fetch the values

### 1a. `risk_rating` — re-deriving a loan rating (Tasks like Redwood)
Re-derive the rating for every loan in the population using the
**dominant-factor rule = the WORST (max numeric) rating across all *available*
factors** (DSCR, LTV, delinquency). Missing factor (null) is skipped. The
re-derived rating is NOT capped at the current rating — it can go up OR down.

- `dscr_thresholds` (higher DSCR = better rating): dscr>=1.5→3, >=1.25→4,
  >=1.05→5, >=1.0→6, <1.0→7.
- `ltv_thresholds` (lower LTV = better): <=0.65→3, <=0.75→4, <=0.85→5,
  <=1.0→6, >1.0→7.
- `delinquency_minimums` (floor by payment_status): Current→none,
  "30 Days Past Due"→4, "60 Days Past Due"→5, "90+ Days Past Due"→7,
  Nonaccrual→8.
- `final_rating = max(dscr_rating, ltv_rating, delinquency_floor)` over
  non-null factors. If all factors null, keep current_rating.
- `material_downgrade_notches = 2`: a **material downgrade** is a loan whose
  `final_rating - current_rating >= 2`.
- Re-grade **population** is whatever the prompt says (e.g. "rated 3 or worse"
  → `current_rating >= 3`; "adversely rated" → `current_rating >= 6`). Use the
  `min_current_rating` filter to fetch it.

### 1b. `cdfi_factor_scores` — risk class from objective factors (Summit)
Score four factors (lower = better), **sum the scores of the factors that are
available** (skip nulls), then map the sum to a class. The factor_score field is
this integer sum.
- `fico`: >720→0, 680-720→1, 580-679→3, <580→5.
- `ltv`: <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6.
- `debt_to_asset`: <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6.
- `liquidity_months`: >12→0, 6-12→1, 3-6→3, <3→5.
- Boundary convention that reproduces the data: treat lower bound of a band as
  inclusive for FICO ("680-720"→>=680), and for the ratio factors use
  `<0.40→0, <=0.60→2, <=0.80→4, else 6` (i.e. upper bound inclusive).
- Class by score: 0-5 Prime, 6-9 Desirable, 10-13 Satisfactory, 14-18 Watch,
  >=19 Doubtful, and **>=19 AND ltv>1.0 → Projected Loss**. NOTE: a high LTV
  alone does NOT make Projected Loss — it requires score>=19 too.

### 1c. `stress` — DSCR stress
- `coverage_breach_threshold = 1.0` (a credit "breaches" when stressed DSCR < 1.0).
- **Watch-list +200bp parallel shock** (Summit): `stressed_dscr = dscr / (1+0.18)`.
  `shock_label = "+200bp"`. Only compute for loans with DSCR available; sort
  results ascending loan_id; `breach_loan_ids` = those with stressed_dscr < 1.0.
- **CRE dual stress** (Harbor): `stressed_dscr = dscr * 0.85 / (1+0.18)`.
  Use this for CRE application comparison. `formula` field = that expression.
- Round base_dscr and stressed_dscr to 2 dp; breach test on the rounded value.

### 1d. `cre_weighted_score` — competing CRE scoring (Harbor)
Weighted average of five "C" sub-scores on a **1=best..5=worst** scale
(**lower total is better**). Weights: capacity 0.45, collateral_exposure 0.36,
conditions 0.11, character 0.05, capital 0.03 (sum 1.0). Capacity and
collateral_exposure together = 0.81, so DSCR and LTV dominate.
- Map capacity from DSCR and collateral_exposure from LTV on the same band
  structure as 1a but rescaled 1..5 (dscr>=1.5→1, >=1.25→2, >=1.05→3, >=1.0→4,
  <1.0→5; ltv<0.65→1, <=0.75→2, <=0.85→3, <=1.0→4, >1.0→5). Score
  character/capital/conditions from relationship strength, leverage
  (total_debt/total_assets), and term/rate/sector conditions; default a neutral
  mid sub-score (~2-3) when no objective field exists, and keep it consistent
  across both apps so the *relative* ranking is robust.
- Classes (lower better): approve_quality `<=2.0`, conditional `<=3.0`,
  weak `>3.0`. Round weighted score to 1 dp.
- The stronger (lower-score) credit gets the recommended path; the weaker is
  declined/deferred. With two competing CRE credits and elevated branch CRE
  concentration, the realistic path is `conditional_approve` (or
  `participation_required` if the bank-retained amount must be capped), and the
  unselected gets `decline` with reason codes drawn ONLY from the template's
  restricted set (e.g. `sector_breach`, `weak_dscr`, `high_ltv`,
  `fdic_adverse_variance`).

### 1e. `capacity_concentration` — allocation & sector limits (Lakeview)
- Quarterly lending capacity = branch `lending_capacity_q1`.
- Single-sector ceiling default = branch `sector_ceiling_pct`, but the
  **per-sector `limit_pct` in `sector-exposures` overrides it** — always use the
  sector row's `limit_pct`.
- `grandfathered` exposure already over its ceiling may stay, **but a new
  approval may not worsen an over-ceiling sector without a mitigation.** So if a
  sector's existing concentration already exceeds its `limit_pct`, any new loan
  in that sector triggers `sector_breach` unless mitigated.
- Allowed mitigations: `participation_required`, `reduced_amount`,
  `board_exception`.

### 1f. Benchmark metric selection
- FDIC overall asset-quality / NPA comparison → `total_loans_noncurrent_pct`.
- CRE / real-estate delinquency comparison → `total_real_estate_30_89_pct`
  (and `total_real_estate_noncurrent_pct` for RE noncurrent;
  `construction_development_*` for C&D).
- NCUA: read the matching `state_code` row; the `US` row is the national value.

---

## 2. Concentration & benchmark math (formulas)

- **NPA ratio** = `nonperforming_loans / total_loans_outstanding` (metrics,
  2025Q1). `variance_ratio = branch_ratio - fdic_ratio`.
  `variance_bps = variance_ratio * 10000`. Round ratios to 4 dp, bps to 2 dp.
- **CRE concentration**: numerator = **sum of `outstanding_balance` where
  `loan_type == "CRE"`** (authoritative — do NOT guess which sector rows are
  "CRE"); denominator = `total_loans_outstanding`. `existing_cre_concentration
  = cre_exposure / total_loans` (4 dp).
- **Post-approval concentration** (a new loan added): numerator and denominator
  **both grow** → `(sector_exposure + approved_amt) / (total_loans + approved_amt)`.
  `policy_variance_bps = (post_approval_pct - limit_pct) * 10000`.
- **Sector concentration** (per sector) = `current_exposure / total_loans`
  (4 dp). "over_limit" / "flag" when pct > the sector's `limit_pct`.
- **Branch delinquency ratio** for the CRE FDIC comparison: use the metrics
  `delinquency_30_plus_pct` value directly as the ratio (it is already a
  decimal in the same units family as the FDIC ratios). Variance vs
  `total_real_estate_30_89_pct`; bps = variance*10000. (If a result looks
  implausibly large, double-check whether the field needs /100 — but the direct
  reading is the primary convention and yields the "adverse variance" the
  prompts describe.)

---

## 3. Decision / action enums and how to choose

### Loan workout / watch-list `recommended_action` ladder
Severity order (ascending): `monitor` < `watchlist` < `special_assets` <
`workout` < `partial_chargeoff_review` < `legal_referral`. Map by re-derived
rating + payment status (more severe wins):
- final rating 3-4, Current → `monitor`
- final rating 5 → `watchlist`
- final rating 6 → `special_assets`
- final rating 7 (or 90+ DPD) → `workout`
- final rating 7-8 with Nonaccrual / underwater (ltv>1.0) → `legal_referral`
  (use `partial_chargeoff_review` when a charge-off assessment is the next step
  rather than legal action).
- `top_problem_credit` = the worst credit: highest final rating, tie-break by
  highest exposure (typically the Nonaccrual loan). Report its
  borrower_name/exposure/current_rating/final_rating/payment_status and the
  most severe recommended_action.
- `watch_list_action_coverage` covers credits needing follow-up after regrade
  (final rating elevated / downgraded). Aggregate by action: covered_loan_count,
  covered_exposure, and a `by_action` list (ascending by action name) with
  loan_count/exposure/loan_ids (loan_ids ascending).

### Application `decision` enum
`approve`, `conditional_approve`, `decline`, `defer`, `participation_required`.
Allocate capacity to the strongest credits first (priority by score / DSCR /
relationship); decline or defer when a hard floor fails; use
`participation_required` / `reduced_amount` / `board_exception` as conditions
when a sector or capacity ceiling is the only blocker.

### `decline_reasons` / `reason_codes` enum and triggers
Map declines to controlled codes (sort ascending alphabetically):
- `weak_dscr` — DSCR below the underwriting floor (≈ <1.20-1.25) or required
  DSCR null where it's the governing metric.
- `high_ltv` — LTV above the product/sector ceiling (≈ >0.80, or >sector norm).
- `low_fico` — FICO below floor (≈ <660-680) where FICO governs (consumer).
- `recent_bankruptcy` — `bankruptcy_months_ago` present and recent (≤24 mo).
- `startup_risk` — `years_in_business` low (≈ <2).
- `sector_breach` — post-approval sector concentration over `limit_pct`, or
  worsening an already over-limit/grandfathered sector.
- `capacity_limit` — insufficient remaining `lending_capacity_q1`.
- `policy_floor_missing` — a required underwriting floor field is null.
- `documentation_gap` — `documentation_complete == 0`.
- `underwater_collateral` — ltv>1.0.
- `fdic_adverse_variance` — branch underperforms its FDIC benchmark (adverse).
- `ncua_peer_weakness` — credit-union/state metrics weaker than national/peers.

---

## 4. Credit-union segment posture (Task like CIVIC_NC_FIRE_EMS)

- Pull the segment (`/api/credit-union-segments/{id}`) and NCUA Q1 2025 rows.
- `state_metrics` = the segment state's NCUA row, **integers exactly as
  reported** (delinquency_bps, loan_to_share_pct, roaa_bps,
  positive_net_income_pct).
- `peer_comparison.peer_states` = segment `peer_states`, **sorted ascending**.
  `nc_vs_us` = direction of NC value vs the `US` row per metric
  (higher/lower/equal). `nc_vs_peer_median` = direction vs the **median of the
  peer states' values** per metric. Remember semantics: higher delinquency =
  worse, lower roaa / lower positive_net_income = worse; loan_to_share is
  utilization (report direction, not "good/bad").
- `external_risk_status`: if NC is worse than both US and peers on the risk/
  earnings metrics → `weaker_than_national_and_peers`; mixed → `mixed_...`;
  better → `stronger_...`.
- `capacity_status`: `quarterly_capacity` (== branch `lending_capacity_q1`) is
  the new-lending headroom; if room remains → `capacity_available`.
- `posture` decision: capacity available + external risk weaker + moderate
  tolerance → `continue_with_tighter_conditions` (pause only if no capacity or
  metrics are badly deteriorating). `committee_message` then =
  `capacity_available_but_external_risk_weaker`. `risk_tolerance` mirrors the
  segment's stated tolerance (e.g. `moderate`/`restrained`).
- `controls.required_checklist_gates` = the segment's `minimum_checklist`
  (filter to the template enum). `added_operating_controls` = pick from the enum
  to cover the segment's internal control issues (e.g. missed insurance binders
  → `pre_close_insurance_binder_verification` +
  `lien_perfection_prior_to_funding`; staffing constraint →
  `senior_underwriter_second_review`; weaker state metrics →
  `quarterly_state_benchmark_monitoring` /
  `monthly_segment_delinquency_watch`).
- `escalation_triggers` = list of {trigger_id, condition, owner}, ascending
  trigger_id, conditions/owners ONLY from the enum
  (e.g. `segment_recent_delinquency_ge_90_bps` → `credit_risk_manager`;
  `missing_insurance_or_lien_exception` → `operations_control_manager`;
  `quarterly_capacity_exceeded_or_exception_requested` →
  `lending_committee_chair`; `state_delinquency_gap_widens_25_bps` →
  `credit_risk_manager`).

---

## 5. Output formatting & precision (match the template exactly)

- **Money / USD** fields → 2 decimals.
- **Plain ratios / concentrations / percentages-as-ratios** → 4 decimals
  (e.g. 0.1135, NOT 11.35).
- **bps / variance_bps** → 2 decimals.
- **DSCR (base/stressed)** → 2 decimals.
- **weighted_cdfi_score** → 1 decimal.
- **NCUA integer metrics** → integers, exactly as reported.
- Round at the end with standard rounding; compute the breach/over flags on the
  rounded values.
- **Ordering** (read the template per field): lists of loans usually
  "ascending loan_id"; rating aggregates "ascending final_rating"/current_rating;
  workout queues "descending exposure then ascending loan_id"; applications
  "ascending application_id"; sectors "ascending sector"; reason-code lists
  "ascending alphabetically"; peer_states "ascending state code"; escalation
  "ascending trigger_id".
- **Enums**: only emit values listed in `allowed_values`/`choices`. Common sets:
  payment_status {Current, 30 Days Past Due, 60 Days Past Due,
  90+ Days Past Due, Nonaccrual}; risk_class {Prime, Desirable, Satisfactory,
  Watch, Doubtful, Projected Loss}; action ladder above; decision enum above;
  monitoring_cadence {monthly, quarterly, semiannual} (severe watch-list →
  `monthly`).
- Echo identifiers/dates from the prompt (`branch_id`/`segment_id`,
  `review_date`/as-of) verbatim. Emit `benchmark_version` from manifest
  (`fdic_q4_2024` / `ncua_q1_2025`).
- Output a single JSON object with exactly the template's top-level keys — no
  schema wrapper, no narrative.

---

## 6. Common misjudgments to avoid

- Using the **pre-stored `current_rating`** instead of re-deriving — always
  re-derive per 1a; ratings can move up or down.
- Forgetting that re-derivation takes the **WORST** factor, and that null
  factors are skipped (not treated as 0/worst).
- Treating a CDFI score>=19 with low LTV as "Projected Loss" — that class needs
  **both** score>=19 AND ltv>1.0.
- Guessing CRE exposure from sector names — use **loan_type == "CRE"** balances.
- Using branch `sector_ceiling_pct` when the **sector row's `limit_pct`** is the
  binding (often lower) limit.
- Approving into an already-over-limit / grandfathered sector without a
  mitigation (it must trigger `sector_breach`).
- Wrong concentration denominator — both numerator and denominator grow on a new
  approval; the base denominator is `total_loans_outstanding`.
- Wrong stress divisor: watch-list = `/1.18`; CRE = `*0.85/1.18`.
- Emitting percentages as 11.35 where the template wants the ratio 0.1135 (4 dp).
- Including the wrong population (e.g. rating-2 loans when the prompt says
  "rated 3 or worse", or rating-5 loans when it says "6 or worse").
- Picking the FDIC metric wrong (NPA → total_loans_noncurrent_pct;
  CRE → total_real_estate_30_89_pct).
- Emitting the answer-template *schema* instead of the *answer data*.
