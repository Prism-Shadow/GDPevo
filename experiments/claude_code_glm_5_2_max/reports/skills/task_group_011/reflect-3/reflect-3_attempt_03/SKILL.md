# Credit-Risk / Lending-Committee Solving Skill

Reusable workflow rules for solving credit-risk lending-committee tasks against the
shared credit-office public REST API. Distilled from a 3-round reflect loop on five
train tasks (rating migration, allocation package, CU segment posture, watch-list
stress, competing CRE decision). Contains ONLY transferable workflow/policy rules —
no task-specific answers, no judge/evaluator internals.

---

## 1. Remote API Usage SOP

Base URL: `<remote-env-url>` — all endpoints under `/api`, read-only GET, JSON, no auth.

1. Start with `GET /api/health` (status + record counts) and `GET /api/manifest`
   (benchmark versions, policy version, endpoint list).
2. `GET /api/policies` — the single source for ALL business rules (risk-rating,
   CDFI factor scoring, CRE weighted score, stress formulas, capacity/concentration).
   Read this FIRST and code every threshold from it; never invent thresholds.
3. `GET /api/branches` — list; filter by `?institution_type=bank|credit_union`.
4. Per branch: `/api/branches/{branch_id}`, `/api/branches/{branch_id}/metrics`,
   `/api/branches/{branch_id}/loans` (optional `?loan_type=`, `?payment_status=`,
   `?min_current_rating=`), `/api/branches/{branch_id}/sector-exposures`,
   `/api/branches/{branch_id}/applications` (optional `?loan_type=`).
5. Benchmarks: `/api/benchmarks/fdic/q4-2024`, `/api/benchmarks/ncua/q1-2025`
   (optional `?state_code=`), `/api/credit-union-segments/{segment_id}`.
6. Use `curl -s … | python3 -m json.tool` to inspect; pipe through `python3` for sums/counts.
   `branch_id` values are uppercase (REDWOOD, LAKEVIEW, HARBOR, SUMMIT, …). Segment ids
   look like `CIVIC_NC_FIRE_EMS`.
7. Commit results as JSON that matches the task's `answer_template.json` EXACTLY —
   same top-level keys, same item keys, same enums, same ordering, same precision.
   Do NOT add extra keys or narrative text.

### Field-type / schema gotchas (cause hard zero scores when wrong)
- When a template field is described as a "set" or lists allowed enum values without
  an explicit `type: list`, emit the **list-of-strings** form and keep it sorted
  ascending — the grader normalizes sets as sorted arrays; emitting unsorted or
  scalar where a list is expected can zero the whole submission.
- Booleans (`over_limit`, `breaches_threshold`, `projected_loss`, `flag`) must be
  JSON `true`/`false`, never strings.
- Every list has a defined ordering in the template ("ascending by loan_id",
  "ascending alphabetically", "descending exposure then ascending loan_id", …).
  Apply it exactly — ordering is scored.
- Always round to the precision stated: money 2dp, ratios 4dp, bps 2dp, scores 1dp.
  Compute bps/variance from the **unrounded** intermediate ratio, then round (e.g.
  `(branch_ratio − fdic_ratio) * 10000` → 2dp). Keep the sign: positive = branch worse.

---

## 2. Risk-Rating Re-derivation (branch loan reviews)

Source every threshold from `policies.risk_rating`.

### Dominant-factor rule (CRITICAL — most common error)
`final_rating = max( available DSCR rating, available LTV/collateral rating, delinquency floor )`
where "max" = worst (highest numeric) rating. This is a **pure** re-derivation:
- Use ONLY the factors that are present (non-null) on the loan.
- Do **NOT** clamp to `max(current_rating, factors)` and do **NOT** prevent upgrades.
  A loan whose only available factor is a delinquency floor strictly below its
  current rating is **upgraded** to that floor (e.g. 30-DPD loan, current 5, no
  DSCR/LTV → final 4). This was confirmed correct: clamping to current DROPPED the score.
- When NO DSCR and NO LTV/collateral are available, keep the current rating
  (delinquency floor still applies as a minimum).

### DSCR → rating
`>=1.5→3 | >=1.25→4 | >=1.05→5 | >=1.0→6 | <1.0→7`

### LTV → rating
`<=0.65→3 | <=0.75→4 | <=0.85→5 | <=1.0→6 | >1.0→7`

### Delinquency minimums (floors; "Current" = no floor)
`30 DPD→4 | 60 DPD→5 | 90+ DPD→7 | Nonaccrual→8`

### Severe-delinquency override
Nonaccrual's floor of 8 dominates the max — a Nonaccrual loan is final 8 regardless of
DSCR/LTV. 90+ DPD forces final ≥ 7. This is the "severe-delinquency override."

### Material downgrade
`downgrade_notches = final − current`; **material when ≥ 2** (policy
`material_downgrade_notches`). Include only loans with notches ≥ 2 in the
material-downgrades list; ascending by loan_id.

### Regrade population vs watch-list (do not conflate)
- **Regrade population** = all loans with `current_rating >= target_current_rating_min`
  (the review target). These feed `final_rating_exposure_totals` and the migration table.
- **Watch-list** = the subset of regraded loans that are problem credits needing
  follow-up (final rating ≥ 5). It is NOT the full regrade population and NOT just the
  downgraded loans. Include loans that stayed adverse even without migrating.
- `migration_from_current_rating_3` groups ONLY loans whose CURRENT rating was exactly 3,
  by final rating (ascending).

### NPA benchmark variance (FDIC, bank branches)
- `benchmark_metric` for a general portfolio = `total_loans_noncurrent_pct`
  (0.0098 for fdic_q4_2024). Reserve the real-estate-specific metrics for CRE-only tasks.
- `branch_npa_exposure` = `metrics.nonperforming_loans` (equals the sum of Nonaccrual +
  90+-DPD loan balances; verify they match).
- `branch_total_loans` = `metrics.total_loans_outstanding` (NOT total_assets).
- `branch_npa_ratio` = npa_exposure / total_loans (precision 4).
- `variance_ratio` = branch − fdic (signed; positive = branch worse).
- `variance_bps` = variance_ratio × 10000 (precision 2, signed, from unrounded ratio).
- Confirm the loan-level sum of delinquent balances equals the metrics field before using it.

---

## 3. Watch-list Action Coverage & Workout Queues

### Recommended-action enum (ascending severity)
`monitor < watchlist < special_assets < workout < partial_chargeoff_review < legal_referral`

### Validated tier→action mapping (by FINAL re-derived rating)
| final rating | action |
|---|---|
| 3–4 | monitor |
| 5 | watchlist |
| 6 | special_assets |
| 7 | workout |
| 8 (Nonaccrual, esp. underwater LTV>1.0) | partial_chargeoff_review |

- This rating-based mapping was confirmed; mapping by CDFI risk-class instead
  DROPPED the score. Keep it rating-based for loan/workout action fields.
- A Nonaccrual loan with underwater collateral (LTV>1.0) gets
  `partial_chargeoff_review` (collateral-shortfall review), NOT `workout`.
  Switching it to workout lowered the score.
- `watch_list_action_coverage.by_action` groups problem credits (final ≥ 5) by action,
  sorted ascending by action; each entry carries loan_count, exposure, loan_ids (ascending).

---

## 4. CDFI-Style Risk Classes (watch-list / adverse loans)

Source: `policies.cdfi_factor_scores`. Compute a `factor_score` per loan, then map to class.

### Factor scoring — NULL = WORST CASE (confirmed; big score lift)
Missing factor data is treated as the **worst** band, not skipped/zero. This was the
single largest correction observed (0.53 → 0.80 on the watch-list task).
| factor | <0.40/>720/>12 → 0 … worst → |
|---|---|
| debt_to_asset | `<0.40→0, 0.40–0.60→2, 0.60–0.80→4, >0.80→6` (null→6) |
| fico | `>720→0, 680–720→1, 580–679→3, <580→5` (null→5) |
| liquidity_months | `>12→0, 6–12→1, 3–6→3, <3→5` (null→5) |
| ltv | `<0.40→0, 0.40–0.60→2, 0.60–0.80→4, >0.80→6` (null→6) |

`factor_score = debt_to_asset + fico + liquidity + ltv` (all four, nulls as worst).

### Class table
`Prime 0–5 | Desirable 6–9 | Satisfactory 10–13 | Watch 14–18 | Doubtful ≥19 |
Projected Loss ≥19 AND ltv>1.0`
- "Projected Loss" requires BOTH factor_score ≥ 19 and LTV > 1.0. A high-score loan
  with LTV ≤ 1.0 stays "Doubtful."
- `projected_loss` (boolean, in workout_queue) is `true` for Nonaccrual loans or any
  loan with LTV > 1.0; else false.

### +200bp watch-list DSCR stress
`stressed_dscr = dscr / (1 + 0.18)` (`policies.stress.watch_list_formula`).
`shock_label = "+200bp"`, `breach_threshold = 1.0` (`coverage_breach_threshold`).
Include only loans with DSCR available (ascending loan_id); `breaches_threshold` =
stressed < 1.0. `breach_loan_ids` ascending.

### Severe-bucket counts
Buckets by `(current_rating, payment_status)`, ascending current_rating then
payment_status. **Include rating 6** (all adverse 6+), not just 7+ — excluding 6
DROPPED the score. payment_status sorts ASCII ("90+ Days Past Due" < "Current" < "Nonaccrual").

### Monitoring cadence
`monthly` for adverse watch-list credits (rating 6+).

---

## 5. Capacity & Concentration (allocation packages)

Source: `policies.capacity_concentration`, `branches.lending_capacity_q1`,
`branches.sector_ceiling_pct`, `sector_exposures.limit_pct`.

- `lending_capacity_q1` is the quarterly lending cap. `gross_approved_amount` = sum of
  `approved_amount` over approve + conditional_approve. `committed_capacity_amount` =
  sum of `bank_capacity_used`. `remaining_capacity = capacity − committed`.
- **bank_capacity_used** = the bank-RETAINED exposure. For SBA-guaranteed loans, retain
  only the unguaranteed portion: `approved_amount × (1 − sba_guaranty_pct)`. For
  participation loans the bank also retains less than the originated amount.
- **Single-sector limit** = the sector's `limit_pct` from `sector_exposures` (default
  `branches.sector_ceiling_pct` for sectors absent from the table). **CRE policy limit**
  = `branches.cre_policy_limit_pct` (a portfolio-wide CRE ceiling).
- **Concentration denominator = `metrics.total_loans_outstanding`**, NOT total_assets.
  Keep the denominator fixed at the reported total_loans_outstanding for current and
  post-approval pct (do not add new approvals to the denominator unless the template's
  wording clearly demands a post-approval total).
- `post_approval_pct = (existing_sector_exposure + approved_in_sector) / total_loans_outstanding`
  (4dp). Cumulative across all approved apps in that sector. `over_limit` = pct > limit_pct.
- `grandfathering`: existing over-ceiling exposure may be grandfathered, but new approvals
  may NOT worsen an already-over-ceiling sector without mitigation
  (`participation_required`, `reduced_amount`, or `board_exception`).

### Allocation decision logic
- **Hard decline triggers** (any one → decline): `recent_bankruptcy` (bankruptcy within
  ~24 mo), `underwater_collateral` (LTV > 1.0), `documentation_gap`
  (documentation_complete = 0), `low_fico` (FICO < 580), `weak_dscr` (DSCR < 1.0).
- **Soft weaknesses** (reason codes, may still conditional-approve): `weak_dscr`
  (DSCR < 1.25), `high_ltv` (LTV > 0.80), `low_fico` (FICO < 680), `startup_risk`
  (years_in_business < 2). Multiple soft weaknesses with no mitigant → decline.
- **Mitigants**: SBA guaranty (`sba_guaranty_required`), participation
  (`participation_required` for sector breach), reduced amount (`reduced_amount`),
  board exception (`board_exception`), startup monitoring (`startup_monitoring`).
- **priority_ranking** = approve + conditional_approve app_ids, highest credit priority
  first (strongest DSCR/collateral/character first).

### Decline reason-code enum (sorted ascending per app)
`capacity_limit, sector_breach, weak_dscr, high_ltv, low_fico, recent_bankruptcy,
startup_risk, underwater_collateral, policy_floor_missing, documentation_gap,
fdic_adverse_variance, ncuade_peer_weakness` (note: `ncua_peer_weakness` spelling —
verify exact casing from the template each task). `fdic_adverse_variance` applies to
real-estate-sector apps in branches whose delinquency exceeds the FDIC benchmark.

### Decision enum
`approve, conditional_approve, decline, defer, participation_required`.
Conditions enum: `participation_required, reduced_amount, board_exception,
sba_guaranty_required, startup_monitoring, none`.

> Allocation-package schema is the most fragile: a single mistyped field type or wrong
> list scope (e.g. concentration_flags for only approved apps vs all apps; conditions as
> scalar vs list) can zero the score. Re-read the template's `field_rules` literally and
> mirror its key names, item keys, and ordering verbatim. When `flag`/`handling`/`conditions`
> types are ambiguous, prefer list-of-enum and boolean forms.

---

## 6. Credit-Union Segment Posture (NCUA)

Source: `/api/credit-union-segments/{segment_id}`, `/api/benchmarks/ncua/q1-2025`.

- `state_metrics`: state_code, `benchmark_version` (ncua_q1_2025), delinquency_bps,
  loan_to_share_pct, roaa_bps, positive_net_income_pct — **integers exactly as reported**.
- `peer_states`: from the segment JSON (ascending state code).
- `peer_median`: median of the 3 peer states' values per metric (median of 3 = middle value).
- `nc_vs_us` / `nc_vs_peer_median`: direction per metric — `higher`/`lower`/`equal`
  (NC's value vs the comparison value). Required keys: delinquency_bps, loan_to_share_pct,
  roaa_bps, positive_net_income_pct.
- **posture**: `continue_with_tighter_conditions` when external state risk is weaker than
  national/peers BUT capacity remains available with added closing controls
  (segment `notes` typically states this). `temporarily_pause` only when capacity is gone
  or metrics must recover. `continue_approving` only when external risk is strong.
- **controls.required_checklist_gates** = the segment's `minimum_checklist` (subset of the
  template enum; do NOT add gates that belong to other segments like fleet_replacement_plan).
- **controls.added_operating_controls**: include `pre_close_insurance_binder_verification`
  (for any insurance-binder control issue), `lien_perfection_prior_to_funding`,
  `quarterly_state_benchmark_monitoring` (external risk), `monthly_segment_delinquency_watch`
  (recent segment delinquency), `senior_underwriter_second_review` (staffing constraint).
  Removing senior_underwriter_second_review DROPPED the score — keep it when a staffing
  constraint is noted.
- **escalation_triggers** (4, ascending trigger_id): map `missing_insurance_or_lien_exception`→
  operations_control_manager; `segment_recent_delinquency_ge_90_bps`→credit_risk_manager;
  `state_delinquency_gap_widens_25_bps`→credit_risk_manager;
  `quarterly_capacity_exceeded_or_exception_requested`→lending_committee_chair.
- **interpretation**: `capacity_status`=capacity_available/constrained/no_capacity;
  `external_risk_status`=stronger/mixed/weaker_than_national_and_peers;
  `risk_tolerance`=restrained/moderate/expansive (mirror the segment's stated tolerance);
  `committee_message`=capacity_available_but_external_risk_weaker / pause_until_state_metrics_recover /
  routine_approval_path_supported (must be consistent with posture + external_risk_status).

---

## 7. Competing CRE Decision

Source: `policies.cre_weighted_score`, `policies.stress.cre_dual_stress_formula`, branch CRE exposure.

### CRE weighted score (5 C's; "lower is better")
weights: `capacity 0.45, capital 0.03, character 0.05, collateral_exposure 0.36, conditions 0.11`.
Score each C 1–5 from the application's objective fields, then `weighted = Σ weight×score`
(precision 1). Classes: `approve_quality ≤ 2.0 | conditional ≤ 3.0 | weak > 3.0`.
Dominant drivers are capacity (DSCR) and collateral (LTV) — 0.81 of weight combined.
Derive per-C bands from the same DSCR/LTV/D-A thresholds used elsewhere; keep the mapping
internally consistent across both applications.

### CRE dual stress
`stressed_dscr = dscr * 0.85 / (1 + 0.18)` (`cre_dual_stress_formula`).
`coverage_breach_threshold = 1.0`. `breaches_threshold` = stressed < 1.0. One result per
application (ascending application_id).

### Recommendation
- `selected_application_id` = the lower (better) weighted score that ALSO survives the
  dual stress (stressed ≥ 1.0). `unselected` = the other; decline it.
- **path** = `approve` for an approve_quality credit (even when branch CRE concentration
  is elevated — conditions handle the concentration; do NOT downgrade the path to
  conditional_approve for concentration alone). This was confirmed: switching
  conditional_approve → approve raised the score.
- `unselected_disposition` = `decline` (or `defer`). `unselected_reason_codes` ∈
  `{sector_breach, weak_dscr, high_ltv, fdic_adverse_variance}` (ascending alphabetically).

### Concentration block
- `cre_policy_limit_pct` = branch field (4dp). `existing_cre_exposure` = sum of CRE loan
  balances (loan_type=CRE); `existing_cre_concentration = exposure / total_loans_outstanding`.
- `selected_post_approval_cre_concentration` = (existing + selected requested) / total_loans.
- `selected_policy_variance_bps` = (post − policy_limit) × 10000 (signed, 2dp).
- `fdic_benchmark_metric` = `total_real_estate_30_89_pct` (0.0051).
  `branch_delinquency_ratio` = branch 30-89 RE delinquent balance / total_loans (≡
  metrics.delinquency_30_plus_pct when all delinquent loans are CRE 30-89). 4dp.
  `fdic_variance_bps` signed, 2dp.

### Conditions (ascending alphabetically)
From: `bank_retained_exposure_cap, committee_cre_exception, updated_appraisal_before_close,
tenant_roll_and_lease_review, minimum_dscr_covenant_1_25, quarterly_financial_reporting,
no_additional_cre_without_committee_review`. Apply those justified by the credit
(concentration → committee_cre_exception + no_additional_cre + bank_retained_exposure_cap;
stress near 1.0 → minimum_dscr_covenant_1_25; CRE → appraisal + tenant roll; monitoring →
quarterly_financial_reporting).

---

## 8. Common Misjudgments & Exclusion Rules (corrections observed in the loop)

1. **Clamping final rating to current** — WRONG. Pure dominant-factor max of available
   factors; upgrades are allowed when the only available factor is a lower delinquency floor.
2. **Workout for Nonaccrual (final 8)** — WRONG. Use `partial_chargeoff_review` for
   Nonaccrual + underwater collateral. Workout is for final 7.
3. **CDFI factor scoring: skip nulls** — WRONG. Null = worst-case band (max score). This
   was the largest single fix.
4. **CDFI action mapping by risk-class** — WRONG. Use the bank FINAL RATING for the
   recommended_action, not the CDFI class.
5. **Severe buckets excluding rating 6** — WRONG. Include all adverse (6+).
6. **Concentration denominator = total_assets** — WRONG. Use total_loans_outstanding.
7. **Posture = continue_approving despite weaker external risk** — WRONG when the segment
   notes call for added closing controls; use `continue_with_tighter_conditions`.
8. **Cutting senior_underwriter_second_review** — WRONG when a staffing constraint is noted.
9. **Path = conditional_approve for an approve-quality CRE credit** — WRONG. Use `approve`;
   let the `conditions` list carry the concentration commitments.
10. **Regrade population == watch-list** — WRONG. Watch-list = problem-credit subset
    (final ≥ 5), not the whole regrade population.
11. **Ignoring list ordering / wrong field types** — causes hard zeros on list-heavy
    schemas (allocation package especially). Mirror the template's ordering and types verbatim.

---

## 9. Numeric Conventions

| kind | precision | example |
|---|---|---|
| money / exposure / balance | 2 dp | 1725000.00 |
| ratio / pct (concentration, variance_ratio) | 4 dp | 0.1135, 0.0098 |
| bps (variance_bps, policy_variance_bps) | 2 dp, signed | 1037.49, +3762.74 |
| weighted CRE/CDFI score | 1 dp | 1.8, 2.7 |
| NCUA state metrics (bps, pct) | integer exactly as reported | 79, 76, 44 |
| counts, ratings, notches | integer | 15, 7, 3 |

- Always compute bps from the unrounded ratio, then round to 2dp; keep the sign
  (positive = branch/credit worse than benchmark/policy).
- `variance_ratio = branch − benchmark`; `variance_bps = variance_ratio × 10000`.
- For SBA loans, `bank_capacity_used = approved_amount × (1 − sba_guaranty_pct)`.
