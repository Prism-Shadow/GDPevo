---
name: credit-committee-packets
description: >-
  Produce committee-ready JSON answers for the shared "credit office" lending-committee task family
  (bank branches and credit-union segments served by the HTTP API at http://127.0.0.1:8003). Use this
  skill whenever a prompt asks you to prepare a JSON deliverable for a Credit Risk Committee / lending
  committee about a branch_id or segment_id and one of these jobs: re-derive/migrate loan risk ratings,
  build a watch-list stress packet (+200bp DSCR stress, CDFI risk classes, workout queue), allocate
  pending applications against quarterly lending capacity with concentration flags and decline reason
  codes, compare competing CRE applications with weighted scoring, or write a credit-union segment
  posture page from NCUA benchmarks. Trigger on terms like rating migration, NPA benchmark, material
  downgrade, watch-list, adverse-rated, CDFI risk class, DSCR stress, lending capacity allocation,
  concentration ceiling, sector breach, decline reason codes, CRE weighted score, segment posture,
  escalation triggers — even when the word "skill" is not used. Always conform to the supplied
  answer_template.json shape and the authoritative policy endpoint.
---

# Credit Committee Packets

You author one JSON object that exactly matches the task's `answer_template.json`, computed from a live
read-only HTTP API. The API is the **single source of truth**; the policy endpoint holds the authoritative
thresholds. Do not invent numbers, do not read local files, and emit **only** the JSON (no prose) unless the
prompt says otherwise.

This skill covers five recurring task types. They share one toolkit (the same API, the same policy, the same
risk-rating / stress / scoring math). Read this body, then open the matching section of
`references/task_playbooks.md` for the exact output shape and a worked, validated procedure.

## 0. Always do these first

1. **Read the answer template.** It is the contract. Match every required key, every enum value, every
   ordering rule, and every rounding precision exactly. The template's `precision`, `ordering`, and
   `allowed_values` annotations are not decoration — graders check them.
2. **Identify the target.** `branch_id` for branch tasks, `segment_id` for credit-union segment tasks.
   IDs are matched case-insensitively but **echo them back uppercased** exactly as the standard answers do
   (e.g. `"REDWOOD"`, `"CIVIC_NC_FIRE_EMS"`).
3. **Fetch the policy once** and keep it: `GET /api/policies`. Apply its thresholds verbatim; never hardcode
   numbers you remember from an example.
4. **Identify which of the five task types** you are in from the template's top-level keys (see the router
   below), then follow that playbook.

## API quick reference

Base URL: `http://127.0.0.1:8003`. All JSON; money/ratios are plain numbers.

| Endpoint | Use |
|---|---|
| `GET /api/policies` | Authoritative thresholds: risk_rating, stress, cdfi_factor_scores, cre_weighted_score, capacity_concentration. |
| `GET /api/branches/{id}` | Branch attributes: `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`, `institution_type`, `state_code`. |
| `GET /api/branches/{id}/metrics?quarter=YYYYQn` | Quarterly book. Use **2025Q1** as the review quarter unless told otherwise. Gives `total_loans_outstanding`, `delinquency_30_plus_pct`, `nonperforming_loans`. |
| `GET /api/branches/{id}/loans?min_current_rating=N&payment_status=&loan_type=` | Loan records. Fields below. `min_current_rating=N` returns loans with `current_rating >= N`. |
| `GET /api/branches/{id}/sector-exposures` | Per-sector `current_exposure`, `limit_pct`, `grandfathered`. |
| `GET /api/branches/{id}/applications?loan_type=` | Pending applications (the `*-APP-*` records). |
| `GET /api/benchmarks/fdic/q4-2024` | FDIC ratios (see metric names below). |
| `GET /api/benchmarks/ncua/q1-2025?state_code=XX` | NCUA per-state rows. Response is `{"rows":[...]}`. States include peers and a `US` national row. |
| `GET /api/credit-union-segments/{id}` | Segment profile: `peer_states`, `risk_tolerance`, `minimum_checklist`, `quarterly_capacity`, `internal_context`. |

**Key loan fields:** `loan_id`, `borrower_name`, `current_rating`, `payment_status`, `outstanding_balance`
(this is the *exposure*), `dscr`, `ltv`, `fico`, `debt_to_asset`, `liquidity_months`, `collateral_value`,
`loan_type`, `sector`, `days_past_due`. Any of `dscr`/`ltv`/`fico`/etc. may be `null` — treat null as
"factor not available" and skip it, never as zero.

**Task-type router (match on the template's top-level keys):**

- `portfolio_regrade`, `npa_benchmark`, `material_downgrades`, `top_problem_credit` → **Rating Migration Review**
- `watch_list_summary`, `stress_results`, `workout_queue`, `severe_bucket_counts` → **Watch-List Stress Packet**
- `allocation`, `decisions`, `concentration_flags`, `decline_reasons`, `post_approval_concentrations` → **Allocation Package**
- `applications_compared`, `recommended_path`, `stress`, `concentration`, `conditions` → **Competing CRE Decision**
- `posture`, `state_metrics`, `peer_comparison`, `controls`, `escalation_triggers`, `interpretation` → **Segment Posture Page**

## Core business rules (shared across tasks)

These are derived from `/api/policies` and verified against the standard answers. The exact band values
live in the policy JSON — read them at runtime; the rules below tell you *how* to apply them.

### Re-deriving a risk rating (`risk_rating` block)

The final re-derived rating is the **worst (numerically highest) rating** produced by the available factors —
this is the `dominant_factor_rule`. Compute a candidate rating from each factor that is present, then take the
max:

- **DSCR** → walk `dscr_thresholds` from best to worst: the first band whose `min` the DSCR meets gives the
  rating; if DSCR is below every `min` (the `max_below: 1.0` band), it is the worst rating (7).
- **LTV** → walk `ltv_thresholds`: the first band whose `max` the LTV is `<=` gives the rating; if LTV exceeds
  the top `max` (the `min_above: 1.0` band) it is the worst rating (7).
- **Delinquency** → `delinquency_minimums[payment_status]` is a *floor*: `Current`→null (no floor),
  `30 Days Past Due`→4, `60 Days Past Due`→5, `90+ Days Past Due`→7, `Nonaccrual`→8.

`final_rating = max(candidate ratings that are not null)`. **If no factor is available at all, keep the loan's
existing `current_rating`.** Exposure is always `outstanding_balance`.

**Material downgrade:** `downgrade_notches = final_rating - current_rating`. A downgrade is *material* when
`downgrade_notches >= risk_rating.material_downgrade_notches` (currently 2). Upgrades and 1-notch moves are
not material.

### Recommended / watch-list action by governing rating

Map the governing rating (the *final* re-derived rating in regrade tasks; the *current* rating in watch-list
tasks where the population is defined by current_rating) to an action enum:

- rating **<= 5** → `monitor` (and such loans are **excluded** from watch-list action coverage entirely)
- rating **6** → `watchlist`
- rating **7** → `special_assets`
- rating **8** → `partial_chargeoff_review`

`workout` and `legal_referral` exist in the enum but were not exercised by the train set; only use them if a
prompt explicitly directs a workout/legal path. The top/most-severe problem credit is the loan with the worst
final rating (tie-break by largest exposure); for a rating-8 Nonaccrual credit the action is
`partial_chargeoff_review`.

### Stress formulas (`stress` block)

- **Watch-list +200bp parallel shock:** `stressed_dscr = dscr / (1 + 0.18)` (i.e. `dscr / 1.18`).
  `shock_label = "+200bp"`.
- **CRE dual stress:** `stressed_dscr = dscr * 0.85 / (1 + 0.18)` (i.e. `dscr * 0.85 / 1.18`).
- **Breach:** `stressed_dscr < coverage_breach_threshold` (1.0). Round stressed/base DSCR to 2 decimals.
  Only include loans/applications where DSCR is present.

### CDFI factor scoring & risk class (`cdfi_factor_scores` block)

Sum the integer sub-scores for each factor that is **present** (skip nulls): `fico` band + `ltv` band +
`debt_to_asset` band + `liquidity_months` band. Then map the total to a class using `classes`:
Prime 0–5, Desirable 6–9, Satisfactory 10–13, Watch 14–18, Doubtful ≥19.
**Projected Loss override:** classify as `Projected Loss` when collateral is underwater (`ltv > 1.0`) on a
defaulted credit (Nonaccrual), *or* when score ≥19 and `ltv > 1.0`. The `projected_loss` boolean in a workout
queue is true exactly for the `Projected Loss` loans.

### Capacity, concentration & benchmark math

- **Exposure** of a loan = `outstanding_balance`. **Sector / CRE existing exposure** = sum of the relevant
  `outstanding_balance` (or the `current_exposure` rows from `/sector-exposures`).
- **Branch total loans** = `metrics.total_loans_outstanding` for the review quarter (2025Q1).
- **Concentration ratio** = exposure ÷ total book, rounded to **4 decimals**. **Post-approval** ratios add the
  newly approved amount to *both* numerator (the affected sector / CRE) and the denominator (total book).
- **CRE concentration** = sum of `loan_type == "CRE"` outstanding balances ÷ `total_loans_outstanding`.
- **Variance** between any branch ratio and a benchmark ratio: `variance_ratio = branch_ratio - benchmark_ratio`
  (4 decimals), `variance_bps = variance_ratio * 10000` (2 decimals). Same pattern for a post-approval ratio
  vs a policy limit (`policy_variance_bps`).
- **NPA / noncurrent** loans = `payment_status in ("90+ Days Past Due", "Nonaccrual")`.

### FDIC / NCUA benchmark metric selection

- FDIC noncurrent NPA work uses `total_loans_noncurrent_pct`. FDIC CRE delinquency work uses
  `total_real_estate_30_89_pct` (compared against the branch `delinquency_30_plus_pct`). The template's
  `benchmark_metric` / `fdic_benchmark_metric` enum tells you which one is expected — pick that one.
- NCUA state metrics are copied **verbatim as integers** from the matching `state_code` row. Compare the
  target state against the `US` row (`nc_vs_us`) and against the **median** of the segment's `peer_states`
  (`nc_vs_peer_median`); direction is `higher`/`lower`/`equal` of the target value vs the comparison value
  (note: for delinquency, "higher" means worse).

## Output conventions (apply to every task)

- **Rounding:** currency/exposure → 2 decimals; ratios/concentration/variance_ratio → 4 decimals;
  bps → 2 decimals; DSCR (base & stressed) → 2 decimals; CDFI weighted score → 1 decimal. Round only the final
  emitted value; carry full precision through intermediate steps.
- **Ordering:** obey each list's stated ordering exactly. Common ones: `ascending loan_id`,
  `ascending by final_rating`, `ascending by application_id`, reason codes / condition lists
  **ascending alphabetically**, sectors ascending, `workout_queue` is **descending exposure then ascending
  loan_id**, `severe_bucket_counts` ascending current_rating then payment_status.
- **Enums:** every action / decision / reason-code / class / direction value must come from the template's
  allowed set. Never emit a free-text value where an enum is required.
- **Numbers, not strings:** money and ratios are JSON numbers. Echo IDs as uppercase strings.
- **Whole-list selection:** when a task says "rated 3 or worse" or "rating 6 or worse", fetch with
  `min_current_rating=N`; "noncurrent" means the two noncurrent payment statuses; population filters are by
  **current_rating** unless the task explicitly says to filter on the re-derived rating.

## Procedure

1. Read the template; identify task type via the router.
2. `GET /api/policies`; fetch the branch/segment, metrics (2025Q1), loans/applications, sector-exposures, and
   the FDIC/NCUA benchmark the template names — only what that task needs.
3. Open the matching section of `references/task_playbooks.md` and follow the worked procedure. It lists the
   exact fields, the field-by-field computation, and the validated formulas for that task.
4. Compute with full precision; round and order at the end.
5. Emit only the JSON object. Re-check it against the template's required keys, enums, ordering, and precision
   before finishing.

## Common misjudgments to avoid

- **Null factors are not zero.** A null DSCR/LTV/FICO is *skipped*, not scored 0. A loan with no rateable
  factor keeps its existing `current_rating`.
- **Don't round mid-computation.** Round once, at emit time, or downstream ratios/variances drift.
- **Population vs governing rating.** "Adverse" / "rated N or worse" selects by `current_rating`; the *action*
  and *migration* use the rating appropriate to the task (final for regrade, current for watch-list). Don't
  mix them.
- **Exposure = outstanding_balance**, not collateral_value or requested_amount (for booked loans).
- **Post-approval denominators grow.** Adding an approval increases the total book in the denominator too;
  don't divide by the pre-approval total.
- **Pick the benchmark metric the template names**, not the first FDIC field you see. NPA uses the noncurrent
  metric; CRE delinquency uses the real-estate 30–89 metric.
- **Watch-list coverage excludes rating ≤5.** Only 6/7/8 credits get a watch action.
- **Echo the review_date / as-of date and branch/segment id exactly** as given (uppercased id).
- **Emit JSON only.** No markdown fences, no commentary, when the prompt asks for the JSON answer.
