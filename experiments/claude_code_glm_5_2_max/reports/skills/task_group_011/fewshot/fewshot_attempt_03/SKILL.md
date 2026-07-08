# SKILL — Credit-Risk / Lending-Committee Decision Packets (task_group_011)

A transferable method for producing committee-ready JSON answers against the shared
credit-office public API. Distilled from five fully-worked train tasks
(Redwood rating migration, Lakeview allocation, Civic NC fire/EMS posture, Summit
watch-list stress, Harbor competing-CRE). Use this as the operating procedure whenever
a task asks for risk-rating re-derivation, NPA/FDIC/NCUA variance, capacity &
concentration analysis, CDFI risk classification, +200bp DSCR stress, decline-reason
coding, or watch-list/workout queuing.

The environment is REMOTE and read-only. Never read local `env/` source, DB files, or
scripts. Never call `/api/judge` (no judge endpoint is available to you).

---

## 1. Remote API usage SOP

**Base URL:** `<remote-env-url>`  (all endpoints return JSON, no auth)

**Call discipline:** `curl -s` GET only. Pipe through `jq` to inspect/shape. Write
large responses to `/tmp/<name>.json` then `jq` subsets, so you do not re-fetch.

**Endpoint map (the only surfaces you need):**

| GET path | Use it for |
| --- | --- |
| `/api/health` | sanity check + table counts |
| `/api/manifest` | confirm `benchmark_versions` (`fdic_q4_2024`, `ncua_q1_2025`) and `policy_version` (`credit_policy_v2025Q1`) |
| `/api/policies` | the authoritative rule tables (see §3) |
| `/api/branches` | list branches; filter `?institution_type=bank\|credit_union` |
| `/api/branches/{BRANCH}` | `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`, `total_assets`, `state_code`, `fdic_benchmark_set` |
| `/api/branches/{BRANCH}/metrics` | per-quarter: `total_loans_outstanding`, `nonperforming_loans`, `delinquency_30_plus_pct`, `total_deposits`, `allowance_for_loan_losses`, `net_charge_offs` |
| `/api/branches/{BRANCH}/loans` | full loan objects; filters `?loan_type=`, `?payment_status=`, `?min_current_rating=` |
| `/api/branches/{BRANCH}/sector-exposures` | per-sector `current_exposure` + `limit_pct` + `grandfathered` |
| `/api/branches/{BRANCH}/applications` | pending applications; filter `?loan_type=` |
| `/api/benchmarks/fdic/q4-2024` | five FDIC benchmark ratios |
| `/api/benchmarks/ncua/q1-2025` | per-state + `US` row: `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`; optional `?state_code=` |
| `/api/credit-union-segments/{SEGMENT}` | segment JSON for credit-union posture tasks |

`branch_id` values are uppercase (`REDWOOD`, `LAKEVIEW`, `SUMMIT`, `HARBOR`, …).
Segment ids look like `CIVIC_NC_FIRE_EMS`.

**Always fetch the latest quarter from `/metrics`** (sort by `quarter`, take last;
observed `2025Q1`). Do not assume the first array element is current.

**Key object field names (do not guess):**
- Loan exposure = `outstanding_balance` (NOT `balance`, which is null). Loans also
  carry `dscr`, `ltv`, `debt_to_asset`, `fico`, `liquidity_months`,
  `payment_status`, `days_past_due`, `current_rating`, `sector`, `loan_type`,
  `annual_debt_service`, `collateral_value`, `borrower_name`.
- Application requested size = `requested_amount`. Also: `sba_guaranty_pct`,
  `bankruptcy_months_ago`, `years_in_business`, `co_guarantor_strength`,
  `documentation_complete`, `prior_delinquencies_12m`, `dti`, `existing_relationship_years`.
- `total_loans_outstanding` lives on **metrics**, not on the branch object (the branch
  object has no such field). `/loans` sum and `/metrics` total can differ; **prefer
  `/metrics.total_loans_outstanding`** as the authoritative denominator.

---

## 2. Numeric conventions (apply everywhere)

| Quantity | Precision | Notes |
| --- | --- | --- |
| Money / exposure / balance | 2 decimals (USD) | round half-up |
| Ratios / concentrations / percentages | 4 decimals | e.g. `0.4695` |
| Basis points (`variance_bps`, etc.) | 2 decimals, **signed** | positive = branch worse than benchmark |
| DSCR / stress ratios | 2 decimals | |
| Counts, ratings, notches, scores | integer | |

**`variance_bps` rule (critical):** `variance_bps = (branch_ratio − benchmark_ratio) ×
10000`, signed, rounded to 2dp. Compute `branch_ratio` at **full precision from the
raw numerics** — do NOT recompute it from the 4dp-rounded display ratio. When the
branch ratio is itself a stored metric (e.g. `delinquency_30_plus_pct`), that stored
value is the full-precision input. The 4dp `*_ratio` fields in the output are
display-rounded independently.

Example (verified): nonperforming 1,725,000 / total_loans 15,191,701.54 =
0.11354884… ; minus FDIC 0.0098 = 0.10374884… ; ×10000 = **1037.49** (not 1037.00
from the rounded 0.1037).

**Ordering rules (apply to every list):**
- Any `loan_ids` array: ascending string sort.
- `material_downgrades`, `workout_queue` tie-break, etc.: ascending `loan_id`.
- `final_rating_exposure_totals`, `migration_from_current_rating_3`: ascending by
  `final_rating`.
- `watch_list_action_coverage.by_action`: ascending by `action` name.
- `workout_queue`: **descending** exposure, then ascending `loan_id`.
- `severe_bucket_counts`: ascending `current_rating`, then `payment_status`.
- `decisions`, `applications_compared`, `post_approval_concentrations`: ascending
  `application_id` / `sector`.
- `concentration_flags`: ascending `sector` then `application_id`.
- `escalation_triggers`: ascending `trigger_id`.
- Any alphabetized enum list (`reason_codes`, `conditions`, `unselected_reason_codes`):
  ascending alphabetical.

---

## 3. The policy tables (from `/api/policies`)

Read `/api/policies` once and hold these tables.

### 3.1 Risk-rating re-derivation (`risk_rating`)
- `dominant_factor_rule`: **final rating = the worst (maximum) numeric rating from the
  available DSCR, LTV, and delinquency factors.** Current rating is NOT a factor when
  any objective factor is available; it is only the fallback when every factor is
  missing (`dscr` null AND `ltv` null AND payment `Current`).
- DSCR → rating: `≥1.5→3`, `≥1.25→4`, `≥1.05→5`, `≥1.0→6`, `<1.0→7`.
- LTV → rating: `≤0.65→3`, `≤0.75→4`, `≤0.85→5`, `≤1.0→6`, `>1.0→7`.
- Delinquency minimums (the **severe-delinquency override** — a floor, not a cap):
  `30 DPD→4`, `60 DPD→5`, `90+ DPD→7`, `Nonaccrual→8`, `Current→null`.
- `material_downgrade_notches = 2`: a downgrade of ≥2 notches is "material" and goes in
  `material_downgrades`.

Re-derive each loan by taking `max(dscr_rating?, ltv_rating?, delinquency_floor?)`
where `?` = "only if present." This can produce **upgrades** (e.g. strong
DSCR+LTV can lift a loan from 4 to 3). A loan with all factors missing keeps its
`current_rating`. A `Nonaccrual` loan floors at 8 regardless of DSCR/LTV.

### 3.2 CDFI factor scores (`cdfi_factor_scores`) — 0 best, 6 worst
- **ltv**: `<0.40→0`, `0.40–0.60→2`, `0.60–0.80→4`, `>0.80→6`
- **debt_to_asset**: `<0.40→0`, `0.40–0.60→2`, `0.60–0.80→4`, `>0.80→6`
- **fico**: `>720→0`, `680–720→1`, `580–679→3`, `<580→5`
- **liquidity_months**: `>12→0`, `6–12→1`, `3–6→3`, `<3→5`
- **factor_score** = sum of available factor sub-scores (skip null factors).
- **Class by total score**: `0–5 Prime`, `6–9 Desirable`, `10–13 Satisfactory`,
  `14–18 Watch`, `≥19 Doubtful`, **`Projected Loss` = ≥19 AND ltv>1.0** — with the
  observed **severe-delinquency override**: an adversely-rated, Nonaccrual loan that is
  underwater (`ltv>1.0`) is classed `Projected Loss` even if its numeric score is below
  19 (the loss is projected from collateral shortfall + nonaccrual).

### 3.3 CRE weighted score (`cre_weighted_score`) — lower is better
- Weights: `capacity 0.45`, `collateral_exposure 0.36`, `conditions 0.11`,
  `character 0.05`, `capital 0.03` (sum 1.0).
- `weighted_cdfi_score = Σ weight_c × sub-score_c`, each sub-score on the 0–6 scale
  (0 best). Map the five Cs to application factors: `collateral_exposure`←ltv table,
  `capital`←debt_to_asset (total_debt/total_assets) table, `character`←fico table (or
  `co_guarantor_strength`: strong→0, standard→3, none→6 when fico is null),
  `conditions`←sector/loan-type risk (stable CRE→low, cyclical Hospitality→high),
  `capacity`←DSCR mapped to a 0/2/4/6 band (higher DSCR = lower score).
- `score_class`: `≤2.0 approve_quality`, `≤3.0 conditional`, `>3.0 weak`.

### 3.4 Stress (`stress`)
- `coverage_breach_threshold = 1.0` (DSCR below 1.0 = breach).
- **Watch-list stress (+200bp):** `stressed_dscr = dscr / (1 + 0.18)` i.e. `dscr/1.18`.
  `shock_label = "+200bp"`. Apply only to loans **with DSCR available**; omit null-DSCR
  loans from `stress_results.results`.
- **CRE dual stress:** `stressed_dscr = dscr × 0.85 / 1.18`. Reported `formula` string:
  `"dscr * 0.85 / 1.18"`.
- Use the policy formula verbatim — the "+200bp" label is a name, the actual divisor
  is `1.18` (`1 + 0.18`).

### 3.5 Capacity & concentration (`capacity_concentration`)
- `lending_capacity_field = branches.lending_capacity_q1`.
- `single_sector_default_field = branches.sector_ceiling_pct`; per-sector overrides
  come from `sector-exposures.limit_pct`.
- `allowed_mitigations = [participation_required, reduced_amount, board_exception]`.
- Grandfathering: existing over-ceiling exposure is grandfathered, but **new approvals
  may not worsen an over-ceiling sector without mitigation**.

---

## 4. Transferable business rules by domain

### 4.1 Risk-rating regrade (Redwood-style)
Population = all loans with `current_rating ≥ target_current_rating_min` (the prompt
specifies the min, e.g. "rated 3 or worse" → min 3). Re-derive every loan per §3.1.

Output pieces:
- `target_exposure` = sum of `outstanding_balance` over the population.
- `final_rating_exposure_totals`: group population by `final_rating` (ascending),
  with `loan_count` and `exposure`.
- `migration_from_current_rating_3`: the subset whose `current_rating == 3` (or
  whatever the "from" rating is), grouped by `final_rating`, with `loan_ids` ascending.
- `material_downgrades`: every loan whose `downgrade_notches = current − final ≥ 2`,
  with `loan_id, current_rating, final_rating, downgrade_notches, exposure`; ascending
  `loan_id`. (`downgrade_notches` is positive when rating worsened.)
- `top_problem_credit`: the single worst credit — highest `final_rating` (ties →
  largest exposure; a `Nonaccrual`/rating-8 loan with the largest exposure wins).
  `recommended_action` per the §4.7 action map.
- **`watch_list_action_coverage`**: covers loans with `final_rating ≥ 6` (NOT the
  regrade population — only those needing follow-up). group by `recommended_action`,
  with `loan_ids` ascending. `covered_loan_count`/`covered_exposure` are the sum.
  Loans with final ≤5 are *not* covered (they are routine `monitor`).

**Misjudgment guard:** regrade population (`current_rating ≥ min`) ≠ watch-list
coverage population (`final_rating ≥ 6`). A loan can be in the regrade but not
covered (e.g. upgraded to ≤5), and vice versa is impossible (covered ⇒ in regrade
when min≤6). Do not mix them.

### 4.2 NPA & FDIC/NCUA variance
**FDIC (bank branches):** choose the benchmark metric by the branch's character:
- mixed/general portfolio → `total_loans_noncurrent_pct` (0.0098)
- real-estate/CRE-weighted → `total_real_estate_30_89_pct` (0.0051) or
  `total_real_estate_noncurrent_pct` (0.0121)
- construction-heavy → `construction_development_noncurrent_pct` (0.0076)
Full FDIC ratios: `total_loans_noncurrent 0.0098`, `total_real_estate_noncurrent
0.0121`, `total_real_estate_30_89 0.0051`, `construction_development_noncurrent
0.0076`, `construction_development_30_89 0.0042`.

**Branch NPA ratio** (NPA-style task):
- `branch_npa_exposure = metrics.nonperforming_loans` (latest quarter) — equivalently
  sum of `outstanding_balance` where `payment_status ∈ {90+ Days Past Due, Nonaccrual}`.
- `branch_total_loans = metrics.total_loans_outstanding`.
- `branch_npa_ratio = branch_npa_exposure / branch_total_loans` (4dp).
- `variance_ratio = branch_npa_ratio − fdic_benchmark_ratio` (4dp).
- `variance_bps = (branch_npa_ratio_full − fdic_benchmark_ratio) × 10000`, signed, 2dp.

**Branch delinquency vs FDIC** (CRE-style task): `branch_delinquency_ratio =
metrics.delinquency_30_plus_pct` (already 4dp). `fdic_variance_ratio =
branch_delinquency_ratio − fdic_benchmark_ratio`; `fdic_variance_bps =
(branch_delinquency_ratio − fdic_benchmark_ratio) × 10000` (signed, 2dp).

**CRITICAL denominator rule:** concentration/NPA ratios use `total_loans_outstanding`
(from metrics), **never `total_assets`** (`total_assets` is ~30× larger and yields
nonsense ratios). NPA/delinquency variance is reported in bps and is **signed**
(positive = branch underperforming the benchmark).

**NCUA (credit-union segments):** pull the target-state row and the `US` row from
`/api/benchmarks/ncua/q1-2025`; pull peer states from the segment's `peer_states`.
For each of the four metrics (`delinquency_bps`, `loan_to_share_pct`, `roaa_bps`,
`positive_net_income_pct`), set direction `higher`/`lower`/`equal` for NC-vs-US and
NC-vs-peer-median (median = middle value of the sorted peer values). "Higher
delinquency" and "lower roaa / lower positive_net_income" mean NC is **weaker**.

### 4.3 Capacity & concentration ceilings (Lakeview/Harbor-style)
**Lending capacity:**
- `lending_capacity_q1` = branch field.
- For each approved/conditional app, `bank_capacity_used` (the capacity the bank
  actually consumes) depends on mitigation:
  - plain **approve** → `bank_capacity_used = approved_amount` (100% retained).
  - **SBA guaranty** → `bank_capacity_used = approved_amount × (1 − sba_guaranty_pct)`.
  - **participation_required** → bank retains `B` sized so the retained sector
    exposure lands exactly on the sector limit:
    `(existing_sector_exposure + B) / (total_loans_outstanding + Σ bank_capacity_used_of_all_approved_apps) = sector_limit_pct`.
    Solve for `B`; the remainder (`approved_amount − B`) is participated out.
- `gross_approved_amount = Σ approved_amount` over approve+conditional apps (full
  amounts, before SBA/participation).
- `committed_capacity_amount = Σ bank_capacity_used` over approve+conditional apps.
- `remaining_capacity = lending_capacity_q1 − committed_capacity_amount`.
- Apps are processed in **priority order**; capacity is consumed in that order.
  `priority_ranking` = approve+conditional apps ordered by credit strength (observed:
  DSCR descending, missing-DSCR apps last; committee/`9xx` applications typically rank
  high), highest first. Declined apps are excluded from `priority_ranking`.

**Sector concentration (post-approval view):**
- `exposure_after_approval` (sector) = `existing_sector_exposure + full_approved_amount`
  of the app(s) in that sector (full amount is booked to the sector even when
  participation/SBA reduces capacity — participation is a funding/capacity mitigation,
  not a sector removal).
- Denominator = `total_loans_outstanding + gross_approved_amount` (existing loans plus
  all full approved amounts).
- `post_approval_pct = exposure_after_approval / denominator` (4dp).
- `over_limit = post_approval_pct > limit_pct` (strict).
- `limit_pct` per sector from `sector-exposures` (override) or branch `sector_ceiling_pct`.

**concentration_flags:** flag an application whose post-approval sector concentration
reaches **at or very near** the sector limit (within ~10 bps, or over). `handling =
participation_required` (themitigation). Sectors comfortably below the limit are not
flagged. Order by `sector` then `application_id`.

**CRE-portfolio concentration (Harbor-style):**
- `cre_policy_limit_pct = branch.cre_policy_limit_pct`.
- `existing_cre_exposure = Σ outstanding_balance where loan_type == "CRE"`.
- `existing_cre_concentration = existing_cre_exposure / total_loans_outstanding` (4dp).
- `selected_post_approval_cre_concentration = (existing_cre_exposure + selected_amount)
  / (total_loans_outstanding + selected_amount)` (4dp; full selected amount).
- `selected_policy_variance_bps =
  (selected_post_approval_cre_concentration_full − cre_policy_limit_pct) × 10000`,
  signed, 2dp.

### 4.4 Decline reason codes & decision enums
Evaluate each application against credit gates; **decline reasons list every
unmitigated gate that fails** (sorted ascending alphabetically).

| Reason code | Trigger |
| --- | --- |
| `high_ltv` | commercial loan (CRE/C&I/SBA/Equipment) with `ltv > 0.80` (consumer/residential use higher thresholds) |
| `weak_dscr` | commercial `dscr < 1.25` without SBA-guaranty/strong mitigant |
| `low_fico` | `fico < 580` |
| `recent_bankruptcy` | `bankruptcy_months_ago < 24` (non-null) |
| `startup_risk` | `years_in_business < 2` without SBA guaranty mitigant |
| `underwater_collateral` | `ltv > 1.0` |
| `capacity_limit` | branch lending capacity exhausted after higher-priority apps, **or** the app's sector is already over its ceiling (no sector capacity) |
| `sector_breach` | post-approval sector concentration over limit |
| `documentation_gap` | `documentation_complete == 0` (→ defer) |
| `policy_floor_missing` | required checklist gate absent |
| `fdic_adverse_variance` | branch NPA/delinquency materially above FDIC benchmark (CRE-context reason) |
| `ncua_peer_weakness` | NCUA state metrics weaker than peers (credit-union context) |

**Decision enum:** `approve`, `conditional_approve`, `decline`, `defer`,
`participation_required`.
**Conditions enum:** `participation_required`, `reduced_amount`, `board_exception`,
`sba_guaranty_required`, `startup_monitoring`, `none`.
**Handling enum:** `approve`, `conditional_approve`, `decline`,
`participation_required`, `none`.

Decision flow: documentation gate → hard credit gates (decline if unmitigated failure)
→ sector-capacity gate (decline `capacity_limit`/`sector_breach` if sector over ceiling
unmitigated) → lending-capacity gate (decline `capacity_limit` if exhausted) → else
`conditional_approve` when a mitigant is required (SBA guaranty, participation,
startup monitoring, reduced amount) → else `approve`.
- Declined and plain-approved apps get `conditions: ["none"]`.
- `conditional_approve` lists the mitigants, e.g. `["sba_guaranty_required","startup_monitoring"]`.
- `priority_ranking` includes approve + conditional_approve only (not declines/defers).

### 4.5 CDFI risk class & +200bp watch-list stress (Summit-style)
Population = loans with `current_rating ≥ adverse_rating_min` (prompt-specified, e.g.
"6 or worse" → min 6).
- `adverse_balance = Σ outstanding_balance` over the population.
- For each loan, compute `factor_score` (§3.2) and `risk_class` (§3.2), applying the
  **Projected Loss override** for underwater (`ltv>1.0`) Nonaccrual loans. `risk_classes`
  list ascending `loan_id`.
- `monitoring_cadence`: `monthly` for an adverse watch-list (ratings ≥6); `quarterly`
  /`semiannual` only for milder populations.
- **DSCR stress** (§3.4): `stressed_dscr = dscr / 1.18`, threshold 1.0. Include only
  loans with DSCR available. `breach_loan_ids` = those with `stressed_dscr < 1.0`,
  ascending.
- `workout_queue`: all adverse loans, ordered **descending exposure, then ascending
  loan_id**. `recommended_action` per §4.7. `projected_loss = (risk_class ==
  "Projected Loss")`.
- `severe_bucket_counts`: group the adverse population by `(current_rating,
  payment_status)`, ascending rating then payment_status, with count + exposure.

### 4.6 Watch-list action coverage & workout queues
Distinct from §4.5's CDFI queue — this is the **risk-rating-driven** action map (used
in regrade tasks). For loans needing follow-up (`final_rating ≥ 6`), assign:

| `final_rating` / status | `recommended_action` |
| --- | --- |
| 6 (Watch) | `watchlist` |
| 7 (Substandard) | `special_assets` |
| 8 + Nonaccrual | `partial_chargeoff_review` |
| 8 + Current/other severe | `workout` or `legal_referral` (use judgment; nonaccrual+underwater → `partial_chargeoff_review`) |
| ≤5 | `monitor` (excluded from coverage; routine) |

Escalation by payment status: a `90+ Days Past Due` loan escalates one action level
(e.g. Desirable-class 90+DPD → `special_assets`); `Nonaccrual` + underwater →
`partial_chargeoff_review` with `projected_loss = true`. In the workout queue (§4.5),
`projected_loss` is true **only** for `Projected Loss` class.

### 4.7 Recommended-action enum (all tasks)
`monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`,
`legal_referral` — ascending severity. `payment_status` enum: `Current`, `30 Days Past
Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`.

---

## 5. Output field definitions & exact enums (per task archetype)

### 5.1 Rating-migration review (Redwood)
Top-level: `branch_id, review_date(YYYY-MM-DD), portfolio_regrade, npa_benchmark,
material_downgrades, top_problem_credit`.
- `portfolio_regrade`: `target_current_rating_min(int)`, `target_loan_count`,
  `target_exposure(2dp)`, `final_rating_exposure_totals[](asc final_rating)`,
  `migration_from_current_rating_3[](asc final_rating, loan_ids asc)`,
  `watch_list_action_coverage{covered_loan_count, covered_exposure, by_action[](asc action)}`.
- `npa_benchmark`: `benchmark_version, benchmark_metric(enum: total_loans_noncurrent_pct
  | total_real_estate_noncurrent_pct | construction_development_noncurrent_pct),
  branch_npa_exposure, branch_total_loans, branch_npa_ratio(4dp), fdic_benchmark_ratio(4dp),
  variance_ratio(4dp), variance_bps(2dp signed)`.
- `material_downgrades[]`(asc loan_id): `loan_id, current_rating, final_rating,
  downgrade_notches, exposure`.
- `top_problem_credit`: `loan_id, borrower_name, exposure, current_rating, final_rating,
  payment_status(enum), recommended_action(enum)`.
- `watch_list_action_coverage.by_action` action enum: `monitor | watchlist |
  special_assets | workout | partial_chargeoff_review | legal_referral`.

### 5.2 Allocation package (Lakeview)
Top-level: `branch_id, allocation, decisions, concentration_flags, decline_reasons,
post_approval_concentrations`.
- `allocation`: `lending_capacity_q1, gross_approved_amount, committed_capacity_amount,
  remaining_capacity, priority_ranking[](application_id, approve+conditional only)`.
- `decisions[]`(asc application_id): `application_id, decision(enum), approved_amount,
  bank_capacity_used, conditions[](enum)`.
- `concentration_flags[]`(asc sector, application_id): `sector, application_id,
  limit_pct, post_approval_pct, flag(bool), handling(enum)`.
- `decline_reasons{ app_id: [reason_codes sorted asc] }` — map only declined apps.
- `post_approval_concentrations[]`(asc sector): `sector, exposure_after_approval,
  post_approval_pct, limit_pct, over_limit(bool)`.
- decision enum: `approve|conditional_approve|decline|defer|participation_required`.
- conditions enum: `participation_required|reduced_amount|board_exception|
  sba_guaranty_required|startup_monitoring|none`.
- reason_code enum: `capacity_limit|sector_breach|weak_dscr|high_ltv|low_fico|
  recent_bankruptcy|startup_risk|underwater_collateral|policy_floor_missing|
  documentation_gap|fdic_adverse_variance|ncua_peer_weakness`.

### 5.3 Credit-union segment posture (Civic NC fire/EMS)
Top-level: `segment_id, posture, state_metrics, peer_comparison, controls,
escalation_triggers, interpretation`.
- `posture` enum: `continue_approving | continue_with_tighter_conditions |
  temporarily_pause`.
- `state_metrics`: `state_code, benchmark_version, delinquency_bps, loan_to_share_pct,
  roaa_bps, positive_net_income_pct` (integers exactly as NCUA reports).
- `peer_comparison`: `peer_states[](asc)`, `nc_vs_us{4 directions}`,
  `nc_vs_peer_median{4 directions}`; direction enum `higher|lower|equal` (higher
  delinquency / lower roaa / lower positive_net_income = NC weaker).
- `controls`: `required_checklist_gates`(set, from segment.minimum_checklist),
  `added_operating_controls`(set, chosen from enum based on segment.internal_context).
  required enum: `board_authorization|equipment_invoice|fleet_replacement_plan|
  payer_contract_summary|public_contract_or_tax_support|proof_of_insurance|
  ucc_or_title_lien`.
  added enum: `pre_close_insurance_binder_verification|lien_perfection_prior_to_funding|
  senior_underwriter_second_review|quarterly_state_benchmark_monitoring|
  monthly_segment_delinquency_watch|committee_exception_for_capacity_overrun`.
- `escalation_triggers[]`(asc trigger_id, e.g. ET001/ET002/ET003): `trigger_id,
  condition(enum), owner(enum)`.
  condition enum: `segment_recent_delinquency_ge_90_bps|
  missing_insurance_or_lien_exception|quarterly_capacity_exceeded_or_exception_requested|
  state_delinquency_gap_widens_25_bps`.
  owner enum: `credit_risk_manager|operations_control_manager|lending_committee_chair`.
  Owner mapping: delinquency trigger → `credit_risk_manager`; insurance/lien exception
  → `operations_control_manager`; capacity/exception → `lending_committee_chair`.
- `interpretation`: `capacity_status(capacity_available|capacity_constrained|
  no_capacity)`, `external_risk_status(stronger_than_national_and_peers|
  mixed_vs_national_and_peers|weaker_than_national_and_peers)`, `risk_tolerance(
  restrained|moderate|expansive)`, `committee_message(capacity_available_but_external_risk_weaker|
  pause_until_state_metrics_recover|routine_approval_path_supported)`.
- **Decision logic:** capacity available + external risk weaker (NC delinquency above US
  and peers, roaa/pni below) + risk_tolerance moderate →
  `continue_with_tighter_conditions`, message
  `capacity_available_but_external_risk_weaker`. Pick added controls that respond to
  the segment's specific `internal_context` (insurance-binder misses →
  `pre_close_insurance_binder_verification` + `lien_perfection_prior_to_funding`;
  staffing constraint → `senior_underwriter_second_review`; external state risk →
  `quarterly_state_benchmark_monitoring` + `monthly_segment_delinquency_watch`).

### 5.4 Watch-list stress packet (Summit)
Top-level: `branch_id, watch_list_summary, stress_results, workout_queue,
severe_bucket_counts`.
- `watch_list_summary`: `adverse_rating_min, adverse_loan_count, adverse_balance(2dp),
  risk_classes[](asc loan_id: loan_id, risk_class(enum), factor_score(int)),
  monitoring_cadence(monthly|quarterly|semiannual)`.
- `stress_results`: `shock_label("+200bp"), breach_threshold(1.0), results[](asc
  loan_id, DSCR-available only: loan_id, base_dscr, stressed_dscr, breaches_threshold),
  breach_loan_ids[](asc)`.
- `workout_queue[]`(desc exposure, then asc loan_id): `loan_id, exposure, risk_class,
  payment_status, recommended_action, projected_loss(bool)`.
- `severe_bucket_counts[]`(asc current_rating, then payment_status):
  `current_rating, payment_status, loan_count, exposure`.
- risk_class enum: `Prime|Desirable|Satisfactory|Watch|Doubtful|Projected Loss`.

### 5.5 Competing-CRE decision (Harbor)
Top-level: `branch_id, applications_compared, recommended_path, stress, concentration,
conditions`.
- `applications_compared[]`(asc application_id): `application_id, weighted_cdfi_score(1dp,
  lower better), score_class(approve_quality|conditional|weak), decision(enum),
  reason_codes[](asc, reason enum)`.
- `recommended_path`: `selected_application_id, path(enum), unselected_application_id,
  unselected_disposition(decline|defer), unselected_reason_codes[](asc, subset enum:
  sector_breach|weak_dscr|high_ltv|fdic_adverse_variance)`.
- `stress`: `formula("dscr * 0.85 / 1.18"), coverage_breach_threshold(1.0), results[](asc
  application_id: application_id, base_dscr, stressed_dscr, breaches_threshold)`.
- `concentration`: `cre_policy_limit_pct(4dp), existing_cre_exposure(2dp),
  existing_cre_concentration(4dp), selected_post_approval_cre_concentration(4dp),
  selected_policy_variance_bps(2dp signed), fdic_benchmark_metric(total_real_estate_30_89_pct),
  branch_delinquency_ratio(4dp), fdic_benchmark_ratio(4dp), fdic_variance_ratio(4dp),
  fdic_variance_bps(2dp signed)`.
- `conditions[]`(asc, enum): `bank_retained_exposure_cap|committee_cre_exception|
  updated_appraisal_before_close|tenant_roll_and_lease_review|minimum_dscr_covenant_1_25|
  quarterly_financial_reporting|no_additional_cre_without_committee_review`.
- **Decision logic:** compute `weighted_cdfi_score` per app; the **lower** score is
  stronger. Run the CRE dual stress on both; the selected credit is the stronger one
  that **also** passes the stress (`stressed_dscr ≥ 1.0`). Because the branch CRE
  concentration already exceeds the policy limit, the selected path is
  `participation_required` (mitigate via participation + covenants). The unselected
  credit gets `unselected_disposition = defer` (weak, revisitable) with its reason
  codes (e.g. `fdic_adverse_variance, sector_breach, weak_dscr` when it also breaches
  stress). Apply the full conditions list when the path is `participation_required`
  on an over-limit CRE branch.

---

## 6. Common misjudgments & exclusion rules (avoid these)

1. **Regrade population vs watch-list coverage.** Regrade population =
   `current_rating ≥ target_min`. Watch-list action coverage = `final_rating ≥ 6`
   (post-regrade). They are different sets. Do not put final-≤5 loans in
   `watch_list_action_coverage`; do not count final-≤5 loans as "covered."
2. **Severe-delinquency override.** Payment status sets a RATING FLOOR (90+→7,
   Nonaccrual→8) and a CLASS override (Nonaccrual + ltv>1.0 → `Projected Loss`). A
   good DSCR/LTV does NOT override a severe delinquency downward. Take the max, not
   the average.
3. **Ascending `loan_id` everywhere** it appears in a list. String sort (`RED-LN-008`
   before `RED-LN-013` before `RED-LN-901`). Workout queue is the exception: descending
   exposure first, ascending `loan_id` only as tie-break.
4. **Concentration denominator = `total_loans_outstanding`, NOT `total_assets`.**
   `total_assets` is ~30× larger and yields meaningless tiny ratios. Also: the
   post-approval denominator = `total_loans_outstanding + gross_approved_amount`
   (include new full approvals), and `existing_cre_exposure` uses `loan_type=="CRE"`
   (not a sector-name guess).
5. **`variance_bps` uses full-precision inputs.** Do not derive bps from the 4dp
   rounded ratio. Compute ratio from raw numerics, subtract benchmark, ×10000, then
   round to 2dp. `variance_bps` is **signed** (negative if branch beats benchmark).
6. **Participation does not remove sector exposure.** `exposure_after_approval`
   uses the FULL approved amount; only `bank_capacity_used` is reduced by
   SBA-guaranty/participation. Don't subtract the participated portion from sector
   exposure.
7. **`bank_capacity_used` for SBA** = `approved_amount × (1 − sba_guaranty_pct)`, not
   the full amount. For participation, solve the limit equation (§4.3), don't guess.
8. **Include only DSCR-available loans in `stress_results.results`**; null-DSCR loans
   are omitted (but still appear in `workout_queue`/`risk_classes`).
9. **`priority_ranking` excludes declines/defers** — approve + conditional_approve only.
10. **`projected_loss` boolean** is true only for `risk_class == "Projected Loss"`
    (underwater + nonaccrual), not for every 90+DPD/nonaccrual loan.
11. **`over_limit` is strict** (`post_approval_pct > limit_pct`); a sector exactly at
    the limit is `over_limit=false` but may still trigger a `concentration_flags`
    entry (near-limit).
12. **Don't call `/api/judge`** and don't read `env/`, test tasks, or evaluator
    internals. Stick to the public GET endpoints in §1.

---

## 7. Worked example fragments (method only — not copyable gold)

- **Risk regrade:** a loan `current_rating 3`, `dscr 0.87`, `ltv 0.82`, payment
  `Current` → DSCR `<1.0→7`, LTV `≤0.85→5`, delinquency floor null → final `max(7,5)=7`,
  downgrade 4 notches → material. A loan `current_rating 5`, `dscr 1.79`, `ltv 0.63`,
  `Current` → `max(3,3)=3` (upgrade, not material, not in watch-list coverage).
- **NPA variance:** nonperforming 1,725,000 / total_loans 15,191,701.54 = 0.11355;
  FDIC `total_loans_noncurrent_pct` 0.0098; `variance_bps = 1037.49` (signed positive).
- **SBA capacity:** requested 840,000, `sba_guaranty_pct 0.75` →
  `bank_capacity_used = 840,000 × 0.25 = 210,000`; full 840,000 still counts in
  `gross_approved_amount` and sector exposure.
- **Participation sizing:** existing healthcare 1,937,814.40, sector limit 0.19,
  approved 1,650,000, total_loans 14,334,094.87, other approved committed 2,294,253.45
  → solve `(1,937,814.40 + B)/(14,334,094.87 + 2,294,253.45 + B) = 0.19` →
  `B ≈ 1,508,113.31` retained, `≈ 141,886.69` participated.
- **+200bp stress:** base DSCR 1.59 → `1.59/1.18 = 1.35` (passes ≥1.0); base 1.01 →
  `0.86` (breaches).
- **CRE dual stress:** base 1.47 → `1.47×0.85/1.18 = 1.06` (passes); base 1.32 →
  `0.95` (breaches) → weaker credit deferred.
- **CRE concentration:** existing CRE 7,011,570.24 / total_loans 14,933,688.02 =
  0.4695 (already over the 0.29 policy limit → grandfathered but no worsening without
  mitigation → `participation_required`); selected post = (7,011,570.24 + 2,100,000) /
  (14,933,688.02 + 2,100,000) = 0.5349; `selected_policy_variance_bps = 2449.15`.
- **CDFI class:** ltv 1.18→6, debt_to_asset 0.88→6, liquidity 1.6→5, fico null →
  score 17 (Watch band) but Nonaccrual + ltv>1.0 → **Projected Loss** override,
  `projected_loss = true`, action `partial_chargeoff_review`.

---

## 8. Execution checklist (per task)

1. Parse the prompt: identify branch_id / segment_id, review date, the population
   threshold (e.g. "rated 3 or worse," "current_rating 6 or worse"), and which
   archetype (§5) applies. Load the matching `answer_template.json`.
2. `GET /api/policies` and hold the tables (§3).
3. Fetch the branch `/metrics` (latest quarter), `/loans` (with the right
   `?min_current_rating=`/`?loan_type=`/`?payment_status=` filter), `/sector-exposures`,
   `/applications` as the archetype needs.
4. Fetch the relevant benchmark (`/api/benchmarks/fdic/q4-2024` or
   `/api/benchmarks/ncua/q1-2025`); for NCUA, fetch the state row, the `US` row, and
   the segment's `peer_states` rows.
5. Re-derive / classify / stress per §3–§4, preserving exact enums and orderings.
6. Compute money 2dp, ratios 4dp, bps 2dp signed (full-precision inputs for bps).
7. Emit a single JSON object matching the template — no narrative outside JSON. Verify
   every list is sorted per §2 and every enum value is from the template's allowed set.
