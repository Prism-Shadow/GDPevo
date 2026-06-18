# Credit Office — detailed rule tables

These expand the SKILL.md summary. They were derived by reproducing official train answers exactly.
Always re-read `GET /api/policies` for the live thresholds; the bands below match
`credit_policy_v2025Q1` but the API is the source of truth.

## Table of contents
1. Risk-rating re-derivation
2. recommended_action mapping (validated)
3. CDFI factor scoring & Projected-Loss override
4. Application underwriting decline floors
5. Capacity, concentration & participation math
6. CRE 5-C weighted scoring & competing-credit decisions
7. Benchmark variance (FDIC / NCUA)
8. Credit-union segment posture, controls & escalation triggers
9. Ordering / precision cheatsheet

---

## 1. Risk-rating re-derivation

For each loan compute a rating from every available factor, then take the **max numeric** (worst):
- DSCR: ≥1.5→3, ≥1.25→4, ≥1.05→5, ≥1.0→6, <1.0→7. (null DSCR = no DSCR factor.)
- LTV: ≤0.65→3, ≤0.75→4, ≤0.85→5, ≤1.0→6, >1.0→7. (null LTV = no LTV factor.)
- Delinquency: Current→(none), 30DPD→4, 60DPD→5, 90+DPD→7, Nonaccrual→8.

No factors at all (DSCR & LTV null, Current) ⇒ retain `current_rating`.
Material downgrade list = loans where `final − current ≥ 2`, ordered ascending `loan_id`,
each item `{loan_id, current_rating, final_rating, downgrade_notches, exposure}`.

## 2. recommended_action mapping (validated across two train tasks)

Severity-driven, evaluated top-down:

| Condition (first match wins)              | recommended_action          |
|-------------------------------------------|-----------------------------|
| payment_status == Nonaccrual              | partial_chargeoff_review    |
| final_rating ≥ 7  OR  90+ Days Past Due   | special_assets              |
| final_rating 5–6 (Current adverse)        | watchlist                   |
| otherwise                                 | monitor                     |

The enum also lists `workout` and `legal_referral`, but the official answers never use them for this
family — do not select them. `top_problem_credit.recommended_action` follows the same map (a
Nonaccrual top credit ⇒ `partial_chargeoff_review`).

Watch-list **coverage population = final_rating ≥ 6**. Group covered loans by action; within an
action sort `loan_ids` ascending; sort the `by_action` list ascending by `action` string;
`covered_loan_count` / `covered_exposure` are sums over the covered set.

## 3. CDFI factor scoring & Projected-Loss override

Banded scores (sum the factors present; missing factor = 0 contribution):
- FICO: >720→0, 680–720→1, 580–679→3, <580→5.
- LTV: <0.40→0, 0.40–0.60→2, 0.60–0.80→4, >0.80→6.
- debt_to_asset: <0.40→0, 0.40–0.60→2, 0.60–0.80→4, >0.80→6.
- liquidity_months: >12→0, 6–12→1, 3–6→3, <3→5.

Class by total score: Prime 0–5, Desirable 6–9, Satisfactory 10–13, Watch 14–18, Doubtful ≥19.
**Override:** if `ltv > 1.0`, class = **Projected Loss** regardless of score (a score of 17 with
ltv 1.18 is Projected Loss, not Watch). `projected_loss` boolean field = (class == "Projected Loss").

## 4. Application underwriting decline floors (inferred from official decisions)

Reason codes (template enum). Apply per applicant; a clean applicant with no hard fail and remaining
capacity is approved.

| reason_code          | trigger                                                             |
|----------------------|---------------------------------------------------------------------|
| weak_dscr            | dscr < 1.25 (and not otherwise mitigated, e.g. SBA)                 |
| high_ltv             | ltv > 0.80 for business/CRE loans (consumer loans judged on DTI)    |
| low_fico             | fico < 580                                                          |
| recent_bankruptcy    | bankruptcy_months_ago is not null and recent (≈ within 24 months)   |
| startup_risk         | years_in_business < 2                                               |
| underwater_collateral| ltv > 1.0                                                          |
| documentation_gap    | documentation_complete == 0                                        |
| capacity_limit       | no lending capacity remains after higher-priority approvals         |
| sector_breach        | approval would push/keep a sector over its limit_pct without mitig. |

Notes that proved decisive in training:
- A strong file in a sector at/near its ceiling is NOT declined — it becomes a participation
  (`participation_required`) or conditional approval with a mitigation, with a `concentration_flags`
  entry, not a `decline`.
- SBA guaranty mitigates startup/weak-DSCR risk: such an app can be `conditional_approve` with
  conditions `["sba_guaranty_required","startup_monitoring"]` instead of declined.
- Consumer applications use DTI, not LTV, as the leverage screen.
- `decline_reasons` maps each declined application_id → its reason codes sorted ascending
  alphabetically. Declined apps: amount/bank used = 0, conditions ["none"], not in priority_ranking.

## 5. Capacity, concentration & participation math

- Capacity = `branches.lending_capacity_q1`.
- `gross_approved_amount` = sum of approved + conditionally-approved `approved_amount`.
- `committed_capacity_amount` = sum of `bank_capacity_used`.
- `remaining_capacity` = capacity − committed.
- **Concentration denominator = post-approval book** = `total_loans_outstanding` + sum of ALL
  approved/conditional approved amounts (FULL approved amounts, even for participations).
  - sector post_approval_pct = (existing sector exposure + approval added to that sector) / denom.
  - `post_approval_concentrations` lists the sectors touched by approvals (per the template scope),
    each `{sector, exposure_after_approval, post_approval_pct (4dp), limit_pct, over_limit (bool)}`,
    ordered ascending by sector.
  - `concentration_flags` are the sectors that hit/near their limit; `flag` is a boolean; `handling`
    uses the handling enum; ordered by sector then application_id.

**bank_capacity_used (the bank-retained portion):**
- Plain approve: bank_capacity_used = approved_amount.
- SBA-guaranteed: bank_capacity_used = approved_amount × (1 − `sba_guaranty_pct`)  (e.g. 75%
  guaranty ⇒ bank retains 25%).
- Participation on a non-SBA over-ceiling loan: the bank retains only part of the loan; the retained
  fraction is set by the participation arrangement and is **not cleanly derivable from the published
  fields** — if an app carries an explicit participation/retention field use it, otherwise report the
  bank-retained amount the arrangement specifies and flag the residual uncertainty rather than
  assuming a flat 50%. (A flat 50% assumption was wrong in training.)

`priority_ranking` = ordered list of approved + conditionally-approved application_ids only,
highest priority first (strongest credits / lowest risk first).

## 6. CRE 5-C weighted scoring & competing-credit decisions

Weights: capacity 0.45, collateral_exposure 0.36, conditions 0.11, character 0.05, capital 0.03
(lower total = better). Class: ≤2.0 approve_quality, ≤3.0 conditional, >3.0 weak.

The per-component score scale is NOT in the policy doc. Do not fabricate a precise component score.
Instead:
- Score both credits consistently and use the result only to (a) rank them and (b) place each in a
  class by the cutoffs. The stronger (lower) credit is `selected`.
- `weighted_cdfi_score` is reported to 1 dp; if you cannot derive the exact published value, your
  *ranking and class* are what mostly drive the gradeable decision fields — get those right.

Decision/path for the selected CRE credit:
- If the branch's CRE concentration is over `cre_policy_limit_pct` (it generally is in these tasks),
  the path is **participation_required** (sector breach forces mitigation), not plain
  conditional_approve.
- The **unselected** competing credit's disposition is **defer** (lost the competition but viable),
  not decline.
- reason_codes (ascending alphabetical) for over-limit CRE credits: `sector_breach` (over CRE limit)
  + `fdic_adverse_variance` (branch delinquency far over FDIC RE benchmark) + `weak_dscr` if the
  stressed DSCR breaches 1.0.
- `conditions` (ascending alphabetical) is the set of applicable controls from the template enum;
  when far over limit and forcing a committee exception, expect the full applicable set including
  `updated_appraisal_before_close` — do not arbitrarily drop conditions.

## 7. Benchmark variance (FDIC / NCUA)

- NPA / noncurrent: `branch_npa_exposure` = noncurrent loans (90+ DPD + Nonaccrual) balances;
  `branch_total_loans` = metric `total_loans_outstanding`; `branch_npa_ratio` = exposure/total (4dp).
  Pick the matching FDIC metric enum (`total_loans_noncurrent_pct` for whole-book NPA).
- `branch_delinquency_ratio` for CRE/RE benchmark = use the branch metric `delinquency_30_plus_pct`
  directly (do NOT recompute a bespoke RE-type ratio). FDIC metric enum = `total_real_estate_30_89_pct`.
- variance_ratio = branch_ratio − benchmark_ratio (4 dp).
- **variance_bps = (full-precision branch_ratio − benchmark_ratio) × 10000, rounded to 2 dp at the
  end.** Never multiply a pre-rounded ratio. (1037.49 not 1037.0; 2802.0; 2449.15 not 2449.0.)

## 8. Credit-union segment posture, controls & escalation triggers

- `state_metrics`: read the NCUA Q1-2025 row for the segment's state; values are integers as
  reported (delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct).
- `peer_states`: from the segment's `peer_states`, ascending state code. Compute peer medians.
- Direction fields = NC value vs comparison value: higher / lower / equal (purely directional;
  do not editorialize good/bad).
- `required_checklist_gates` = the segment's `minimum_checklist`, **in source order** (not sorted).
- `added_operating_controls`: choose the controls evidenced by the segment context (missed insurance
  binders ⇒ pre_close_insurance_binder_verification + lien_perfection_prior_to_funding; staffing
  constraint ⇒ senior_underwriter_second_review; external risk ⇒ quarterly_state_benchmark_monitoring
  + monthly_segment_delinquency_watch). Omit controls with no evidence (e.g.
  committee_exception_for_capacity_overrun when capacity is available).
- `escalation_triggers`: emit only triggers whose condition is actually armed by the data:
  - `segment_recent_delinquency_ge_90_bps` — included when recent delinquency is at/approaching the
    90-bps watch level → owner credit_risk_manager.
  - `missing_insurance_or_lien_exception` — included when a control_issue evidences missed binders →
    owner operations_control_manager.
  - `quarterly_capacity_exceeded_or_exception_requested` — included when capacity/staffing pressure
    exists → owner lending_committee_chair.
  - `state_delinquency_gap_widens_25_bps` — OMIT unless the current state-vs-US gap meets 25 bps
    (a 21-bps gap does not arm it).
  - `trigger_id` = zero-padded `ET001`, `ET002`, … ascending; sort the list ascending by trigger_id.
- `interpretation`: capacity_status (capacity_available when quarterly capacity remains),
  external_risk_status (weaker_than_national_and_peers when delinquency higher & roaa/income lower
  than both US and peers), risk_tolerance = segment's `risk_tolerance`, committee_message picked from
  the enum to match (capacity available but external risk weaker ⇒
  `capacity_available_but_external_risk_weaker`).
- `posture`: continue_with_tighter_conditions when capacity remains but external risk is elevated and
  recent delinquency is below the hard-pause trigger; temporarily_pause only when a hard trigger is
  breached.

## 9. Ordering / precision cheatsheet

- USD → 2 dp; ratios → 4 dp; weighted_cdfi_score → 1 dp; *_bps → 2 dp; NCUA state metrics → integers.
- Compute full precision; round once at the final field. Especially: bps = ratio_full × 10000 then round.
- List ordering: obey the template's `ordering` clause exactly. payment_status string sorts
  ascending lexicographically ("90+ Days Past Due" < "Current"). Source-ordered sets keep source order.
- Booleans are booleans; enums must come from the template's allowed values; include every required key.
