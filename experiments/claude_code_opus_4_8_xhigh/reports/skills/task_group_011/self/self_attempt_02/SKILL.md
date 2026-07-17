---
name: self_attempt_02
description: Credit-risk / lending-committee SOP for the "credit office" HTTP API environment (rating regrade, CDFI scoring, concentration & capacity, DSCR stress, CRE decisioning, NCUA segment posture).
---

# Credit Office — Lending Committee Solver SOP

You produce committee-ready JSON for a "credit office" environment exposed as a read-only HTTP API.
Every task names a target (branch_id, segment_id, or competing applications) and an answer template
that exactly defines the output keys, enums, ordering, and per-field precision. Match the template
shape literally. Output JSON only — no prose.

## 0. Golden rules

- **Use the remote API, never local files.** Ignore any prompt instruction to run `env/setup.sh` or
  read a local `env/` dir. Base URL (no auth, GET only): `<remote-env-url>`
- **Branch ids are upper-cased by the server.** Use e.g. `REDWOOD`, `LAKEVIEW`, `SUMMIT`, `HARBOR`.
  Segment ids are used as given (e.g. `CIVIC_NC_FIRE_EMS`).
- **Always fetch `/api/policies` first** — it holds the real numeric rules (rating thresholds, CDFI
  factor tables + class ranges, CRE weighted-score weights+classes, stress formulas, concentration
  rules). Then fetch only the data the specific task needs.
- **Precision is per field, set by the template.** Apply Python `round(x, n)` at the END. Conventions:
  money/exposure = 2 dp; ratios/percentages-as-ratios = 4 dp; bps = 2 dp; DSCR = 2 dp;
  CRE weighted score = 1 dp; CDFI factor_score & ratings & counts = integers.
  Percentages are emitted as **ratios** (0.2106), not as 21.06, unless template says otherwise.
- **bps = ratio * 10000**, computed from the (already 4-dp) ratio then rounded to 2 dp.
  `variance_ratio = branch_ratio - benchmark_ratio`; `variance_bps = variance_ratio * 10000`.
- Respect every `ordering` directive and use only the template's enum values verbatim.

## 1. API endpoints — what to call for what

```
GET /api/health                                  # record counts (sanity)
GET /api/manifest                                # versions: fdic_q4_2024, ncua_q1_2025; policy_version
GET /api/policies                                # ALL business rules (see section 2)
GET /api/branches                                # all 10 branches (cre_policy_limit_pct, sector_ceiling_pct,
                                                 #   lending_capacity_q1, total_assets, state_code, institution_type)
GET /api/branches/{ID}                           # one branch's same fields
GET /api/branches/{ID}/metrics[?quarter=2025Q1]  # nonperforming_loans, total_loans_outstanding,
                                                 #   delinquency_30_plus_pct, allowance, net_charge_offs (2 quarters: 2025Q1, 2024Q4)
GET /api/branches/{ID}/loans[?loan_type=&payment_status=&min_current_rating=]   # portfolio
GET /api/branches/{ID}/sector-exposures          # per-sector current_exposure, limit_pct, grandfathered (0/1)
GET /api/branches/{ID}/applications[?loan_type=] # pending apps (CRE app pairs end in -901/-902)
GET /api/benchmarks/fdic/q4-2024                 # one FDIC row (ratios below)
GET /api/benchmarks/ncua/q1-2025[?state_code=XX] # 12 state rows incl. "US"
GET /api/credit-union-segments/{SEGMENT_ID}      # segment posture inputs
```

Gotchas: metrics returns BOTH quarters — pick the as-of quarter (usually `2025Q1`). Server query
filters work but you can also filter client-side. CRE concentration uses `loan_type=="CRE"` on loans,
NOT the `sector` label (sectors named "Retail CRE"/"Industrial CRE" are sector tags, not the CRE class).

## 2. Policy ruleset (from `/api/policies`) — memorize the structure, re-read the numbers each run

### 2a. Risk-rating re-derivation (`risk_rating`)
Final re-derived rating = **worst (max numeric) of the available factor ratings** ("dominant factor rule").
Factors: DSCR rating, LTV/collateral rating, delinquency minimum. Skip any factor whose input is null.
If NO factor is available, keep the loan's existing `current_rating` (no change).

- DSCR thresholds (use value if not null): `>=1.5 →3`, `>=1.25 →4`, `>=1.05 →5`, `>=1.0 →6`, `<1.0 →7`.
- LTV thresholds: `<=0.65 →3`, `<=0.75 →4`, `<=0.85 →5`, `<=1.0 →6`, `>1.0 →7`.
- Delinquency minimums by `payment_status`: `Current→none`, `30 Days Past Due→4`,
  `60 Days Past Due→5`, `90+ Days Past Due→7`, `Nonaccrual→8`.
- `material_downgrade_notches = 2`: a "material downgrade" is final_rating − current_rating **>= 2**.
  Loans that regrade UP (negative notches) are NOT downgrades.

### 2b. CDFI factor scoring (`cdfi_factor_scores`) — lower score is better
Sum the available factor scores (skip nulls):
- FICO: `>720 →0`, `680–720 →1`, `580–679 →3`, `<580 →5`.
- LTV: `<0.40 →0`, `0.40–0.60 →2`, `0.60–0.80 →4`, `>0.80 →6`.
- debt_to_asset: same bands as LTV (`<0.40→0, 0.40–0.60→2, 0.60–0.80→4, >0.80→6`).
- liquidity_months: `>12 →0`, `6–12 →1`, `3–6 →3`, `<3 →5`.

Class by total factor_score:
`Prime 0–5`, `Desirable 6–9`, `Satisfactory 10–13`, `Watch 14–18`, `Doubtful >=19`,
**`Projected Loss` = score >=19 AND ltv > 1.0**. (A high-LTV loan with score < 19 is still just
Watch/etc — Projected Loss REQUIRES score>=19 *and* ltv>1.0. Doubtful is score>=19 with ltv<=1.0.)
Boundary handling that reproduces the tables: treat band edges as in the lower-score bucket where the
table lists an inclusive range (e.g. liquidity exactly 6 → score 1; exactly 12 → score 0).

### 2c. CRE weighted score (`cre_weighted_score`) — lower is better
Weights (the 5 C's): `capacity 0.45`, `collateral_exposure 0.36`, `conditions 0.11`,
`character 0.05`, `capital 0.03` (sum = 1.0). Score each C on the 0–6 CDFI-style scale, then take
the weighted sum (treat a missing C as 0 contribution; denominator = full 1.0 weight). Mapping used:
- capacity = DSCR mapped `>=1.5→0, >=1.25→2, >=1.05→4, <1.05→6`,
- collateral_exposure = LTV score (2b),
- capital = debt_to_asset score (2b), using `total_debt/total_assets` on the application,
- character = FICO score (2b),
- conditions = liquidity score (2b) if present, else 0.
Round weighted score to **1 dp**. Classes: `approve_quality <=2.0`, `conditional <=3.0`, `weak >3.0`.

### 2d. Stress formulas (`stress`)
- Watch-list parallel +200bp shock: `stressed_dscr = dscr / (1 + 0.18)`.
- CRE dual stress: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- `coverage_breach_threshold = 1.0`; `breaches_threshold = stressed_dscr < 1.0`.
- Only include loans/apps where DSCR is present in the `results` list. Round DSCRs to 2 dp.
  Decide the breach on the **unrounded** stressed value, then report the rounded value.

### 2e. Capacity & concentration (`capacity_concentration`)
- Sector concentration denominator = the branch's **total loans** = latest-quarter
  `total_loans_outstanding` (equals the sum of all `sector-exposures.current_exposure`).
- Per-sector ceiling = that sector's `limit_pct` from `/sector-exposures` (falls back to branch
  `sector_ceiling_pct` if a sector isn't listed). CRE class ceiling = branch `cre_policy_limit_pct`.
- `grandfathering_note`: existing over-ceiling exposure may be grandfathered (`grandfathered=1`), but a
  NEW approval may not worsen that sector without a mitigation. Some sectors already sit slightly over
  their limit even with `grandfathered=0` — treat existing exposure as grandfathered baseline.
- Allowed mitigations: `participation_required`, `reduced_amount`, `board_exception`.
- Post-approval concentration: the approved amount adds to BOTH numerator (that sector / CRE) and
  denominator (total loans): `post_pct = (sector_exp + approved) / (total_loans + approved)`.
- Lending capacity = branch `lending_capacity_q1`. Sum of approved/committed amounts must not exceed
  it; `remaining_capacity = lending_capacity_q1 − committed`.

## 3. Task playbooks

### Task A — Branch rating-migration / NPA review (e.g. REDWOOD)
Population = loans with `current_rating >= N` where N is the stated minimum (prompt "rated 3 or worse"
→ `target_current_rating_min = 3`). Re-derive every loan in the population (2a).
- `final_rating_exposure_totals`: group by final_rating; per group loan_count & summed
  `outstanding_balance`; order ascending by final_rating.
- `migration_from_current_rating_3`: among the population, take loans whose **current_rating == 3**,
  group by final_rating, list `loan_ids` ascending; order ascending by final_rating.
- `material_downgrades`: loans with notches >= 2; fields current_rating, final_rating,
  downgrade_notches, exposure; order ascending by loan_id.
- `npa_benchmark`: `benchmark_metric = total_loans_noncurrent_pct` (NPA review uses the noncurrent
  metric). `branch_npa_exposure = nonperforming_loans` (latest quarter),
  `branch_total_loans = total_loans_outstanding`, `branch_npa_ratio = npa/total` (4 dp),
  `fdic_benchmark_ratio` = FDIC `total_loans_noncurrent_pct`, variance ratio & bps as in §0.
  `benchmark_version` = `fdic_q4_2024`.
- `top_problem_credit`: the worst credit = highest final_rating, tie-break highest exposure. Report its
  borrower_name, payment_status, recommended_action (see §4).
- `watch_list_action_coverage`: the credits needing follow-up after regrade (the regraded population that
  warrants action). Bucket by `action` (the recommended_action of §4), order by action ascending;
  give covered_loan_count, covered_exposure, and per-action loan_count/exposure/loan_ids (ids ascending).

### Task B — Branch watch-list stress & workout (e.g. SUMMIT)
"Adversely rated" = loans with `current_rating >= 6` (per prompt: "6 or worse").
`adverse_rating_min = 6`, `adverse_loan_count`, `adverse_balance` = summed outstanding_balance.
- `risk_classes`: per loan, CDFI factor_score (2b) and risk_class; order ascending by loan_id.
- `stress_results`: +200bp watch-list formula (2d) over loans WITH DSCR; `shock_label = "+200bp"`,
  `breach_threshold = 1.0`; `breach_loan_ids` ascending.
- `workout_queue`: each adverse loan with exposure, risk_class, payment_status, recommended_action (§4),
  `projected_loss = (risk_class == "Projected Loss")`; order **descending exposure, then ascending loan_id**.
- `severe_bucket_counts`: group the adverse population by (current_rating, payment_status); loan_count &
  exposure; order ascending current_rating then payment_status.
- `monitoring_cadence`: severe/adverse watch-list books are watched `monthly`.

### Task C — Competing CRE decision (e.g. HARBOR, two -901/-902 apps)
- For each app compute `weighted_cdfi_score` (2c, 1 dp) and `score_class`.
- CRE dual stress (2d) for both apps → base_dscr, stressed_dscr, breaches_threshold; `formula` =
  the policy string `"stressed_dscr = dscr * 0.85 / (1 + 0.18)"`; threshold 1.0.
- Existing CRE: `existing_cre_exposure` = sum outstanding_balance of `loan_type=="CRE"` loans;
  `existing_cre_concentration = existing/total_loans` (4 dp); `cre_policy_limit_pct` = branch field.
- Stronger credit = lower weighted score, and prefer no stress breach. Compute
  `selected_post_approval_cre_concentration` = (existing + selected.requested)/(total + selected.requested);
  `selected_policy_variance_bps = (post − cre_policy_limit_pct) * 10000`.
- FDIC delinquency check: `fdic_benchmark_metric = total_real_estate_30_89_pct`;
  `branch_delinquency_ratio = delinquency_30_plus_pct` (latest quarter);
  `fdic_benchmark_ratio` = FDIC `total_real_estate_30_89_pct`; variance ratio & bps.
- Path: because branch CRE concentration is typically FAR over the limit, the stronger credit usually
  takes `participation_required` (caps bank-retained exposure) with committee CRE exception conditions;
  use `conditional_approve` only if concentration stays within tolerance. The weaker app is declined
  (or deferred) with `unselected_reason_codes` drawn ONLY from
  {`sector_breach`,`weak_dscr`,`high_ltv`,`fdic_adverse_variance`} that actually apply (stress breach →
  weak_dscr; CRE over limit → sector_breach; FDIC underperformance → fdic_adverse_variance; high LTV → high_ltv).
- `conditions` list (alphabetical) drawn from: `bank_retained_exposure_cap`, `committee_cre_exception`,
  `minimum_dscr_covenant_1_25`, `no_additional_cre_without_committee_review`, `quarterly_financial_reporting`,
  `tenant_roll_and_lease_review`, `updated_appraisal_before_close` — pick those justified by the facts
  (over-limit CRE → bank_retained_exposure_cap + committee_cre_exception + no_additional_cre_without_committee_review).
- Per-app `reason_codes` are alphabetical; the selected approved-via-participation app still carries the
  structural flags that apply (e.g. sector_breach, fdic_adverse_variance).

### Task D — Branch lending-committee allocation (e.g. LAKEVIEW)
Decision per application using credit floors → reason codes (enum):
- `weak_dscr`: DSCR present and < 1.25.
- `low_fico`: FICO present and < 620 (subprime; CDFI <580 is worst).
- `high_ltv`: LTV > 0.90 (CRE/secured); `underwater_collateral`: LTV > 1.0.
- `recent_bankruptcy`: `bankruptcy_months_ago` not null and recent (<= 24 months).
- `startup_risk`: `years_in_business` < 2 (esp. < 1).
- `documentation_gap`: `documentation_complete == 0`.
- `policy_floor_missing`: a required floor input is missing (e.g. no DSCR for a commercial credit).
- `sector_breach`: post-approval sector concentration > sector limit_pct.
- `capacity_limit`: cumulative approvals would exceed `lending_capacity_q1`.
- `fdic_adverse_variance` / `ncua_peer_weakness`: external benchmark underperformance.

Decision enum: `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`.
Clean strong credits → approve. Fixable issues (sector near ceiling, startup with SBA guaranty,
reducible amount) → conditional_approve with a `conditions` value
(`participation_required`/`reduced_amount`/`board_exception`/`sba_guaranty_required`/`startup_monitoring`/`none`).
Hard floor failures (recent bankruptcy + low FICO + high LTV, deep startup + high LTV) → decline.
- `allocation`: `lending_capacity_q1`, `gross_approved_amount` (sum of approved + conditional approved
  amounts), `committed_capacity_amount`, `remaining_capacity = capacity − committed`, and
  `priority_ranking` = ordered application_ids (best first) of approved & conditional_approve apps only.
- `decisions`: per app application_id, decision, approved_amount (0 for declines), bank_capacity_used,
  conditions; order ascending by application_id.
- `concentration_flags`: per (sector, application) where the approval pushes a sector to/over its limit;
  give limit_pct, post_approval_pct (4 dp ratio), flag, handling (enum incl. `none`); order by sector
  then application_id.
- `decline_reasons`: object mapping each declined application_id → sorted list of reason codes.
- `post_approval_concentrations`: per sector, exposure_after_approval, post_approval_pct (4 dp),
  limit_pct, over_limit (bool); order ascending by sector.

### Task E — Credit-union segment posture (e.g. CIVIC_NC_FIRE_EMS)
Inputs: `/api/credit-union-segments/{ID}` + `/api/benchmarks/ncua/q1-2025`.
- `state_metrics`: take the segment's `state_code` row from NCUA verbatim (integers as reported):
  delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct. `benchmark_version=ncua_q1_2025`.
- `peer_comparison.peer_states` = segment `peer_states`, sorted ascending. Compute direction of the
  segment state's value vs the `US` row (`nc_vs_us`) and vs the **median of the peer-state rows**
  (`nc_vs_peer_median`), per metric: `higher`/`lower`/`equal`.
- `external_risk_status`: weigh delinquency (lower=better), roaa & positive_net_income (higher=better),
  loan_to_share (context). If the state is worse on delinquency AND profitability vs both US and peer
  median → `weaker_than_national_and_peers`. Map analogously for stronger/mixed.
- `capacity_status`: compare segment `quarterly_capacity` headroom & `notes`. If notes say capacity is
  available (with added controls) → `capacity_available`; constrained/none otherwise.
- `posture`: capacity available but external risk weaker → `continue_with_tighter_conditions`
  (use `temporarily_pause` only if metrics are bad AND notes say pause; `continue_approving` if strong).
- `risk_tolerance`: a controlled/tightened stance is `restrained` even if the segment's stated tolerance
  is "moderate"; `committee_message` then = `capacity_available_but_external_risk_weaker`.
- `controls.required_checklist_gates` = map the segment `minimum_checklist` items to the enum
  (board_authorization, equipment_invoice, public_contract_or_tax_support, proof_of_insurance,
  ucc_or_title_lien, plus fleet_replacement_plan/payer_contract_summary if the focus warrants).
- `controls.added_operating_controls`: pick from the enum to address the segment's `internal_context`
  issues (missed insurance binder → pre_close_insurance_binder_verification +
  lien_perfection_prior_to_funding; staffing constraint → senior_underwriter_second_review;
  weaker external metrics → quarterly_state_benchmark_monitoring + monthly_segment_delinquency_watch).
- `escalation_triggers`: list with trigger_id (ascending), condition (from the enum, e.g.
  `segment_recent_delinquency_ge_90_bps`, `missing_insurance_or_lien_exception`,
  `quarterly_capacity_exceeded_or_exception_requested`, `state_delinquency_gap_widens_25_bps`) and owner
  (`credit_risk_manager` / `operations_control_manager` / `lending_committee_chair`). Match owners to
  the nature of the trigger (credit metrics→credit_risk_manager; control/insurance→operations_control_manager;
  capacity/exception→lending_committee_chair).

## 4. recommended_action / handling mapping (severity ladder)
Action enum severity (low→high): `monitor` < `watchlist` < `special_assets` < `workout` <
`partial_chargeoff_review` < `legal_referral`. Map by final/current rating, risk_class, and payment status:
- pass-ish (final rating 3–4 / Prime–Desirable, Current) → `monitor`
- rating 5 / Satisfactory–Watch, current but weak → `watchlist`
- rating 6 / Watch → `special_assets`
- rating 7 / Doubtful, or 90+ days past due → `workout`
- Nonaccrual / underwater collateral / Projected Loss → `legal_referral` (or
  `partial_chargeoff_review` when a partial charge-off is the documented step).
The single worst credit (highest rating, Nonaccrual) typically → `legal_referral`.

## 5. Step-by-step SOP for a new task
1. Read the prompt: identify task type (A–E), target id(s), as-of date, population threshold, the exact
   output template file `input/payloads/answer_template.json`.
2. `GET /api/policies`; then fetch only the needed data (branch + metrics + loans/sector-exposures/
   applications, or segment + NCUA, or FDIC benchmark). Use upper-case branch ids.
3. Determine the population/exclusions precisely (rating threshold; loan_type=="CRE"; pending apps).
   Skip null factors; keep current_rating when no factor exists; honor grandfathering.
4. Compute with the §2 rules. Decide breaches on unrounded values; round only at output.
5. Assemble JSON to the template: every required key, correct enums, correct ordering, correct precision
   (money 2dp, ratios 4dp, bps 2dp, DSCR 2dp, CRE score 1dp, integers for counts/ratings/factor_score).
6. Self-check: (a) each required_top_level_key present; (b) no value outside the allowed enum sets;
   (c) lists sorted as specified; (d) ratios emitted as fractions not whole percents;
   (e) variance_bps == round(variance_ratio*10000, 2); (f) sums (loan_count/exposure) reconcile to the
   population; (g) `branch_id`/`segment_id` echoes the target exactly. Output JSON only.
