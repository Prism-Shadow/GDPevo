# Credit-Risk / Lending-Committee Solver Skill

Self-contained operational skill for solving credit-risk committee evaluation tasks against the remote credit-office public REST API. A solver sees only: a task prompt, an `answer_template.json`, environment access, and this file. There are NO gold answers and NO judge endpoint available at solve time — all derivation logic must come from the API data and credit policy.

---

## 1. ENVIRONMENT ACCESS SOP

**Base URL:** `<remote-env-url>` — all endpoints return JSON, no auth, GET only.

**Call pattern:** use `curl -s` and pipe through `python3 -m json.tool` or `python3 -c "import sys,json; ..."`. Save large responses to `/tmp/*.json` and parse with python to avoid truncation. Always retrieve FULL lists (never slice `[0:2]` — scenario-critical records use ID suffixes like `-901`, `-902`, `-903` that sort AFTER normal IDs and may be missed by naive slicing).

### Endpoint map (which endpoint feeds which answer section)

| Endpoint | Use it for |
|---|---|
| `GET /api/health` | Sanity check; record counts |
| `GET /api/manifest` | Benchmark versions (`fdic_q4_2024`, `ncua_q1_2025`), policy version (`credit_policy_v2025Q1`), generated seed |
| `GET /api/policies` | **Single source of truth for ALL business rules** — risk-rating thresholds, CDFI scoring, CRE weights, stress formulas, capacity/concentration rules, delinquency minimums |
| `GET /api/branches` | List all branches; filter `?institution_type=bank` or `credit_union` |
| `GET /api/branches/{branch_id}` | Branch detail: `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`, `total_assets`, `state_code`, `institution_type`, `fdic_benchmark_set` |
| `GET /api/branches/{branch_id}/metrics` | **List of 2 quarters** (2025Q1 + 2024Q4). Use the latest quarter (2025Q1). Fields: `nonperforming_loans`, `total_loans_outstanding`, `delinquency_30_plus_pct`, `net_charge_offs`, `allowance_for_loan_losses`, `total_deposits` |
| `GET /api/branches/{branch_id}/loans` | Loan portfolio. Filters: `?min_current_rating=N` (rating >= N), `?loan_type=CRE`, `?payment_status=Nonaccrual` |
| `GET /api/branches/{branch_id}/sector-exposures` | Per-sector rows: `sector`, `current_exposure` (USD), `limit_pct`, `grandfathered` (0/1) |
| `GET /api/branches/{branch_id}/applications` | Pending applications. Filter `?loan_type=CRE`. **Important:** scenario applications have IDs ending in `-901`, `-902`, `-903` — always fetch the complete list |
| `GET /api/benchmarks/fdic/q4-2024` | FDIC ratios: `total_loans_noncurrent_pct`, `total_real_estate_noncurrent_pct`, `construction_development_noncurrent_pct`, `total_real_estate_30_89_pct`, `construction_development_30_89_pct` |
| `GET /api/benchmarks/ncua/q1-2025` | Dict with `benchmark_version` and `rows[]`. Each row: `state_code` (incl. `US` for national), `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`. Optional `?state_code=NC` |
| `GET /api/credit-union-segments/{segment_id}` | Segment JSON: `segment_id`, `segment_name`, `state_code`, `quarterly_capacity`, `current_outstanding`, `member_profile`, `portfolio_focus`, `minimum_checklist`, `peer_states`, `risk_tolerance`, `internal_context` (with `recent_delinquency_bps`, `control_issue`, `staffing_constraint`, `portfolio_yield_pct`), `notes` |

### ID conventions
- `branch_id`: uppercase (e.g. REDWOOD, LAKEVIEW, SUMMIT, HARBOR). A task names its own target branch. Credit-union segments also appear in `/api/branches` with `institution_type=credit_union` (e.g. CIVIC_NC_FIRE_EMS).
- `loan_id`: `{BRANCH_PREFIX}-LN-NNN` (e.g. `RED-LN-001`). Scenario-injected loans use `-901`, `-902`, `-903` suffixes.
- `application_id`: `{BRANCH_PREFIX}-APP-NNN` (e.g. `HAR-APP-901`). When a prompt names specific application IDs, fetch all applications for the branch and match — the `-9xx` IDs always exist.

---

## 2. DATA STRUCTURES REFERENCE

### Loan object (from /loans)
```
loan_id, borrower_name, branch_id, loan_type, sector, current_rating, payment_status,
outstanding_balance, collateral_value, dscr, ltv, debt_to_asset, fico, liquidity_months,
guarantor_strength, interest_rate, annual_debt_service, days_past_due, annual_review_date,
notes
```
- `dscr`, `ltv`, `fico`, `liquidity_months` can be `null` (e.g. HELOC, residential mortgages often lack DSCR/LTV).
- `current_rating`: integer 1-8 (1=best, 8=worst).
- `payment_status`: `Current` | `30 Days Past Due` | `60 Days Past Due` | `90+ Days Past Due` | `Nonaccrual`.

### Application object (from /applications)
```
application_id, applicant_name, business_name, branch_id, loan_type, sector, purpose,
requested_amount, proposed_rate, term_months, dscr, ltv, dti, fico, total_assets,
total_debt, annual_revenue, net_income, collateral_value, co_guarantor_strength,
years_in_business, existing_relationship_years, prior_delinquencies_12m,
bankruptcy_months_ago, documentation_complete (0/1), sba_guaranty_pct,
relationship_deposit_balance, notes
```
- Applications do NOT have `liquidity_months` or `debt_to_asset` — compute `debt_to_asset = total_debt / total_assets` when needed.
- `fico` can be `null` (especially for business/CRE loans).
- `co_guarantor_strength`: `none` | `limited` | `standard` | `strong`.

### Branch metrics (from /metrics — list of 2 quarters)
```
quarter ("2025Q1" | "2024Q4"), nonperforming_loans, total_loans_outstanding,
delinquency_30_plus_pct, net_charge_offs, allowance_for_loan_losses, total_deposits
```
- `nonperforming_loans` = sum of outstanding_balance for loans with `payment_status = "Nonaccrual"` (confirmed: matches exactly).
- `total_loans_outstanding` = sum of ALL loan outstanding_balances (confirmed: matches exactly).
- **Always use the latest quarter (2025Q1)** unless the task specifies otherwise.

### Branch detail (from /branches/{id})
```
branch_id, branch_name, institution_type (bank|credit_union), state_code,
total_assets, lending_capacity_q1, sector_ceiling_pct, cre_policy_limit_pct,
fdic_benchmark_set
```

### Credit-union segment (from /credit-union-segments/{id})
```
segment_id, segment_name, state_code, quarterly_capacity, current_outstanding,
member_profile, portfolio_focus[], minimum_checklist[], peer_states[],
risk_tolerance, internal_context {recent_delinquency_bps, control_issue,
staffing_constraint, portfolio_yield_pct}, notes
```

### FDIC benchmark (from /benchmarks/fdic/q4-2024)
```
benchmark_version: "fdic_q4_2024"
total_loans_noncurrent_pct: 0.0098
total_real_estate_noncurrent_pct: 0.0121
construction_development_noncurrent_pct: 0.0076
total_real_estate_30_89_pct: 0.0051
construction_development_30_89_pct: 0.0042
```

### NCUA benchmark (from /benchmarks/ncua/q1-2025)
```
benchmark_version: "ncua_q1_2025"
rows[]: each {state_code, delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct}
```
- `state_code = "US"` is the national row. State rows: AL, FL, GA, MI, MN, NC, OH, PA, SC, TN, VA.
- All values are **integers** (report them exactly as-is, do NOT convert to decimals).

---

## 3. CORE BUSINESS RULES (from /api/policies)

### 3.1 Risk rating re-derivation (tasks 001, general)

Policy key: `risk_rating`. Re-derive each loan's rating from objective factors, then take the **worst (highest) numeric rating** across all available factors (dominant_factor_rule).

**DSCR thresholds** (apply only if `dscr` is not null):
| DSCR | Rating |
|---|---|
| >= 1.50 | 3 |
| >= 1.25 | 4 |
| >= 1.05 | 5 |
| >= 1.00 | 6 |
| < 1.00 | 7 |

**LTV thresholds** (apply only if `ltv` is not null):
| LTV | Rating |
|---|---|
| <= 0.65 | 3 |
| <= 0.75 | 4 |
| <= 0.85 | 5 |
| <= 1.00 | 6 |
| > 1.00 | 7 |

**Delinquency minimums** (always apply — this is the severe-delinquency override):
| payment_status | Minimum rating |
|---|---|
| Current | (no floor / null) |
| 30 Days Past Due | 4 |
| 60 Days Past Due | 5 |
| 90+ Days Past Due | 7 |
| Nonaccrual | 8 |

**Final rating = max(dscr_rating, ltv_rating, delinquency_minimum)** over available factors. When a factor is null, skip it. The delinquency minimum ACTS AS A FLOOR — if DSCR/LTV would give a better (lower) rating, the delinquency floor overrides it. This is the "severe-delinquency override."

**Material downgrade**: `downgrade_notches = final_rating - current_rating`. Material if `>= material_downgrade_notches (2)`.

### 3.2 NPA benchmark variance (task 001, 005)

```
branch_npa_exposure   = metrics.nonperforming_loans  (latest quarter)
branch_total_loans    = metrics.total_loans_outstanding  (latest quarter)
branch_npa_ratio      = branch_npa_exposure / branch_total_loans   (4dp)
fdic_benchmark_ratio  = <selected FDIC metric value>              (4dp)
variance_ratio        = branch_npa_ratio - fdic_benchmark_ratio   (4dp, SIGNED)
variance_bps          = variance_ratio * 10000                    (2dp, SIGNED)
```
- **Positive variance = branch is WORSE than benchmark** (branch ratio exceeds benchmark).
- FDIC metric selection (task 001 allows 3 choices): use `total_loans_noncurrent_pct` for mixed-portfolio bank branches; use `total_real_estate_noncurrent_pct` for CRE-heavy branches; use `construction_development_noncurrent_pct` for construction-heavy branches. Pick the one whose loan-type composition best matches the branch portfolio.
- Task 005 template FORCES `fdic_benchmark_metric = "total_real_estate_30_89_pct"` (value 0.0051). The `branch_delinquency_ratio` in task 005 = `metrics.delinquency_30_plus_pct` from the latest quarter.

### 3.3 Lending capacity & sector concentration (task 002, 005)

**Capacity:**
```
lending_capacity_q1    = branch.lending_capacity_q1
gross_approved_amount  = sum of approved_amount for approve + conditional_approve decisions
committed_capacity_amount = sum of bank_capacity_used (= approved_amount after mitigations/reductions)
remaining_capacity     = lending_capacity_q1 - committed_capacity_amount
```

**Sector concentration** (the denominator is `total_loans_outstanding` from branch metrics, NOT `total_assets`):
```
existing_sector_pct     = sector_exposure.current_exposure / total_loans_outstanding
post_approval_pct       = (current_exposure + approved_amount) / total_loans_outstanding   (4dp)
limit_pct               = branch.sector_ceiling_pct  (default per-sector ceiling)
over_limit              = post_approval_pct > limit_pct   (boolean)
```

**CRE concentration** (task 005):
```
cre_policy_limit_pct            = branch.cre_policy_limit_pct
existing_cre_exposure           = sum of outstanding_balance for all loans where loan_type == "CRE"  (2dp, USD)
existing_cre_concentration      = existing_cre_exposure / total_loans_outstanding   (4dp)
selected_post_approval_cre_concentration = (existing_cre_exposure + selected.requested_amount) / total_loans_outstanding  (4dp)
selected_policy_variance_bps    = (selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000  (2dp, SIGNED)
```
- Some sectors in `sector-exposures` have `limit_pct == cre_policy_limit_pct` (these are CRE-designated sectors: e.g. Hospitality, Office). Others use the `sector_ceiling_pct`. Use `loan_type == "CRE"` from the loans endpoint as the authoritative CRE exposure measure — it's more precise than aggregating real-estate-named sectors.

**Grandfathering rule:** existing over-ceiling exposure (where `grandfathered == 1` in sector-exposures) may be retained, but NEW approvals may not worsen an over-limit sector without a mitigation (`participation_required`, `reduced_amount`, or `board_exception`).

**Allowed mitigations** (from policy `capacity_concentration.allowed_mitigations`):
`participation_required`, `reduced_amount`, `board_exception`.

### 3.4 CDFI factor scoring & risk classes (task 004, 005)

Policy key: `cdfi_factor_scores`. Four factor tables, each yielding an integer score. **Lower score = better.**

| Factor | Range → Score |
|---|---|
| **debt_to_asset** | <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6 |
| **fico** | >720→0, 680-720→1, 580-679→3, <580→5 |
| **liquidity_months** | >12→0, 6-12→1, 3-6→3, <3→5 |
| **ltv** | <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6 |

**CDFI total factor_score** = sum of the 4 available factor scores (integer).

**Risk class** (from total score):
| Score range | Class |
|---|---|
| 0-5 | Prime |
| 6-9 | Desirable |
| 10-13 | Satisfactory |
| 14-18 | Watch |
| >= 19 (and ltv <= 1.0) | Doubtful |
| >= 19 (and ltv > 1.0) | Projected Loss |

**Edge case — null factors:** When `fico` is null (common for business loans), assign the **maximum penalty** (fico→5) since a missing credit score is a risk indicator. When `liquidity_months` is null (applications don't have it), assign max penalty (5) or use an available proxy. When `debt_to_asset` is null, compute it from `total_debt / total_assets` if both are available; otherwise max penalty (6).

### 3.5 CRE weighted score (task 005)

Policy key: `cre_weighted_score`. Five C's with weights:
```
capacity:           0.45
capital:            0.03
character:          0.05
collateral_exposure: 0.36
conditions:         0.11
```

**Inferred factor-to-C mapping** (NOT explicitly in policy — derive each C's 0-6 score from the application data):
| C factor | Source field | Scoring (inferred from cdfi tables / factor analogy) |
|---|---|---|
| capacity | DSCR | >=1.5→0, >=1.25→2, >=1.05→4, >=1.0→5, <1.0→6 |
| capital | debt_to_asset = total_debt/total_assets | <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6 |
| character | fico | >720→0, 680-720→1, 580-679→3, <580→5, null→5 |
| collateral_exposure | ltv | <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6 |
| conditions | co_guarantor_strength | strong→0, standard→1, limited→3, none→5 |

```
weighted_cdfi_score = capacity_score*0.45 + capital_score*0.03 + character_score*0.05
                    + collateral_exposure_score*0.36 + conditions_score*0.11   (1dp)
```
**Lower is better.** Score class:
| Score | Class |
|---|---|
| <= 2.0 | approve_quality |
| <= 3.0 | conditional |
| > 3.0 | weak |

### 3.6 DSCR stress formulas (task 004, 005)

From policy `stress`:
- **Watch-list stress** (task 004): `stressed_dscr = dscr / (1 + 0.18)` — the `+200bp` parallel shock. `shock_label = "+200bp"`.
- **CRE dual stress** (task 005): `stressed_dscr = dscr * 0.85 / (1 + 0.18)` — combines a 15% NOI haircut with the 200bp rate shock. Report as the `formula` field.
- **Breach threshold** = `coverage_breach_threshold` = 1.00 (from policy). `breaches_threshold = stressed_dscr < 1.00`.
- Only compute stress for loans/applications where `dscr` is not null. List ordering: ascending by `loan_id` (or `application_id`).
- `breach_loan_ids`: ascending sorted list of IDs where `breaches_threshold == true`.

### 3.7 Watch-list action & workout assignment (task 001, 004)

Action enum: `monitor`, `watchlist`, `special-assets`, `workout`, `partial_chargeoff_review`, `legal_referral`.

**Inferred action mapping** (from final rating + payment_status — not gold-confirmed, use as default):
| Final rating | Payment status | Action |
|---|---|---|
| 3-4 | Current | monitor |
| 5 | Current | watchlist |
| 5 | 30 DPD | watchlist |
| 6 | Current | special-assets |
| 6 | 30-60 DPD | workout |
| 7 | any | workout |
| 7-8 | 90+ DPD / Nonaccrual | workout |
| 8 (Nonaccrual) + ltv > 1.0 | Nonaccrual | partial_chargeoff_review |
| 8 (Nonaccrual) + ltv <= 1.0 | Nonaccrual | workout |

**Workout queue** (task 004): include all adverse loans (rating >= 6) or loans requiring active management. Order: **descending exposure, then ascending loan_id**. Fields: `loan_id`, `exposure`, `risk_class`, `payment_status`, `recommended_action`, `projected_loss` (boolean = true when `risk_class == "Projected Loss"`).

### 3.8 Decision logic for pending applications (task 002, 005)

**Decision enum:** `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`.

**Decline reason codes:** `capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`.

**Inferred decision thresholds** (from policy + credit-scoring logic):
| Condition | Threshold | Effect |
|---|---|---|
| DSCR < 1.00 | weak_dscr | decline |
| DSCR 1.00-1.25 | borderline | conditional_approve |
| DSCR >= 1.25 | adequate | approve |
| LTV > 1.00 | underwater_collateral | decline |
| LTV > 0.85 | high_ltv | conditional_approve or decline (if >1.0) |
| FICO < 580 (when not null) | low_fico | decline or conditional_approve |
| FICO null (business loan) | policy_floor_missing | conditional_approve if otherwise strong |
| bankruptcy_months_ago < 24 (when not null) | recent_bankruptcy | decline |
| years_in_business < 2 | startup_risk | decline or conditional_approve |
| documentation_complete == 0 | documentation_gap | defer |
| post-approval sector > limit_pct | sector_breach | decline or participation_required |
| requested_amount > remaining capacity | capacity_limit | decline or participation_required |
| SBA guaranty available (sba_guaranty_pct > 0) | — | upgrades decline → conditional_approve with `sba_guaranty_required` |

**Conditions enum** (task 002): `participation_required`, `reduced_amount`, `board_exception`, `sba_guaranty_required`, `startup_monitoring`, `none`.

**Priority ranking** (task 002): ordered list of `application_id` values, highest priority first, **including approved AND conditionally approved applications only** (excludes declined/deferred). Rank by credit quality (DSCR, LTV, FICO) — strongest credits first.

### 3.9 Concentration flags handling (task 002)

For each application that would push a sector over its `limit_pct`:
```
flag = "breach" (if post_approval_pct > limit_pct)  -- but flag is actually boolean "over_limit" in post_approval_concentrations
handling = approve | conditional_approve | decline | participation_required | none
```
- If the sector is already grandfathered (over ceiling), new approval in that sector requires `participation_required` or `reduced_amount` mitigation or must `decline`.
- `concentration_flags` list ordering: sort by sector, then application_id.

---

## 4. TASK-TYPE PLAYBOOKS

### Task type A: Rating migration review (task 001 pattern)

**Inputs needed:** branch loans (filtered `?min_current_rating=3`), branch metrics (latest quarter), FDIC benchmark, policies.

**Steps:**
1. Fetch `loans?min_current_rating=3` → regrade population. `target_current_rating_min = 3`, `target_loan_count = len(population)`, `target_exposure = sum(outstanding_balance)`.
2. For each loan, re-derive rating using §3.1 rules. Skip null factors.
3. **final_rating_exposure_totals**: group ALL regrade loans by `final_rating` (ascending), show count + exposure.
4. **migration_from_current_rating_3**: group ONLY loans with `current_rating == 3` by `final_rating` (ascending), show count + exposure + loan_ids (ascending).
5. **material_downgrades**: loans where `final_rating - current_rating >= 2`, ordered ascending by `loan_id`. Fields: `loan_id, current_rating, final_rating, downgrade_notches, exposure`.
6. **npa_benchmark**: per §3.2. Choose FDIC metric matching portfolio. `benchmark_version = "fdic_q4_2024"`.
7. **top_problem_credit**: the loan with worst final_rating (highest), worst payment_status, highest exposure. Fields include `borrower_name`, `payment_status`, `recommended_action`.
8. **watch_list_action_coverage**: group regrade loans needing follow-up by action (§3.7). `covered_loan_count`, `covered_exposure`, `by_action` list (ascending by action name, loan_ids ascending).

### Task type B: Allocation package (task 002 pattern)

**Inputs needed:** branch detail, branch metrics, sector-exposures, applications, policies.

**Steps:**
1. Fetch all applications for the branch. For each, evaluate DSCR/LTV/FICO/bankruptcy/years_in_business/documentation.
2. Assign `decision` per §3.8. For approve/conditional_approve, set `approved_amount` (= requested_amount, or reduced if mitigation) and `bank_capacity_used`.
3. **allocation**: `lending_capacity_q1`, `gross_approved_amount` (sum of approved_amounts), `committed_capacity_amount` (post-mitigation), `remaining_capacity`, `priority_ranking` (approved + conditional only, best credit first).
4. **decisions**: list sorted by application_id ascending. Fields: `application_id, decision, approved_amount, bank_capacity_used, conditions`.
5. **concentration_flags**: for each application in a potentially breaching sector, compute post_approval_pct vs limit_pct. Sort by sector then application_id.
6. **decline_reasons**: object mapping each declined application_id to a sorted (ascending alphabetically) list of reason codes.
7. **post_approval_concentrations**: list sorted by sector ascending. Fields: `sector, exposure_after_approval, post_approval_pct (4dp), limit_pct, over_limit (bool)`. Denominator = total_loans_outstanding.

### Task type C: Credit-union segment posture (task 003 pattern)

**Inputs needed:** segment data, NCUA benchmarks, policies.

**Steps:**
1. Fetch segment by `segment_id`. Extract `state_code`, `peer_states`, `minimum_checklist`, `risk_tolerance`, `internal_context`.
2. **state_metrics**: NCUA row for the segment's `state_code`. Report integer values exactly. Fields: `state_code, benchmark_version ("ncua_q1_2025"), delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct`.
3. **peer_comparison**: 
   - `peer_states`: ascending sorted list from segment data.
   - `nc_vs_us`: direction (higher/lower/equal) of state value vs US national value, for each of the 4 metrics.
   - `nc_vs_peer_median`: direction of state value vs median of peer_states' values, for each of the 4 metrics.
   - Higher delinquency = worse; higher roaa/positive_net_income = better; higher loan_to_share = neutral-to-risky.
4. **posture**: based on capacity + external risk:
   - capacity available + external risk weaker → `continue_with_tighter_conditions`
   - capacity available + external risk strong → `continue_approving`
   - no capacity or severe external weakness → `temporarily_pause`
5. **controls**:
   - `required_checklist_gates`: set from segment's `minimum_checklist` (intersect with allowed choices).
   - `added_operating_controls`: inferred from segment's `internal_context` (control_issue → matching control, staffing_constraint → second review, recent_delinquency → delinquency watch, external risk → benchmark monitoring).
6. **escalation_triggers**: list ascending by `trigger_id`. Assign `owner` based on trigger type (risk → credit_risk_manager, operations → operations_control_manager, capacity/exception → lending_committee_chair).
7. **interpretation**: `capacity_status` (from segment capacity), `external_risk_status` (from NC vs US + peers), `risk_tolerance` (from segment), `committee_message` (matching combination).

### Task type D: Watch-list stress packet (task 004 pattern)

**Inputs needed:** branch loans (filtered `?min_current_rating=6`), policies.

**Steps:**
1. **watch_list_summary**: `adverse_rating_min = 6`, `adverse_loan_count`, `adverse_balance` (sum outstanding_balance). 
2. **risk_classes**: for each adverse loan, compute CDFI factor_score (§3.4) and risk_class. List ascending by loan_id. Fields: `loan_id, risk_class, factor_score` (integer).
3. **stress_results**: `shock_label = "+200bp"`, `breach_threshold = 1.00`. For loans with DSCR available, compute `stressed_dscr = dscr / 1.18` (2dp). `breaches_threshold = stressed_dscr < 1.00`. List ascending by loan_id. `breach_loan_ids` ascending.
4. **workout_queue**: all adverse loans needing active management. Order: **descending exposure, then ascending loan_id**. Fields: `loan_id, exposure, risk_class, payment_status, recommended_action, projected_loss` (bool = risk_class == "Projected Loss").
5. **severe_bucket_counts**: group adverse loans by `(current_rating, payment_status)`. List ascending by current_rating, then payment_status. Fields: `current_rating, payment_status, loan_count, exposure`.
6. **monitoring_cadence**: `monthly` if any severe delinquencies (90+ DPD/Nonaccrual), else `quarterly`.

### Task type E: Competing CRE decision (task 005 pattern)

**Inputs needed:** branch detail, branch metrics, branch loans, sector-exposures, applications (the two named IDs), policies, FDIC benchmark.

**Steps:**
1. Fetch the two named applications (e.g. `HAR-APP-901`, `HAR-APP-902`).
2. For each: compute `weighted_cdfi_score` (§3.5, 1dp) and `score_class` (§3.5).
3. **applications_compared**: list ascending by `application_id`. Fields: `application_id, weighted_cdfi_score, score_class, decision, reason_codes` (ascending alphabetically).
4. **stress**: `formula = "stressed_dscr = dscr * 0.85 / (1 + 0.18)"`, `coverage_breach_threshold = 1.00`. Results ascending by application_id: `application_id, base_dscr (2dp), stressed_dscr (2dp), breaches_threshold (bool)`.
5. **concentration** (§3.3): compute existing CRE exposure from `loan_type == "CRE"` loans, existing + post-approval concentrations, policy variance bps, and FDIC variance (forced metric `total_real_estate_30_89_pct`).
6. **recommended_path**: select the application with the BETTER (lower) weighted_cdfi_score and that doesn't breach the stress threshold. `path` = approve/conditional_approve/decline/defer/participation_required. `unselected_application_id`, `unselected_disposition` (decline or defer), `unselected_reason_codes` (ascending alphabetically, from subset: sector_breach, weak_dscr, high_ltv, fdic_adverse_variance).
7. **conditions**: ascending alphabetically, from the allowed set. Infer from selected app's risk factors (CRE concentration elevated → committee_cre_exception, no_additional_cre_without_committee_review; DSCR covenant → minimum_dscr_covenant_1_25; CRE collateral → updated_appraisal_before_close, tenant_roll_and_lease_review; monitoring → quarterly_financial_reporting; exposure management → bank_retained_exposure_cap).

---

## 5. OUTPUT CONVENTIONS

### Precision
| Field type | Precision | Example |
|---|---|---|
| Money / USD | 2 decimal places | `1725000.00` |
| Ratios (concentrations, NPA ratio, variance_ratio, LTV, DSCR) | 4 decimal places | `0.1136` |
| Basis points (variance_bps, policy_variance_bps) | 2 decimal places, SIGNED | `1038.00` or `-220.50` |
| DSCR (base_dscr, stressed_dscr) | 2 decimal places | `1.47` |
| Weighted CDFI score | 1 decimal place | `2.7` |
| Factor scores, ratings, notches, counts | integer | `19` |
| NCUA benchmark values | integer (exactly as reported) | `79` |
| Booleans | `true` / `false` | `true` |

### Ordering rules (CRITICAL — evaluators check ordering)
- `loan_ids` in any list: **ascending** string sort.
- `migration_from_current_rating_3`: ascending by `final_rating`.
- `final_rating_exposure_totals`: ascending by `final_rating`.
- `material_downgrades`: ascending by `loan_id`.
- `decisions` (task 002): ascending by `application_id`.
- `concentration_flags` (task 002): sort by `sector`, then `application_id`.
- `post_approval_concentrations` (task 002): ascending by `sector`.
- `applications_compared` (task 005): ascending by `application_id`.
- `stress.results` (task 004, 005): ascending by `loan_id` / `application_id`.
- `workout_queue` (task 004): **descending exposure, then ascending loan_id** (this one is DIFFERENT).
- `severe_bucket_counts` (task 004): ascending by `current_rating`, then `payment_status`.
- `by_action` (task 001): ascending by `action` name.
- `risk_classes` (task 004): ascending by `loan_id`.
- `escalation_triggers` (task 003): ascending by `trigger_id`.
- `peer_states` (task 003): ascending state code.
- `reason_codes`, `conditions`: ascending alphabetically.
- `priority_ranking` (task 002): highest priority first (NOT alphabetical).

### Complete enum reference

**payment_status:** `Current`, `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`

**decision:** `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`

**conditions (002):** `participation_required`, `reduced_amount`, `board_exception`, `sba_guaranty_required`, `startup_monitoring`, `none`

**reason_codes (002/005):** `capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`

**watch-list action:** `monitor`, `watchlist`, `special-assets`, `workout`, `partial_chargeoff_review`, `legal_referral`

**CDFI risk_class:** `Prime`, `Desirable`, `Satisfactory`, `Watch`, `Doubtful`, `Projected Loss`

**CRE score_class:** `approve_quality`, `conditional`, `weak`

**handling (002):** `approve`, `conditional_approve`, `decline`, `participation_required`, `none`

**posture (003):** `continue_approving`, `continue_with_tighter_conditions`, `temporarily_pause`

**capacity_status (003):** `capacity_available`, `capacity_constrained`, `no_capacity`

**external_risk_status (003):** `stronger_than_national_and_peers`, `mixed_vs_national_and_peers`, `weaker_than_national_and_peers`

**risk_tolerance (003):** `restrained`, `moderate`, `expansive`

**committee_message (003):** `capacity_available_but_external_risk_weaker`, `pause_until_state_metrics_recover`, `routine_approval_path_supported`

**direction (003):** `higher`, `lower`, `equal`

**checklist_gates (003):** `board_authorization`, `equipment_invoice`, `fleet_replacement_plan`, `payer_contract_summary`, `public_contract_or_tax_support`, `proof_of_insurance`, `ucc_or_title_lien`

**operating_controls (003):** `pre_close_insurance_binder_verification`, `lien_perfection_prior_to_funding`, `senior_underwriter_second_review`, `quarterly_state_benchmark_monitoring`, `monthly_segment_delinquency_watch`, `committee_exception_for_capacity_overrun`

**escalation conditions (003):** `segment_recent_delinquency_ge_90_bps`, `missing_insurance_or_lien_exception`, `quarterly_capacity_exceeded_or_exception_requested`, `state_delinquency_gap_widens_25_bps`

**escalation owners (003):** `credit_risk_manager`, `operations_control_manager`, `lending_committee_chair`

**monitoring_cadence (004):** `monthly`, `quarterly`, `semiannual`

**CRE conditions (005):** `bank_retained_exposure_cap`, `committee_cre_exception`, `updated_appraisal_before_close`, `tenant_roll_and_lease_review`, `minimum_dscr_covenant_1_25`, `quarterly_financial_reporting`, `no_additional_cre_without_committee_review`

**unselected_disposition (005):** `decline`, `defer`

**unselected_reason_codes (005):** `sector_breach`, `weak_dscr`, `high_ltv`, `fdic_adverse_variance`

**FDIC benchmark_metric (005) — FORCED:** `total_real_estate_30_89_pct`

**FDIC benchmark_metric (001) — choose:** `total_loans_noncurrent_pct`, `total_real_estate_noncurrent_pct`, `construction_development_noncurrent_pct`

---

## 6. PITFALLS & EDGE CASES

### 6.1 Regrade population vs watch-list
- Task 001 regrades loans rated **3 or worse** (`min_current_rating=3`, i.e. rating >= 3).
- Task 004 watch-list is loans rated **6 or worse** (`min_current_rating=6`, i.e. rating >= 6).
- These are DIFFERENT populations — do not mix them. The `target_current_rating_min` / `adverse_rating_min` field records which threshold was used.

### 6.2 Severe-delinquency override
- The delinquency minimum is a FLOOR, not a replacement. Compute DSCR rating and LTV rating independently, THEN take the max with the delinquency floor.
- A loan with DSCR=1.79 (rating 3) and payment_status="Nonaccrual" (floor 8) gets final_rating=8, NOT 3. The override always wins when delinquency is severe.
- 90+ DPD forces minimum rating 7; Nonaccrual forces minimum rating 8. These are the most common override cases.

### 6.3 Null factors in rating re-derivation
- When `dscr` is null (HELOC, some residential mortgages), skip the DSCR factor entirely.
- When `ltv` is null, skip the LTV factor.
- When BOTH are null but payment_status is "Current" (no delinquency floor), the loan retains its `current_rating` (cannot re-derive). It should NOT appear in migration tables as a downgrade.
- Always check for nulls before applying thresholds.

### 6.4 Concentration denominator
- **Use `total_loans_outstanding` (from branch metrics), NOT `total_assets`.** This is the most common error. The sector_ceiling_pct and cre_policy_limit_pct are fractions of the loan portfolio, not of total assets.
- `total_loans_outstanding` = sum of all loan outstanding_balances = branch metrics `total_loans_outstanding` (confirmed identical).

### 6.5 CRE exposure measurement
- Use `loan_type == "CRE"` from the loans endpoint as the authoritative CRE exposure. The sector-exposures table categorizes by sector name, and not all real-estate sectors carry the `cre_policy_limit_pct` as their `limit_pct`. Some CRE sectors (Construction, Multifamily) may show `sector_ceiling_pct` as their limit, creating an undercount if you filter by `limit_pct == cre_policy_limit_pct`.

### 6.6 Variance sign convention
- `variance_ratio = branch_ratio - benchmark_ratio` (branch minus benchmark).
- `variance_bps = variance_ratio * 10000`.
- **Positive = branch is WORSE** (higher NPA/delinquency than benchmark = adverse).
- Negative = branch is BETTER than benchmark.
- The sign matters — do not use absolute value.

### 6.7 NCUA direction interpretation
- For `delinquency_bps`: higher = WORSE (more delinquent).
- For `loan_to_share_pct`: higher = riskier (more leveraged), but direction is just "higher/lower" — report the factual direction.
- For `roaa_bps`: higher = BETTER (more profitable).
- For `positive_net_income_pct`: higher = BETTER.
- When determining `external_risk_status`, weigh: if NC is worse (higher delinquency, lower roaa, lower positive_net_income) than BOTH US and peers on most metrics → `weaker_than_national_and_peers`. If mixed → `mixed_vs_national_and_peers`.

### 6.8 Application ID verification
- When a prompt names specific application IDs (e.g. "HAR-APP-901 and HAR-APP-902"), fetch ALL applications for the branch and verify those IDs exist. The `-9xx` scenario IDs always exist but sort after normal IDs — never slice a list and assume you have all records.
- If named IDs are missing (should not happen with well-formed tasks), fall back to the applications matching the described criteria (e.g. the two CRE applications with the highest requested amounts).

### 6.9 priority_ranking includes conditional approvals
- The `priority_ranking` list (task 002) includes BOTH `approve` AND `conditional_approve` decisions — NOT just clean approvals. Declined and deferred applications are excluded.

### 6.10 workout_queue ordering is DIFFERENT
- Unlike most lists (ascending ID), the workout_queue is ordered by **descending exposure first, then ascending loan_id** as a tiebreaker. This is the one list where the largest exposures come first.

### 6.11 Factor score edge cases for CDFI
- `fico = null`: assign max penalty score **5** (missing credit history = risk).
- `liquidity_months = null` (applications): assign max penalty **5** or use `existing_relationship_years` as a partial proxy.
- When computing `debt_to_asset` for applications: `debt_to_asset = total_debt / total_assets`. If `total_assets` is 0 or null, assign max penalty **6**.
- A loan can have `risk_class = "Projected Loss"` ONLY if `factor_score >= 19 AND ltv > 1.0`. If `factor_score >= 19` but `ltv <= 1.0`, the class is `Doubtful`.

### 6.12 Quarter selection
- Branch metrics returns TWO quarters (2025Q1 and 2024Q4). **Always use 2025Q1** (the latest) unless the task explicitly specifies a prior quarter. Using the wrong quarter produces wrong NPA ratios, wrong total_loans_outstanding, and wrong concentrations.

### 6.13 SBA guaranty as a mitigant
- If an application has `sba_guaranty_pct > 0`, this is a strong mitigant. A loan that would otherwise `decline` for `weak_dscr` or `high_ltv` may become `conditional_approve` with condition `sba_guaranty_required`. The SBA guaranty reduces the bank's effective risk.

### 6.14 Grandfathered sectors
- If a sector in sector-exposures has `grandfathered == 1`, the existing over-ceiling exposure is allowed to remain. BUT new approvals that would worsen (increase) that sector's concentration require a mitigation (`participation_required`, `reduced_amount`, `board_exception`) or must be declined with `sector_breach`.

### 6.15 NCUA peer median calculation
- Peer median = median of the NCUA benchmark values for the segment's `peer_states`. For 3 peer states, this is the middle value when sorted. For an even number of peers, average the two middle values.
- Compare the segment's state value to this median for the `nc_vs_peer_median` direction fields.

### 6.16 Escalation trigger threshold checks
- `segment_recent_delinquency_ge_90_bps`: fires when `internal_context.recent_delinquency_bps >= 90`. Check the actual value (e.g. 86 < 90 → NOT currently triggered, but should still be listed as an escalation trigger to monitor).
- `state_delinquency_gap_widens_25_bps`: compare segment state delinquency_bps vs US delinquency_bps. If the gap >= 25 bps → triggered. NC (79) vs US (58) = 21 bps gap → NOT yet triggered, but monitor.

---

## 7. SOLVING WORKFLOW (step-by-step)

1. **Read the prompt** — identify the task type (A-E), target branch_id or segment_id, and any named IDs.
2. **Read the answer_template.json** — catalog every required field, its type, precision, enum constraints, and ordering rule. The template is the contract.
3. **Fetch policies** (`/api/policies`) — load all scoring tables, thresholds, and formulas.
4. **Fetch the branch/segment detail** and **branch metrics** (latest quarter).
5. **Fetch loans** (with appropriate `?min_current_rating=` filter) or **applications** (with `?loan_type=` filter). Get COMPLETE lists.
6. **Fetch sector-exposures** and **benchmarks** (FDIC and/or NCUA as needed).
7. **Compute** each answer field following the playbooks above. Double-check precision and ordering.
8. **Assemble** the JSON output matching the template's `required_top_level_keys` exactly. Use only allowed enum values.
9. **Verify**: all lists are correctly ordered, all numbers have correct precision, all enums are from the allowed set, no extra/missing top-level keys.
10. **Output** only valid JSON — no narrative text outside the JSON.
