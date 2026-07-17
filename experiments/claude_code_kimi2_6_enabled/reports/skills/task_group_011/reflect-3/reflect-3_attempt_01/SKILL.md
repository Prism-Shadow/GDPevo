# Credit Office Committee JSON Skill

## Overview
Generate committee-ready JSON answers for credit risk decisions by querying the public API and strictly conforming to the task's `answer_template.json` schema.

## Test-Time Workflow

1. **Read the prompt** to identify the target branch/segment, review date, and specific deliverable.
2. **Read `input/payloads/answer_template.json`** before fetching any data. Record:
   - `required_top_level_keys`
   - Every enum field and its allowed values
   - Ordering rules for lists
   - Numeric precision requirements
3. **Fetch data from the public API** using the base URL in `environment_access.md`:
   - Start with `/api/manifest` to discover endpoints
   - Fetch branch/segment details, loans, applications, metrics, sector exposures, policies, benchmarks
4. **Apply policy rules** from `/api/policies` to derive ratings, scores, and decisions.
5. **Build JSON output** matching the template exactly. No narrative text outside the JSON.
6. **Validate** before returning:
   - All required top-level keys present
   - Enum values match exactly (case-sensitive)
   - Lists sorted per template ordering rules
   - Numbers rounded to specified precision
   - No extra keys at any level

## API Endpoints (Common)

- `GET /api/manifest` — discover endpoints and record counts
- `GET /api/branches` — list branches
- `GET /api/branches/{branch_id}` — branch details (capacity, limits)
- `GET /api/branches/{branch_id}/loans` — loan portfolio
- `GET /api/branches/{branch_id}/metrics` — quarterly metrics
- `GET /api/branches/{branch_id}/sector-exposures` — sector limits and exposure
- `GET /api/branches/{branch_id}/applications` — pending applications
- `GET /api/policies` — risk rating, CDFI scoring, stress formulas, concentration rules
- `GET /api/benchmarks/fdic/q4-2024` — FDIC benchmarks
- `GET /api/benchmarks/ncua/q1-2025` — NCUA benchmarks
- `GET /api/credit-union-segments/{segment_id}` — segment details

## Key Field Definitions & Business Rules

### Risk Rating Re-derivation (`/api/policies` → `risk_rating`)
- **DSCR thresholds**: ≥1.5→3, ≥1.25→4, ≥1.05→5, ≥1.0→6, <1.0→7
- **LTV thresholds**: ≤0.65→3, ≤0.75→4, ≤0.85→5, ≤1.0→6, >1.0→7
- **Delinquency floors**: Current→null, 30 DPD→4, 60 DPD→5, 90+ DPD→7, Nonaccrual→8
- **Dominant factor rule**: final rating = max(available DSCR rating, LTV rating, delinquency floor)
- **Material downgrade**: migration ≥ 2 notches

### CDFI Factor Scoring (`/api/policies` → `cdfi_factor_scores`)
- Only use **available** factors. Do NOT penalize missing fields.
- **Score thresholds**: Prime(0–5), Desirable(6–9), Satisfactory(10–13), Watch(14–18), Doubtful(≥19), Projected Loss(≥19 and LTV>1.0)
- Factor tables:
  - FICO: >720→0, 680–720→1, 580–679→3, <580→5
  - LTV: <0.40→0, 0.40–0.60→2, 0.60–0.80→4, >0.80→6
  - Debt-to-asset: <0.40→0, 0.40–0.60→2, 0.60–0.80→4, >0.80→6
  - Liquidity months: >12→0, 6–12→1, 3–6→3, <3→5

### CRE Weighted Score (`/api/policies` → `cre_weighted_score`)
- Weights: capacity 0.45, capital 0.03, character 0.05, collateral_exposure 0.36, conditions 0.11
- Map each factor to a 1–5 score, then compute weighted sum.
- **Classes**: approve_quality (≤2.0), conditional (≤3.0), weak (>3.0)

### Stress Formulas (`/api/policies` → `stress`)
- **CRE dual-stress**: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`
- **Watch-list +200bp**: `stressed_dscr = dscr / (1 + 0.18)`
- **Breach threshold**: 1.0

### Concentration & Capacity
- **Sector limit**: use `sector_ceiling_pct` from branch or per-sector `limit_pct` from sector-exposures
- **Post-approval %** = (current_exposure + requested_amount) / total_loans_outstanding
- **CRE exposure** = sum of `loan_type == 'CRE'` outstanding balances only
- **CRE concentration** = existing_cre_exposure / total_loans_outstanding

### NPA / Benchmark Variance
- **Branch NPA ratio** = `nonperforming_loans` / `total_loans_outstanding` from branch metrics
- **FDIC benchmark**: use the metric specified in the template (e.g., `total_loans_noncurrent_pct`, `total_real_estate_30_89_pct`)
- **Variance** = branch_ratio − fdic_ratio; express in bps (×10000)

## Output-Field Conventions

| Template Pattern | Convention |
|---|---|
| `ordering: ascending by X` | Sort list by field X ascending; tie-break alphabetically or by secondary key |
| `ordering: descending exposure, then ascending loan_id` | Primary sort −exposure, secondary sort loan_id |
| `precision: 2` | Round to 2 decimals (`round(value, 2)`) |
| `precision: 4` | Round to 4 decimals (`round(value, 4)`) |
| Enum fields | Must be exact string from `allowed_values`; case-sensitive |
| `type: list` of objects | Each item must contain all `item_required_keys` |
| `type: object` | Must contain all `required_keys` |

## Common Pitfalls

1. **Wrong template structure** — Always match `required_top_level_keys` exactly. Adding or omitting a key at any level often drops the score to 0.
2. **Missing enum value** — A single invalid enum value invalidates the entire answer.
3. **Incorrect list ordering** — Judges check ordering rules strictly. Use Python's `sorted()` with the correct key.
4. **Treating missing data as worst-case** — For CDFI scoring, policy-derived ratings, and DSCR/LTV thresholds, only apply rules when the underlying field is present. Do not invent defaults.
5. **Wrong denominator for concentration** — Use `total_loans_outstanding` from branch metrics, not total assets.
6. **NPA definition** — Use branch metrics `nonperforming_loans` divided by `total_loans_outstanding`. Do not include 30/60 DPD loans unless they are in the metrics NPA figure.
7. **Watch-list action coverage** — Include only loans that actually need follow-up (material downgrade, derived rating ≥5, or non-current status). Do not blanket-cover all reviewed loans.
8. **Priority ranking** — In allocation tasks, include only approved and conditional_approved applications; sort by priority logic (quality first, then amount).
9. **Concentration flags** — Include ALL applications, not just breached ones. Set `flag: true` only when post-approval % > limit. Set `handling` to the app's decision when flagged, otherwise `"none"`.
10. **Post-approval concentrations** — Include ALL sectors from sector-exposures, even sectors with no pending applications.
11. **Trigger IDs** — Use simple numeric IDs like `"01"`, `"02"`, `"03"` (not `"TR-01"`).
12. **Peer comparison** — `peer_states` must exactly match the segment's `peer_states` list, sorted ascending.
13. **State metrics** — Report exact integers from the NCUA benchmark table; do not round or recalculate.
14. **CRE scoring factor mapping** — Capacity maps to DSCR, Capital to debt-to-asset, Character to years-in-business/delinquencies, Collateral to LTV, Conditions to documentation/relationship length.
15. **Unselected reason codes** — In competing-CRE decisions, the unselected app's reason_codes are restricted to a smaller allowed set (e.g., `sector_breach`, `weak_dscr`, `high_ltv`, `fdic_adverse_variance`).
