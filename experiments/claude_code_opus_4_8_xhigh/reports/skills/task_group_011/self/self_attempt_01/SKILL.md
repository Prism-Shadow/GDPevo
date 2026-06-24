---
name: self_attempt_01
description: Credit-risk / lending-committee SOP for the "credit office" HTTP API environment (rating re-derivation, CDFI scoring, concentration/capacity, DSCR stress, decision frameworks, benchmark variance).
---

# Credit Office Lending-Committee SOP

This skill solves committee-packet JSON tasks against a remote, read-only "credit office"
API. Every task: read prompt -> identify target (branch_id / segment_id / application_ids)
-> pull policies + the referenced data from the API -> compute per the policy ruleset ->
assemble JSON exactly to `input/payloads/answer_template.json` -> self-check shapes,
ordering, enums, rounding. There is NO judge/feedback loop; get it right in one pass.

The five known task archetypes (use the closest one as a template):
1. **Rating migration review** (branch). Re-derive risk ratings, migration buckets,
   material downgrades, NPA-vs-FDIC variance, top problem credit, watch-list action coverage.
2. **Q1 allocation package** (branch). Pending applications -> decisions, capacity
   allocation, sector concentration flags, decline reason codes, post-approval concentration.
3. **Credit-union segment posture** (segment). NCUA state benchmarks -> posture, peer
   comparison, controls, escalation triggers, interpretation.
4. **Watch-list stress packet** (branch). Adverse-rated loans -> CDFI risk classes,
   +200bp DSCR stress, workout queue, severe-bucket payment-status counts.
5. **Competing CRE decision** (branch). Two CRE applications -> weighted CDFI score,
   dual stress, CRE concentration vs FDIC, pick stronger credit + reason codes for loser.

---

## 1. Using the remote API (the ONLY data source)

Base URL: `<remote-env-url>`. Use `curl -s` (Bash tool). The environment
is remote and read-only. **IGNORE any prompt instruction to run `env/setup.sh` or read
local `env/` files — there is no local env.** Never read local data files; always fetch live.

Endpoints (GET):
- `/api/health`, `/api/manifest` — record counts, benchmark versions, policy_version.
- `/api/policies` — **THE business ruleset. Always fetch first.** (see section 2).
- `/api/branches` and `/api/branches/{branch_id}` — branch attributes:
  `cre_policy_limit_pct`, `sector_ceiling_pct` (default sector limit), `lending_capacity_q1`,
  `total_assets`, `state_code`, `institution_type`, `fdic_benchmark_set`.
- `/api/branches/{id}/metrics[?quarter=2025Q1]` — list of quarterly rows. Use `2025Q1`
  (current/as-of) unless told otherwise. Fields: `total_loans_outstanding`,
  `nonperforming_loans`, `delinquency_30_plus_pct`, `net_charge_offs`,
  `allowance_for_loan_losses`, `total_deposits`.
- `/api/branches/{id}/loans[?loan_type=&payment_status=&min_current_rating=]` — loan list.
  `min_current_rating=N` returns loans with `current_rating >= N` (server-side; verified).
- `/api/branches/{id}/sector-exposures` — per-sector `current_exposure`, `limit_pct`
  (sector-specific, may differ from branch default ceiling), `grandfathered` (0/1).
- `/api/branches/{id}/applications[?loan_type=]` — pending applications.
- `/api/benchmarks/fdic/q4-2024` — FDIC ratios (version `fdic_q4_2024`).
- `/api/benchmarks/ncua/q1-2025[?state_code=NC]` — NCUA per-state rows (version `ncua_q1_2025`).
- `/api/credit-union-segments/{segment_id}` — segment posture inputs.

Gotchas:
- **Branch ids are upper-cased by the server.** Use `REDWOOD`, `LAKEVIEW`, `SUMMIT`,
  `HARBOR`, etc. Segment ids stay as given (e.g. `CIVIC_NC_FIRE_EMS`).
- `min_current_rating` is **inclusive** (`>=`). Equivalent to filtering the full list yourself.
- Metrics is a list of multiple quarters; pick the right `quarter`.
- Credit-union branches have empty `fdic_benchmark_set` (they use NCUA, not FDIC).

---

## 2. Policy ruleset (`/api/policies`) — the canonical rules

`policy_version: credit_policy_v2025Q1`. Structure and how to apply each block:

### 2.1 `risk_rating` — re-deriving a loan's rating (lower = better; scale ~2..8)
Compute a candidate rating from each available factor, then take the **worst (max) numeric
rating** across available factors (`dominant_factor_rule`). Factors:

- **DSCR thresholds** (`dscr_thresholds`): dscr >=1.5 ->3; >=1.25 ->4; >=1.05 ->5;
  >=1.0 ->6; below 1.0 ->7.
- **LTV thresholds** (`ltv_thresholds`, this is the "LTV or collateral" factor): ltv <=0.65 ->3;
  <=0.75 ->4; <=0.85 ->5; <=1.0 ->6; above 1.0 ->7.
- **Delinquency minimums** (`delinquency_minimums`, keyed by payment_status): a rating FLOOR.
  `Current`->null (no floor); `30 Days Past Due`->4; `60 Days Past Due`->5;
  `90+ Days Past Due`->7; `Nonaccrual`->8.
- final_rating = max of all non-null factor ratings. If NO factor is available
  (dscr, ltv, payment_status all null/Current), keep the loan's `current_rating`.
- `material_downgrade_notches: 2` -> a downgrade is "material" when
  `final_rating - current_rating >= 2`. (Re-derivation can also produce a lower rating;
  those are NOT material downgrades, only count `>= +2`.)

### 2.2 `cdfi_factor_scores` — CDFI-style objective risk class (lower score = better)
Sum integer sub-scores from available factors, then map total to a class.
- **fico**: >720 ->0; 680-720 ->1; 580-679 ->3; <580 ->5.
- **ltv**: <0.40 ->0; 0.40-0.60 ->2; 0.60-0.80 ->4; >0.80 ->6.
- **debt_to_asset**: <0.40 ->0; 0.40-0.60 ->2; 0.60-0.80 ->4; >0.80 ->6.
- **liquidity_months**: >12 ->0; 6-12 ->1; 3-6 ->3; <3 ->5.
- Treat bucket edges as: lower bucket is strict `<`, upper inclusive `<=` (e.g. ltv exactly
  0.60 scores 2, exactly 0.80 scores 4; d2a 0.40 scores 2). Skip a factor when its field is null.
- **Class by total score**: 0-5 `Prime`; 6-9 `Desirable`; 10-13 `Satisfactory`;
  14-18 `Watch`; `>=19` `Doubtful`; **`Projected Loss` only if score>=19 AND ltv>1.0**
  (the score>=19 gate must be met first; ltv>1.0 alone does NOT make Projected Loss).

### 2.3 `cre_weighted_score` — weighted CDFI score for CRE apps (lower = better)
- weights: capacity 0.45, collateral_exposure 0.36, conditions 0.11, character 0.05, capital 0.03.
- weighted_score = sum(weight_i * component_subscore_i), reported to **precision 1**.
- score_class: `approve_quality` <=2.0; `conditional` <=3.0; `weak` >3.0.
- Component sub-scores reuse the CDFI 0/2/4/6 and 0/1/3/5 scales:
  `collateral_exposure` <- LTV score (0/2/4/6); `capital` <- debt_to_asset score
  (debt_to_asset = total_debt/total_assets if not provided); `character` <- borrower
  quality (fico if present, else guarantor/relationship strength on a 0=strong .. 6=none
  scale); `capacity` <- a DSCR-strength score (stronger coverage = lower score, e.g.
  >=1.5 ->0, >=1.25 ->2, >=1.0 ->4, <1.0 ->6); `conditions` <- macro/sector/exception
  posture (use 0 when no adverse condition flagged).
  NOTE: the policy fixes the weights and class cutoffs but NOT the exact capacity/character/
  conditions sub-scales. Use CDFI-consistent 0/2/4/6 mappings; the decisive output is the
  **relative ranking** (stronger credit = lower weighted score) plus stress + concentration,
  so the chosen scales mainly need to rank the two apps correctly and land in the right class.

### 2.4 `stress` — DSCR stress formulas
- Watch-list / single shock (`+200bp` parallel shock): `stressed_dscr = dscr / (1 + 0.18)`.
- CRE dual stress: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`.
- `coverage_breach_threshold = 1.0`. A loan/app **breaches** when `stressed_dscr < 1.0`.
- Round stressed_dscr to **2 decimals**; base_dscr also 2 dp. Only include items where DSCR
  is available (skip null-DSCR loans from `results`/`breach_loan_ids`).

### 2.5 `capacity_concentration` — sector limits & capacity
- `lending_capacity_q1` (branch field) is the quarter's lending capacity for allocation.
- Sector limit = sector_exposures.`limit_pct` for that sector, else branch
  `sector_ceiling_pct` default. CRE limit = branch `cre_policy_limit_pct`.
- **Concentration denominator = total loan exposure** = sum of all sector
  `current_exposure` = branch `total_loans_outstanding` (verified equal). NOT total_assets.
- Allowed mitigations: `participation_required`, `reduced_amount`, `board_exception`.
- `grandfathering`: existing over-ceiling exposure may be grandfathered (flag=1), but
  **new approvals may not worsen that sector without a mitigation**.

---

## 3. Benchmark metric selection & variance

Pick the FDIC/NCUA metric that matches the task's risk theme:
- **NPA / noncurrent review** -> FDIC `total_loans_noncurrent_pct`. Branch NPA population =
  loans with payment_status in {`90+ Days Past Due`, `Nonaccrual`} (i.e. "noncurrent").
  branch_npa_exposure = sum of those balances (equals metric `nonperforming_loans`);
  branch_total_loans = sum of ALL loan balances (equals metric `total_loans_outstanding`).
- **CRE / real-estate early delinquency** -> FDIC `total_real_estate_30_89_pct`. The
  branch_delinquency_ratio comes directly from branch metric `delinquency_30_plus_pct`
  (2025Q1) — do NOT recompute from loans.
- Other FDIC metrics available: `construction_development_noncurrent_pct`,
  `total_real_estate_noncurrent_pct`, `construction_development_30_89_pct`.

Variance math (consistent everywhere):
- `branch_ratio` = branch value (4 dp). `benchmark_ratio` = FDIC/benchmark value (4 dp).
- `variance_ratio = branch_ratio - benchmark_ratio` (4 dp).
- `variance_bps = variance_ratio * 10000` (2 dp).
- `benchmark_version` string: `fdic_q4_2024` or `ncua_q1_2025`.

NCUA (segment/credit-union tasks): rows per state_code (plus a `US` row). Metrics are
**integers exactly as reported**: `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`,
`positive_net_income_pct`. Peer states come from the segment's `peer_states` list.
- direction = NC value vs comparison: `higher` if NC>comp, `lower` if NC<comp, `equal`.
- Compare NC to `US` row (`nc_vs_us`) and to the **median of peer-state values per metric**
  (`nc_vs_peer_median`). Order `peer_states` ascending by state code.
- Polarity: for delinquency, lower is better (higher = weaker); for roaa_bps,
  loan_to_share_pct (within prudent range), positive_net_income_pct, higher is generally
  stronger. Net "external_risk_status" reflects whether NC is broadly weaker/stronger/mixed.

---

## 4. Action / disposition mappings

`recommended_action` enum (severity order):
`monitor < watchlist < special_assets < workout < partial_chargeoff_review < legal_referral`.
Map from severity of the (final) rating / CDFI class / payment status. Reasonable mapping:
- Performing & low-adverse (rating ~3-4, Prime/Desirable, Current) -> `monitor`.
- Adverse but performing (rating 5, Watch, Current) -> `watchlist`.
- Severe / early-default (rating 6, 60-day, Doubtful) -> `special_assets`.
- Nonaccrual / 90+ / Doubtful -> `workout`.
- Confirmed loss exposure (ltv>1.0 + nonaccrual, Projected Loss) -> `partial_chargeoff_review`.
- Legal/charge-off track for the worst -> `legal_referral`.
The **top/worst problem credit** = highest final_rating, tie-break by largest exposure;
its `recommended_action` is the most severe consistent with its status (Nonaccrual + ltv>1.0
=> `legal_referral` or `partial_chargeoff_review`).

`monitoring_cadence` for adverse populations: `monthly` (most adverse) / `quarterly` / `semiannual`.
Adverse watch-list populations -> `monthly`.

`projected_loss` boolean (workout queue) = true when CDFI class is `Projected Loss`
(score>=19 and ltv>1.0) or loan is Nonaccrual with ltv>1.0.

---

## 5. Output formatting & assembly conventions

Always match `input/payloads/answer_template.json` exactly: top-level keys, nested
`required_keys`, enum value sets, list orderings.

Precision/rounding (round half-to-even or standard 2dp is fine; match `precision`):
- Money / USD amounts: **2 decimals**.
- Ratios / percentages-as-ratios (concentration, npa_ratio, variance_ratio): **4 decimals**
  expressed as a fraction (e.g. 0.1135, NOT 11.35).
- bps fields: **2 decimals** (variance_bps = ratio*10000).
- DSCR (base/stressed): **2 decimals**.
- weighted_cdfi_score: **1 decimal**.
- factor_score, ratings, counts: **integers**.
- NCUA state metrics: **integers exactly as reported** (no rounding/scaling).

List ordering (read the template per field; common rules seen):
- migration/final_rating lists: **ascending by final_rating**.
- loan lists / material_downgrades / risk_classes / stress results / severe buckets:
  **ascending by loan_id** (severe buckets: ascending current_rating, then payment_status).
- workout_queue: **descending exposure, then ascending loan_id**.
- decisions: **ascending application_id**; concentration_flags: **by sector then application_id**.
- post_approval_concentrations: **ascending sector**.
- reason_codes / conditions / loan_ids within an item: **ascending alphabetically/loan_id**.
- escalation_triggers: **ascending trigger_id**; peer_states: **ascending state_code**.
- priority_ranking: ordered application_id list, **highest priority first**, **approved +
  conditionally approved only** (exclude declined/deferred).

Enum discipline: use ONLY values listed in the template. Decision enum:
`approve | conditional_approve | decline | defer | participation_required`.
score_class: `approve_quality | conditional | weak`. CDFI risk_class:
`Prime | Desirable | Satisfactory | Watch | Doubtful | Projected Loss`.
payment_status: `Current | 30 Days Past Due | 60 Days Past Due | 90+ Days Past Due | Nonaccrual`.
Reason codes (decline): `capacity_limit, sector_breach, weak_dscr, high_ltv, low_fico,
recent_bankruptcy, startup_risk, underwater_collateral, policy_floor_missing,
documentation_gap, fdic_adverse_variance, ncua_peer_weakness`.
Output ONLY the JSON object — no narrative text outside it.

---

## 6. Population / exclusion rules (common misjudgments)

- "rated 3 or worse" / "current_rating 3 or worse" = `current_rating >= 3`
  (numbers are severity; larger = worse). "6 or worse" = `>= 6`. Use `min_current_rating`.
- Rating-2 (and better) loans are OUT of regrade/adverse populations.
- NPA / noncurrent population = `90+ Days Past Due` + `Nonaccrual` only. 30/60-day are NOT NPA.
- "30-89 day" real-estate delinquency = `30 Days Past Due` + `60 Days Past Due` (NOT 90+/Nonaccrual).
- Material downgrades: only `final - current >= 2`; ignore unchanged or improved loans.
- "migration_from_current_rating_3" = subset whose `current_rating == 3` exactly (not >=3).
- Loans with all factors null/Current keep current_rating (not auto-downgraded).
- CDFI Projected Loss requires score>=19 AND ltv>1.0 — high ltv alone is just Watch/Doubtful.
- Concentration uses total LOAN exposure as denominator, not total assets.
- Grandfathered (flag=1) sectors: existing overage tolerated; new worsening needs mitigation.
- Stress `results` exclude loans/apps without a DSCR value.
- For competing-credit tasks the winner has the LOWER weighted score / fewer breaches /
  better concentration impact; the loser gets `decline` or `defer` + the matching reason
  codes (e.g. `weak_dscr` if stressed breach, `high_ltv`, `sector_breach`,
  `fdic_adverse_variance`).

---

## 7. Step-by-step SOP for a NEW task

1. Read the prompt. Note target id(s), as-of/review date, and which template file to match.
   Read `input/payloads/answer_template.json` fully (keys, enums, ordering, precision).
2. `GET /api/policies` and `GET /api/manifest`. Cache the policy blocks you need.
3. Fetch the target's data: branch detail + metrics (right quarter) + loans and/or
   sector-exposures and/or applications; segment endpoint for segments; the matching
   FDIC or NCUA benchmark.
4. Identify the population (rating threshold / two named apps / segment state) and apply
   exclusion rules in section 6.
5. Compute per policy: re-derive ratings (2.1), CDFI scores/classes (2.2), CRE weighted
   score (2.3), DSCR stress (2.4), concentration/capacity (2.5), benchmark variance (3),
   actions/dispositions (4). Use a small script for sums/ordering to avoid arithmetic slips.
6. Assemble the JSON to the template: correct keys, enums, list ordering, and per-field
   rounding (section 5). Drop nothing required; add nothing extra.
7. Self-check: every required key present? every enum value legal? lists ordered as
   specified? money 2dp / ratios 4dp / bps 2dp / dscr 2dp / weighted 1dp / metrics integer?
   ratios expressed as fractions not percents? priority_ranking excludes declines? Output
   pure JSON only.

## 8. Worked patterns (transferable, no memorized answers)

- Rating review: pop = loans with current_rating>=3; for each compute final_rating
  (max of dscr/ltv/delinquency factor ratings); build `final_rating_exposure_totals`
  (group whole pop by final_rating), `migration_from_current_rating_3` (group the
  current==3 subset by final_rating with loan_ids), `material_downgrades` (final-current>=2),
  npa_benchmark (noncurrent exposure / total loans vs FDIC total_loans_noncurrent_pct),
  top_problem_credit (worst final_rating, then largest exposure), watch_list_action_coverage
  (group post-regrade follow-up loans by recommended_action).
- Watch-list stress: pop = current_rating>=6; assign CDFI class+factor_score; +200bp stress
  (dscr/1.18, threshold 1.0) over DSCR-available loans; workout_queue ordered by exposure desc;
  severe_bucket_counts grouped by (current_rating, payment_status).
- CRE compare: weighted CDFI score per app (lower=better, class cutoffs 2.0/3.0); dual stress
  (dscr*0.85/1.18); existing CRE concentration = CRE-loan exposure / total loans vs
  cre_policy_limit_pct; selected post-approval concentration adds requested amount to both
  numerator and denominator; FDIC metric total_real_estate_30_89_pct, branch_delinquency_ratio
  from metric delinquency_30_plus_pct; pick the lower-score, non-breaching, less-concentrating
  credit; loser -> decline/defer with reason codes; winner path likely conditional_approve /
  participation_required when CRE already over limit, with conditions like
  `bank_retained_exposure_cap`, `committee_cre_exception`, `minimum_dscr_covenant_1_25`.
- Allocation: capacity = lending_capacity_q1; rank/approve apps within capacity; screen each
  for decline reasons (weak_dscr, high_ltv, low_fico, recent_bankruptcy, startup_risk,
  documentation_gap); concentration_flags where post-approval sector pct > limit_pct;
  post_approval_concentrations per sector; priority_ranking = approved+conditional only.
- Segment posture: NCUA state metrics (integers); peer median vs US directions; capacity from
  quarterly_capacity vs pipeline; controls from minimum_checklist + control_issue
  (insurance/lien gaps -> binder verification + lien perfection); escalation triggers w/ owners;
  interpretation (capacity_available + weaker external risk -> continue_with_tighter_conditions,
  committee_message capacity_available_but_external_risk_weaker).
