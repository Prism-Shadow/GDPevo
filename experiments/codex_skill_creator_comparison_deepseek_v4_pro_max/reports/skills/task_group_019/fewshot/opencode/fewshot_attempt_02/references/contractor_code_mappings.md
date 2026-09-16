# Contractor Deficiency-to-Action Code Mappings

This reference maps each deficiency code to the required actions an applicant must take, along with the risk implication.

## Deficiency Codes and Their Required Actions

| Deficiency Code | Required Actions | Risk Contribution |
|---|---|---|
| `active_suspension` | `board_review_suspension` (or `board_review` / `clear_suspension`) | DENY trigger — sets risk to high |
| `bond_cancelled` | `obtain_current_bond` | Medium risk |
| `bond_shortfall` | `increase_bond_amount` | Medium risk |
| `no_active_bond` | `file_active_bond` | Medium risk |
| `insurance_expired` | `provide_current_insurance` (or `renew_insurance`) | Medium risk |
| `insurance_pending` | `verify_insurance_binding` | Medium risk |
| `insurance_shortfall` | `increase_insurance_amount` | High risk contributor |
| `insurance_not_current` | `provide_current_insurance` | Medium risk |
| `endorsement_missing` | `obtain_required_endorsement` | Medium risk |
| `endorsement_pending` | `verify_pending_endorsement` | Medium risk |
| `endorsement_not_verified` | `verify_endorsement` | Medium risk |
| `experience_shortfall` | `submit_experience_evidence` (or `document_experience`) | Medium risk |
| `open_minor_violation` | `resolve_minor_violation_review` | Medium risk |
| `open_serious_violation` | `resolve_serious_violation` | DENY trigger — sets risk to high |
| `unresolved_serious_complaint` | `resolve_complaint` | DENY trigger — sets risk to high |
| `inspection_doc_gap` | `clear_document_gap` | Medium risk |
| `inspection_safety_recheck` | `complete_safety_recheck` | High risk contributor |

## Action Code Canonical Forms

When the answer template specifies a fixed list of `required_actions` enum values, use those exact strings. When the template provides a guidance list, prefer:

| Canonical Action Code | Use When |
|---|---|
| `board_review` | Active suspension or serious unresolved complaint needs board-level review |
| `board_review_suspension` | Suspension specifically requires board review |
| `clear_document_gap` | Inspection documentation gap needs resolution |
| `clear_suspension` | Applicant must resolve the active suspension |
| `complete_safety_recheck` | Failed safety inspection needs re-inspection |
| `document_experience` | Experience documentation is insufficient |
| `file_active_bond` | No active bond exists on file |
| `increase_bond` | Bond amount is insufficient |
| `increase_bond_amount` | Bond amount is insufficient (longer form) |
| `increase_insurance` | Insurance coverage is insufficient |
| `increase_insurance_amount` | Insurance coverage is insufficient (longer form) |
| `obtain_current_bond` | Bond was cancelled and needs replacement |
| `obtain_required_endorsement` | Required endorsement has not been obtained |
| `provide_current_insurance` | Insurance is expired or not current |
| `renew_insurance` | Insurance has expired and needs renewal |
| `resolve_complaint` | Unresolved serious complaint needs resolution |
| `resolve_minor_violation_review` | Minor violation needs review and resolution |
| `resolve_serious_violation` | Serious violation needs resolution |
| `submit_experience_evidence` | Experience evidence is missing or insufficient |
| `verify_endorsement` | Endorsement status needs verification |
| `verify_insurance_binding` | Pending insurance needs binding verification |
| `verify_pending_endorsement` | Pending endorsement needs status verification |

## Deficiency-to-Determination Logic

```
Has active_suspension?                          → DENY (high)
Has open_serious_violation + other deficiencies? → DENY (high)
Has unresolved_serious_complaint + other?        → DENY (high)
Has any deficiency, but no DENY trigger?         → HOLD (medium/high)
Has no deficiency at all?                        → APPROVE (low)
```

Always order codes alphabetically within each application's `deficiency_codes` and `required_actions` arrays.
