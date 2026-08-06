# Determination / Posture Decision Rules

## Contractor Batch — APPROVE / HOLD / DENY

Decision priority (first applicable rule wins):

```
1. DENY  — applicant has an active suspension in license history
2. HOLD  — one or more deficiency codes apply, no deny-trigger
3. APPROVE — zero deficiencies
```

Deficiency-to-action mapping (representative; always verify against the answer template's allowed values):

| Deficiency code | Typical required action |
|---|---|
| `active_suspension` | `board_review_suspension` / `clear_suspension` |
| `bond_cancelled` / `no_active_bond` | `obtain_current_bond` / `file_active_bond` |
| `bond_shortfall` | `increase_bond_amount` / `increase_bond` |
| `insurance_expired` / `insurance_not_current` | `provide_current_insurance` / `renew_insurance` |
| `insurance_pending` | `verify_insurance_binding` |
| `insurance_shortfall` | `increase_insurance_amount` / `increase_insurance` |
| `endorsement_missing` | `obtain_required_endorsement` |
| `endorsement_pending` | `verify_pending_endorsement` |
| `endorsement_not_verified` | `verify_endorsement` |
| `experience_shortfall` | `submit_experience_evidence` / `document_experience` |
| `open_serious_violation` / `unresolved_serious_complaint` | `resolve_serious_violation` / `resolve_complaint` |
| `open_minor_violation` | `resolve_minor_violation_review` |
| `inspection_doc_gap` | `clear_document_gap` |
| `inspection_safety_recheck` | `complete_safety_recheck` |

Risk tier logic:
- **high**: active suspension, serious violation/complaint, or deficiencies across ≥2 categories
- **medium**: deficiencies within a single category
- **low**: zero deficiencies (APPROVE)

Policy-impacted flag: set to `true` when a current policy introduces a requirement that did not exist under the prior baseline AND that requirement creates a deficiency or material flag for this application.

---

## Liquor Staff Package — issue_restricted / request_follow_up / deny

Decision logic:

```
1. DENY              — disqualifying condition (unresolved serious incident, missing fundamental documentation)
2. REQUEST_FOLLOW_UP — verification gaps exist but are resolvable; not disqualifying
3. ISSUE_RESTRICTED  — all critical gaps resolved or mitigated; remaining risks are covered by controls
```

Same-premises basis: `true` when prior license history at the same premises exists (check settlements + privileges).

Covered risk codes vs. verification gap codes:
- **Covered**: risks that existing controls or prior settlement terms already address.
- **Gap**: risks that have no current control or documentation.

Standard obligations vs. location-specific controls:
- **Standard obligations**: obligations that apply to ALL licensees of this class (generic).
- **Location-specific controls**: controls activated because of this location's particular profile (may overlap with standard, but only include those with a location-specific basis).

First 90-day plan timing:
- `first_30_days`: urgent safety and compliance checks (signage, ID procedures, safety walkthroughs).
- `days_31_60`: follow-up verification, compliance confirmations.
- `days_61_90`: closing compliance checks, documentation review.
- For hotel lounges: prioritize camera export tests, food-service area checks, late-night closing visits.

---

## Alcohol Renewal Queue — Ranking (not a determination per se)

Queue ordering (highest priority = rank 1):

```
1. Higher risk tier   (high > medium > low)
2. More violations    (within same tier)
3. Most recent violation date first (within same violation count)
```

Risk tier per licensee:
- **high**: multiple serious violations, or any board-order-level violation
- **medium**: one serious or multiple minor violations
- **low**: one minor violation

Next-step label:
- `board_review`: high-severity or repeat violations
- `manual_ALERT_check`: ALERT-system flags
- `manual_fine_check`: outstanding fine-related violations
- `additional_record_check`: uncertain matches requiring verification

Match confidence:
- `exact`: license number matches directly
- `close_address`: address matches but license number differs/missing
- `uncertain`: name similarity or partial match only

Boundary enforcement:
- Violations dated AFTER the boundary → excluded from ranking, listed in `post_boundary_violation_ids_excluded`
- Violations dated ON or BEFORE the boundary → included for scoring and ranking
