---
name: reflect-3_attempt_01
description: Judge-refined credit-risk / lending-committee SOP for the prismshadow credit-office API (rating re-derivation, CDFI scoring, concentration/DSCR stress, benchmark variance, segment posture).
---

# Credit-Office Committee SOP

You produce committee-ready JSON for a shared "credit office" environment. All data
comes from a remote HTTP API. Each task ships an `answer_template.json` that defines the
EXACT output shape; conform to it precisely (top-level keys, nested keys, enum value sets,
list ordering, per-field rounding). The template is authoritative — read it first and last.

## 1. Remote API — how to fetch data

Base URL: `<remote-env-url>`  (use the API, NOT any local `env/` files).

Endpoints (all GET, JSON):
- `/api/health`, `/api/manifest` — sanity + record counts + benchmark versions + policy_version.
- `/api/policies` — THE rulebook (risk_rating, cdfi_factor_scores, cre_weighted_score, stress, capacity_concentration). Always fetch this early.
- `/api/branches[?institution_type=bank|credit_union]`, `/api/branches/{branch_id}`.
- `/api/branches/{branch_id}/metrics[?quarter=2025Q1]` — returns a list of quarters; pick the as-of quarter (usually `2025Q1`).
- `/api/branches/{branch_id}/loans[?loan_type=&payment_status=&min_current_rating=]`.
- `/api/branches/{branch_id}/sector-exposures` — existing sector exposure + per-sector `limit_pct` + `grandfathered` flag.
- `/api/branches/{branch_id}/applications[?loan_type=]`.
- `/api/benchmarks/fdic/q4-2024`, `/api/benchmarks/ncua/q1-2025[?state_code=]`.
- `/api/credit-union-segments/{segment_id}`.

Gotchas:
- `branch_id` and `segment_id` must be UPPER-CASED exactly as given in the prompt (e.g. `REDWOOD`, `LAKEVIEW`, `SUMMIT`, `HARBOR`, `CIVIC_NC_FIRE_EMS`).
- Branch `metrics` is a list (multiple quarters). Filter to the review quarter.
- Verified invariant: for a branch, **sum(all loan outstanding_balance) == metrics.total_loans_outstanding == sum(sector_exposures.current_exposure)**. Use this to cross-check and to choose denominators.
- Many loan/application fields are `null` (dscr, ltv, fico, debt_to_asset, liquidity_months, collateral_value). Null-handling is decisive — see each rule below.
- Benchmark versions: fdic=`fdic_q4_2024`, ncua=`ncua_q1_2025` (from manifest). Use these literal strings when a field wants `benchmark_version`.

## 2. Output formatting conventions (apply unless template says otherwise)

- Money / exposures / balances: round to **2 decimals**.
- Ratios / concentrations / percentages-as-ratios: round to **4 decimals** (e.g. 0.1135, NOT 11.35).
- Basis points (bps): round to **2 decimals**; `bps = (ratio_a - ratio_b) * 10000`.
- DSCR (base and stressed): round to **2 decimals**.
- Weighted CDFI score (CRE): **1 decimal**. Factor sum scores (watch-list CDFI): **integer**.
- Ratings, loan_count, factor_score: **integer**.
- Lists: follow the template's `ordering` exactly (e.g. "ascending loan_id", "ascending by final_rating", "descending exposure then ascending loan_id", "sort by sector then application_id", "ascending alphabetically" for reason codes, "ascending state code").
- Enum/"set" fields: emit ONLY allowed values; sets are scored per-member (a missing correct item and an extra wrong item both cost). Do not invent values.
- Echo identifiers verbatim (branch_id, segment_id, review/as-of date as `YYYY-MM-DD`).

## 3. Risk-rating re-derivation (CONFIRMED, high value)

From `policies.risk_rating`. Re-derive each loan's rating as the **worst (max numeric)** of the
rating implied by each AVAILABLE factor:

- DSCR thresholds (use `>=`): >=1.5 -> 3; >=1.25 -> 4; >=1.05 -> 5; >=1.0 -> 6; <1.0 -> 7.
- LTV thresholds (use `<=`): <=0.65 -> 3; <=0.75 -> 4; <=0.85 -> 5; <=1.0 -> 6; >1.0 -> 7.
- Delinquency minimums (floor by payment_status): Current -> none; 30 DPD -> 4; 60 DPD -> 5; 90+ DPD -> 7; Nonaccrual -> 8.
- `final_rating = max(of the factors that are present)`. If a factor is null, drop it.
- If NO factor is available, keep the loan's `current_rating` as final.
- Material downgrade: `final_rating - current_rating >= policies.risk_rating.material_downgrade_notches` (=2). List ascending by loan_id with current/final/downgrade_notches/exposure.
- Regrade population is prompt-defined (e.g. "rated 3 or worse" => `current_rating >= 3`).
- `top_problem_credit` = highest final_rating, tie-break highest exposure.
- Recommended-action banding (watch-list/regrade), best estimate: final 5 -> watchlist, 6 -> special_assets, 7 -> workout, 8 (and/or Nonaccrual) -> legal_referral, <=4 -> monitor.

## 4. Benchmark variance (CONFIRMED, high value)

Pick the benchmark metric matching the task's exposure type:
- Portfolio NPA / noncurrent review -> FDIC `total_loans_noncurrent_pct`.
- Real-estate / CRE delinquency review -> FDIC `total_real_estate_30_89_pct`.
- (Also available: `construction_development_noncurrent_pct`, `construction_development_30_89_pct`, `total_real_estate_noncurrent_pct`.)

NPA ratio:
- `branch_npa_exposure = metrics.nonperforming_loans`; `branch_total_loans = metrics.total_loans_outstanding`.
- `branch_npa_ratio = nonperforming_loans / total_loans_outstanding` (4dp).
- `variance_ratio = branch_ratio - fdic_benchmark_ratio` (4dp); `variance_bps = variance_ratio * 10000` (2dp).
- Cross-check: nonperforming_loans usually equals the summed balance of Nonaccrual (+90+) loans.

Real-estate delinquency basis is ambiguous between two readings (document/compute both, prefer the metric-consistent one):
- (a) all 30-89 DPD balance / total_loans_outstanding (this equals `metrics.delinquency_30_plus_pct` when all delinquencies are RE), or
- (b) RE-loan 30-89 DPD balance / total RE-loan balance (true RE-specific ratio, comparable to the FDIC RE metric).

NCUA benchmarks: rows keyed by `state_code` (one row per state plus a `US` row). Use the row for the segment/branch state; values are integers reported verbatim (delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct).

## 5. Concentration / capacity (CONFIRMED data mechanics)

From `policies.capacity_concentration`:
- Per-sector limit = `sector_exposures[sector].limit_pct` (override table). For a sector with NO row, use the branch default `branches.sector_ceiling_pct`.
- CRE limit = `branches.cre_policy_limit_pct`.
- Lending capacity = `branches.lending_capacity_q1`.
- **Concentration denominator = total_loans_outstanding.** sector_pct = sector_current_exposure / total_loans_outstanding (4dp). (Verified: sum of sector exposures == total_loans_outstanding.)
- Existing CRE exposure = sum of branch loans with `loan_type == 'CRE'`; CRE concentration = that / total_loans_outstanding.
- Grandfathering rule: a sector may already be OVER its ceiling (check before any approval). New approvals may NOT worsen an already-over sector WITHOUT a mitigation from `allowed_mitigations` = {participation_required, reduced_amount, board_exception}.
- Post-approval concentration: adding a new loan grows BOTH numerator (sector) and denominator (total), since loans sum to total. Two defensible forms — be explicit and consistent:
  - (existing_sector + new) / (total_loans + new)  [loan added to book], or
  - (existing_sector + new) / total_loans  [against current book].
  - The "+new in denominator" form is the more internally consistent default; if a result looks off, try the other.

## 6. CRE weighted CDFI score (decision tasks) — USE WITH CAUTION

`policies.cre_weighted_score`: weights capacity 0.45, collateral_exposure 0.36, conditions 0.11,
character 0.05, capital 0.03. Lower is better. Classes: approve_quality <=2.0; conditional <=3.0; weak >3.0.
The five C's are scored on a 0-6 scale and weighted-summed. The exact C->factor mapping and null
handling are NOT fully pinned down; the most plausible mapping is:
- collateral_exposure -> LTV (cdfi ltv table), character -> FICO, capital -> debt_to_asset, conditions -> liquidity_months,
- capacity -> DSCR (no DSCR table in cdfi_factor_scores; derive a 0-6 DSCR score, e.g. >=1.5->0, 1.25-1.5->2, 1.05-1.25->4, <1.05->6).
- Null factors (common for CRE: fico, liquidity): either treat as 0, treat as worst, OR renormalize weights over present factors. THIS CHOICE MATERIALLY CHANGES THE SCORE AND CLASS — pick the one consistent with the template's precision and any prompt hint; flag the assumption.
- Pick the stronger (lower-score) credit as `selected`; the other is `unselected` with disposition decline/defer and a restricted reason-code set.

## 7. Stress formulas (CONFIRMED math)

From `policies.stress`:
- CRE dual stress (applications): `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- Watch-list +200bp stress (existing loans): `stressed_dscr = dscr / (1 + 0.18)`; shock_label `"+200bp"`.
- `coverage_breach_threshold = 1.0`; a loan/application breaches if `stressed_dscr < 1.0`.
- Round base and stressed DSCR to 2dp; compute breaches only for records where DSCR is present; emit `breach_loan_ids` ascending.

## 8. Watch-list CDFI factor classes (sum-based) — USE WITH CAUTION

`policies.cdfi_factor_scores`. SUM the factor scores (NOT weighted) over factors:
- debt_to_asset: <0.40 ->0, 0.40-0.60 ->2, 0.60-0.80 ->4, >0.80 ->6.
- ltv: same bands as debt_to_asset.
- fico: >720 ->0, 680-720 ->1, 580-679 ->3, <580 ->5.
- liquidity_months: >12 ->0, 6-12 ->1, 3-6 ->3, <3 ->5.
Classes by the sum: Prime 0-5, Desirable 6-9, Satisfactory 10-13, Watch 14-18, Doubtful >=19,
Projected Loss (>=19 AND ltv>1.0).
- Null factor handling is UNRESOLVED (skip-missing vs missing-as-worst). Note: skip-missing on these
  adverse loans rarely reaches Doubtful/Projected Loss, which is implausible for a watch list and
  conflicts with loan notes that flag underwater/nonaccrual credits as projected-loss; missing-as-worst
  makes those credits reach Doubtful/Projected Loss. Decide deliberately and state the assumption.
- Adverse population for watch-list tasks is prompt-defined (e.g. "current_rating 6 or worse" => `>=6`).
- Monitoring cadence for an adverse watch list defaults to `monthly`.
- `severe_bucket_counts`: group the population by (current_rating, payment_status); order ascending
  current_rating then payment_status. Deterministic — get this exactly right.
- `workout_queue`: order descending exposure, then ascending loan_id; `projected_loss = (risk_class == 'Projected Loss')`.

## 9. Credit-union segment posture (CONFIRMED, high value)

For `/api/credit-union-segments/{segment_id}` + NCUA Q1 2025:
- `state_metrics` = the NCUA row for `segment.state_code` (integers verbatim); benchmark_version `ncua_q1_2025`.
- `peer_comparison.peer_states` = `segment.peer_states` sorted ascending.
- `nc_vs_us` = direction of the segment-state metric vs the `US` row; `nc_vs_peer_median` = vs the MEDIAN of the peer-state values. Direction: `higher` if state>other, `lower` if state<other, `equal`.
- `external_risk_status`: weaker_than_national_and_peers when the state has higher delinquency AND lower roaa AND lower positive_net_income vs both US and peer median; mixed/stronger otherwise.
- `capacity_status` / `risk_tolerance` / `posture` / `committee_message` come from the segment object and its `notes`:
  - `risk_tolerance` = `segment.risk_tolerance`.
  - If notes say capacity remains available but external risk is weaker -> posture `continue_with_tighter_conditions`, capacity_status `capacity_available`, committee_message `capacity_available_but_external_risk_weaker`.
- `controls.required_checklist_gates` = `segment.minimum_checklist` verbatim.
- `controls.added_operating_controls` derive from `internal_context` (each item is scored separately, so include all justified and exclude unjustified ones):
  - insurance-binder control_issue -> `pre_close_insurance_binder_verification` + `lien_perfection_prior_to_funding`.
  - single/constrained senior underwriter -> `senior_underwriter_second_review`.
  - state delinquency above national -> `quarterly_state_benchmark_monitoring`.
  - elevated `recent_delinquency_bps` (near/above ~90) -> `monthly_segment_delinquency_watch`.
  - include `committee_exception_for_capacity_overrun` ONLY if capacity is constrained/overrun (omit when capacity available).
- `escalation_triggers`: map each real concern to a `condition` + `owner` (credit_risk_manager / operations_control_manager / lending_committee_chair); order ascending by trigger_id. (Owner/condition exactness for this section was the hardest to confirm — double check each pairing against the internal_context and use the lending_committee_chair for capacity/committee items, operations_control_manager for insurance/lien items, credit_risk_manager for delinquency/benchmark items.)

## 10. Decline / reason codes & decisions (allocation & CRE tasks)

Reason-code enum (allocation): capacity_limit, sector_breach, weak_dscr, high_ltv, low_fico,
recent_bankruptcy, startup_risk, underwater_collateral, policy_floor_missing, documentation_gap,
fdic_adverse_variance, ncua_peer_weakness. Map each only when its trigger is met:
- weak_dscr: DSCR below the policy floor (DSCR rating <1.25 is the strongest signal; a `minimum_dscr_covenant_1_25` condition exists).
- high_ltv: LTV above ceiling (>0.80 or >0.85 — choose one and apply consistently); underwater_collateral: LTV > 1.0.
- low_fico: FICO below floor (<580 is clearly low; <620 plausible).
- recent_bankruptcy: `bankruptcy_months_ago` is not null.
- startup_risk: `years_in_business` < ~2.
- documentation_gap: `documentation_complete == 0`.
- sector_breach: approving would put the sector over its limit (or worsen an already-over sector).
- fdic_adverse_variance: the branch underperforms the relevant FDIC benchmark.
- Sort reason-code lists alphabetically; map declined application_id -> sorted reason list.

Decisions/allocation: lending_capacity_q1 caps approvals; when total requested exceeds capacity,
capacity binds (rank survivors and decline the remainder with `capacity_limit`). `bank_capacity_used`
for SBA loans excludes the guaranteed portion (`amount * (1 - sba_guaranty_pct)`). priority_ranking
includes only approved + conditionally-approved (highest priority first).

## 11. SOP for a new task

1. Read the prompt + its `answer_template.json`. List every required key, enum set, ordering rule, and precision. The template is the contract.
2. GET `/api/manifest` and `/api/policies`. Identify which policy blocks apply (risk_rating, cdfi, cre_weighted, stress, concentration).
3. Pull the branch/segment data needed: branch, the correct-quarter metrics, loans, sector-exposures, applications, and the named benchmark.
4. Identify the POPULATION from the prompt's explicit rule (e.g. rating>=3, rating>=6, the two named applications). Apply in/out rules before any math.
5. Compute with the confirmed formulas (sections 3-10). Honor null-handling and denominator choices; cross-check with the sum invariant.
6. Build the JSON to the template: exact keys, enum values, ordering, and rounding.
7. Self-check (below), then emit ONLY the JSON (no prose).

## 12. Self-check list

- [ ] Output has exactly the template's top-level keys and nested required keys; no extras.
- [ ] Every enum value is from the allowed set; every "set"/list has no missing or extra members.
- [ ] All lists sorted per the template's stated ordering.
- [ ] Rounding: money 2dp, ratios 4dp, bps 2dp, DSCR 2dp, weighted CDFI 1dp, factor sums/ratings integer.
- [ ] Population in/out rules applied exactly as the prompt states; null factors handled per rule.
- [ ] Ratings re-derived as worst-of available factors; material downgrade uses >=2 notches.
- [ ] Benchmark metric matches the exposure type; variance_bps = variance_ratio * 10000.
- [ ] Concentration denominator = total_loans_outstanding; sector limit from override table else branch default; grandfathered/over-ceiling sectors handled.
- [ ] Stress: CRE = dscr*0.85/1.18; watch-list = dscr/1.18; breach if <1.0; only for present DSCR.
- [ ] branch_id/segment_id upper-cased; dates YYYY-MM-DD; benchmark_version strings literal.
- [ ] For composite scoring-table fields (CRE weighted, CDFI sum, allocation decisions): state and apply ONE consistent factor-mapping + null convention; these are the highest-risk fields — re-derive carefully and verify each keyed item, since errors here cascade across dependent sections.
