# Skill: Credit-Risk / Lending-Committee Answer Generation

Reusable workflow rules distilled from a 3-round reflect loop on 5 credit-risk train
tasks (branch rating migration, Q1 allocation package, credit-union segment posture,
watch-list stress packet, competing CRE decision). These are WORKFLOW RULES, not
answers. Apply them to any task in this family.

## 1. Remote API SOP

The environment is a REMOTE read-only HTTP API. Never look for local `env/` source,
DB files, or a local server.

- Base URL: `<remote-env-url>`  (all endpoints under `/api`)
- Call with `curl -s ... | jq ...`. No auth. GET only.
- Endpoints used:
  - `/api/health`, `/api/manifest` (versions, policy_version, record counts)
  - `/api/policies` (capacity/concentration, risk-rating, cdfi_factor_scores,
    cre_weighted_score, stress) — READ THIS FIRST, it drives every rule below.
  - `/api/branches`, `/api/branches/{branch_id}` (assets, lending_capacity_q1,
    sector_ceiling_pct, cre_policy_limit_pct, state_code, institution_type)
  - `/api/branches/{branch_id}/metrics?quarter=` (per-quarter: total_loans_outstanding,
    nonperforming_loans, delinquency_30_plus_pct, allowance, charge-offs, deposits)
  - `/api/branches/{branch_id}/loans` (filter `?loan_type=`, `?payment_status=`,
    `?min_current_rating=`). Fields: outstanding_balance, dscr, ltv, debt_to_asset,
    liquidity_months, fico, current_rating, payment_status, guarantor_strength, sector.
  - `/api/branches/{branch_id}/sector-exposures` — fields are `current_exposure`,
    `limit_pct`, `grandfathered` (NOT "exposure"/"concentration_pct").
  - `/api/branches/{branch_id}/applications` (pending apps)
  - `/api/benchmarks/fdic/q4-2024`, `/api/benchmarks/ncua/q1-2025?state_code=`
  - `/api/credit-union-segments/{segment_id}`
- Fetch the policy JSON and both benchmark sets ONCE and reuse. Use the LATEST
  quarter metrics (e.g. `2025Q1`) unless the task names a quarter.

## 2. Risk-Rating Re-derivation (rating-migration tasks)

Policy `risk_rating`. Re-derive the final rating for each loan in the regrade
population and NEVER substitute a "sensible" override — apply the rule strictly.

- Regrade population = loans with `current_rating >= target_current_rating_min`
  (task-dependent, e.g. >= 3). Pass loans (rating <= 2) are EXCLUDED.
- Compute a factor rating from each AVAILABLE factor; the final rating is the
  WORST (max numeric) of the available factor ratings:
  - DSCR thresholds: `>=1.5→3, >=1.25→4, >=1.05→5, >=1.0→6, <1.0→7`
  - LTV thresholds: `<=0.65→3, <=0.75→4, <=0.85→5, <=1.0→6, >1.0→7`
  - Delinquency minimums (a FLOOR that is itself a factor): Current→(no floor),
    30 DPD→4, 60 DPD→5, 90+ DPD→7, Nonaccrual→8
- "Available" = factor is non-null. A loan whose ONLY available factor is the
  delinquency floor STILL takes that floor as its final rating (do NOT keep the
  current rating to avoid an upgrade). Confirmed: overruling this dropped the
  score. Only when NO factor is available at all do you carry the current rating.
- Material downgrade = `final_rating - current_rating >= 2` notches
  (`risk_rating.material_downgrade_notches`).
- `final_rating_exposure_totals`: ALL regrade-pop loans grouped by final_rating
  (ascending), no loan_ids.
- `migration_from_current_rating_3`: the rating-3 stratum — loans whose CURRENT
  rating == 3, grouped by final_rating, WITH loan_ids (ascending). (If the field
  appears elsewhere with a threshold suffix, treat "_3" as referring to the
  current-rating-3 stratum, not the whole population.)

## 3. Watch-list Action Coverage & Workout Actions

- Watch-list coverage population = loans with `final_rating >= 5` (Watch and
  below). Pass loans (final 3-4) are NOT covered. Confirmed by feedback.
- Recommended-action ladder by final rating (ascending severity):
  - 5 → `watchlist`
  - 6 → `special-assets`
  - 7 → `workout`
  - 8 → `partial_chargeoff_review` (Nonaccrual / underwater-collateral cases)
  - (3-4 → `monitor`, only if a pass loan must be listed)
- `top_problem_credit` = the worst final rating (highest), break ties by exposure;
  for ties use the Nonaccrual/underwater loan. Its recommended_action must match
  the coverage action for the same loan.
- Adverse/watch-list population for stress tasks = `current_rating >= 6`
  ("6 or worse"). `severe_bucket_counts` summarises payment-status counts by
  rating bucket — include the ratings the task calls "severe" (verify 6-vs-7,8
  scope; the natural read is the same adverse population, but "severe" may mean
  7-8 only — check against the task wording).
- `monitoring_cadence`: monthly for severe/workout lists; quarterly for a
  watch-list review packet. Pick the one matching the packet's severity.

## 4. CDFI Factor Scores & Risk Classes (watch-list / CRE scoring)

Policy `cdfi_factor_scores`. Factor tables (fico, ltv, debt_to_asset,
liquidity_months) each map a value to a 0-6 score; sum them into a `factor_score`.

- MISSING factor → assign the WORST score for that factor (penalise missing data):
  fico null→5, ltv null→6, debt_to_asset null→6, liquidity_months null→5.
  Confirmed: switching null→0 to null→worst raised the score materially.
- fico: `>720→0, 680-720→1, 580-679→3, <580→5`
- ltv: `<0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6`
- debt_to_asset: same ranges/scores as ltv
- liquidity_months: `>12→0, 6-12→1, 3-6→3, <3→5`
- Risk class from factor_score: Prime 0-5, Desirable 6-9, Satisfactory 10-13,
  Watch 14-18, Doubtful >=19, `Projected Loss` = `>=19 AND ltv>1.0`.
- `projected_loss` boolean (workout queue) = `risk_class == "Projected Loss"`.

## 5. Stress Formulas

Policy `stress`. Two formulas — use the one the task names:

- Watch-list +200bp parallel shock (watch-list stress packets):
  `stressed_dscr = dscr / (1 + 0.18)`; `shock_label = "+200bp"`;
  `coverage_breach_threshold = 1.0`; breach = `stressed_dscr < 1.0`.
  Include only loans WITH a DSCR (skip null DSCR).
- CRE dual-stress (competing-CRE decisions):
  `stressed_dscr = dscr * 0.85 / (1 + 0.18)`; threshold 1.0.
  Put the formula string verbatim from the policy into the `formula` field when
  the template has one.

## 6. CRE Concentration & FDIC Variance (competing-CRE / concentration tasks)

- `cre_policy_limit_pct` and `sector_ceiling_pct` come from the branch record;
  per-sector `limit_pct` comes from `/sector-exposures`.
- DENOMINATOR RULE: every concentration/delinquency ratio divides by
  `total_loans_outstanding` (from metrics) — NOT total_assets, NOT total_deposits.
  This is a frequent error.
- existing_cre_concentration = `sum(CRE loan balances) / total_loans_outstanding`.
- post_approval concentration (per sector) =
  `(existing_sector_exposure + sum of approved amounts in that sector) / total_loans_outstanding`.
- `selected_post_approval_cre_concentration` =
  `(existing_cre + selected_app.requested_amount) / total_loans_outstanding`.
- FDIC/NCUA variance:
  - benchmark_version: `fdic_q4_2024` / `ncua_q1_2025` (from manifest).
  - For a bank NPA review use `benchmark_metric = total_loans_noncurrent_pct`
    (FDIC 0.0098); for a CRE real-estate delinquency compare use
    `total_real_estate_30_89_pct` (FDIC 0.0051) — match the template's allowed enum.
  - `branch_*_ratio` = branch exposure / total_loans_outstanding.
  - `variance_ratio = branch_ratio - benchmark_ratio` (SIGNED; positive = branch
    worse than benchmark).
  - `variance_bps = (branch_ratio_RAW - benchmark_ratio_RAW) * 10000`, rounded to
    2dp. ALWAYS compute bps from the RAW (unrounded) variance, not from the
    4dp-rounded ratio. Confirmed: this fix alone raised a score.
- NCUA segment posture: `state_metrics` are the integer values exactly as the NCUA
  row reports (delinquency_bps, loan_to_share_pct, roaa_bps,
  positive_net_income_pct). `peer_comparison` directions (higher/lower/equal) are
  NC-vs-US and NC-vs-peer-MEDIAN (median of the segment's `peer_states`).

## 7. Credit-Union Segment Posture (segment tasks)

- `posture`: `continue_with_tighter_conditions` when capacity is available but
  external state risk is weaker and there are control issues (the typical case
  when notes say "capacity remains available when added closing controls are
  used"). `temporarily_pause` only if metrics must recover first;
  `continue_approving` only for a strong segment.
- `controls.required_checklist_gates` = the segment's `minimum_checklist` set
  (from the segment endpoint). Do NOT add gates that aren't in the segment's
  list just because they appear in the template's universe (e.g. fleet/payer
  gates belong to other segments unless the segment lists them).
- `controls.added_operating_controls`: add controls justified by the segment's
  `internal_context` and `notes` — e.g. `pre_close_insurance_binder_verification`
  (missed insurance binder), `lien_perfection_prior_to_funding` (lien closing
  control), `quarterly_state_benchmark_monitoring` + `monthly_segment_delinquency_watch`
  (state/segment delinquency above median), `senior_underwriter_second_review`
  (oversight). Do NOT add `committee_exception_for_capacity_overrun` unless a
  capacity overrun actually exists. (Removing two confirmed-correct controls
  broke the score; each added control is checked individually.)
- `escalation_triggers`: one per condition in the template's condition_choices,
  ordered by ascending `trigger_id`; owner mapping: delinquency/state-benchmark
  triggers → `credit_risk_manager`; insurance/lien operational triggers →
  `operations_control_manager`; capacity/exception triggers → `lending_committee_chair`.
- `interpretation`: capacity_status from the segment's available capacity;
  external_risk_status from NC-vs-national-and-peers; risk_tolerance mirrors the
  segment's stated `risk_tolerance`; committee_message matches the
  capacity×external-risk combination.

## 8. Q1 Allocation Package (capacity tasks) — best-effort, structurally fragile

This task type was the hardest to score (feedback returned 0.0 across rounds;
treat the rules below as UNVERIFIED hypotheses and double-check field shapes):

- `allocation`: `lending_capacity_q1` (from branch) = gross capacity;
  `gross_approved_amount` = sum of approved_amount over approve+conditional apps;
  `committed_capacity_amount` = sum of `bank_capacity_used` (bank-retained, after
  participations); `remaining_capacity = lending_capacity_q1 - committed`.
  `priority_ranking` = application_ids of approved+conditionally-approved apps,
  strongest credit first.
- Hard DECLINE triggers (reason codes): `recent_bankruptcy` (months_ago < 24),
  `low_fico` (<580), `underwater_collateral` (ltv>1.0), `documentation_gap`
  (documentation_complete==0), `weak_dscr` (dscr<1.0, or consumer DTI>0.50).
- Mitigable → `conditional_approve` with conditions: `sector_breach`
  (post-approval sector > limit_pct) → `participation_required`;
  `high_ltv` (ltv>0.85) / `weak_dscr` (1.0-1.25) → `reduced_amount`;
  `startup_risk` (years_in_business<2) → `startup_monitoring` (and
  `sba_guaranty_required` if SBA guaranty present).
- `participation_required` appears in BOTH the decision enum and the conditions
  enum. Prefer using it as a CONDITION on a `conditional_approve` decision (the
  decision stays approve/conditional_approve/decline/defer). Bank-retained
  capacity for a participation loan = retain only up to the sector headroom
  (limit×total_loans − existing sector exposure), sell the rest.
- For a sector ALREADY over its ceiling, a new approval worsens it → decline
  (`sector_breach`) unless the credit is strong enough to mitigate via full
  participation.
- `concentration_flags`: one entry per app whose post-approval sector > limit
  (`flag` boolean true), sorted by sector then application_id; `handling` =
  how the breach is treated (decline / participation_required / conditional_approve).
- `decline_reasons`: object mapping each DECLINED application_id → its sorted
  list of reason codes (only declined apps are keys).
- `post_approval_concentrations`: per sector with approved apps, sorted by sector.
- Conditions list for every app: `["none"]` for approve/decline/defer; the
  specific mitigations for conditional_approve.

## 9. Decision / Reason / Condition Enums (exact strings)

- Decisions: `approve`, `conditional_approve`, `decline`, `defer`,
  `participation_required`.
- Conditions: `participation_required`, `reduced_amount`, `board_exception`,
  `sba_guaranty_required`, `startup_monitoring`, `none`.
- Decline reason codes: `capacity_limit`, `sector_breach`, `weak_dscr`,
  `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`,
  `underwater_collateral`, `policy_floor_missing`, `documentation_gap`,
  `fdic_adverse_variance`, `ncua_peer_weakness`.
- Recommended actions (workout/watch-list): `monitor`, `watchlist`,
  `special-assets`, `workout`, `partial_chargeoff_review`, `legal_referral`.
- Payment status: `Current`, `30 Days Past Due`, `60 Days Past Due`,
  `90+ Days Past Due`, `Nonaccrual`.
- CDFI risk classes: `Prime`, `Desirable`, `Satisfactory`, `Watch`, `Doubtful`,
  `Projected Loss`.
- CRE score classes: `approve_quality` (<=2.0), `conditional` (<=3.0), `weak`
  (>3.0). Lower weighted score is better.

## 10. CRE Weighted Score (competing-CRE) — UNRESOLVED, treat with care

Policy `cre_weighted_score`: weights capacity 0.45, capital 0.03, character 0.05,
collateral_exposure 0.36, conditions 0.11 (sum 1.0); classes approve_quality<=2.0,
conditional<=3.0, weak>3.0. The 5-C sub-score inputs are NOT documented in the
policy and this was the single biggest unresolved gap (score stuck at ~0.21
regardless of null treatment). Best-guess mapping to investigate:
capacity→DSCR (score 0-6), capital→debt_to_asset, character→fico, collateral_exposure→ltv,
conditions→liquidity, then weighted sum rounded to 1dp. NULL treatment
(null→0 vs null→worst) did NOT change the score here, so the mapping itself is
likely wrong — re-derive carefully (consider character→guarantor_strength,
conditions→sector/purpose, or a DSCR score table derived from the
`risk_rating.dscr_thresholds`). Compare the two apps; the lower score is the
stronger credit and becomes the selected path.

## 11. Numeric Conventions & Output Discipline

- Money: 2 decimals (USD). Ratios/percentages: 4 decimals. Basis points: 2
  decimals, SIGNED (positive = branch/adverse over benchmark).
- Compute bps from RAW values, round only the final bps (never from a pre-rounded
  ratio). Compute ratios to 4dp from raw, independently.
- All list orderings are explicit in each template — follow them exactly:
  ascending loan_id / application_id / sector / trigger_id / action; "descending
  exposure then ascending loan_id" for workout queues; sort reason-code lists
  alphabetically.
- Output ONLY the JSON object matching `answer_template.json` — no narrative
  text outside the JSON.
- Re-derive every value from live API data; do not hard-code.

## 12. Common Misjudgments to Avoid

- **bps from rounded ratio** → recompute from raw variance. (corrected, +score)
- **"Sensible" override of the strict re-derivation rule** (e.g. keeping current
  rating for a delinquency-only loan to avoid an upgrade) → WRONG. Apply
  max-of-available-factors strictly. (overruling dropped the score)
- **CDFI null→0** → WRONG. Use worst-tier score for missing factors. (corrected, +score)
- **Concentration denominator = total_assets** → WRONG. Use total_loans_outstanding.
- **Regrade population vs watch-list coverage**: regrade population is
  `current_rating >= min` (e.g. >=3); watch-list action coverage is
  `final_rating >= 5`. Different sets.
- **Severe-delinquency override**: Nonaccrual/90+ delinquency is a factor equal
  to its floor (8/7) even when DSCR/LTV are absent — it must be the max.
- **Including pass loans in coverage** (final 3-4) → exclude; only final>=5.
- **Adding template-universe checklist gates not in the segment's
  minimum_checklist** → only use the segment's actual gates.
- **Global string-replace when patching a build script** → it can hit multiple
  loops and silently corrupt other sections; patch the specific code block.
- **participation_required as a standalone decision vs as a condition** →
  prefer conditional_approve + participation_required condition unless the
  template clearly wants the decision value.

## 13. Iterative Verification Discipline

When iterating on a candidate answer, change ONE hypothesis per round where
possible so the score delta isolates the fix; keep the best-scoring candidate.
When a candidate scores near-zero across several unrelated content changes,
suspect a structural/conformance issue (field type, enum value, missing key,
wrong list ordering) rather than content, and re-read `answer_template.json`
field-by-field before retrying. Verify each list's required ordering and each
field's required type/precision against the template before submitting.
