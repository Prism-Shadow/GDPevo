# Enum Value Catalog

This file consolidates all allowed enum values from the five training tasks, organized by domain and field.
Values listed here are the **only** permitted values for each field — never invent new codes.

## Contractor Domain

### Determination
- `APPROVE`
- `HOLD`
- `DENY`

### Deficiency Codes (train_001 variant)
- `active_suspension`
- `bond_cancelled`
- `bond_shortfall`
- `endorsement_missing`
- `endorsement_pending`
- `experience_shortfall`
- `inspection_doc_gap`
- `inspection_safety_recheck`
- `insurance_expired`
- `insurance_pending`
- `insurance_shortfall`
- `open_minor_violation`
- `open_serious_violation`

### Deficiency Codes (train_004 variant)
- `active_suspension`
- `bond_shortfall`
- `endorsement_not_verified`
- `experience_shortfall`
- `insurance_expired`
- `insurance_not_current`
- `insurance_shortfall`
- `no_active_bond`
- `unresolved_serious_complaint`

> Note: Deficiency code enums vary between task variants. Always use the values from the specific answer_template.json provided with the task.

### Required Actions (train_001 variant)
- `board_review_suspension`
- `clear_document_gap`
- `complete_safety_recheck`
- `increase_bond_amount`
- `increase_insurance_amount`
- `obtain_current_bond`
- `obtain_required_endorsement`
- `provide_current_insurance`
- `resolve_minor_violation_review`
- `resolve_serious_violation`
- `submit_experience_evidence`
- `verify_insurance_binding`
- `verify_pending_endorsement`

### Required Actions (train_004 variant)
- `board_review`
- `clear_suspension`
- `document_experience`
- `file_active_bond`
- `increase_bond`
- `increase_insurance`
- `provide_current_insurance`
- `renew_insurance`
- `resolve_complaint`
- `verify_endorsement`

> Note: Required action enums also vary between task variants. Always use the values from the specific answer_template.json.

### Risk Tier
- `low`
- `medium`
- `high`

## Liquor Domain

### Recommended Posture
- `issue_restricted`
- `request_follow_up`
- `deny`

### Covered Risk Codes (train_002 variant)
- `AFTER_HOURS`
- `ASSAULT`
- `FOOD_SERVICE_GAP`
- `MINOR_SALE`
- `NOISE`
- `PUBLIC_SAFETY`
- `SALE_TO_MINOR`
- `SAME_PREMISES`
- `TAX_HOLD`

### Covered Risk Codes (train_005 variant)
- `AFTER_HOURS`
- `ASSAULT`
- `CAMERA_COVERAGE`
- `FOOD_SERVICE_GAP`
- `ID_CHECK`
- `MINOR_SALE`
- `NOISE`
- `PATIO_BOUNDARY`
- `TAX_HOLD`

### Verification Gap Codes (train_002 variant)
- `CONTROL_SIGNAGE_CONFLICTING`
- `CONTROL_SIGNAGE_CURRENT_MISSING`
- `FLOOR_PLAN_CONFLICTING`
- `FLOOR_PLAN_STALE`
- `NEIGHBOR_NOTICE_MISSING`
- `OPEN_INCIDENT_FOLLOW_UP`
- `POLICE_MEMO_CONFLICTING`
- `SITE_PHOTO_MISSING`
- `TAX_CLEARANCE_MISSING`

### Verification Gap Codes (train_005 variant)
- `camera_evidence_missing`
- `control_signage_missing`
- `floor_plan_conflicting`
- `food_service_evidence_missing`
- `late_night_monitoring_needed`
- `neighbor_notice_missing`
- `police_memo_identity_note`
- `site_photo_missing`
- `tax_hold_unresolved`

### Standard / Location-Specific Control Codes
- `CCTV`
- `DELIVERY`
- `FOOD_SERVICE`
- `HOURS`
- `ID_CHECK`
- `NOISE`
- `PATIO`
- `SECURITY`

### First 90-Day Check Codes (train_002 variant)
- `after_hours_visit`
- `control_signage_recheck`
- `food_service_check`
- `id_check_observation`
- `noise_log_review`
- `patio_boundary_check`
- `police_memo_follow_up`
- `security_cctv_walkthrough`
- `tax_clearance_check`

### First 90-Day Check Codes (train_005 variant)
- `camera_export_test`
- `control_signage_review`
- `food_service_service_area_check`
- `id_check_observation`
- `incident_log_review`
- `late_night_closing_visit`
- `noise_patio_boundary_check`
- `tax_clearance_review`

### Timing Windows
- `first_30_days`
- `days_31_60`
- `days_61_90`

### Escalation Trigger Codes (train_002 variant)
- `AFTER_HOURS_VIOLATION`
- `BOARD_ORDER_CONFLICT`
- `CONTROL_SIGNAGE_NOT_VERIFIED`
- `MAJOR_INCIDENT_REPORTED`
- `REFERRED_MINOR_SALE_UNRESOLVED`
- `SECURITY_CCTV_CONTROL_FAILURE`
- `TAX_HOLD_REOPENED`

### Escalation Trigger Codes (train_005 variant)
- `after_hours_service`
- `footage_not_produced`
- `food_service_not_available`
- `id_check_failure`
- `minor_sale`
- `missing_camera_coverage`
- `noise_or_patio_breach`
- `open_tax_hold_uncleared`
- `patio_boundary_failure`
- `unreported_violent_incident`

## Alcohol Renewal Domain

### Match Confidence
- `exact`
- `close_address`
- `uncertain`

### Risk Tier
- `low`
- `medium`
- `high`

### Next Step Label
- `manual_fine_check`
- `manual_ALERT_check`
- `board_review`
- `additional_record_check`
