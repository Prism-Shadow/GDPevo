# Risk Tier Decision Tree

Applies across all task types (contractor, liquor, alcohol renewal).

---

## Contractor Risk Tiers

```
START
 │
 ├─ Has active_suspension? ──── YES → HIGH
 │
 ├─ Has open_serious_violation or unresolved_serious_complaint? ──── YES → HIGH
 │
 ├─ Count of unique deficiency_codes ≥ 3? ──── YES → HIGH
 │
 ├─ Count of unique deficiency_codes = 2? ──── YES → MEDIUM
 │
 ├─ Count of unique deficiency_codes = 1?
 │   ├─ Is the sole deficiency open_minor_violation? ──── YES → MEDIUM
 │   └─ Otherwise (bond, insurance, endorsement, experience, inspection) ─→ MEDIUM
 │
 └─ Count of unique deficiency_codes = 0? ──── YES → LOW
```

### Refinements

- A HOLD determination with a single remediable deficiency (e.g., `insurance_pending`) may still be **medium** — not high — unless the deficiency is serious.
- `policy_impacted: true` with zero other deficiencies → **medium** (the policy change creates a new flag, even if the application would otherwise be clean).
- Applications with both a serious and a minor deficiency → **high**.

---

## Liquor Restricted-License Risk Tiers

Liquor templates do not have an explicit risk_tier field in the staff package. Risk is expressed through:
- `recommended_posture` (`deny` = highest risk, `request_follow_up` = medium, `issue_restricted` = controlled)
- The number and severity of `verification_gap_codes`
- The breadth of `escalation_trigger_codes`

### Implicit Risk Classification (if needed for cross-domain reasoning)

| Posture | Gap Count | Implicit Risk |
|---------|-----------|---------------|
| `deny` | Any | High |
| `request_follow_up` | ≥ 3 gaps | High |
| `request_follow_up` | 1–2 gaps | Medium |
| `issue_restricted` | 0 gaps | Low |
| `issue_restricted` | 1–2 minor gaps | Medium |

---

## Alcohol Renewal Queue Risk Tiers

```
START
 │
 ├─ Has violations classified as SERIOUS by /api/renewal/rules? ──── YES → HIGH
 │
 ├─ Violation count ≥ 3? ──── YES → HIGH
 │
 ├─ Violation count = 2? ──── YES → MEDIUM
 │
 ├─ Violation count = 1?
 │   ├─ Is the single violation a minor type? ──── YES → MEDIUM
 │   └─ Is the single violation serious? ──── YES → HIGH
 │
 └─ Violation count = 0? ──── YES → LOW
```

### Match Confidence Interaction

- `uncertain` match confidence on any violation → bump risk tier up one level (low → medium, medium → high).
- `close_address` match confidence → no automatic bump, but flag for `additional_record_check`.

---

## Cross-Domain Summary

| Risk Tier | Contractor | Liquor (implicit) | Alcohol Renewal |
|-----------|-----------|-------------------|-----------------|
| **High** | Active suspension, serious violation, ≥3 deficiencies, or policy-impacted with another flag | `deny` posture or ≥3 gaps with `request_follow_up` | Serious violation, ≥3 violations, or uncertain match + any violation |
| **Medium** | 1–2 remediable deficiencies, no serious | `request_follow_up` with 1–2 gaps, or `issue_restricted` with minor gaps | 1–2 violations, no serious classification |
| **Low** | No deficiencies | `issue_restricted` with 0 gaps | No matched violations |
