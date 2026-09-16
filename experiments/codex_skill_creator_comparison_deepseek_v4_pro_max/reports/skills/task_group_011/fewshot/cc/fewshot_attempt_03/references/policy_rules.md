# Policy Rules Reference

This file walks through every section of the `/api/policies` response. Use it
to map loan and application fields to the correct policy outcome. The policy
response has this top-level structure:

- `policy_version` — string, always `"credit_policy_v2025Q1"`
- `risk_rating` — how to re-derive loan risk ratings
- `cdfi_factor_scores` — CDFI-style factor scoring for risk classification
- `cre_weighted_score` — weighted scoring for CRE application comparison
- `stress` — DSCR stress formulas and breach thresholds
- `capacity_concentration` — lending capacity and sector-concentration rules

---

## 1. risk_rating

### dominant_factor_rule

```
"dominant_factor_rule": "Final re-derived rating is the worst numeric rating from available DSCR, LTV or collateral, and delinquency factors."
```

The final rating is `max(r_dscr, r_ltv, r_delq)`, where each dimension that
has available data contributes a numeric rating. If none of the three
dimensions produce a rating, keep the loan's `current_rating`.

### material_downgrade_notches

```
"material_downgrade_notches": 2
```

A downgrade is material when `final_rating - current_rating >= 2`.

### dscr_thresholds

```json
[
  {"min": 1.5,  "rating": 3},
  {"min": 1.25, "rating": 4},
  {"min": 1.05, "rating": 5},
  {"min": 1.0,  "rating": 6},
  {"max_below": 1.0, "rating": 7}
]
```

Walk the array in order. For each row:
- If it has `min`, the rating applies when `dscr >= min`.
- If it has `max_below`, the rating applies when `dscr < max_below`.

Stop at the first matching row. If `dscr` is null or none match, skip.

Examples:
- dscr = 1.47 → `min: 1.25` → rating 4
- dscr = 0.84 → `max_below: 1.0` → rating 7
- dscr = 1.05 → `min: 1.05` → rating 5
- dscr = null → no DSCR rating

### ltv_thresholds

```json
[
  {"max": 0.65, "rating": 3},
  {"max": 0.75, "rating": 4},
  {"max": 0.85, "rating": 5},
  {"max": 1.0,  "rating": 6},
  {"min_above": 1.0, "rating": 7}
]
```

Walk the array in order:
- If it has `max`, the rating applies when `ltv <= max`.
- If it has `min_above`, the rating applies when `ltv > min_above`.

Stop at the first matching row. If `ltv` is null, skip.

Examples:
- ltv = 0.68 → `max: 0.75` → rating 4
- ltv = 0.8206 → `max: 0.85` → rating 5
- ltv = 1.10 → `min_above: 1.0` → rating 7
- ltv = null → no LTV rating

### delinquency_minimums

```json
{
  "Current": null,
  "30 Days Past Due": 4,
  "60 Days Past Due": 5,
  "90+ Days Past Due": 7,
  "Nonaccrual": 8
}
```

Look up `payment_status`. `null` means no delinquency-based floor. Otherwise
the value is a rating number. This is a floor, but since the dominant-factor
rule takes the maximum, it effectively means: if payment status mandates
rating X, the final rating cannot be lower than X.

---

## 2. cdfi_factor_scores

The `classes` array defines six CDFI risk classes. The `classes` list is
informational — to classify a loan, use the four factor tables below, sum the
scores, and look up the class.

### Factor tables

Four dimensions: `ltv`, `fico`, `liquidity_months`, `debt_to_asset`.

Each table is an array of `{"range": "description", "score": integer}`.

**ltv**
```
<0.40   → 0
0.40-0.60 → 2
0.60-0.80 → 4
>0.80   → 6
```

**fico**
```
>720     → 0
680-720  → 1
580-679  → 3
<580     → 5
```

**liquidity_months**
```
>12   → 0
6-12  → 1
3-6   → 3
<3    → 5
```

**debt_to_asset**
```
<0.40   → 0
0.40-0.60 → 2
0.60-0.80 → 4
>0.80   → 6
```

**Null handling**: If a field is null, score it as 0.

### Classes

Sum the four factor scores, then classify:

| Total score | Class | Extra condition |
|---|---|---|
| 0-5 | Prime | |
| 6-9 | Desirable | |
| 10-13 | Satisfactory | |
| 14-18 | Watch | |
| >=19 | Doubtful | ltv <= 1.0 |
| >=19 | Projected Loss | ltv > 1.0 |

When `ltv` is null, treat it as not exceeding 1.0 for the Projected Loss
check (so score >=19 with null ltv → Doubtful).

---

## 3. cre_weighted_score

The policy provides weights and class boundaries:

```json
"weights": {
  "capacity": 0.45,
  "capital": 0.03,
  "character": 0.05,
  "collateral_exposure": 0.36,
  "conditions": 0.11
}
"classes": [
  {"class": "approve_quality", "max": 2.0},
  {"class": "conditional", "max": 3.0},
  {"class": "weak", "min_above": 3.0}
]
```

### Scoring dimensions

Score each dimension 1 (best), 2 (medium), or 3 (worst). The policy does not
provide explicit per-dimension thresholds, so derive them from the
policy's broader context and the application data:

**capacity** (DSCR-driven):
- DSCR >= 1.50 → 1
- DSCR 1.20-1.50 → 2
- DSCR < 1.20 → 3

**capital** (net income and existing relationship):
- Strong relationship (>=5 years) + solid net income → 1
- Standard relationship + moderate net income → 2
- Weak relationship or minimal net income → 3

**character** (FICO, bankruptcy, prior delinquencies):
- FICO >= 720, no bankruptcy, no prior delinquencies → 1
- Mixed → 2
- FICO < 580, or recent bankruptcy, or multiple delinquencies → 3

**collateral_exposure** (LTV and concentration):
- LTV <= 0.60 and sector has headroom → 1
- LTV 0.60-0.80 → 2
- LTV > 0.80 or sector near/over limit → 3

**conditions** (loan type, purpose, term):
- Strong purpose (owner-occupied, essential equipment) + reasonable term → 1
- Mixed → 2
- Speculative purpose or very long term on weak collateral → 3

Multiply each dimension score by its weight and sum. The result is the
weighted CDFI score (round to 1 decimal).

---

## 4. stress

```json
"stress": {
  "coverage_breach_threshold": 1.0,
  "cre_dual_stress_formula": "stressed_dscr = dscr * 0.85 / (1 + 0.18)",
  "watch_list_formula": "stressed_dscr = dscr / (1 + 0.18)",
  "watch_list_parallel_shock": "+200bp"
}
```

### Watch-list stress (parallel +200bp shock)

```
stressed_dscr = dscr / 1.18
```

Used for watch-list and adverse-rating reviews. Apply to every loan or
application that has a numeric `dscr`.

### CRE dual-stress

```
stressed_dscr = dscr * 0.85 / 1.18
```

Used for competing CRE decisions. Same application rule as above.

### Breach

A result breaches threshold when `stressed_dscr < 1.0`.

---

## 5. capacity_concentration

```json
"capacity_concentration": {
  "allowed_mitigations": ["participation_required", "reduced_amount", "board_exception"],
  "branch_sector_override_table": "sector_exposures",
  "grandfathering_note": "Existing over-ceiling exposure may be grandfathered, but new approvals may not worsen that sector without mitigation.",
  "lending_capacity_field": "branches.lending_capacity_q1",
  "single_sector_default_field": "branches.sector_ceiling_pct"
}
```

### Key rules

1. **Lending capacity** comes from the branch's `lending_capacity_q1` field.
2. **Sector limits** come from the `sector-exposures` endpoint
   (`limit_pct`, `current_exposure`). The total loan base for percentage
   computation is `total_loans_outstanding` from the latest quarter's
   branch metrics.
3. **General sector ceiling** is `sector_ceiling_pct` on the branch — used as
   a fallback for sectors not explicitly listed in sector-exposures.
4. **CRE-specific limit** is `cre_policy_limit_pct` on the branch.
5. **Grandfathered** sectors (`grandfathered: 1`) already exceed their
   limit; new approvals must not worsen the overage without mitigation.
6. **Allowed mitigations** when a limit would be breached:
   `participation_required` (share exposure), `reduced_amount` (cut the
   approval), `board_exception` (override with board authorization).
7. **Bank capacity used**: For full approvals, equals `approved_amount`.
   For participation-required, only the bank-retained portion counts.
   For SBA loans with a guaranty percentage, the bank portion is
   `approved_amount * (1 - sba_guaranty_pct)`.
8. **Committed capacity amount** is the sum of `bank_capacity_used` across
   all approved and conditionally approved applications.
