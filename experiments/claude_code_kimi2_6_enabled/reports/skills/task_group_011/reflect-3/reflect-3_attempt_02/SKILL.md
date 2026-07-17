# Credit Office API Workflow Skill

## Overview
Tasks require querying a remote credit-office public API and producing a committee-ready JSON answer matching a strict template. The API base URL is provided in `environment_access.md`. Do not run local env/setup.sh.

## API Endpoints (always use remote public API)
- `GET /api/manifest` – lists all available endpoints and benchmark versions
- `GET /api/branches` – all branches
- `GET /api/branches/{branch_id}` – branch details (capacity, limits, state)
- `GET /api/branches/{branch_id}/metrics` – quarterly metrics (use Q1 2025)
- `GET /api/branches/{branch_id}/loans` – loan portfolio
- `GET /api/branches/{branch_id}/sector-exposures` – sector concentrations
- `GET /api/branches/{branch_id}/applications` – pending applications
- `GET /api/policies` – rating thresholds, CDFI score tables, stress formulas
- `GET /api/benchmarks/fdic/q4-2024` – FDIC benchmarks
- `GET /api/benchmarks/ncua/q1-2025` – NCUA benchmarks (rows by state_code)
- `GET /api/credit-union-segments/{segment_id}` – segment data

## Common Business Rules

### Risk Rating Re-derivation (from policies)
- **DSCR**: ≥1.5→3, ≥1.25→4, ≥1.05→5, ≥1.0→6, <1.0→7
- **LTV**: ≤0.65→3, ≤0.75→4, ≤0.85→5, ≤1.0→6, >1.0→7
- **Delinquency**: Current→null, 30 DPD→4, 60 DPD→5, 90+ DPD→7, Nonaccrual→8
- Final rating = **worst** of available DSCR, LTV, and delinquency factors.
- If a factor is missing (None), skip it.

### CDFI Factor Score (from policies)
- debt_to_asset: <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6
- fico: >720→0, 680-720→1, 580-679→3, <580→5
- liquidity_months: >12→0, 6-12→1, 3-6→3, <3→5
- ltv: <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6
- Sum all available factor scores.
- Risk class: ≤5 Prime, ≤9 Desirable, ≤13 Satisfactory, ≤18 Watch, ≥19 & ltv>1.0 Projected Loss, ≥19 Doubtful.

### Stress Formulas (from policies)
- **Watch-list +200bp**: `stressed_dscr = dscr / (1 + 0.18)`
- **CRE dual-stress**: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`
- Breach threshold = 1.0

### Material Downgrade
- Downgrade notches = final_rating − current_rating
- Material = ≥2 notches (policy: `material_downgrade_notches: 2`)

### NPA Benchmark
- `branch_npa_exposure` = `nonperforming_loans` from branch metrics (Q1 2025)
- `branch_total_loans` = `total_loans_outstanding` from branch metrics
- `branch_npa_ratio` = branch_npa_exposure / branch_total_loans (4 decimals)
- Use `total_loans_noncurrent_pct` as the default FDIC benchmark metric unless the task specifically calls for real-estate or construction.

## Output Conventions

### Ordering
- Lists of loans/applications: ascending by `loan_id` or `application_id`
- Action buckets: ascending alphabetically by action name
- Sectors: ascending alphabetically
- Watch-list workout queue: descending by exposure, then ascending loan_id
- Severe bucket counts: ascending by current_rating, then by payment_status order (Current, 30 DPD, 60 DPD, 90+ DPD, Nonaccrual)

### Precision
- Currency: round to 2 decimals
- Percentages/ratios: round to 4 decimals
- Basis points: round to 2 decimals
- DSCR: round to 2 decimals

### Enum Values
- Always use exact enum strings from the template. Never invent values.
- Payment status: `Current`, `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`
- Actions: `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`
- Decisions: `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`
- Conditions: `participation_required`, `reduced_amount`, `board_exception`, `sba_guaranty_required`, `startup_monitoring`, `none`

## Task-Specific Patterns

### Rating Migration Review (e.g., train_001)
1. Fetch branch loans, filter by `current_rating >= target_min`
2. Re-derive final ratings using DSCR/LTV/delinquency rules
3. Build `final_rating_exposure_totals` and `migration_from_current_rating_3`
4. `watch_list_action_coverage` maps final ratings to actions (3→monitor, 4→watchlist, 5→special_assets, 6→workout, 7→partial_chargeoff_review, 8→legal_referral)
5. `top_problem_credit` = worst final rating, tie-break by highest exposure

### Allocation Package (e.g., train_002)
1. Fetch applications, sector exposures, branch capacity
2. Compute post-approval sector % = (current_exposure + approved_amount) / total_loans_outstanding
3. Decision logic:
   - Clean + within limits → `approve`
   - Minor issue (weak DSCR, high LTV) → `conditional_approve` with relevant condition
   - Sector breach → `conditional_approve` with `participation_required` or `reduced_amount`
   - Multiple severe issues → `decline`
4. `bank_capacity_used` = approved_amount for approve/conditional; for participation_required use 50% of approved amount
5. `priority_ranking` = all approved/conditional apps sorted by amount descending
6. `decline_reasons` = sorted list of reason codes per declined app
7. `post_approval_concentrations` = every sector with exposure_after_approval

### Credit-Union Posture (e.g., train_003)
1. Fetch segment and NCUA benchmarks
2. State metrics = exact integer values from NCUA row for the segment's state
3. Peer comparison: compute median of peer_states for each metric; direction = higher/lower/equal vs US and vs peer median
4. `required_checklist_gates` = segment's `minimum_checklist` (sorted)
5. `added_operating_controls` = choose controls that address segment's noted issues (e.g., insurance binder verification for insurance gaps)
6. Posture: if delinquency above peers but capacity available → `continue_with_tighter_conditions`
7. `interpretation` fields must be consistent with posture and metrics

### Watch-List Stress (e.g., train_004)
1. Fetch loans with `current_rating >= adverse_min`
2. Compute CDFI factor scores and risk classes
3. `monitoring_cadence`: if any Watch/Doubtful/Projected Loss → `monthly`, else `quarterly`
4. Stress all loans with DSCR available; `breaches_threshold` if stressed_dscr < 1.0
5. Workout queue: map risk class to action; `projected_loss` = true for Nonaccrual or 90+ DPD

### Competing CRE Decision (e.g., train_005)
1. Fetch both applications, branch loans, metrics, FDIC benchmark
2. Compute weighted CDFI score using policy weights (capacity 0.45, capital 0.03, character 0.05, collateral_exposure 0.36, conditions 0.11)
3. Score class: ≤2.0 approve_quality, ≤3.0 conditional, >3.0 weak
4. CRE dual-stress both applications; select the one that does NOT breach
5. Unselected gets `decline` with reason codes sorted alphabetically
6. Concentration: existing_cre_exposure = sum of CRE loans; post-approval = existing + selected amount
7. `selected_policy_variance_bps` = (post_conc − cre_policy_limit_pct) × 10000
8. `fdic_benchmark_metric` = `total_real_estate_30_89_pct`

## Common Pitfalls
- **Do not use localhost or env/setup.sh**; always use the remote API URL from `environment_access.md`
- **Round precisely**: currency to 2 decimals, ratios to 4 decimals, bps to 2 decimals
- **Sort correctly**: ascending loan_id, alphabetical action, descending exposure for workout queue
- **Skip missing factors**: if DSCR or LTV is None, do not include it in rating derivation
- **Use Q1 2025 metrics**: metrics endpoint returns two quarters; pick the one with quarter="2025Q1"
- **Enum exactness**: any value not in the template's allowed enum will fail validation
- **Do not include narrative** outside the JSON object
- **Total loans denominator**: for concentrations, use `total_loans_outstanding` from metrics, not total_assets
