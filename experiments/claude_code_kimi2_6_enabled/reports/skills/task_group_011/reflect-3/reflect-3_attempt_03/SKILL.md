# Credit Office Committee JSON Packet Skill

## API Workflow

Fetch data in this order for every branch/segment task:

1. `GET /api/branches/{branch_id}` — branch config (capacity, limits, state, assets)
2. `GET /api/branches/{branch_id}/metrics` — latest quarter metrics (nonperforming_loans, total_loans_outstanding, delinquency_30_plus_pct)
3. `GET /api/branches/{branch_id}/loans` — full loan portfolio
4. `GET /api/branches/{branch_id}/sector-exposures` — per-sector exposure and limit_pct
5. `GET /api/branches/{branch_id}/applications` — pending applications (for allocation/CRE tasks)
6. `GET /api/policies` — credit policy thresholds and formulas
7. `GET /api/benchmarks/fdic/q4-2024` or `/api/benchmarks/ncua/q1-2025` — benchmark data
8. `GET /api/credit-union-segments/{segment_id}` — segment config, peer_states, minimum_checklist, internal_context

Use the latest metric row (max quarter string like "2025Q1").

## Risk Rating Re-derivation (Universal Rule)

From `/api/policies`:

- **DSCR**: ≥1.5→3, ≥1.25→4, ≥1.05→5, ≥1.0→6, <1.0→7
- **LTV**: ≤0.65→3, ≤0.75→4, ≤0.85→5, ≤1.0→6, >1.0→7
- **Delinquency**: Current→null, 30 DPD→4, 60 DPD→5, 90+ DPD→7, Nonaccrual→8
- **Final rating** = max of all *available* factor ratings. If no DSCR/LTV/delinquency factors are available, fallback to `current_rating`.
- Material downgrade = final_rating − current_rating ≥ 2 (policy value `material_downgrade_notches`).

## Output-Field Conventions

### Precision
- Currency (USD): round to exactly 2 decimals (`round(value, 2)`)
- Ratios: 4 decimals
- Basis points (bps): 2 decimals
- Integer fields: exact integers (no `.0`)

### Ordering
- loan_id lists: ascending alphanumeric
- application_id lists: ascending alphanumeric
- sector lists: ascending alphabetically
- state lists: ascending alphabetically
- exposure-descending queues: `(-exposure, loan_id)`

### Enums
Use only the exact strings listed in `answer_template.json`. Never invent values.

## Task-Specific Business Rules

### 1. Branch Rating Migration Review (e.g., REDWOOD)
- Regrade population: loans with `current_rating >= 3` ("3 or worse")
- NPA benchmark: use `nonperforming_loans` and `total_loans_outstanding` from **branch metrics**, do NOT sum non-current loans from the loan list
- `watch_list_action_coverage.by_action` must include **all** actions (including `monitor`). `covered_loan_count` and `covered_exposure` should reflect loans with non-monitor actions only
- Action mapping by final_rating: 3→monitor, 4→watchlist, 5→special_assets, 6→workout, 7→partial_chargeoff_review, 8→legal_referral

### 2. Lending Allocation Package (e.g., LAKEVIEW)
- Sector concentration denominator is **`total_loans_outstanding`** from branch metrics, NOT `total_assets`
- `bank_capacity_used` for SBA loans should be reduced by the guaranty percentage (`approved_amount * (1 - sba_guaranty_pct)`)
- `concentration_flags` is **per-application**: `post_approval_pct` = (`existing_sector[sector]` + `this_app_approved_amount`) / `total_loans_outstanding`
- Only applications whose own approved amount pushes their sector over `limit_pct` get `flag=true`
- `committed_capacity_amount` = sum of `bank_capacity_used` (not gross approved amounts)
- Declined applications get `approved_amount=0.0`, `bank_capacity_used=0.0`, `conditions=[]`

### 3. Credit-Union Segment Posture (e.g., CIVIC_NC_FIRE_EMS)
- `peer_states`: use the **exact list** from the segment endpoint (`segment["peer_states"]`)
- `required_checklist_gates`: use the **exact list** from `segment["minimum_checklist"]`
- `state_metrics` values must come from the NCUA benchmark table (not segment internal_context)
- `risk_tolerance`: use `segment["risk_tolerance"]` when available
- For peer median comparisons, compute median of each metric across peer states

### 4. Watch-List Stress Packet (e.g., SUMMIT)
- Adverse population: loans with `current_rating >= 6`
- CDFI risk class: compute factor score from available `debt_to_asset`, `fico`, `liquidity_months`, `ltv` using the tables in `/api/policies`
  - Score ≤5→Prime, ≤9→Desirable, ≤13→Satisfactory, ≤18→Watch, >18 & ltv>1.0→Projected Loss, otherwise Doubtful
- Watch-list stress formula: `stressed_dscr = round(dscr / 1.18, 2)` (policy `watch_list_formula`)
- Shock label: `+200bp watch-list parallel shock`
- Breach threshold: 1.0
- Workout queue actions: risk-class driven—Projected Loss→legal_referral, Doubtful→partial_chargeoff_review, Watch→workout, Satisfactory→special_assets, Desirable→watchlist, Prime→monitor
- `monitoring_cadence`: `monthly` if any Projected Loss / Doubtful / Nonaccrual exists, otherwise `quarterly`

### 5. Competing CRE Decision (e.g., HARBOR)
- Compare only the two specified CRE application IDs
- CRE weighted score: approximate the 5 C's with 1–4 scale, weight by policy (`capacity 0.45`, `collateral_exposure 0.36`, etc.), round to 1 decimal
  - capacity from DSCR, collateral from LTV, capital from debt-to-asset or equity ratio, character from FICO/delinquencies/bankruptcy
- CRE dual-stress: `stressed_dscr = round(dscr * 0.85 / 1.18, 2)`
- `existing_cre_exposure` includes all real-estate-related sectors: Construction, Hospitality, Office, Multifamily, Residential, Retail CRE, Industrial CRE
- Concentration denominator: `total_loans_outstanding`
- `unselected_reason_codes` allowed values: `sector_breach`, `weak_dscr`, `high_ltv`, `fdic_adverse_variance`. Include `fdic_adverse_variance` whenever branch delinquency exceeds the FDIC benchmark.
- Conditions: always include `no_additional_cre_without_committee_review` when branch CRE is already near/above policy limit

## Common Pitfalls
- Do NOT use `total_assets` for sector or CRE concentration denominators; use `total_loans_outstanding`
- Do NOT compute NPA by summing all non-current loans; use the branch metric `nonperforming_loans`
- Do NOT guess peer states for credit unions; read them from the segment endpoint
- Do NOT omit `monitor` from `watch_list_action_coverage.by_action`
- Do NOT compute `concentration_flags` post_approval_pct using aggregate after ALL approvals; compute per-application
- Do NOT forget to sort every list to the ordering specified in the template
- Do NOT include narrative outside the JSON object
