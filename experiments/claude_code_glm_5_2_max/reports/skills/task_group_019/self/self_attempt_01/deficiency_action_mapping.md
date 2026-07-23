# Deficiency Code → Required Action Mapping

This file maps each deficiency code to its corresponding required action across observed contractor and liquor task schemas. When a deficiency code is assigned, the paired required action must also appear.

## Contractor Domain

| Deficiency Code | Required Action | Notes |
|---|---|---|
| `active_suspension` | `board_review_suspension` or `clear_suspension` | Suspension must be resolved or board-reviewed before approval. Task-specific which action code is used. |
| `bond_cancelled` | `obtain_current_bond` | Bond was previously held but is now cancelled. |
| `bond_shortfall` | `increase_bond_amount` or `increase_bond` | Bond exists but does not meet the current minimum. |
| `no_active_bond` | `file_active_bond` | No bond on record at all. |
| `endorsement_missing` | `obtain_required_endorsement` | Required specialty endorsement not filed. |
| `endorsement_pending` | `verify_pending_endorsement` | Endorsement filed but not yet verified. |
| `endorsement_not_verified` | `verify_endorsement` | Endorsement claimed but verification missing. |
| `experience_shortfall` | `submit_experience_evidence` or `document_experience` | Documented experience below threshold. |
| `inspection_doc_gap` | `clear_document_gap` | Missing documentation from inspection records. |
| `inspection_safety_recheck` | `complete_safety_recheck` | Safety item requires re-inspection. |
| `insurance_expired` | `provide_current_insurance` or `renew_insurance` | Insurance policy past expiration as of review date. |
| `insurance_not_current` | `provide_current_insurance` or `renew_insurance` | Insurance status does not meet currency standard. |
| `insurance_pending` | `verify_insurance_binding` | Insurance application filed but not yet bound. |
| `insurance_shortfall` | `increase_insurance_amount` or `increase_insurance` | Coverage amount below the required minimum. |
| `open_minor_violation` | `resolve_minor_violation_review` | Minor violation unresolved; does not block but requires follow-up. |
| `open_serious_violation` | `resolve_serious_violation` | Serious violation must be resolved before approval. |
| `unresolved_serious_complaint` | `resolve_complaint` | Serious complaint pending resolution. |

## Liquor Domain

Liquor templates do not use deficiency codes directly. Instead, gaps and risks are expressed through:

- **covered_risk_codes** — risks already mitigated by current controls
- **verification_gap_codes** — gaps requiring resolution
- **escalation_trigger_codes** — conditions that trigger escalation

The mapping is implicit: each verification gap code corresponds to a condition that the first_90_day_plan or escalation_triggers must address.

| Verification Gap Code | Typical 90-Day Check or Escalation |
|---|---|
| `camera_evidence_missing` | `camera_export_test` (90-day plan) / `missing_camera_coverage` (escalation) |
| `food_service_evidence_missing` | `food_service_service_area_check` (90-day plan) / `food_service_not_available` (escalation) |
| `floor_plan_conflicting` / `FLOOR_PLAN_CONFLICTING` / `FLOOR_PLAN_STALE` | `control_signage_recheck` or `control_signage_review` (90-day plan) |
| `late_night_monitoring_needed` | `late_night_closing_visit` (90-day plan) / `after_hours_service` (escalation) |
| `tax_hold_unresolved` / `TAX_CLEARANCE_MISSING` | `tax_clearance_check` or `tax_clearance_review` (90-day plan) / `open_tax_hold_uncleared` or `TAX_HOLD_REOPENED` (escalation) |
| `control_signage_missing` / `CONTROL_SIGNAGE_CURRENT_MISSING` | `control_signage_recheck` or `control_signage_review` (90-day plan) |
| `CONTROL_SIGNAGE_CONFLICTING` | `control_signage_recheck` (90-day plan) |
| `police_memo_identity_note` / `POLICE_MEMO_CONFLICTING` | `police_memo_follow_up` (90-day plan) |
| `neighbor_notice_missing` / `NEIGHBOR_NOTICE_MISSING` | No direct 90-day check; addressed via escalation or follow-up |
| `site_photo_missing` / `SITE_PHOTO_MISSING` | `control_signage_recheck` or site visit (90-day plan) |
| `OPEN_INCIDENT_FOLLOW_UP` | `police_memo_follow_up` (90-day plan) |

## General Rule

**Every deficiency code or verification gap must have at least one corresponding action or plan entry.** An orphan deficiency with no remediation path indicates an incomplete analysis. Conversely, an action without a corresponding deficiency or gap should be removed unless it is a mandatory standard obligation.
