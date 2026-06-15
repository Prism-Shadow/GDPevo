---
name: credit-committee-packets
description: >-
  Produce committee-ready JSON answers for the shared Credit Office / lending-committee
  task family: branch loan-rating regrades and migration reviews, branch lending-capacity
  allocation packages for pending applications, credit-union segment posture pages,
  watch-list stress and workout packets, and competing CRE underwriting decisions. Use
  this skill whenever a prompt references a Credit Risk Committee, lending committee,
  branch_id or segment_id, risk-rating regrade/migration, watch-list/adverse-rated loans,
  CDFI risk classes, DSCR stress (+200bp / dual stress), NPA or delinquency benchmark
  variance (FDIC/NCUA), sector/CRE concentration limits, lending capacity allocation,
  or asks for a JSON answer matching an answer_template.json against the credit office
  HTTP API at http://127.0.0.1:8003. Apply it even when the prompt only hints at these
  (e.g. "regrade the loans rated 3 or worse", "compare the two CRE requests", "posture
  recommendation for the segment") and does not name the skill explicitly.
---

# Credit Committee Packets

You produce a single JSON object that a lending committee will read. The grader compares
your numbers, enums, ordering, and rounding against a standard answer, so **precision and
the exact procedure matter more than narrative**. There is no partial credit for prose.

Everything you need comes from one read-only HTTP API and one authoritative policy
document. **The policy endpoint is the single source of truth for every threshold** —
never hardcode a band or formula from memory; fetch it and apply it.

## 0. Universal workflow (do this every task)

1. **Read the prompt** and identify: the task type (see §1), the target `branch_id` or
   `segment_id`, the review/as-of date, and any explicit population filter (e.g. "rated
   3 or worse", "current_rating 6 or worse", the two application_ids to compare).
2. **Read `input/payloads/answer_template.json`** (or the template the prompt names). It
   defines the required top-level keys, every field, the enums, the ordering rule, and the
   rounding precision for each field. Treat it as a contract: output exactly those keys,
   nothing more, nothing less, and obey each declared `ordering` and `precision`.
3. **Fetch the data** from the API (§2). Always fetch `/api/policies` first.
4. **Compute** using the SOPs in §3–§7 for the matching task type.
5. **Emit only the JSON object.** No markdown fence, no commentary outside the JSON.

If the prompt mentions `env/setup.sh` or an "API base URL printed by setup", ignore that
plumbing — the API is already live at `http://127.0.0.1:8003`. Do not look for local
data, db, or env files; the HTTP API is the only source.

## 1. Identifying the task type

Match the prompt and the template's top-level keys to one of five families:

| Signal in prompt / template keys | Task type | SOP |
|---|---|---|
| `portfolio_regrade`, "rating migration", "re-derive risk ratings", `material_downgrades`, `npa_benchmark` | **A. Regrade & migration review** | §3 |
| `allocation`, `decisions`, `concentration_flags`, `decline_reasons`, pending applications, "lending capacity" | **B. Capacity allocation package** | §4 |
| `posture`, `state_metrics`, `peer_comparison`, `controls`, `escalation_triggers`, segment_id, NCUA | **C. Credit-union segment posture** | §5 |
| `watch_list_summary`, `stress_results`, `workout_queue`, `severe_bucket_counts`, "adverse rated", CDFI risk class | **D. Watch-list stress & workout** | §6 |
| `applications_compared`, `weighted_cdfi_score`, `recommended_path`, competing CRE, `conditions` | **E. Competing CRE decision** | §7 |

Read **`references/policy_and_formulas.md`** for the full policy schema, every band/table,
and the exact arithmetic conventions. Read it whenever you are unsure of a threshold.

## 2. Using the HTTP API

Base URL `http://127.0.0.1:8003`. All responses are JSON; money/ratios are plain numbers.
`branch_id` and `segment_id` are matched case-insensitively. Fetch with `curl` or Python
`urllib`. The endpoints you will actually use:

- `GET /api/policies` — authoritative thresholds. **Fetch first, every task.**
- `GET /api/branches/{id}` — branch row: `lending_capacity_q1`, `cre_policy_limit_pct`,
  `sector_ceiling_pct`, `state_code`, `institution_type`, `fdic_benchmark_set`.
- `GET /api/branches/{id}/metrics?quarter=YYYYQn` — quarterly metrics. Use the **2025Q1**
  row unless the review date implies otherwise. Fields: `total_loans_outstanding`,
  `nonperforming_loans`, `delinquency_30_plus_pct`, `net_charge_offs`,
  `allowance_for_loan_losses`. The endpoint returns a list (newest quarters included);
  filter to the right `quarter`.
- `GET /api/branches/{id}/loans` — one row per loan. Key fields: `loan_id`,
  `current_rating`, `dscr`, `ltv`, `debt_to_asset`, `fico`, `liquidity_months`,
  `payment_status`, `days_past_due`, `outstanding_balance`, `loan_type`, `sector`,
  `borrower_name`, `collateral_value`. Some factors are `null` — handle missing factors
  explicitly (see §3). Optional filters: `?loan_type=`, `?payment_status=`,
  `?min_current_rating=`.
- `GET /api/branches/{id}/sector-exposures` — `sector`, `current_exposure`, `limit_pct`,
  `grandfathered`.
- `GET /api/branches/{id}/applications` — pending applications. Key fields:
  `application_id`, `requested_amount`, `dscr`, `ltv`, `fico`, `dti`,
  `years_in_business`, `bankruptcy_months_ago`, `sba_guaranty_pct`,
  `documentation_complete`, `loan_type`, `sector`, plus CRE scoring inputs
  (`net_income`, `collateral_value`, `existing_relationship_years`, `co_guarantor_strength`).
- `GET /api/benchmarks/fdic/q4-2024` — `total_loans_noncurrent_pct`,
  `total_real_estate_noncurrent_pct`, `construction_development_noncurrent_pct`,
  `total_real_estate_30_89_pct`, `construction_development_30_89_pct`.
- `GET /api/benchmarks/ncua/q1-2025?state_code=XX` — per-state credit-union rows:
  `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`. Omit the
  filter to get all states including a `US` row (needed for medians/national comparison).
- `GET /api/credit-union-segments/{segment_id}` — segment posture inputs:
  `minimum_checklist`, `peer_states`, `risk_tolerance`, `quarterly_capacity`,
  `current_outstanding`, and `internal_context` (`recent_delinquency_bps`, `control_issue`,
  `staffing_constraint`).

## 3. SOP A — Regrade & rating-migration review

**Population:** loans whose `current_rating >= target_min` (the prompt states the min,
usually 3 — "rated 3 or worse"). Higher rating number = worse credit.

**Re-derive each loan's final rating** = the **worst (max) numeric rating** across the
factors for which data is available (`dominant_factor_rule`):

- DSCR rating band (policy `risk_rating.dscr_thresholds`): `>=1.5→3, >=1.25→4, >=1.05→5,
  >=1.0→6, <1.0→7`.
- LTV rating band (`ltv_thresholds`): `<=0.65→3, <=0.75→4, <=0.85→5, <=1.0→6, >1.0→7`.
- Delinquency minimum (`delinquency_minimums`) from `payment_status`: `Current→none,
  30 Days Past Due→4, 60 Days Past Due→5, 90+ Days Past Due→7, Nonaccrual→8`. This is a
  **floor** (the rating can be worse from another factor, never better).

`final_rating = max(of the available factor ratings)`. If **all** factors are null/absent
(no DSCR, no LTV, payment `Current`), keep the loan's existing `current_rating`.

**Output pieces:**
- `target_loan_count`, `target_exposure` = count and Σ`outstanding_balance` of the population.
- `final_rating_exposure_totals`: group the population by `final_rating`; per group emit
  `{final_rating, loan_count, exposure}`. Order **ascending by final_rating**.
- `migration_from_current_rating_3`: only loans whose `current_rating == 3`, grouped by
  `final_rating`, each with `loan_ids` (ascending). Order ascending by `final_rating`.
- `watch_list_action_coverage`: loans that landed on a watch action after regrade. Map
  `final_rating → recommended_action` (§8). **Only watch-rated loans are covered** —
  loans with `final_rating <= 5` get `monitor` and are excluded from coverage. Report
  `covered_loan_count`, `covered_exposure`, and `by_action` groups (ascending by `action`,
  each with ascending `loan_ids`).
- `material_downgrades`: loans where `final_rating - current_rating >= material_downgrade_notches`
  (policy value, currently 2). Per loan: `{loan_id, current_rating, final_rating,
  downgrade_notches, exposure}`. Order ascending by `loan_id`.
- `npa_benchmark`: see §9.
- `top_problem_credit`: the single worst credit — highest `final_rating`, breaking ties by
  largest `exposure`. Emit `loan_id, borrower_name, exposure, current_rating, final_rating,
  payment_status, recommended_action`.

## 4. SOP B — Capacity allocation package

Goal: decide each pending application, allocate the branch's quarterly lending capacity to
the strongest credits, and report concentration impact.

**Per-application screen.** Decline (or condition) on objective red flags. Thresholds
inferred and confirmed against the policy bands — verify each against `/api/policies`:
- `weak_dscr`: DSCR below the new-loan floor (~1.15; income-producing loans only — CRE,
  C&I, SBA, Equipment).
- `high_ltv`: LTV above ~0.80 for commercial/income-producing loans. Retail loans
  (Consumer, Residential Mortgage) tolerate higher LTV when FICO is strong.
- `low_fico`: FICO below ~620 (retail loans — Consumer/Residential — screen on FICO+LTV,
  not DSCR).
- `startup_risk`: `years_in_business < 2`.
- `recent_bankruptcy`: `bankruptcy_months_ago` present and recent (<= ~24 months).
- `capacity_limit`: an otherwise-clean credit that falls below the committee's allocation
  cutoff this round (lowest-quality qualifying applicant when appetite is constrained).
- `sector_breach`: approving would push the application's sector over its `limit_pct`.

**Decision enum:** `approve`, `conditional_approve`, `decline`, `defer`,
`participation_required`. Use `conditional_approve` when a credit is fundable only with a
mitigant (e.g. participation for a sector breach, or SBA guaranty + startup monitoring for
a young borrower). Declined apps get `approved_amount = 0.0`, `bank_capacity_used = 0.0`,
`conditions = ["none"]`.

**bank_capacity_used (the capacity charge, distinct from the booked loan amount):**
- Plain approve: `= approved_amount`.
- **SBA guaranty** (`sba_guaranty_pct` present): bank retains only the unguaranteed share:
  `bank_capacity_used = approved_amount * (1 - sba_guaranty_pct)`.
- **Participation required** (sector breach): bank retains the maximum `R` that keeps the
  breaching sector at its limit, solved against a base that also includes only retained
  amounts:
  `R = (limit_pct * (total_loans_outstanding + sum_other_retained) - existing_sector_exposure) / (1 - limit_pct)`
  where `sum_other_retained` is the Σ`bank_capacity_used` of the other approvals.

**allocation block:** `lending_capacity_q1` (from the branch row), `gross_approved_amount`
= Σ`approved_amount` over approved + conditionally-approved apps (full loan amounts),
`committed_capacity_amount` = Σ`bank_capacity_used`, `remaining_capacity` =
`lending_capacity_q1 - committed_capacity_amount`, and `priority_ranking` = the approved /
conditionally-approved `application_id`s ordered best credit first (lowest re-derived risk
rating, then higher DSCR). Approved-and-conditional only — never list declined/deferred.

**concentration_flags:** one row per sector that a new approval pushes to/over its limit.
`{sector, application_id, limit_pct, post_approval_pct (ratio, 4 dp), flag (bool),
handling}`. Order by sector then application_id.

**decline_reasons:** object mapping each **declined** `application_id` → a list of reason
codes **sorted ascending alphabetically**. Only declined apps appear.

**post_approval_concentrations:** one row per sector that received an approval. Use the
post-book base **`base = total_loans_outstanding + gross_approved_amount`** (full approved
amounts, not retained). `exposure_after_approval = existing_sector_exposure +
full_approved_amount_for_that_sector`; `post_approval_pct = exposure_after_approval / base`
(ratio, 4 dp); `limit_pct` from the sector row; `over_limit` bool. Order ascending by sector.

## 5. SOP C — Credit-union segment posture

**state_metrics:** the NCUA row for the segment's `state_code`, copied **as integers
exactly as reported** (`delinquency_bps`, `loan_to_share_pct`, `roaa_bps`,
`positive_net_income_pct`), plus `state_code` and `benchmark_version` (`ncua_q1_2025`).

**peer_comparison:** `peer_states` = the segment's `peer_states` (ascending). For each of
the 4 metrics, give the **direction of NC's value** relative to (a) the `US` row
(`nc_vs_us`) and (b) the **median across the peer states** (`nc_vs_peer_median`):
`higher`/`lower`/`equal`. Remember the polarity: higher delinquency = worse; lower roaa /
lower positive_net_income = worse.

**posture** (`continue_approving` / `continue_with_tighter_conditions` /
`temporarily_pause`): choose `continue_with_tighter_conditions` when capacity is available
but external state metrics are weaker than peers/national and there are control issues;
`temporarily_pause` only if metrics are severely adverse or capacity is gone.

**controls.required_checklist_gates** = the segment's `minimum_checklist` (these are the
gates already mandated). **added_operating_controls** = the operational mitigants the
internal_context calls for, e.g. a missed-insurance-binder control issue →
`pre_close_insurance_binder_verification` + `lien_perfection_prior_to_funding`; weak
external delinquency → `monthly_segment_delinquency_watch` +
`quarterly_state_benchmark_monitoring`; staffing/control issue →
`senior_underwriter_second_review`. Both are **sets** — emit ascending/sorted, deduplicated.

**escalation_triggers:** ordered `ET001, ET002, ...`. Each `{trigger_id, condition, owner}`
from the allowed enums. Typical mapping: delinquency breach →
`segment_recent_delinquency_ge_90_bps` / `credit_risk_manager`; insurance-or-lien gap →
`missing_insurance_or_lien_exception` / `operations_control_manager`; capacity overrun →
`quarterly_capacity_exceeded_or_exception_requested` / `lending_committee_chair`.

**interpretation:** `capacity_status` (`capacity_available` when `quarterly_capacity`
remains), `external_risk_status` (`weaker_than_national_and_peers` when NC is worse on the
risk metrics vs both US and peer median), `risk_tolerance` (pass through the segment's
`risk_tolerance`), `committee_message` (the enum matching the posture — e.g.
`capacity_available_but_external_risk_weaker`).

## 6. SOP D — Watch-list stress & workout

**Population:** "adverse rated" = loans with `current_rating >= adverse_min` (prompt states
it, usually 6). `adverse_loan_count`, `adverse_balance` = Σ`outstanding_balance`.

**risk_classes (CDFI factor scoring):** for each adverse loan, sum the per-factor scores
from policy `cdfi_factor_scores` over the available factors (skip nulls):
- FICO: `>720→0, 680-720→1, 580-679→3, <580→5`.
- LTV: `<0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6`.
- debt_to_asset: same band structure as LTV (`<0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6`).
- liquidity_months: `>12→0, 6-12→1, 3-6→3, <3→5`.

`factor_score` = that sum (report as the integer base score). Map to `risk_class` by band:
`0-5 Prime, 6-9 Desirable, 10-13 Satisfactory, 14-18 Watch, >=19 Doubtful`. **Projected
Loss override:** a credit with `ltv > 1.0` in a loss posture (Nonaccrual) is `Projected
Loss` even if its base score sits in the Watch band. Order `risk_classes` ascending by
`loan_id`. `monitoring_cadence`: `monthly` for an adverse/distressed population.

**stress_results (+200bp watch-list shock):** policy `watch_list_formula`
`stressed_dscr = dscr / (1 + 0.18)`, `breach_threshold = coverage_breach_threshold` (1.0),
`shock_label = "+200bp"`. Compute only for loans **with DSCR available**, ordered ascending
by `loan_id`: `{loan_id, base_dscr, stressed_dscr (2 dp), breaches_threshold}` where
`breaches_threshold = stressed_dscr < 1.0`. `breach_loan_ids` = the breaching ids ascending.

**workout_queue:** every adverse loan, ordered **descending by exposure, then ascending
loan_id**. `{loan_id, exposure, risk_class, payment_status, recommended_action,
projected_loss}`. `recommended_action` per §8; `projected_loss = (risk_class == "Projected
Loss")`.

**severe_bucket_counts:** group the adverse population by `(current_rating, payment_status)`;
`{current_rating, payment_status, loan_count, exposure}`. Order ascending by
`current_rating`, then by `payment_status` (alphabetical — note "90+ Days Past Due" sorts
before "Current").

## 7. SOP E — Competing CRE decision

Compare the named CRE applications and pick the stronger.

**weighted_cdfi_score** (policy `cre_weighted_score`): a weighted average of five "C"
sub-scores, each on a 1–5 scale where **lower is better**, assigned from objective factors
(capacity from DSCR, collateral_exposure from LTV / sector concentration, plus conditions,
character, capital). Weights: `capacity 0.45, collateral_exposure 0.36, conditions 0.11,
character 0.05, capital 0.03`. Report to **1 decimal**. `score_class` by band: `<=2.0
approve_quality, <=3.0 conditional, >3.0 weak`. Order `applications_compared` ascending by
`application_id`; `reason_codes` ascending alphabetically.

**stress (CRE dual stress):** policy `cre_dual_stress_formula`
`stressed_dscr = dscr * 0.85 / (1 + 0.18)`; report the `formula` string, threshold 1.0,
and per app `{application_id, base_dscr, stressed_dscr (2 dp), breaches_threshold =
stressed_dscr < 1.0}`. Order ascending by application_id.

**concentration:** CRE exposure = Σ`outstanding_balance` of `loan_type == "CRE"` loans.
`cre_policy_limit_pct` from the branch. `existing_cre_concentration = existing_cre_exposure /
total_loans_outstanding`. For the **selected** app, `selected_post_approval_cre_concentration
= (existing_cre_exposure + approved_amount) / (total_loans_outstanding + approved_amount)`
(denominator grows with the new loan). `selected_policy_variance_bps =
(post_conc - cre_policy_limit_pct) * 10000` (from unrounded values, 2 dp). FDIC piece uses
`fdic_benchmark_metric = total_real_estate_30_89_pct`: `branch_delinquency_ratio` =
`delinquency_30_plus_pct`; `fdic_variance_ratio = branch - benchmark` (4 dp);
`fdic_variance_bps = (branch - benchmark) * 10000` (2 dp).

**recommended_path:** select the lower (better) weighted score / non-breaching stress;
`path` = its decision. For the unselected credit choose `decline` or `defer` and give its
`unselected_reason_codes` (ascending). A breaching stress + sector breach + FDIC adverse
variance on a weak-class credit typically yields `defer`.

**conditions:** the set of CRE conditions attached to the selected path, sorted ascending
alphabetically (e.g. `bank_retained_exposure_cap`, `committee_cre_exception`,
`minimum_dscr_covenant_1_25`, `tenant_roll_and_lease_review`, `updated_appraisal_before_close`,
`quarterly_financial_reporting`, `no_additional_cre_without_committee_review`).

## 8. Final-rating / risk-class → recommended_action mapping

The watch-action ladder, consistent across tasks (action enum: `monitor`, `watchlist`,
`special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`):

- `final_rating == 8` **or** `payment_status == "Nonaccrual"` **or** `risk_class ==
  "Projected Loss"` → `partial_chargeoff_review`.
- `final_rating == 7`, **or** `90+ Days Past Due`, **or** `risk_class == "Watch"` →
  `special_assets`.
- `final_rating == 6` (or other adverse-but-performing) → `watchlist`.
- `final_rating <= 5` → `monitor` (and excluded from watch-list coverage in SOP A).

## 9. NPA / benchmark-variance arithmetic (shared)

For a branch noncurrent/NPA comparison (`npa_benchmark`):
- `branch_npa_exposure` = `nonperforming_loans` (metrics, target quarter).
- `branch_total_loans` = `total_loans_outstanding`.
- `branch_npa_ratio` = `branch_npa_exposure / branch_total_loans`, **displayed 4 dp**.
- `benchmark_metric` is `total_loans_noncurrent_pct` for an all-loans NPA review (or the
  real-estate / construction variant when the prompt scopes to that book);
  `fdic_benchmark_ratio` is that field from the FDIC benchmark, 4 dp.
- `variance_ratio` = `branch_npa_ratio - fdic_benchmark_ratio`, 4 dp.
- `variance_bps` = `(branch_ratio - fdic_ratio) * 10000`, 2 dp.

## 10. Rounding, precision, and ordering — read before you emit

These conventions are observed in the standard answers; getting them wrong fails the grade
even when the logic is right:

- **Currency/USD** fields → 2 decimals.
- **Ratio/concentration/percentage** fields → 4 decimals (they are ratios, e.g. `0.1897`,
  not `18.97`). `limit_pct` is the raw policy value (e.g. `0.19`).
- **bps** fields → 2 decimals.
- **DSCR** values (base/stressed) → 2 decimals. **weighted_cdfi_score** → 1 decimal.
- **Compute bps from the UNROUNDED ratio, not the rounded display value.** E.g. NPA ratio
  displays `0.1135` but `variance_bps` is `1037.49` (from the full-precision `0.11354…`),
  not `1037.00`. Round only at the final emission step; never chain rounded intermediates.
- **breach is strict `< 1.0`** at threshold 1.0 (a stressed DSCR of 0.97 breaches; 1.00 does
  not).
- **Obey every `ordering` clause in the template** exactly: ascending `loan_id` /
  `application_id` / `final_rating` / `action`, descending exposure then ascending loan_id
  for workout queues, alphabetical for reason-code and condition lists. String fields sort
  lexicographically (so `"90+ Days Past Due"` < `"Current"`).
- **Enums are closed sets.** Use only the allowed values from the template/policy; never
  invent a status, action, reason code, or class.

## 11. Common misjudgments to avoid

- **Don't skip the policy fetch.** Bands and formulas can change with the policy version;
  read `/api/policies` every run and apply the live values.
- **Re-derive ratings — don't trust `current_rating`.** The whole point of a regrade is that
  the booked rating is stale; the final rating is the worst factor band.
- **Worst factor wins; delinquency is a floor only.** `Current` contributes no delinquency
  rating; a clean payment status never improves a rating set by DSCR/LTV.
- **Handle nulls per factor** (skip the missing factor; never treat null DSCR as 0). If all
  factors are missing, fall back to the existing `current_rating`.
- **Booked amount vs capacity charge are different** (SBA and participation reduce
  `bank_capacity_used` but the **full** loan amount hits sector exposure and
  `gross_approved_amount`).
- **Use the right concentration base:** post-approval sector pct uses `total_loans +
  gross_approved`; CRE post-approval pct uses `total_loans + that one approved amount`.
- **Only the required population is in scope** — filter to `current_rating >= min` (or the
  stated population) before any grouping or totals; never include out-of-scope loans.
- **Emit only the JSON object**, exactly the template's keys, no extra fields, no prose.

When a detail is ambiguous, prefer the interpretation that is consistent across the policy
document and the field semantics in the template, and recompute against `/api/policies`
rather than guessing.
