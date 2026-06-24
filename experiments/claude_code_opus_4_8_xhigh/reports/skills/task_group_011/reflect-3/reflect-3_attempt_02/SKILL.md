---
name: reflect-3_attempt_02
description: Feedback-refined credit-risk / lending-committee SOP for the prismshadow credit office API (ratings, CDFI scoring, DSCR stress, concentration, segment posture).
---

# Credit Office Committee SOP

You produce committee-ready JSON for a shared "credit office" environment. Every task targets a
branch / segment and must conform EXACTLY to the task's `input/payloads/answer_template.json`.
All data comes from the remote HTTP API. Do NOT read local `env/` files.

## 0. Golden rules (highest leverage)

1. Conform to the answer_template literally: exact top-level keys, nested keys, list ORDERING,
   enum spelling, and per-field PRECISION. A structurally non-conformant answer can score 0.
2. Two task shapes behave very differently:
   - "Compute / lookup" tasks (rating migration, segment posture) award generous PARTIAL credit.
     Get the deterministic numbers and lookups perfect and you score high even if a judgment enum
     is off.
   - "Decision / recommendation / classification" tasks (capacity allocation, competing-credit
     selection, watch-list workout classification) are effectively GATED: if the core
     decision/class/action anchors are not exactly right, the score collapses toward 0. There is
     little middle ground. Spend your effort making the deterministic anchors (population,
     formulas, denominators, rounding, enum-from-policy) airtight, then derive enums strictly from
     the policy tables — never improvise thresholds.
3. Pull every threshold/weight/formula from `GET /api/policies`. Do not invent floors.
4. Use the values VERBATIM as the API returns them (NCUA bps are integers; FDIC ratios are
   already ratios; branch metric percentage fields are stored as-is). Do not silently rescale
   unless the template's precision/units force it.

## 1. Remote API (use ONLY these; base from the task's environment_access)

Base: `<remote-env-url>`

- `GET /api/health`, `GET /api/manifest` — start here. Manifest gives benchmark_versions
  (fdic=fdic_q4_2024, ncua=ncua_q1_2025) and policy_version.
- `GET /api/policies` — the rulebook (see section 2). ALWAYS fetch.
- `GET /api/branches` , `GET /api/branches/{branch_id}` — branch master:
  `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`, `total_assets`,
  `state_code`, `fdic_benchmark_set`, `institution_type`.
- `GET /api/branches/{branch_id}/metrics[?quarter=2025Q1]` — list (2025Q1 + 2024Q4). Use 2025Q1
  for as-of 2025-03-31. Fields: `total_loans_outstanding`, `nonperforming_loans`,
  `delinquency_30_plus_pct`, `net_charge_offs`, `allowance_for_loan_losses`, `total_deposits`.
- `GET /api/branches/{branch_id}/loans[?loan_type=&payment_status=&min_current_rating=]`
  `min_current_rating=N` returns loans with current_rating >= N. `loan_type=CRE` filters CRE.
- `GET /api/branches/{branch_id}/sector-exposures` — per-sector `current_exposure`, `limit_pct`,
  `grandfathered` (0/1).
- `GET /api/branches/{branch_id}/applications[?loan_type=]` — pending apps.
- `GET /api/benchmarks/fdic/q4-2024` — FDIC ratios (all already decimals/ratios).
- `GET /api/benchmarks/ncua/q1-2025[?state_code=]` — `{"rows":[{state_code, delinquency_bps,
  loan_to_share_pct, roaa_bps, positive_net_income_pct}...]}`, integers. Includes a "US" row.
- `GET /api/credit-union-segments/{segment_id}` — segment master.

Gotchas:
- branch_id and segment_id are UPPER-CASE (REDWOOD, LAKEVIEW, HARBOR, SUMMIT, CIVIC_NC_FIRE_EMS).
- Loan/borrower names can collide across branches and notes can be misleading; only use the
  records returned for YOUR branch/segment.
- `nonperforming_loans` can be 0 for a branch (Harbor); that is real.

## 2. Policy rulebook (from /api/policies; confirmed via feedback)

### 2a. Risk-rating re-derivation ("dominant factor" / worst-of)
Final re-derived rating = the WORST (max numeric) rating across the AVAILABLE factors below;
ignore factors whose inputs are null. If no factor is available, fall back to current_rating.

- DSCR thresholds: dscr >=1.5 -> 3; >=1.25 -> 4; >=1.05 -> 5; >=1.0 -> 6; <1.0 -> 7.
- LTV thresholds: ltv <=0.65 -> 3; <=0.75 -> 4; <=0.85 -> 5; <=1.0 -> 6; >1.0 -> 7.
- Delinquency minimums (by payment_status): Current -> none; "30 Days Past Due" -> 4;
  "60 Days Past Due" -> 5; "90+ Days Past Due" -> 7; Nonaccrual -> 8.
- Material downgrade = downgrade of >= `material_downgrade_notches` (=2) notches
  (final_rating - current_rating >= 2).
- The re-derived rating can be BETTER than current_rating (free re-derive scored fine on the
  migration task); do not artificially floor it at current_rating.

### 2b. CDFI factor scoring (watch-list risk classes)
factor_score = SUM of the component scores below. CONFIRMED nuance: when a component input is
null, scoring it at the WORST (max) value correctly flags Projected Loss for underwater nonaccrual
credits (matched the data note). Treat null = worst-case as the primary reading; "available
factors only" (null skipped) is the fallback if instructed.

- debt_to_asset: <0.40 ->0; 0.40-0.60 ->2; 0.60-0.80 ->4; >0.80 ->6.
- ltv:           <0.40 ->0; 0.40-0.60 ->2; 0.60-0.80 ->4; >0.80 ->6.
- fico: >720 ->0; 680-720 ->1; 580-679 ->3; <580 ->5.
- liquidity_months: >12 ->0; 6-12 ->1; 3-6 ->3; <3 ->5.

Risk class from factor_score: Prime 0-5; Desirable 6-9; Satisfactory 10-13; Watch 14-18;
Doubtful >=19; Projected Loss = (score >=19 AND ltv > 1.0). Check Projected Loss BEFORE Doubtful.

### 2c. CRE weighted score (competing-credit selection)
Weights: capacity 0.45, collateral_exposure 0.36, conditions 0.11, character 0.05, capital 0.03.
weighted_score = sum(weight * component_factor_score); LOWER is better.
Score classes: approve_quality <=2.0; conditional <=3.0; weak >3.0.
Component->factor mapping is the unresolved/high-risk part: collateral_exposure<-ltv score,
capital<-debt_to_asset score (use total_debt/total_assets if no direct field), character<-fico
score, capacity<-a DSCR-derived score, conditions<-documentation/guaranty quality. The stronger
credit is the one with the lower weighted score AND no stress breach. Validate the relative
ranking with the obvious credit signals (DSCR, LTV, leverage) before trusting the absolute score.

### 2d. Stress formulas
- Watch-list parallel +200bp shock: `stressed_dscr = dscr / (1 + 0.18)`.
- CRE dual stress: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- coverage_breach_threshold = 1.0; breach when stressed_dscr < 1.0. Only stress loans/apps that
  have a non-null DSCR; list them ascending by id; collect breach ids separately.

### 2e. Capacity & concentration
- Lending capacity = `branches.lending_capacity_q1`.
- Concentration denominator = branch `total_loans_outstanding` (2025Q1). CONFIRMED: each
  sector's current_exposure / total_loans_outstanding ~ its limit_pct, so the denominator is
  total_loans_outstanding (NOT total_assets).
- Per-sector limit = sector-exposure row `limit_pct`; default to `branches.sector_ceiling_pct`
  for sectors with no row.
- CRE concentration uses `branches.cre_policy_limit_pct`. existing_cre_exposure = SUM of
  outstanding_balance over loans with loan_type=CRE. post_approval = (existing + approved)/total.
- Grandfathering: existing over-ceiling exposure may be grandfathered (`grandfathered=1`), but a
  NEW approval may not worsen an over-ceiling sector without a mitigation
  (participation_required, reduced_amount, board_exception).
- SBA guaranty reduces the bank's retained exposure: bank_capacity_used ~= amount * (1 - sba_pct).
- When summed requested amounts exceed lending_capacity_q1, capacity is the binding constraint:
  rank survivors and fund within capacity; the overflow is declined/deferred with `capacity_limit`.

### 2f. Benchmark metric selection
- General NPA vs FDIC: `total_loans_noncurrent_pct`. branch_npa_ratio =
  nonperforming_loans / total_loans_outstanding (2025Q1).
- CRE / real-estate delinquency vs FDIC: `total_real_estate_30_89_pct`.
- Construction/development: `*_construction_development_*` variants.
- variance_ratio = branch_ratio - fdic_ratio; variance_bps = variance_ratio * 10000.
- FDIC ratios are returned as decimals already; use as-is. (For the branch delinquency ratio,
  if a benchmark comparison is required, mirror the FDIC ratio's scale; the metric field's
  precision in the template tells you how to round.)

### 2g. Segment posture (credit-union)
- state_metrics = the NCUA row for the segment's state, integers VERBATIM
  (delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct).
- peer_states = segment.peer_states (output ascending).
- nc_vs_us / nc_vs_peer_median: direction of the target state's value vs the comparison
  ("higher" / "lower" / "equal"). Comparison = the "US" NCUA row, and the MEDIAN of the peer
  states' values respectively.
- external_risk_status: weaker_than_national_and_peers if the state has higher delinquency and
  lower roaa / positive_net_income than both US and peer median; mixed if signals conflict;
  stronger if better on both.
- capacity_status: read segment notes + quarterly_capacity vs current_outstanding. If notes say
  capacity remains available (often "with added controls") -> capacity_available.
- risk_tolerance: use segment.risk_tolerance VERBATIM (e.g., "moderate"). Do NOT override it from
  your posture (confirmed: overriding to "restrained" LOWERED the score).
- posture: continue_with_tighter_conditions when capacity is available but external risk is
  weaker; temporarily_pause when state metrics are clearly bad / no capacity;
  continue_approving when strong and capacity available.
- committee_message: capacity_available_but_external_risk_weaker (capacity ok + weaker external);
  pause_until_state_metrics_recover; routine_approval_path_supported.
- required_checklist_gates = segment.minimum_checklist (as a set).
- added_operating_controls: map EACH internal_context issue to a control. CONFIRMED the set
  should include lien_perfection_prior_to_funding when a ucc/title lien gate exists, PLUS
  pre_close_insurance_binder_verification (insurance-binder control issue),
  senior_underwriter_second_review (staffing constraint),
  quarterly_state_benchmark_monitoring (state above national),
  monthly_segment_delinquency_watch (elevated/near-threshold segment delinquency).
- escalation_triggers: choose from the condition enum and assign natural owners:
  segment_recent_delinquency_ge_90_bps -> credit_risk_manager;
  missing_insurance_or_lien_exception -> operations_control_manager;
  quarterly_capacity_exceeded_or_exception_requested -> lending_committee_chair;
  state_delinquency_gap_widens_25_bps -> credit_risk_manager. Sort ascending by trigger_id.

### 2h. Action / disposition enums
recommended_action / by_action enum: monitor, watchlist, special_assets, workout,
partial_chargeoff_review, legal_referral. Reasonable severity ladder (verify against template):
Projected Loss / underwater -> partial_chargeoff_review; Nonaccrual or Doubtful -> legal_referral;
Watch / rating 7 -> special_assets or workout; rating 5-6 -> watchlist; milder -> monitor.
Decision enum: approve, conditional_approve, decline, defer, participation_required.
Conditions enum: participation_required, reduced_amount, board_exception, sba_guaranty_required,
startup_monitoring, none. Decline reason-code enum (sort ascending alphabetically):
capacity_limit, sector_breach, weak_dscr, high_ltv, low_fico, recent_bankruptcy, startup_risk,
underwater_collateral, policy_floor_missing, documentation_gap, fdic_adverse_variance,
ncua_peer_weakness.

## 3. Output formatting conventions

- Money / exposure / balances: 2 decimals.
- Ratios / concentrations / percentages-as-ratios: 4 decimals.
- bps fields: 2 decimals (ratio * 10000).
- DSCR (base & stressed): 2 decimals. weighted CRE score: 1 decimal. factor_score: integer.
- NCUA state metrics: integers verbatim.
- List ordering is specified PER FIELD in the template and is graded:
  - rating exposure totals / migration: ascending by final_rating; loan_ids ascending.
  - material_downgrades, risk_classes, stress results: ascending loan_id.
  - workout_queue: descending exposure, then ascending loan_id.
  - severe_bucket_counts: ascending current_rating, then payment_status.
  - decisions: ascending application_id; concentration_flags: by sector then application_id;
    post_approval_concentrations: ascending sector.
  - reason_codes / disposition codes: ascending alphabetically.
- decline_reasons is a MAP {application_id -> sorted reason-code list} for declined apps only.
- Emit only the JSON; no narrative outside it.

## 4. Common misjudgments / exclusion rules

- Population filters: "rated 3 or worse" => current_rating>=3 (min_current_rating=3);
  "adverse / 6 or worse" => current_rating>=6. Use the API filter; don't hand-filter the full set.
- Use the 2025Q1 metric row (as-of 2025-03-31), not 2024Q4.
- Concentration denominator is total_loans_outstanding, NOT total_assets.
- Existing CRE exposure = sum of CRE loan balances, not a single field.
- SBA guaranty reduces bank_capacity_used; the SBA portion does not consume bank capacity.
- Capacity is often the binding constraint (sum of requests can exceed lending_capacity_q1).
- Null factor inputs: treat as worst-case for CDFI risk-class scoring (drives Projected Loss);
  skip nulls only for the worst-of RATING re-derivation and for DSCR stress (no DSCR -> not stressed).
- risk_tolerance comes from the segment record verbatim; do not derive it.
- Re-derived ratings may legitimately improve (lower) for a loan; that is allowed.

## 5. Step-by-step SOP for a new task

1. Read the prompt + answer_template. List every required key, its type, precision, enum set,
   and ordering rule. Identify target id (upper-case).
2. GET /api/manifest, /api/policies. Then fetch the branch/segment, metrics (2025Q1),
   loans (with the right min_current_rating / loan_type), sector-exposures, applications,
   and the named benchmark.
3. Determine the population from the prompt's wording and apply the API filter.
4. Apply the relevant policy rules (section 2): re-derive ratings (worst-of), CDFI scores,
   DSCR stress, weighted CRE score, capacity/concentration, benchmark variance, posture.
5. Make ALL enum/decision/action choices strictly from the policy tables and prompt; never invent
   a threshold. For decision/recommendation/classification tasks, double-check the core anchors.
6. Assemble JSON exactly per template: keys, ordering, precision, enums. Round at the end.
7. Self-check (below), then emit JSON only.

## 6. Self-check list

- [ ] All required top-level + nested keys present; no extras the template forbids.
- [ ] Every numeric field rounded to its template precision (money 2dp, ratio 4dp, bps 2dp,
      DSCR 2dp, weighted score 1dp, factor_score integer, NCUA metrics integer).
- [ ] Every list sorted by its specified ordering rule (check direction and tiebreakers).
- [ ] Every enum value is spelled exactly from the allowed set.
- [ ] Population/filter matches the prompt (rating>=N, loan_type, as-of quarter).
- [ ] Concentration denominator = total_loans_outstanding; CRE exposure = sum of CRE balances.
- [ ] Benchmark metric matches the asset class (total_loans_noncurrent_pct vs
      total_real_estate_30_89_pct vs construction/development).
- [ ] variance_bps = (branch_ratio - benchmark_ratio) * 10000.
- [ ] Stress used the correct formula (watch-list /1.18 vs CRE *0.85/1.18); threshold 1.0.
- [ ] risk_tolerance / required_checklist_gates copied verbatim from the segment.
- [ ] decline_reasons is a map of declined apps only; reason codes sorted alphabetically.
- [ ] Output is pure JSON, no surrounding text.
