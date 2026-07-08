# Lending-Committee Credit-Risk Skill (task_group_011)

Executable experience for credit-risk / lending-committee committee packets built from the
shared **credit-office public REST API**. A solver sees only a task prompt + an
`answer_template.json` + this file + the live API. The tasks in this family always ask you to
pull branch / loan / application / policy / benchmark data, apply a small set of deterministic
credit rules, and emit a JSON object whose shape is fixed by the template.

This is a *method* document, not a per-task answer key. Read the section map, apply the rules,
and let the template's enums/ordering/precision drive the output.

---

## 0. Environment SOP (READ FIRST)

- **Base URL:** `<remote-env-url>` — all endpoints under `/api/`, JSON, no auth.
- **GET only.** The environment is read-only for you. Never POST/PUT. **Never call `/api/judge`**
  (no test-time judge is available; it is out of scope and not part of the public surface).
- Always `GET /api/health` once to confirm the service is up. Use `curl -s … | jq` to shape JSON.
- Quote any URL containing `?`/`&` in zsh (e.g. `curl -s "http://…/loans?min_current_rating=3"`),
  otherwise the shell tries to glob the `?` and the call returns nothing.
- `branch_id` values are uppercase (`REDWOOD`, `LAKEVIEW`, `SUMMIT`, `HARBOR`, … (uppercase; a task names its own target branch)).
  Segment ids look like `CIVIC_NC_FIRE_EMS`.

### Endpoint inventory and what each feeds

| Endpoint | What it returns | Feeds answer section |
| --- | --- | --- |
| `GET /api/manifest` | policy_version, benchmark versions, seed | `benchmark_version`, cross-checks |
| `GET /api/policies` | **the single source of all rules** (capacity/concentration, risk-rating tables, CDFI factor scores, CRE weighted-score weights, stress formulas) | every rule below |
| `GET /api/branches` | all branches; `?institution_type=bank\|credit_union` | branch discovery |
| `GET /api/branches/{branch_id}` | `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`, `total_assets`, `state_code`, `institution_type`, `fdic_benchmark_set` | capacity, concentration ceilings, CRE limit |
| `GET /api/branches/{branch_id}/metrics` | list by quarter; **latest quarter** row has `total_loans_outstanding`, `nonperforming_loans`, `delinquency_30_plus_pct`, `allowance_for_loan_losses`, `net_charge_offs`, `total_deposits` | NPA ratio, FDIC variance, concentration denominators |
| `GET /api/branches/{branch_id}/loans` | loans; filters `?loan_type=`, `?payment_status=`, `?min_current_rating=` | regrade population, watch-list, CRE exposure |
| `GET /api/branches/{branch_id}/sector-exposures` | per-sector `current_exposure`, `limit_pct`, `grandfathered` | sector concentration, flags |
| `GET /api/branches/{branch_id}/applications` | pending applications; `?loan_type=` | allocation decisions, CRE comparison |
| `GET /api/benchmarks/fdic/q4-2024` | FDIC ratios (`total_loans_noncurrent_pct`, `total_real_estate_noncurrent_pct`, `total_real_estate_30_89_pct`, `construction_development_*`) | FDIC benchmark variance |
| `GET /api/benchmarks/ncua/q1-2025` | rows per state + a `US` aggregate; `?state_code=` filters | credit-union segment state metrics, peer comparison |
| `GET /api/credit-union-segments/{segment_id}` | `state_code`, `peer_states`, `quarterly_capacity`, `current_outstanding`, `minimum_checklist`, `risk_tolerance`, `internal_context`, `notes` | segment posture page |

**Query-param semantics:** `?min_current_rating=N` returns loans with `current_rating >= N`
(ratings are worse-as-they-grow: 1 best … 8 worst). `?loan_type=CRE` and `?payment_status=`
are exact-match filters. `?state_code=NC` returns a single-row `rows` array.

### Metric-minding rules
- `metrics` is a **list** keyed by `quarter` (e.g. `2025Q1`, `2024Q4`). Always pick the
  **latest** (highest) quarter for the as-of date in the prompt.
- `sector-exposures` may carry a per-sector `limit_pct` override (e.g. Healthcare 0.19 where the
  branch default `sector_ceiling_pct` is 0.21). Use the per-row `limit_pct`, falling back to
  `branch.sector_ceiling_pct` for sectors not listed.
- `loans` carry nullable factors: `dscr`, `ltv`, `fico`, `debt_to_asset`, `liquidity_months`,
  `collateral_value` can all be `null`. Handle nulls explicitly (see §3).

---

## 1. Numeric & ordering conventions (apply everywhere)

- **Currency:** 2 decimals (USD), round half-up.
- **Ratios / percentages / concentrations:** 4 decimals.
- **Basis points (variance_bps, delinquency_bps):** 2 decimals … **except** NCUA
  `state_metrics` values which are reported as bare integers exactly as the benchmark table
  gives them (see §6).
- **`variance_bps` is computed from the UNROUNDED `variance_ratio`, then rounded to 2dp.** Do not
  compute bps from the already-4dp-rounded ratio (that loses precision — e.g. NPA 1037.49 vs the
  1037.0 you would get from the rounded 0.1037). Pattern:
  `variance_ratio = branch_ratio - benchmark_ratio` (unrounded);
  `variance_bps = variance_ratio * 10000` (round 2dp);
  then publish `variance_ratio` rounded 4dp.
- `signed` variance: branch ratio **minus** benchmark ratio. A branch worse than benchmark yields
  a **positive** variance_bps (more delinquency / more NPA = bad). Keep the sign.
- **List ordering** is always explicit in the template — read it. Common orderings: ascending
  `loan_id`; ascending `final_rating`; ascending `action`/`sector`/`payment_status` (lexicographic
  on the enum string); ascending `trigger_id`; ascending `current_rating` then `payment_status`;
  descending `exposure` then ascending `loan_id` (workout queue); ascending `application_id`;
  ascending alphabetic for reason-code lists.
- All `loan_ids` arrays are sorted ascending `loan_id` (string sort).

---

## 2. Risk-rating re-derivation (regrade) — `/api/policies` → `risk_rating`

The regrade target population is **loans with `current_rating >= target_current_rating_min`**
(default min = 3, i.e. "rated 3 or worse"). Pull them with
`GET /branches/{id}/loans?min_current_rating=3`.

### Factor → rating tables (from policy `risk_rating`)
Apply each *available* factor; **null factors are skipped** (they do not contribute a rating).

- **DSCR** (`dscr`): `>=1.5→3`, `>=1.25→4`, `>=1.05→5`, `>=1.0→6`, `<1.0→7`.
- **LTV** (`ltv`): `<=0.65→3`, `<=0.75→4`, `<=0.85→5`, `<=1.0→6`, `>1.0→7`.
- **Delinquency floor** (`payment_status` → minimum rating, the "severe-delinquency override"):
  `Current→null`, `30 Days Past Due→4`, `60 Days Past Due→5`, `90+ Days Past Due→7`,
  `Nonaccrual→8`.

### Dominant-factor (worst-notch) rule
> `final_rating = max(available factor ratings)` — the **worst (highest numeric)** rating
> produced by DSCR, LTV, and the delinquency floor wins.

- The delinquency floor acts as a hard floor: a `Nonaccrual` loan is **8** no matter how strong
  DSCR/LTV are; a `90+ Days Past Due` loan is **≥7**.
- If **all** factor-derived ratings are null/absent (e.g. an unsecured consumer loan with no DSCR,
  no LTV, and `Current`), **retain the `current_rating`** (no re-derivation possible). You can
  only worsen or hold — never improve — during a regrade.
- `material_downgrade_notches = 2` (policy). A loan whose `final_rating - current_rating >= 2`
  is a **material downgrade**.

### Regrade outputs (per template, e.g. train_001 shape)
- `target_current_rating_min`, `target_loan_count`, `target_exposure` = sum of
  `outstanding_balance` over the target population.
- `final_rating_exposure_totals`: group **all** target loans by `final_rating`; one row per
  final_rating present, ordered ascending `final_rating`, with `loan_count` and `exposure`.
- `migration_from_current_rating_3`: among target loans whose **`current_rating == 3`** (the
  threshold entry point), group those that actually **moved** (final_rating > 3) by `final_rating`,
  with `loan_ids`. Loans that stayed at 3 are shown in the totals but **omitted** from this
  migration list (it is a *migration* — only movers).
- `material_downgrades`: every target loan with `downgrade_notches >= 2`, fields
  `{loan_id, current_rating, final_rating, downgrade_notches, exposure}`, ordered ascending
  `loan_id`. (downgrade_notches = final - current.)
- `top_problem_credit`: the single loan with the **worst final_rating** (ties → largest
  exposure, then lowest loan_id). Include `borrower_name`, `payment_status`, and a
  `recommended_action` per §10.

### Watch-list action coverage (regrade follow-up)
Subset of regraded loans needing follow-up = those with `final_rating >= 6`. Group by
`recommended_action` (§10 mapping). `covered_loan_count`/`covered_exposure` = totals over that
subset; `by_action` ordered ascending by `action` enum string, `loan_ids` ascending.

> **Regrade vs watch-list exclusion:** the *regrade* population is `current_rating >= 3` and
> uses **final_rating** for action mapping; the *watch-list* packet (§9) uses
> `current_rating >= 6` (adverse) with **no regrade** (actions keyed off current_rating). Don't
> mix the two rating bases.

---

## 3. NPA / FDIC benchmark variance

NPA review (train_001-style) uses benchmark metric `total_loans_noncurrent_pct` (the template
also allows `total_real_estate_noncurrent_pct`, `construction_development_noncurrent_pct`).

```
benchmark_version      = "fdic_q4_2024"                       # from branch.fdic_benchmark_set / /api/manifest
benchmark_metric       = one of the template's allowed values (context: NPA → total_loans_noncurrent_pct)
branch_npa_exposure    = metrics[latest].nonperforming_loans
branch_total_loans     = metrics[latest].total_loans_outstanding
branch_npa_ratio       = branch_npa_exposure / branch_total_loans          # 4dp
fdic_benchmark_ratio   = FDIC[benchmark_metric]                            # 4dp
variance_ratio         = branch_npa_ratio - fdic_benchmark_ratio           # 4dp (unrounded for bps)
variance_bps           = variance_ratio * 10000                            # 2dp, from unrounded ratio
```

### Metric → branch-ratio source mapping (pick by benchmark_metric)
- `*_noncurrent_pct` metrics → branch ratio = `nonperforming_loans / total_loans_outstanding`.
- `*_30_89_pct` metrics → branch ratio = `metrics[latest].delinquency_30_plus_pct` (use the field
  directly, already a ratio).

A CRE-concentration packet (train_005-style) instead pairs
`fdic_benchmark_metric = total_real_estate_30_89_pct` with
`branch_delinquency_ratio = metrics[latest].delinquency_30_plus_pct`. Same variance math; the
branch ratio field name in that template is `branch_delinquency_ratio` / `fdic_variance_*`.

---

## 4. Lending capacity & allocation (train_002-style)

For a branch's pending-applications allocation packet:

```
lending_capacity_q1     = branch.lending_capacity_q1          (from /branches/{id})
gross_approved_amount   = sum of approved_amount over APPROVED + CONDITIONAL_APPROVE apps
committed_capacity_amount = sum of bank_capacity_used over those same apps
remaining_capacity      = lending_capacity_q1 - committed_capacity_amount
```

### Decision enum (`approve | conditional_approve | decline | defer | participation_required`)
Conditions enum: `participation_required | reduced_amount | board_exception |
sba_guaranty_required | startup_monitoring | none`.

**Per-application decision logic (apply in priority order):**
1. **Hard decline reasons first** (§8): if any reason code like `low_fico`, `recent_bankruptcy`,
   `underwater_collateral`, `policy_floor_missing`, `documentation_gap` fires → `decline`.
2. **Credit weakness decline**: `high_ltv` AND `weak_dscr` together, or `high_ltv` AND
   `startup_risk`, generally → `decline`. A single borderline weakness with strong offsets
   (e.g. high FICO) may still approve.
3. **Capacity**: after higher-priority apps are funded, if remaining capacity can't absorb the
   app and no other weakness exists → `decline` with reason `capacity_limit`.
4. **Sector/CRE concentration approach** (post_approval pct near or over the sector `limit_pct`)
   → do not decline outright; mitigate via **`conditional_approve`** with condition
   `participation_required` (sell the excess to participants) **or** `reduced_amount`
   (approve a smaller amount) **or** `board_exception` (committee override).
5. **SBA-guaranteed apps** (`sba_guaranty_pct` present) → `conditional_approve` with
   `sba_guaranty_required`; add `startup_monitoring` when `years_in_business` is short (< ~2y).
6. Otherwise → `approve` (condition `none`).

### approved_amount vs bank_capacity_used
- **plain `approve`**: `approved_amount = requested_amount`; `bank_capacity_used = approved_amount`.
- **`sba_guaranty_required`**: `approved_amount = requested_amount`;
  `bank_capacity_used = approved_amount * (1 - sba_guaranty_pct)` (the SBA-guaranteed share is
  not bank risk/capacity).
- **`participation_required`**: `approved_amount = requested_amount` (the full loan is
  originated); `bank_capacity_used = approved_amount − participated_portion` (the sold portion
  relieves bank capacity). The participated portion is the amount needed to bring the relevant
  sector/large-exposure back under its ceiling. When LTV>1 / underwater, the bank may also retain
  only a capped share.
- **`reduced_amount`**: `approved_amount = min(requested, capacity/headroom)`; `bank_capacity_used
  = approved_amount`.
- **`decline`/`defer`**: `approved_amount = 0.0`, `bank_capacity_used = 0.0`, `conditions =
  ["none"]`.

### priority_ranking
Ordered list of `application_id`, **highest priority first, approved + conditional_approve only**
(declines/defers excluded). Priority is committee priority — strategic relationship/quality first,
then core approves, then conditional — **not** simply by amount. Reverse it for tie-breaks if the
template asks ascending.

---

## 5. Concentration (sector ceilings & CRE limit)

### Sector concentration
- Per-sector `limit_pct` comes from `/sector-exposures`; default to `branch.sector_ceiling_pct`
  for sectors absent from that table.
- `grandfathered=1` sectors may sit over ceiling but **new approvals may not worsen** them without
  mitigation (policy `capacity_concentration.grandfathering_note`).
- Allowed mitigations: `participation_required`, `reduced_amount`, `board_exception`.

### Post-approval concentration denominator (IMPORTANT — do not use total_assets)
- **"existing" concentration** (e.g. CRE): `exposure / total_loans_outstanding`.
- **"post_approval" concentration** (sector view after funding approved apps):
  `exposure_after_approval = existing_sector_exposure + approved_amount(s) in that sector`;
  `post_approval_pct = exposure_after_approval / (total_loans_outstanding + gross_approved_amount)`.
  i.e. the post-approval loan book = current book **plus** the gross new approvals.
- For a single selected CRE app (train_005): `selected_post_approval_cre_concentration =
  (existing_cre_exposure + selected.requested_amount) / (total_loans_outstanding +
  selected.requested_amount)` — the **full requested** amount is added (participation is a
  decision/condition, not a concentration reducer; the bank still originates the full loan).

`over_limit` = `post_approval_pct > limit_pct` (strict `>`; a value exactly at the limit is not
over).

### `existing_cre_exposure` derivation
Sum of `outstanding_balance` over `GET /branches/{id}/loans?loan_type=CRE`. (This is the
loan_type=CRE aggregation, **not** the sector-exposures table — the two differ for grandfathered/
mixed sectors.)

### `concentration_flags` (per approved app touching a sector)
One row per approved/conditional app whose sector post-approval pct **approaches or exceeds** the
sector `limit_pct` (within a thin headroom, e.g. ~0.01, or over). Fields: `sector`,
`application_id`, `limit_pct`, `post_approval_pct` (4dp), `flag` (bool), `handling` (enum:
`approve | conditional_approve | decline | participation_required | none`). Sort by `sector` then
`application_id`.

### CRE policy variance (train_005)
```
cre_policy_limit_pct                       = branch.cre_policy_limit_pct
existing_cre_exposure                      = sum(CRE loan balances)
existing_cre_concentration                 = existing_cre_exposure / total_loans_outstanding   # 4dp
selected_post_approval_cre_concentration   = (existing + requested) / (total_loans + requested) # 4dp
selected_policy_variance_bps               = (selected_post - cre_policy_limit_pct) * 10000     # 2dp, unrounded
```

---

## 6. Credit-union segment posture (train_003-style)

Inputs: `GET /credit-union-segments/{segment_id}` + `GET /api/benchmarks/ncua/q1-2025` (+ optional
`?state_code=`).

### state_metrics
Take the segment's `state_code` row from the NCUA benchmark. Report **integer values exactly as
in the table** (no rounding, no /100): `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`,
`positive_net_income_pct`. `benchmark_version = "ncua_q1_2025"`. (Contrast: ratio fields elsewhere
are 4dp — these NCUA fields are integers.)

### peer_comparison
- `peer_states` = segment.`peer_states` (use verbatim, then sort ascending state code).
- `nc_vs_us` and `nc_vs_peer_median`: for each of the four metrics, direction is
  `"higher" | "lower" | "equal"` comparing the segment state's value to (a) the `US` aggregate row
  and (b) the **median** of the `peer_states` rows.
- Note: for `delinquency_bps` higher = worse; for `roaa_bps`/`positive_net_income_pct` higher =
  better; for `loan_to_share_pct` higher = more leveraged. The direction is a pure numeric
  comparison (higher/lower), the *interpretation* is separate. Compute medians with the usual
  middle-of-three for the 3 peer rows.

### posture (enum: `continue_approving | continue_with_tighter_conditions | temporarily_pause`)
Decision matrix driven by `segment.notes`, `risk_tolerance`, `internal_context`, and the
direction matrix:
- Capacity available **and** external risk no worse than national/peers → `continue_approving`.
- Capacity available **but** external risk weaker (NC higher delinquency, lower ROAA, lower
  positive-net-income vs both US and peer median) → **`continue_with_tighter_conditions`** (add
  operating controls, don't pause).
- Capacity exhausted **or** external risk severely adverse / control breakdown →
  `temporarily_pause`.

### controls
- `required_checklist_gates` = segment.`minimum_checklist` (verbatim set from the endpoint), drawn
  from enum: `board_authorization, equipment_invoice, fleet_replacement_plan,
  payer_contract_summary, public_contract_or_tax_support, proof_of_insurance, ucc_or_title_lien`.
- `added_operating_controls` derive from `internal_context`:
  - insurance/lien control issue → `pre_close_insurance_binder_verification`,
    `lien_perfection_prior_to_funding`;
  - staffing/senior-underwriter constraint → `senior_underwriter_second_review`;
  - recent delinquency watch → `monthly_segment_delinquency_watch`;
  - external state monitoring → `quarterly_state_benchmark_monitoring`;
  - capacity overrun possibility → `committee_exception_for_capacity_overrun`.
  Enum: `pre_close_insurance_binder_verification, lien_perfection_prior_to_funding,
  senior_underwriter_second_review, quarterly_state_benchmark_monitoring,
  monthly_segment_delinquency_watch, committee_exception_for_capacity_overrun`. Sort the set.

### escalation_triggers
List of `{trigger_id, condition, owner}`, ordered ascending `trigger_id` (ET001, ET002, …).
Select conditions relevant to the segment's risk profile from: `segment_recent_delinquency_ge_
90_bps, missing_insurance_or_lien_exception, quarterly_capacity_exceeded_or_exception_requested,
state_delinquency_gap_widens_25_bps`. Owner mapping:
- `segment_recent_delinquency_ge_90_bps` → `credit_risk_manager`
- `missing_insurance_or_lien_exception` → `operations_control_manager`
- `quarterly_capacity_exceeded_or_exception_requested` → `lending_committee_chair`

(Include a trigger as a standing escalation gate for the segment even if the current value is just
below its threshold — they are armed gates, not only currently-breached ones. Drop a trigger only
when the segment's profile makes it irrelevant — e.g. omit `state_delinquency_gap_widens_25_bps`
when the state gap is already the dominant, not a widening-delta, risk.)

### interpretation
- `capacity_status`: `capacity_available | capacity_constrained | no_capacity` — based on
  quarterly_capacity headroom vs current origination flow (capacity_available when the quarterly
  budget is not exhausted; do **not** compare `current_outstanding` stock against `quarterly_
  capacity` flow).
- `external_risk_status`: `stronger_than_national_and_peers | mixed_vs_national_and_peers |
  weaker_than_national_and_peers` — from the nc_vs_us / nc_vs_peer_median direction matrix.
- `risk_tolerance`: take `segment.risk_tolerance` (`restrained | moderate | expansive`).
- `committee_message`: pick from `capacity_available_but_external_risk_weaker |
  pause_until_state_metrics_recover | routine_approval_path_supported` to match the posture.

---

## 7. CDFI-style risk classes & factor scoring (watch-list, train_004-style)

From `policy.cdfi_factor_scores`: score each **available** factor (null → skip), sum the scores,
map the sum to a class. **Null factors are skipped, not zeroed.**

### Factor score tables
| Factor | `<0.40`/`>720`/`>12` | `0.40-0.60`/`680-720`/`6-12` | `0.60-0.80`/`580-679`/`3-6` | `>0.80`/`<580`/`<3` |
| --- | --- | --- | --- | --- |
| `ltv` | 0 | 2 | 4 | 6 |
| `debt_to_asset` | 0 | 2 | 4 | 6 |
| `fico` (`>720`→0, `680-720`→1, `580-679`→3, `<580`→5) | 0 | 1 | 3 | 5 |
| `liquidity_months` (`>12`→0, `6-12`→1, `3-6`→3, `<3`→5) | 0 | 1 | 3 | 5 |

(LTV/DTA bands are value ranges; FICO/liquidity are their own scales — use the table literally.)

### Class mapping (policy `cdfi_factor_scores.classes`)
| factor_score sum | risk_class |
| --- | --- |
| 0-5 | `Prime` |
| 6-9 | `Desirable` |
| 10-13 | `Satisfactory` |
| 14-18 | `Watch` |
| >=19 | `Doubtful` |
| **>=14 AND `ltv > 1.0`** | **`Projected Loss`** (underwater-collateral override) |

> The policy text states `Projected Loss = ">=19 and ltv>1.0"`, but the **applied** rule
> escalates any **Watch-or-worse** score (>=14) with `ltv > 1.0` (underwater collateral) to
> `Projected Loss`. Apply this override. (`ltv>1.0` is the "underwater collateral" trigger.)

`watch_list_summary.risk_classes`: list of `{loan_id, risk_class, factor_score}` for the adverse
population, ordered **ascending `loan_id`**. `monitoring_cadence` = `monthly` for an adverse
watch-list (rating >= 6); `quarterly`/`semiannual` only for healthier populations.

---

## 8. Decline reason codes (train_002/005) — derive from application/loan factors

Reason-code enum: `capacity_limit, sector_breach, weak_dscr, high_ltv, low_fico,
recent_bankruptcy, startup_risk, underwater_collateral, policy_floor_missing, documentation_gap,
fdic_adverse_variance, ncua_peer_weakness`.

Trigger thresholds (apply to application fields):
- `high_ltv` — `ltv > 0.80` (for business/CRE; consumer may tolerate slightly more with strong FICO).
- `weak_dscr` — `dscr < 1.25` (below the "pass" pass rating 4 threshold). `dscr is None` on a
  product that doesn't use DSCR (consumer/mortgage) is **not** weak_dscr.
- `low_fico` — `fico < 580`.
- `recent_bankruptcy` — `bankruptcy_months_ago` present and `< ~24` months.
- `startup_risk` (decline) vs `startup_monitoring` (condition): `years_in_business < ~2` is
  startup; pair with strong credit → `startup_monitoring` condition on a conditional approve; pair
  with another weakness → `startup_risk` decline reason.
- `underwater_collateral` — `ltv > 1.0` (collateral value below loan).
- `capacity_limit` — the **only** reason when an otherwise-acceptable app is declined because Q1
  capacity is consumed by higher-priority apps.
- `sector_breach` — approving would push the sector (or CRE aggregate) over its `limit_pct`.
- `fdic_adverse_variance` — branch's FDIC benchmark variance is adverse (positive bps, branch
  worse than benchmark) for the relevant metric; an ambient reason code on CRE/NPA-sensitive apps.
- `ncua_peer_weakness` — credit-union segment where the state is weaker than national/peers.
- `policy_floor_missing` / `documentation_gap` — missing `documentation_complete` or required
  checklist gate.

`decline_reasons` maps each **declined** `application_id` → sorted (ascending alphabetic) list of
reason codes. For "competing credit" tasks (train_005), `unselected_reason_codes` is restricted to
`sector_breach | weak_dscr | high_ltv | fdic_adverse_variance`. The `applications_compared[].reason_
codes` on a **defer** decision mirrors the same list. Always sort reason-code lists **ascending
alphabetically**.

---

## 9. Watch-list stress & workout (train_004-style)

Adverse population = `current_rating >= 6` (parameter `adverse_rating_min`, default 6). Pull via
`GET /branches/{id}/loans?min_current_rating=6`. No regrade here — use `current_rating` directly.

### +200bp DSCR stress (policy `stress`)
```
shock_label          = "+200bp"
formula              = stressed_dscr = dscr / (1 + 0.18)          # watch_list_formula
breach_threshold     = 1.0                                          # policy stress.coverage_breach_threshold
stressed_dscr        = dscr / 1.18                                   # 2dp
breaches_threshold   = stressed_dscr < 1.0                          # strict <
```
`stress_results.results` lists **only loans with `dscr` available** (`dscr is not None`), ordered
ascending `loan_id`. `breach_loan_ids` = those with `breaches_threshold true`, ascending `loan_id`.

### CRE dual stress (train_005-style) — when comparing CRE applications
```
formula              = "dscr * 0.85 / 1.18"     # policy cre_dual_stress_formula
                              (= dscr * 0.85 / (1 + 0.18))
coverage_breach_threshold = 1.0
stressed_dscr        = dscr * 0.85 / 1.18        # 2dp
breaches_threshold   = stressed_dscr < 1.0
```
`stress.results` ordered ascending `application_id`.

### workout_queue
All adverse loans, each `{loan_id, exposure, risk_class, payment_status, recommended_action,
projected_loss}`. Order **descending `exposure`, then ascending `loan_id`**.
- `exposure` = `outstanding_balance`.
- `risk_class` from §7.
- `recommended_action` from §10 (keyed off **`current_rating`** in watch-list packets).
- `projected_loss` = `true` iff `risk_class == "Projected Loss"`, else `false`.

### severe_bucket_counts
Group the adverse population by `(current_rating, payment_status)`; one row per non-empty bucket.
Fields `{current_rating, payment_status, loan_count, exposure}`. Order **ascending
`current_rating`, then `payment_status` (lexicographic on the enum string — `"90+ Days Past Due"`
sorts before `"Current"` because `'9'(0x39)` < `'C'(0x43)`)**.

---

## 10. recommended_action mapping (the action enum)

Enum: `monitor | watchlist | special-assets | workout | partial_chargeoff_review | legal_referral`.

The primary mapping is by the **governing rating** (which is `final_rating` after a regrade, or
`current_rating` for a pure watch-list packet) combined with payment status:

| governing rating | payment_status | recommended_action |
| --- | --- | --- |
| <= 5 | (any) | `monitor` |
| 6 | (any) | `watchlist` |
| 7 | (any) | `special-assets` |
| 8 | `Nonaccrual` | `partial_chargeoff_review` |
| 8 | `90+ Days Past Due` | `partial_chargeoff_review` (or `workout`) |

(`workout` and `legal_referral` apply to active-restructuring / fraud-litigation situations; in
the train data the 6/7/8 mapping above covers standard adverse credits. `legal_referral` is
reserved for fraud/litigation indicators; `workout` for loans already in active restructuring.)

`top_problem_credit.recommended_action` and each `by_action` bucket use this enum, sorted ascending
by action string in `by_action`.

---

## 11. Competing-CRE decision (train_005-style) synthesis

Given two competing CRE applications at one branch:

1. **Compute each app's weighted CDFI score** (policy `cre_weighted_score`):
   - Weights: `capacity 0.45, collateral_exposure 0.36, conditions 0.11, character 0.05,
     capital 0.03` (capacity + collateral dominate at 0.81 combined).
   - Score each of the 5 Cs 1-5 from application attributes (capacity~DSCR,
     collateral~LTV, capital~debt_to_asset = total_debt/total_assets, character~fico/
     co_guarantor_strength/years_in_business/prior_delinquencies, conditions~proposed_rate/
     sector/documentation/purpose). **Lower = better.**
   - `weighted_cdfi_score = Σ weight_c × score_c` (1 decimal).
   - `score_class`: `<=2.0 → approve_quality`, `<=3.0 → conditional`, `>3.0 → weak`.
2. **CRE dual stress** both apps (§9). Flag `weak_dscr` reason if `stressed_dscr < 1.0`.
3. **Reason codes** per app: `fdic_adverse_variance` (branch FDIC variance adverse — ambient on
   both), `sector_breach` if the app's sector/CRE would breach, `weak_dscr` if base or stressed
   DSCR weak, `high_ltv` if `ltv > 0.80`.
4. **Decision per app**: `approve | conditional_approve | decline | defer | participation_required`.
   - `approve_quality` score + no breach + stress passes → `approve`.
   - `conditional` score but CRE concentration breaches → `participation_required` (sell excess;
     keep the better credit).
   - `weak` score + stress breach → `defer` (collect more info / sponsor support), or `decline`
     if a hard reason (low_fico/recent_bankruptcy/underwater) fires.
5. **recommended_path**: `selected_application_id` = the stronger credit (lower weighted score,
   better stress, fewer reason codes). `path` = the selected app's decision enum.
   `unselected_application_id`, `unselected_disposition` ∈ `{decline, defer}` (defer when the
   credit is merely weak/not-yet-declinable; decline only on a hard reason). `unselected_reason_
   codes` (restricted enum §8) sorted ascending alphabetic.
6. **concentration** block per §5. `fdic_*` fields use `total_real_estate_30_89_pct` +
   `delinquency_30_plus_pct`.
7. **conditions** set from: `bank_retained_exposure_cap, committee_cre_exception,
   updated_appraisal_before_close, tenant_roll_and_lease_review, minimum_dscr_covenant_1_25,
   quarterly_financial_reporting, no_additional_cre_without_committee_review`. Choose the set
   matching the selected path (participation → `bank_retained_exposure_cap`; existing CRE already
   over policy limit → `committee_cre_exception` + `no_additional_cre_without_committee_review`;
   CRE deal → `updated_appraisal_before_close` + `tenant_roll_and_lease_review` +
   `minimum_dscr_covenant_1_25` + `quarterly_financial_reporting`). Sort ascending alphabetic.

---

## 12. Common misjudgments & exclusion rules (guardrails)

- **Regrade population vs watch-list population are different.** Regrade = `current_rating >= 3`
  using **final_rating** for actions. Watch-list = `current_rating >= 6` using **current_rating**
  for actions. Do not apply final_rating to a watch-list packet or current_rating to a regrade's
  action mapping.
- **Severe-delinquency override**: `Nonaccrual` → rating 8 and `90+ Days Past Due` → rating ≥7 are
  **floors**, not suggestions. A Nonaccrual loan never gets a final_rating below 8 even with
  DSCR 2.0 and LTV 0.4.
- **Null factors are skipped, never zeroed** (regrade dominant-factor, CDFI factor_score). A loan
  with `dscr=None, ltv=None, payment_status=Current` keeps its `current_rating`.
- **migration_from_current_rating_3 lists only movers** (final_rating > 3) among loans whose
  current_rating == 3. Loans that stayed at 3 appear in `final_rating_exposure_totals` but not in
  the migration list.
- **material_downgrades** uses `>= 2` notches (policy `material_downgrade_notches`), across the
  entire regrade target population (not just current_rating==3 loans).
- **Concentration denominator is the loan book, never `total_assets`.** Existing →
  `total_loans_outstanding`; post-approval → `total_loans_outstanding + gross_approved_amount`
  (or `+ selected.requested_amount` for a single selected CRE app).
- **`existing_cre_exposure`** = sum of `loan_type=CRE` loan balances, **not** the sector-exposures
  table (they diverge for grandfathered/mixed sectors).
- **`variance_bps` from the UNROUNDED ratio**, then round 2dp. Computing from the 4dp-rounded
  ratio is a precision bug.
- **Signed variance**: branch worse-than-benchmark → positive bps (the common case for these
  branches). Keep the sign; don't absolute-value.
- **`post_approval_pct` > `limit_pct`** is `over_limit` (strict `>`). Exactly-at-limit is not
  over.
- **NCUA `state_metrics` are bare integers**, not 4dp ratios. `delinquency_bps`, `loan_to_share_
  pct`, `roaa_bps`, `positive_net_income_pct` are reported as-is.
- **`bank_capacity_used` ≠ `approved_amount`** for SBA/participation: SBA → multiply by
  `(1 - sba_guaranty_pct)`; participation → minus the sold portion. But concentration uses the
  **full approved/requested** amount (the loan is originated in full).
- **`severe_bucket_counts` payment_status ordering is lexicographic on the enum string** —
  `90+ Days Past Due` comes before `Current` (digit before letter in ASCII), not by delinquency
  severity.
- **`priority_ranking` excludes declines and defers** — approved + conditional only.
- **`conditions: ["none"]`** for plain `approve` and for `decline`/`defer` (conditions attach to
  approval paths, not declines). Declines carry their reasons in `decline_reasons`, not in
  `conditions`.
- **GET only / never `/api/judge`** — the judge is not a public endpoint for you.
- Quote URLs with `?`/`&` in zsh.

---

## 13. Output field & enum quick-reference (consolidated)

- **payment_status**: `Current | 30 Days Past Due | 60 Days Past Due | 90+ Days Past Due |
  Nonaccrual`.
- **recommended_action**: `monitor | watchlist | special-assets | workout |
  partial_chargeoff_review | legal_referral`.
- **risk_class (CDFI)**: `Prime | Desirable | Satisfactory | Watch | Doubtful | Projected Loss`.
- **decision**: `approve | conditional_approve | decline | defer | participation_required`.
- **conditions**: `participation_required | reduced_amount | board_exception |
  sba_guaranty_required | startup_monitoring | none`.
- **handling** (concentration_flags): `approve | conditional_approve | decline |
  participation_required | none`.
- **decline reason codes**: `capacity_limit | sector_breach | weak_dscr | high_ltv | low_fico |
  recent_bankruptcy | startup_risk | underwater_collateral | policy_floor_missing |
  documentation_gap | fdic_adverse_variance | ncua_peer_weakness`.
- **CRE conditions**: `bank_retained_exposure_cap | committee_cre_exception |
  updated_appraisal_before_close | tenant_roll_and_lease_review | minimum_dscr_covenant_1_25 |
  quarterly_financial_reporting | no_additional_cre_without_committee_review`.
- **posture**: `continue_approving | continue_with_tighter_conditions | temporarily_pause`.
- **benchmark_version** strings: `fdic_q4_2024`, `ncua_q1_2025`.
- **FDIC benchmark_metric values**: `total_loans_noncurrent_pct | total_real_estate_noncurrent_pct
  | construction_development_noncurrent_pct | total_real_estate_30_89_pct` (use only those the
  template's enum allows).

---

## 14. Per-family execution checklist (transfer to unseen tasks)

1. Parse the prompt for: `branch_id` / `segment_id`, as-of date, target rating threshold,
   specific application_ids, and which section family (regrade / allocation / segment-posture /
   watch-list / competing-CRE).
2. `GET /api/policies` once and cache the rule tables (risk_rating, cdfi_factor_scores,
   cre_weighted_score, stress, capacity_concentration).
3. Pull the branch, latest-quarter metrics, loans (with the right `min_current_rating` /
   `loan_type` filter), applications, sector-exposures, and the relevant benchmark
   (fdic_q4_2024 / ncua_q1_2025) — or the segment — as the family requires.
4. Apply the rule sections above in order; compute every numeric field with the §1 precision
   rules (remember: bps from unrounded ratio).
5. Build the JSON object matching the template's required keys, ordering, enums, and precision
   exactly. Sort every list per its template ordering clause. Strip any key not in the template.
6. Re-check guardrails (§12): no total_assets denominator, no rounded-ratio bps, regrade-vs-
   watchlist rating basis, null-factor skip, severe-delinquency floor, `over_limit` strict `>`.
7. Emit **only** the JSON object (no narrative outside it) unless the prompt allows commentary.
