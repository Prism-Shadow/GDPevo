# Code Mapping Reference

Distilled from training examples train_001 through train_005. These mappings show how observed data conditions translate to template codes. They are illustrative, not exhaustive — always defer to the answer template's allowed values for the specific task.

## Contractor Deficiency Codes → Required Actions

| Deficiency Code | Observed Condition | Required Action |
|---|---|---|
| `active_suspension` | License history shows an active suspension | `board_review_suspension` |
| `bond_cancelled` | Bond record status is cancelled or revoked | `obtain_current_bond` |
| `bond_shortfall` | Bond amount < required amount | `increase_bond_amount` |
| `endorsement_missing` | Required endorsement not on file | `obtain_required_endorsement` |
| `endorsement_pending` | Endorsement application submitted but not yet verified | `verify_pending_endorsement` |
| `experience_shortfall` | Documented experience below threshold | `submit_experience_evidence` |
| `inspection_doc_gap` | Inspection report flags missing documentation | `clear_document_gap` |
| `inspection_safety_recheck` | Inspection requires safety re-inspection | `complete_safety_recheck` |
| `insurance_expired` | Insurance policy end date < review date | `provide_current_insurance` |
| `insurance_pending` | Insurance application submitted, not yet bound | `verify_insurance_binding` |
| `insurance_shortfall` | Coverage amount < required amount | `increase_insurance_amount` |
| `open_minor_violation` | Violation record open with minor severity | `resolve_minor_violation_review` |
| `open_serious_violation` | Violation record open with serious severity | `resolve_serious_violation` |

## Contractor Determination Logic

| Condition | Determination | Risk Tier |
|---|---|---|
| Active suspension OR open serious violation | DENY | high |
| Bond cancelled/expired/shortfall, insurance expired/shortfall, endorsement missing, experience shortfall, or open minor violation — with no blocking conditions | HOLD | medium (or high if multiple) |
| Only minor documentation gaps (inspection doc gap, endorsement pending) | HOLD | low |
| No deficiencies, no blocking conditions | APPROVE | low |

## Liquor Risk → Verification Gap → Escalation Mapping

| Risk Code | Typical Control | Verification Gap If Missing | Escalation Trigger |
|---|---|---|---|
| `AFTER_HOURS` | HOURS restriction | — | `AFTER_HOURS_VIOLATION` |
| `ASSAULT` | SECURITY + CCTV | `POLICE_MEMO_CONFLICTING` | `MAJOR_INCIDENT_REPORTED` |
| `FOOD_SERVICE_GAP` | FOOD_SERVICE | `FLOOR_PLAN_CONFLICTING` | — |
| `MINOR_SALE` / `SALE_TO_MINOR` | ID_CHECK | `OPEN_INCIDENT_FOLLOW_UP` | `REFERRED_MINOR_SALE_UNRESOLVED` |
| `NOISE` | NOISE restriction | `NEIGHBOR_NOTICE_MISSING` | — |
| `PUBLIC_SAFETY` | SECURITY + CCTV | `SITE_PHOTO_MISSING` | `SECURITY_CCTV_CONTROL_FAILURE` |
| `SAME_PREMISES` | — | `FLOOR_PLAN_STALE` or `FLOOR_PLAN_CONFLICTING` | `BOARD_ORDER_CONFLICT` |
| `TAX_HOLD` | — | `TAX_CLEARANCE_MISSING` | `TAX_HOLD_REOPENED` |

## Alcohol Renewal Queue: Next-Step Routing

| Condition | Next Step |
|---|---|
| High risk tier with serious violations | `board_review` |
| Match confidence is `close_address` or `uncertain` | `manual_ALERT_check` |
| Violations include fine-carrying types | `manual_fine_check` |
| Record gaps or data inconsistencies | `additional_record_check` |

## Date Handling

- **Review date** (specified in prompt): The date against which currency is judged. Is the bond active on this date? Is insurance in force on this date?
- **Boundary date** (specified in prompt): The cutoff for violation inclusion. Violations on or before this date count; violations after are excluded.
- **Output dates**: Always `YYYY-MM-DD` format.
- **No review date specified**: Use the current date.
