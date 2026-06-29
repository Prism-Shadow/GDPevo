---
name: reflect-3_attempt_03
description: Validated credit-risk / lending-committee SOP for the credit office environment (rating re-derivation, CDFI scoring, capacity/concentration, DSCR stress, CRE decisions, segment posture).
---

# Credit Office Committee SOP

You produce a single JSON object that conforms exactly to the task's
`input/payloads/answer_template.json`. All data comes from the remote public API
(NOT local files). This skill encodes the business rules, API usage, and output
formatting confirmed for this environment.

## 0. Golden rules (read first)
- Conform to the answer_template: top-level keys, nested required keys, enum
  value sets, list ordering, and per-field precision. A wrong shape or a value
  outside an enum set is scored as wrong.
- Use the public API only. Branch and segment ids go in the URL path in
  UPPERCASE (e.g. `REDWOOD`, `LAKEVIEW`, `SUMMIT`, `HARBOR`, `CIVIC_NC_FIRE_EMS`).
- Always start: `GET /api/manifest` then `GET /api/policies`. `policies` carries
  every scoring table you need (risk_rating, cdfi_factor_scores,
  cre_weighted_score, stress, capacity_concentration). Read it before computing.
- Precision: money 2dp; ratios 4dp; basis points (bps) 2dp; DSCR 2dp;
  weighted_cdfi_score 1dp; counts / ratings / factor scores are integers.
- bps conversion: `variance_bps = (branch_ratio - benchmark_ratio) * 10000`,
  rounded to 2dp. `ratio` differences are rounded to 4dp.

## 1. Public API endpoints
Base: `<remote-env-url>`
- `GET /api/health`, `GET /api/manifest`, `GET /api/policies`
- `GET /api/branches[?institution_type=bank|credit_union]`
- `GET /api/branches/{BRANCH_ID}` — branch facts: lending_capacity_q1,
  sector_ceiling_pct, cre_policy_limit_pct, total_assets, fdic_benchmark_set,
  state_code, institution_type.
- `GET /api/branches/{BRANCH_ID}/metrics[?quarter=YYYYQn]` — returns a list
  (latest first). Use the latest quarter row. Fields:
  total_loans_outstanding, nonperforming_loans, delinquency_30_plus_pct, etc.
- `GET /api/branches/{BRANCH_ID}/loans[?loan_type=&payment_status=&min_current_rating=]`
  — `min_current_rating=N` returns loans with current_rating >= N (use for
  "rated 3 or worse" = min_current_rating=3; "6 or worse" = min_current_rating=6).
- `GET /api/branches/{BRANCH_ID}/sector-exposures` — per-sector current_exposure,
  limit_pct (override), grandfathered flag.
- `GET /api/branches/{BRANCH_ID}/applications[?loan_type=]`
- `GET /api/benchmarks/fdic/q4-2024`
- `GET /api/benchmarks/ncua/q1-2025[?state_code=XX]` — `rows` list; query the
  target state, the `US` row, and each peer state.
- `GET /api/credit-union-segments/{SEGMENT_ID}`

Gotchas:
- The sum of `sector-exposures.current_exposure` equals the latest
  `metrics.total_loans_outstanding`. Use this as the branch loan-portfolio
  denominator for any concentration ratio.
- Branch `metrics.nonperforming_loans` equals the sum of balances of loans in
  `Nonaccrual` payment_status.
- Some loans/applications have null factors (dscr/ltv/fico/collateral). Handle
  nulls explicitly per the rules below; never crash, never silently drop a loan
  from population counts.

## 2. Risk-rating re-derivation (from policies.risk_rating)
For each loan compute a rating from EACH available factor, then take the WORST
(maximum numeric) rating across available factors. Higher number = worse.
- DSCR band: >=1.5 -> 3; >=1.25 -> 4; >=1.05 -> 5; >=1.0 -> 6; <1.0 -> 7.
- LTV band: <=0.65 -> 3; <=0.75 -> 4; <=0.85 -> 5; <=1.0 -> 6; >1.0 -> 7.
- Delinquency minimum (payment_status): "30 Days Past Due" -> 4;
  "60 Days Past Due" -> 5; "90+ Days Past Due" -> 7; "Nonaccrual" -> 8;
  "Current" -> none (no delinquency factor).
- `final_rating = max(rating over available factors)`.
- IMPORTANT: if a loan has NO available objective factor (no DSCR, no LTV/
  collateral, and Current status), it RETAINS its current_rating as the final
  rating. Do not drop it and do not leave it ungraded — it still counts in
  population counts and exposure totals.
- Material downgrade: `final_rating - current_rating >= 2`
  (policies.risk_rating.material_downgrade_notches = 2). Report only these in a
  material_downgrades list; include downgrade_notches = final - current.
- Top / most-severe problem credit: the loan with the worst final_rating, ties
  broken by largest exposure. For a Nonaccrual + underwater (LTV>1) worst credit,
  recommended_action is the most severe enum value the template allows.

## 3. NPA / delinquency benchmark variance
- NPA exposure = branch nonperforming_loans (= sum of Nonaccrual balances).
- branch_total_loans = latest metrics.total_loans_outstanding.
- branch_npa_ratio = NPA exposure / total_loans (4dp).
- For an "NPA / noncurrent" comparison the FDIC metric is
  `total_loans_noncurrent_pct`. For a real-estate delinquency (30-89) comparison
  the FDIC metric is `total_real_estate_30_89_pct`. Pick the metric that matches
  what the task is measuring (noncurrent vs 30-89 delinquency).
- branch_delinquency_ratio for a 30-89 comparison = the branch metric
  `delinquency_30_plus_pct`, used as reported (4dp).
- variance_ratio = branch - benchmark (4dp); variance_bps = *10000 (2dp).
- benchmark_version strings: FDIC = "fdic_q4_2024"; NCUA = "ncua_q1_2025".

## 4. CDFI factor scoring (from policies.cdfi_factor_scores)
Sum band scores of four factors; lower is better:
- debt_to_asset: <0.40 ->0; 0.40-0.60 ->2; 0.60-0.80 ->4; >0.80 ->6.
- ltv: <0.40 ->0; 0.40-0.60 ->2; 0.60-0.80 ->4; >0.80 ->6.
- fico: >720 ->0; 680-720 ->1; 580-679 ->3; <580 ->5.
- liquidity_months: >12 ->0; 6-12 ->1; 3-6 ->3; <3 ->5.
- debt_to_asset for an applicant when not given = total_debt / total_assets.
Risk class from total factor_score:
- Prime 0-5; Desirable 6-9; Satisfactory 10-13; Watch 14-18; Doubtful >=19;
  Projected Loss when score>=19 AND ltv>1.0.
Missing-factor handling: treat a missing factor as 0 (score only available
factors — "assign classes from available objective factors"). Be aware this is
the band most likely to need a per-task sanity check; if a clearly distressed
loan (nonaccrual + underwater) lands in a benign class, reconsider whether the
task wants missing factors scored at the worst band instead. factor_score is an
integer.

## 5. Watch-list / adverse population and DSCR stress
- Adverse / watch-list population = loans with current_rating >= the minimum the
  task names (e.g. 6 or worse). adverse_rating_min = that minimum.
- monitoring_cadence for an adverse watch-list = "monthly".
- Watch-list parallel +200bp stress (policies.stress.watch_list_formula):
  `stressed_dscr = base_dscr / (1 + 0.18)`. shock_label = "+200bp".
  breach_threshold = coverage_breach_threshold = 1.0; breaches if
  stressed_dscr < 1.0. Only loans WITH a DSCR appear in stress results;
  breach_loan_ids ascending.
- CRE dual-stress (policies.stress.cre_dual_stress_formula):
  `stressed_dscr = base_dscr * 0.85 / (1 + 0.18)`; same 1.0 breach threshold.
- workout_queue ordering = descending exposure, then ascending loan_id.
- severe_bucket_counts: group by (current_rating, payment_status); order ascending
  current_rating then payment_status in the canonical status order
  (Current, 30 Days Past Due, 60 Days Past Due, 90+ Days Past Due, Nonaccrual).
- projected_loss flag: true for a loan that is underwater (ltv>1.0) and Nonaccrual
  / in the Projected Loss class.
- Action enum ladder (more severe with rating/status): monitor < watchlist <
  special_assets < workout < partial_chargeoff_review < legal_referral. Map
  current/low-severity to monitor or watchlist; 90+ past due to special_assets;
  nonaccrual/loss to workout / legal_referral. (Exact per-rating mapping is the
  least certain piece; keep it monotonic with severity.)

## 6. Capacity + concentration ALLOCATION tasks (pending applications)
This is the single biggest pitfall: an allocation/decision task is driven by
CAPACITY and SECTOR CONCENTRATION, NOT by aggressive per-loan credit floors.
Do NOT decline applications merely for moderate DSCR or LTV. Decline only for
severe, objective disqualifiers.
- Lending capacity = branches.lending_capacity_q1.
- Sector ceiling = sector_exposures.limit_pct for that sector if present, else
  branches.sector_ceiling_pct (default).
- Concentration ratio denominator = total branch loan portfolio
  (= sum sector_exposures = total_loans_outstanding). Post-approval ratio uses
  the denominator grown by the approved amounts.
- Grandfathering (policies.capacity_concentration): a sector already over ceiling
  may be grandfathered, BUT a new approval that worsens an over-ceiling sector
  requires a mitigation. allowed_mitigations: participation_required,
  reduced_amount, board_exception. Such an approval becomes
  participation_required or conditional_approve (with the mitigation as a
  condition), not a plain approve.
- Capacity: rank applications, allocate until lending_capacity_q1 is exhausted;
  applications that no longer fit get a capacity_limit decline (or defer).
- priority_ranking lists application_ids highest-priority first, including only
  approved and conditionally-approved (and participation_required) applications.
- Severe credit declines (objective): recent bankruptcy within the policy window,
  FICO below the bottom band (<580), underwater collateral (ltv>1.0) on weak
  credits, documentation_complete=0 -> documentation_gap. Startup (years_in_
  business < ~2) -> conditional_approve with startup_monitoring, or
  sba_guaranty_required if an SBA guaranty is present.
- decline_reasons maps each declined application_id to a sorted list of reason
  codes from the template enum.

## 7. Competing CRE decision tasks
- weighted_cdfi_score uses policies.cre_weighted_score.weights
  (capacity .45, collateral_exposure .36, conditions .11, character .05,
  capital .03); lower is better. Map the 5 "C" inputs to factor band scores
  (capacity from DSCR strength, collateral_exposure from LTV, capital from
  debt_to_asset, character from FICO). Classes: approve_quality <=2.0;
  conditional <=3.0; weak >3.0. Report score to 1dp. (The exact numeric mapping
  is the least certain piece; the RELATIVE ranking and the selection are what
  matter most — see next bullets.)
- Select the stronger credit = the LOWER weighted_cdfi_score (better DSCR, lower
  LTV, passes stress).
- Run the CRE dual-stress on each; a stressed_dscr < 1.0 is a weak_dscr reason
  for that application.
- Concentration: existing_cre_exposure = sum of loan_type=CRE outstanding
  balances; existing_cre_concentration = that / total_loans_outstanding (4dp);
  selected_post_approval = (existing_cre + selected_requested) /
  (total_loans + selected_requested) (4dp); selected_policy_variance_bps =
  (post - cre_policy_limit_pct) * 10000 (2dp).
- When the post-approval CRE concentration blows past cre_policy_limit_pct, the
  recommended path is participation_required (cap bank-retained exposure), and
  the selected application's decision in applications_compared must match the
  path. Do not output a plain "approve" while the path is participation_required.
- FDIC underperformance: fdic_benchmark_metric = total_real_estate_30_89_pct;
  branch_delinquency_ratio = delinquency_30_plus_pct; if branch > benchmark the
  branch underperforms -> add fdic_adverse_variance as a reason code.
- Typical reason codes here: both apps carry fdic_adverse_variance (branch
  underperforms FDIC) and sector_breach (CRE over limit); the stress-failing /
  unselected app adds weak_dscr (and high_ltv only if ltv>0.80).
  unselected_disposition is decline or defer (restricted enum). reason-code lists
  are sorted alphabetically.

## 8. Credit-union segment posture page
- state_metrics: copy the target state's NCUA row EXACTLY as integers
  (delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct);
  benchmark_version = "ncua_q1_2025".
- peer_states = segment.peer_states, sorted ascending.
- Direction fields compare the target state's RAW value to the comparison value:
  higher / lower / equal (NOT good/bad). Compute nc_vs_us against the `US` row,
  and nc_vs_peer_median against the median of the peer-state rows
  (median of 3 = the middle value, per metric).
- external_risk_status: weaker_than_national_and_peers if the state is worse on
  the risk-relevant metrics vs both US and peers (higher delinquency, lower roaa,
  lower positive_net_income, etc.); otherwise mixed / stronger.
- capacity_status: capacity_available if the segment's quarterly_capacity has room
  (segment notes usually state this); else constrained / none.
- risk_tolerance (in interpretation) = the segment's STATED risk_tolerance value
  (copy it, e.g. "moderate"); do NOT derive it from the posture.
- posture: continue_with_tighter_conditions when capacity is available but
  external risk is weaker; temporarily_pause only when metrics demand a halt;
  continue_approving when clean.
- committee_message: capacity_available_but_external_risk_weaker (capacity but
  weak external), pause_until_state_metrics_recover, or
  routine_approval_path_supported — match it to posture/capacity/risk.
- controls.required_checklist_gates = segment.minimum_checklist (as a set).
- controls.added_operating_controls: driven by the segment's internal_context.
  A missed-insurance-binder control issue -> pre_close_insurance_binder_
  verification and lien_perfection_prior_to_funding; external delinquency above
  national -> quarterly_state_benchmark_monitoring and
  monthly_segment_delinquency_watch; plus senior_underwriter_second_review.
  Only add committee_exception_for_capacity_overrun if capacity is actually
  constrained/overrun.
- escalation_triggers: trigger_id ascending; map conditions to owners:
  delinquency thresholds and state-gap widening -> credit_risk_manager;
  insurance/lien exceptions -> operations_control_manager; capacity overrun /
  exception requests -> lending_committee_chair.

## 9. Step-by-step SOP for a NEW task
1. Read the prompt and the answer_template fully; list every required key, enum,
   ordering rule, and precision.
2. `GET /api/manifest`, `GET /api/policies`. Identify which policy tables the task
   needs.
3. Pull the target branch/segment + metrics + (loans | applications | sector-
   exposures) + the right benchmark (FDIC for banks, NCUA for credit unions).
4. Build the correct population (apply min_current_rating / sector / loan_type
   filters exactly as worded; keep null-factor loans in counts).
5. Compute per the relevant section above (rating re-derivation / CDFI / stress /
   concentration / posture). Round at the END to the template precision.
6. Assemble JSON in template order; sort every list by its stated ordering key;
   restrict every enum to allowed_values.
7. Run the self-check, then emit JSON only (no narrative).

## 10. Self-check before emitting
- [ ] All required top-level and nested keys present; no extras that break shape.
- [ ] Every enum value is in the template's allowed_values.
- [ ] Population counts and exposure totals include null-factor loans; no loan
      double-counted or dropped.
- [ ] No-objective-factor loans retained current_rating; material downgrade uses
      >=2 notches.
- [ ] Denominators correct: portfolio = total_loans_outstanding = sum sector
      exposures; post-approval denominators grown by approvals.
- [ ] Stress formulas: watch-list = dscr/1.18; CRE = dscr*0.85/1.18; breach<1.0.
- [ ] Allocation tasks: decisions driven by capacity + concentration, NOT
      moderate-credit declines; over-ceiling new approvals carry a mitigation;
      selected/path/decision are internally consistent.
- [ ] Precision applied: money 2dp, ratio 4dp, bps 2dp, dscr 2dp, weighted 1dp,
      counts/ratings integer.
- [ ] Lists sorted by the exact ordering key (loan_id/application_id/sector asc;
      workout_queue exposure desc then loan_id asc; reason codes alphabetical).
- [ ] benchmark_version strings exact: "fdic_q4_2024" / "ncua_q1_2025".
- [ ] Output is valid JSON and nothing else.
