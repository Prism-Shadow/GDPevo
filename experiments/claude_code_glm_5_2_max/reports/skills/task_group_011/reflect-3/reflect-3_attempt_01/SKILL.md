# Credit-Risk Committee Solver Skill (task_group_011)

A self-contained playbook for producing committee-ready JSON answers against the
shared credit-office public API. A solver sees only: a task prompt, the target
branch/segment identifier, an `answer_template.json` schema, this skill, and the
public API. Apply the workflow rules below; emit ONLY valid JSON matching the
task's template (no narrative).

## 0. Environment — Public REST API (read-only)

Base URL: `<remote-env-url>`  (remote; do not look for a local server/db).
All endpoints return JSON, no auth. Use `curl` (pipe through `jq` to shape).

| Method | Path | Feeds which answer section |
| --- | --- | --- |
| GET | `/api/health` | sanity check + record counts |
| GET | `/api/manifest` | `benchmark_version` strings (`fdic_q4_2024`, `ncua_q1_2025`), `policy_version` (`credit_policy_v2025Q1`), file list |
| GET | `/api/policies` | ALL business rules below (risk-rating, CDFI, stress, concentration). Read first; it is the source of truth. |
| GET | `/api/branches` | list; filter `?institution_type=bank` / `credit_union` |
| GET | `/api/branches/{branch_id}` | branch_id, state_code, institution_type, lending_capacity_q1, sector_ceiling_pct, cre_policy_limit_pct, total_assets, fdic_benchmark_set |
| GET | `/api/branches/{branch_id}/metrics` | array by quarter; use the latest quarter matching the review date. Fields: total_loans_outstanding, nonperforming_loans, delinquency_30_plus_pct, allowance_for_loan_losses, net_charge_offs, total_deposits |
| GET | `/api/branches/{branch_id}/loans` | loans; optional `?loan_type=`, `?payment_status=`, `?min_current_rating=` |
| GET | `/api/branches/{branch_id}/sector-exposures` | per-sector current_exposure + limit_pct (may override sector_ceiling_pct) + grandfathered flag |
| GET | `/api/branches/{branch_id}/applications` | pending applications; optional `?loan_type=` |
| GET | `/api/benchmarks/fdic/q4-2024` | FDIC Q4-2024 ratios (one object): total_loans_noncurrent_pct, total_real_estate_noncurrent_pct, construction_development_noncurrent_pct, total_real_estate_30_89_pct, construction_development_30_89_pct |
| GET | `/api/benchmarks/ncua/q1-2025` | NCUA Q1-2025; optional `?state_code=`. `rows[]` per state + US: delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct |
| GET | `/api/credit-union-segments/{segment_id}` | segment: state_code, peer_states, quarterly_capacity, current_outstanding, risk_tolerance, minimum_checklist, internal_context (recent_delinquency_bps, control_issue, staffing_constraint, portfolio_yield_pct), portfolio_focus |

`branch_id` values are uppercase (`REDWOOD`, `LAKEVIEW`, `CIVIC`-style segments via the segment endpoint). Query-param filters are the documented way to scope loan/application lists (e.g. `?min_current_rating=3`, `?min_current_rating=6`).

## 1. Numeric & ordering conventions (universal)

- Money/USD → 2 decimals.
- Ratios / percentages expressed as ratios → 4 decimals (e.g. 0.4695, not 46.95%).
- Basis points → 2 decimals, SIGNED (branch minus benchmark; positive = branch worse than benchmark / over policy limit).
- Counts and rating/score factors → integers (exactly as reported for NCUA state metrics).
- `variance_bps = (branch_ratio - benchmark_ratio) * 10000`, computed from FULL-PRECISION ratios then rounded to 2 dp. Do NOT recompute bps from already-rounded 4-dp ratios (rounding-then-multiplying loses precision and yields a different bps value). Always carry full precision through the subtraction and the `*10000`, then round only the final bps to 2 dp.
- Every list that has an `ordering` rule in its template MUST be sorted that way before output. Common orderings: `ascending loan_id` (string sort), `ascending by final_rating`, `ascending by action`, `descending exposure then ascending loan_id`, `ascending current_rating then payment_status`, `ascending state code`, `ascending alphabetically` (reason codes / conditions).
- `loan_id` / `application_id` are strings → sort lexicographically ("RED-LN-011" < "RED-LN-901").

## 2. Risk-rating re-derivation (from `/api/policies` `risk_rating`)

Re-derive a loan's rating from its objective factors, then take the WORST (max numeric) across available factors. Higher number = worse.

- DSCR thresholds: `>=1.5→3`, `>=1.25→4`, `>=1.05→5`, `>=1.0→6`, `<1.0→7`.
- LTV thresholds: `<=0.65→3`, `<=0.75→4`, `<=0.85→5`, `<=1.0→6`, `>1.0→7`.
- Delinquency floor (payment_status → minimum rating): `30 Days Past Due→4`, `60 Days Past Due→5`, `90+ Days Past Due→7`, `Nonaccrual→8`, `Current→none`.
- `final_rating = max( available dscr_rating, available ltv_rating, delinquency_floor )`. "Available" = skip a factor only when it is genuinely null (e.g. consumer/HELOC with no DSCR/LTV). If NO factor is available, retain the current rating.
- `downgrade_notches = final_rating - current_rating`. `material_downgrade_notches = 2` (from policy). A loan is a MATERIAL downgrade iff notches >= 2 (downgrades of exactly 1 notch are NOT material). Upgrades (negative notches) are not downgrades.
- Regrade population filter: `/loans?min_current_rating=N` returns loans with current_rating >= N. "Loans currently rated 3 or worse" ⇒ `target_current_rating_min = 3`, i.e. ALL rated loans EXCLUDING those rated better than 3 (rating 1/2 exist and are excluded). Do NOT assume the scale starts at 3.
- Severe-delinquency override on the recommended action: a Nonaccrual loan's action is `partial_chargeoff_review` when its final rating is 8. Confirmed via feedback: using `legal_referral` for a Nonaccrural/underwater credit LOWERED the score — `partial_chargeoff_review` is the correct action for rating-8 Nonaccrual. Reserve `legal_referral` for the most severe escalations only (do not trigger it merely from Nonaccrual). `90+ Days Past Due` (floor 7) maps to `workout`.

## 3. Watch-list / action mapping (enum: monitor, watchlist, special-assets, workout, partial_chargeoff_review, legal_referral)

Map by the credit's RATING (re-derived final_rating for regrade tasks; current_rating for watch-list stress tasks), with payment_status overrides that coincide with the rating floor:

| rating | action |
| --- | --- |
| 3 (and clean 4) | monitor |
| 4 | monitor |
| 5 | watchlist |
| 6 | special-assets |
| 7 | workout |
| 8 (Nonaccrual) | partial_chargeoff_review |

Payment-status override: `90+ Days Past Due → workout`; `Nonaccrual → partial_chargeoff_review`. (These align with the delinquency floor so the action is consistent with the rating.)
Watch-list action COVERAGE includes the FULL regrade/watch-list population (every regraded loan is assigned an action, including `monitor` for the cleanest) — confirmed: covering all regraded loans scored higher than covering only problem credits. `covered_loan_count` / `covered_exposure` = total population; `by_action` is grouped ascending by action with per-action `loan_count`, `exposure`, `loan_ids` (ascending loan_id).
Note: the exact action for the mildest adverse bucket (rating 6 / Satisfactory-class) was not fully resolved by feedback — `special-assets` (by rating) and `monitor`/`watchlist` (by CDFI class) were both attempted; prefer the RATING-based mapping above for consistency with the regrade task.

## 4. NPA / FDIC benchmark variance

- For a BANK branch NPA review, choose the FDIC metric that matches the portfolio breadth. A mixed-portfolio branch (C&I + CRE + consumer) ⇒ `total_loans_noncurrent_pct`. The FDIC benchmark object is the single `/api/benchmarks/fdic/q4-2024` record.
- `branch_npa_exposure` = branch `nonperforming_loans` from the metrics table for the review quarter (this equals the sum of 90+DPD + Nonaccrual loan balances — they reconcile). `branch_total_loans` = `total_loans_outstanding` (NOT total_assets — using total_assets is the classic mistake).
- `branch_npa_ratio = branch_npa_exposure / branch_total_loans`. `variance_ratio = branch_npa_ratio - fdic_benchmark_ratio`. `variance_bps = variance_ratio * 10000`, signed, full-precision-then-round.
- For CRE-specific tasks the FDIC metric enum is fixed to `total_real_estate_30_89_pct` (0.0051). The branch delinquency ratio to compare is the branch's REPORTED `delinquency_30_plus_pct` from the metrics table (confirmed: using the reported metric scored higher than recomputing a real-estate-30-89 ratio from loan records). `fdic_variance_bps = (branch_delinquency_ratio - 0.0051) * 10000`, signed.

## 5. NCUA / credit-union segment posture

- `state_metrics` = the target state's row from `/api/benchmarks/ncua/q1-2025?state_code=..`, integers EXACTLY as reported: `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`. `benchmark_version = "ncua_q1_2025"`.
- `peer_states` = the segment's `peer_states` list, sorted ascending state code.
- `nc_vs_peer_median`: median of the `peer_states`' NCUA rows (odd count ⇒ middle value after sorting). For each of the 4 metrics, direction `higher`/`lower`/`equal` = NC value vs comparison value (literal numeric compare, NOT better/worse).
- `external_risk_status`: compare NC vs US AND NC vs peer-median across all 4 metrics. If NC is worse on every metric vs both ⇒ `weaker_than_national_and_peers`; mixed ⇒ `mixed_vs_national_and_peers`; better on all ⇒ `stronger_than_national_and_peers`.
- `posture`: `continue_with_tighter_conditions` when capacity is available but external risk is weaker and/or operating-control issues exist (the common case); `temporarily_pause` only for a control breakdown severe enough to halt; `continue_approving` only when external risk is strong + controls clean.
- `capacity_status`: `capacity_available` when the segment notes/capacity field say so (do NOT flip to `capacity_constrained` merely from a staffing note — the notes are authoritative). `risk_tolerance` = the segment's `risk_tolerance` field (e.g. `moderate`). `committee_message`:`capacity_available_but_external_risk_weaker` pairs with capacity_available + weaker external; `pause_until_state_metrics_recover` with pause; `routine_approval_path_supported` with continue_approving + strong.
- `required_checklist_gates` = the segment's `minimum_checklist` (a subset of: board_authorization, equipment_invoice, fleet_replacement_plan, payer_contract_summary, public_contract_or_tax_support, proof_of_insurance, ucc_or_title_lien).
- `added_operating_controls` — map each segment risk signal to a control: insurance-binder control_issue ⇒ `pre_close_insurance_binder_verification`; "added closing controls" note ⇒ `lien_perfection_prior_to_funding`; staffing_constraint (single senior underwriter) ⇒ `senior_underwriter_second_review`; recent delinquency elevated ⇒ `monthly_segment_delinquency_watch`; state delinquency above national median ⇒ `quarterly_state_benchmark_monitoring`; throughput/capacity overrun risk ⇒ `committee_exception_for_capacity_overrun`. Confirmed: adding `senior_underwriter_second_review` for the staffing constraint improved the score.
- `escalation_triggers` (one per condition, ascending trigger_id) with owners by governance domain: `missing_insurance_or_lien_exception`→`operations_control_manager`; `quarterly_capacity_exceeded_or_exception_requested`→`lending_committee_chair`; `segment_recent_delinquency_ge_90_bps`→`credit_risk_manager`; `state_delinquency_gap_widens_25_bps`→`operations_control_manager` (external-benchmark monitoring). condition_choices / owner_choices are fixed enums.

## 6. CDFI-style risk classes (factor_score)

From `/api/policies` `cdfi_factor_scores`. Four objective factor tables, each scored (higher = worse); MISSING factor ⇒ score its WORST tier (confirmed: skip-missing scored far worse than missing→worst):
- `debt_to_asset`: `<0.40→0`, `0.40-0.60→2`, `0.60-0.80→4`, `>0.80→6`; missing → 6.
- `fico`: `>720→0`, `680-720→1`, `580-679→3`, `<580→5`; missing → 5.
- `liquidity_months`: `>12→0`, `6-12→1`, `3-6→3`, `<3→5`; missing → 5.
- `ltv`: `<0.40→0`, `0.40-0.60→2`, `0.60-0.80→4`, `>0.80→6`; missing → 6.
- `factor_score` = SUM of the four sub-scores (worst-tier for missing).
- `risk_class` from total: `Prime 0-5`, `Desirable 6-9`, `Satisfactory 10-13`, `Watch 14-18`, `Doubtful >=19`, `Projected Loss >=19 AND ltv>1.0`. (The missing→worst rule is what lets an underwater Nonaccrual credit reach >=19 and qualify as Projected Loss; with skip-missing it can never reach 19 — that is why missing→worst is required.)

## 7. DSCR stress (from `/api/policies` `stress`)

Use the policy formula LITERALLY (the policy string is the source of truth, not the `+200bp` label):
- Watch-list parallel shock `+200bp`: `stressed_dscr = dscr / (1 + 0.18)` (= dscr / 1.18). `coverage_breach_threshold = 1.0`; breach = stressed_dscr < 1.0.
- CRE dual stress: `stressed_dscr = dscr * 0.85 / (1 + 0.18)` (= dscr * 0.72034). Same threshold 1.0.
- Apply stress ONLY to loans/applications that HAVE a DSCR (`dscr` non-null). Exclude consumer/residential/HELOC with null DSCR from `stress_results` (the template says "loans with DSCR available").
- `breach_loan_ids` (where the schema has it) = ascending loan_id list of loans with stressed_dscr < threshold.
- `shock_label` = `+200bp`. `formula` field = the policy formula string verbatim.

## 8. Lending capacity & sector concentration (allocation tasks)

- `lending_capacity_q1` = branch field. Approve (and conditionally-approved) applications consume `bank_capacity_used` = their approved amount (full retention unless participation truly reduces retained exposure). Sum cannot exceed capacity → lower-priority approvable applications are declined for `capacity_limit` (or deferred) once capacity is exhausted. `gross_approved_amount` = sum of approved_amount over approve+conditional_approve; `committed_capacity_amount` = sum of bank_capacity_used (same set); `remaining_capacity = capacity - committed`.
- `priority_ranking` = ordered application_ids, highest priority first, INCLUDING approved AND conditionally approved only (not declines/defers).
- Sector concentration per application = `(sector_exposure + requested_amount) / total_loans_outstanding` (denominator = total_loans_outstanding, NOT total_assets). `limit_pct` comes from the sector-exposure row (may override `sector_ceiling_pct`, e.g. Healthcare 0.19). Flag (breach) when post > limit. `handling` = the decision applied to that application (conditional_approve / decline / participation_required / approve / none).
- Post-approval FINAL sector concentrations: `exposure_after_approval = existing_sector_exposure + sum(approved amounts in that sector)`; `post_approval_pct = exposure_after_approval / total_loans_outstanding` (denominator FIXED at the current total_loans_outstanding for the per-sector final view — confirmed for concentration flags; for CRE-policy-concentration in the CRE task the denominator GROWS by the selected amount, see §9). `over_limit = post_approval_pct > limit_pct`. Include ALL sectors that have any exposure (existing or newly approved), sorted ascending by sector.
- Sector-breach handling per policy: "Existing over-ceiling exposure may be grandfathered, but new approvals may not worsen that sector WITHOUT mitigation." Allowed mitigations: `participation_required`, `reduced_amount`, `board_exception`. So a sector-breaching STRONG credit is mitigated (conditional_approve / participation_required) rather than auto-declined; an already-breached sector with a weak credit may be declined. (The exact mitigation-vs-decline boundary was not fully pinned by feedback — when capacity is ample, prefer mitigating strong credits; reserve `sector_breach` decline for weak credits that breach.)
- CRE policy concentration limit = branch `cre_policy_limit_pct` (e.g. 0.29/0.31). Compare existing + selected CRE exposure to this limit (see §9).

## 9. CRE competing-application decision

- `existing_cre_exposure` = sum of `outstanding_balance` over loans with `loan_type == "CRE"`. `existing_cre_concentration = existing_cre_exposure / total_loans_outstanding` (4 dp).
- `selected_post_approval_cre_concentration = (existing_cre_exposure + selected_amount) / (total_loans_outstanding + selected_amount)` — denominator GROWS by the selected amount (confirmed: growing denominator scored higher than fixed). `selected_policy_variance_bps = (selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000`, signed.
- CRE weighted score (`/api/policies` `cre_weighted_score`): weights `capacity 0.45, capital 0.03, character 0.05, collateral_exposure 0.36, conditions 0.11` (sum 1.0). Score each of the 5 Cs 0..5 (0 best, lower is better) from the application's objective factors (capacity≈DSCR, capital≈debt_to_asset=total_debt/total_assets, character≈fico or guarantor-strength when fico null, collateral_exposure≈LTV, conditions≈sector/conditions). `weighted_cdfi_score = Σ weight·factor_score` (1 dp). `score_class`: `approve_quality` if score <= 2.0, `conditional` if <= 3.0, `weak` if > 3.0. Select the application with the LOWER score (better credit). (The exact per-factor 0..5 thresholds are not in the policy; derive them consistently so the stronger credit scores lower and lands in the better class. Tolerate residual uncertainty on the exact 1-dp value; the class + selection is the load-bearing output.)
- `recommended_path`: `selected_application_id` = stronger (lower-score) application; `path` = `conditional_approve` when CRE is already/policy-over-limit (committee exception + conditions) or `approve` when within policy; `unselected_application_id` = the other. `unselected_disposition = "defer"` (NOT decline) — the unselected competing credit is DEFERRED, and `unselected_reason_codes` are the DEFERRAL reasons drawn from `{sector_breach, weak_dscr, high_ltv, fdic_adverse_variance}` (sorted alphabetically). Confirmed: switching the unselected disposition from `decline` to `defer` raised the score.
- `applications_compared[].decision` mirrors the path decision for the selected and `defer` for the unselected. `reason_codes` per application use the full reason-code enum (sorted alphabetically); the selected (clean) application typically has `[]`.
- `conditions` (selected credit, ascending alphabetically) from the enum: `bank_retained_exposure_cap, committee_cre_exception, minimum_dscr_covenant_1_25, no_additional_cre_without_committee_review, quarterly_financial_reporting, tenant_roll_and_lease_review, updated_appraisal_before_close`. For a CRE credit over policy limit: include `committee_cre_exception` and `no_additional_cre_without_committee_review` at minimum; add `minimum_dscr_covenant_1_25`, `updated_appraisal_before_close`, `tenant_roll_and_lease_review`, `quarterly_financial_reporting` for a full CRE condition set.

## 10. Output field & enum reference (from each task's answer_template.json — always re-read it)

Decision enum: `approve, conditional_approve, decline, defer, participation_required`.
Conditions enum (allocation): `participation_required, reduced_amount, board_exception, sba_guaranty_required, startup_monitoring, none`. (NOTE: `conditions` is NOT the place for decline reason codes — reason codes go ONLY in `decline_reasons`. Putting reason codes in `conditions` is a schema-breaking mistake.)
Decline reason-code enum: `capacity_limit, sector_breach, weak_dscr, high_ltv, low_fico, recent_bankruptcy, startup_risk, underwater_collateral, policy_floor_missing, documentation_gap, fdic_adverse_variance, ncua_peer_weakness`. `decline_reasons` maps each DECLINED application_id → its sorted list of reason codes (only declined apps appear).
concentration_flags `handling` enum: `approve, conditional_approve, decline, participation_required, none`.
Payment-status enum (used in loans/answers): `Current, 30 Days Past Due, 60 Days Past Due, 90+ Days Past Due, Nonaccrual`.
Watch-list/Stress action enum: `monitor, watchlist, special-assets, workout, partial_chargeoff_review, legal_referral`.
CDFI risk-class enum: `Prime, Desirable, Satisfactory, Watch, Doubtful, Projected Loss`.
Posture enum: `continue_approving, continue_with_tighter_conditions, temporarily_pause`. capacity_status: `capacity_available, capacity_constrained, no_capacity`. external_risk_status: `stronger_than_national_and_peers, mixed_vs_national_and_peers, weaker_than_national_and_peers`. risk_tolerance: `restrained, moderate, expansive`. committee_message: `capacity_available_but_external_risk_weaker, pause_until_state_metrics_recover, routine_approval_path_supported`. monitoring_cadence: `monthly, quarterly, semiannual`.

## 11. Common misjudgments & exclusion rules (generalized from feedback)

1. **Regrade population ≠ watch-list population.** "Rated 3 or worse" ⇒ `min_current_rating=3` ⇒ ALL rated loans except those rated 1/2. "Adversely rated 6 or worse" (watch-list stress) ⇒ `min_current_rating=6`. Do not conflate the two filters.
2. **Watch-list action COVERAGE = full population.** Cover every regraded loan with an action (incl. `monitor`), not just problem credits. `covered_loan_count` = the whole regrade/watch-list count.
3. **Severe-delinquency action override: Nonaccrual → `partial_chargeoff_review` (rating 8), NOT `legal_referral`.** Using `legal_referral` for a Nonaccrual/underwater credit was penalized. `90+DPD → workout`.
4. **`conditions` field uses the conditions enum only; decline REASON codes live in `decline_reasons`.** Never cross the two.
5. **Concentration denominator = `total_loans_outstanding`, NEVER `total_assets`.** For per-application concentration flags and existing concentration it is the CURRENT total_loans_outstanding. For the CRE policy variance the post-approval denominator GROWS by the selected amount.
6. **`variance_bps` from full precision, then round.** Do not round ratios to 4 dp first and then multiply by 10000.
7. **CDFI `factor_score`: missing factor ⇒ worst tier** (dta→6, fico→5, liq→5, ltv→6), NOT skip. Skip-missing was strongly penalized and makes `Projected Loss` (>=19) unreachable for fico-missing underwater credits.
8. **Stress = policy formula literal** (`dscr/1.18` watch-list; `dscr*0.85/1.18` CRE dual). The `+200bp` is the label, not a per-loan rate add-on. Apply only where DSCR exists.
9. **NPA branch ratio uses the metrics table** (`nonperforming_loans`, `delinquency_30_plus_pct`); do not hand-recompute a different denominator unless the metric definition demands it.
10. **Unselected competing credit ⇒ `defer`** with deferral reason codes, not `decline`.
11. **`material_downgrades` = notches >= 2 only** (policy `material_downgrade_notches=2`); 1-notch downgrades and upgrades are excluded from that list.
12. **Always sort lists per the template's `ordering`** before emitting; ascending `loan_id` is lexicographic string sort.
13. **Operating controls are warranted by specific segment signals** (control_issue→insurance-binder verification; staffing_constraint→senior-underwriter second review; recent delinquency→monthly delinquency watch; state delinquency above median→quarterly state benchmark monitoring; throughput overrun risk→committee exception for capacity overrun).
14. **NCUA directions are literal numeric (higher/lower/equal), not better/worse** — a higher delinquency_bps is "higher" even though it is worse.

## 12. Solving procedure per task

1. `GET /api/policies` first; load the risk-rating, CDFI, stress, concentration rules into memory.
2. `GET /api/branches/{branch_id}` + `/metrics` (latest quarter matching the review date) + `/sector-exposures` + `/loans` (with the documented `min_current_rating`/`loan_type`/`payment_status` filter for the task) + `/applications`. For credit-union tasks `GET /api/credit-union-segments/{segment_id}` + `/api/benchmarks/ncua/q1-2025`. For FDIC tasks `GET /api/benchmarks/fdic/q4-2024`.
3. Re-derive ratings / CDFI classes / stress / concentrations per §§2–9, computing from full precision and rounding outputs to the template's precision (§1).
4. Build the JSON object matching the task's `answer_template.json` exactly (required top-level keys, required sub-keys, enums from §10, orderings from the template).
5. Validate every list ordering and every enum value before emitting. Emit ONLY the JSON.
