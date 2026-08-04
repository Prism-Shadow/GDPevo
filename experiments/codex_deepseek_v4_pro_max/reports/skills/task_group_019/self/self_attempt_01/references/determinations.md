# Determination Codes and Deficiency Mapping

## Contractor Batch Review

### Determination Enum
- `APPROVE` — No deficiencies, or only resolved deficiencies.
- `HOLD` — Deficiencies resolvable through applicant action; not blocking.
- `DENY` — Active suspension, cancelled bond, expired insurance, unresolved serious violations.

### Deficiency Codes and Required Actions

| Deficiency Code | Required Action | Risk Impact |
|---|---|---|
| `active_suspension` | `board_review_suspension` | DENY |
| `bond_cancelled` | `obtain_current_bond` | DENY or HOLD |
| `bond_shortfall` | `increase_bond_amount` | HOLD |
| `endorsement_missing` | `obtain_required_endorsement` | HOLD |
| `endorsement_pending` | `verify_pending_endorsement` | HOLD |
| `experience_shortfall` | `submit_experience_evidence` | HOLD |
| `inspection_doc_gap` | `clear_document_gap` | HOLD |
| `inspection_safety_recheck` | `complete_safety_recheck` | HOLD |
| `insurance_expired` | `provide_current_insurance` | DENY or HOLD |
| `insurance_pending` | `verify_insurance_binding` | HOLD |
| `insurance_shortfall` | `increase_insurance_amount` | HOLD |
| `open_minor_violation` | `resolve_minor_violation_review` | HOLD |
| `open_serious_violation` | `resolve_serious_violation` | DENY |

### Risk Tier Assignment
- `low` — 0 deficiencies, or only resolved items.
- `medium` — 1–2 HOLD-level deficiencies, no DENY-level.
- `high` — Any DENY-level deficiency, or 3+ deficiencies, or active suspension.

### Policy Impact
Set `policy_impacted: true` when the current policy baseline creates a deficiency
or material review flag that would not have applied under the prior baseline.

## Liquor License Staff Package

### Recommended Posture
- `issue_restricted` — License can be issued with conditions and monitoring.
- `request_follow_up` — Additional information needed; pause issuance.
- `deny` — Unresolvable risks or disqualifying factors.

### Same-Premises Basis
Set `same_premises_basis_applies: true` when the location has prior licensing
history that provides a baseline for current evaluation (e.g., prior license at
same address, same operational footprint).

### Covered Risk Codes
Risks adequately addressed by current controls:
- `AFTER_HOURS` — Late-night service risk.
- `ASSAULT` — Violent incident risk on premises.
- `FOOD_SERVICE_GAP` — Food service availability risk.
- `MINOR_SALE` / `SALE_TO_MINOR` — Underage sale risk.
- `NOISE` — Noise complaint risk.
- `PUBLIC_SAFETY` — General public safety concern.
- `SAME_PREMISES` — Risk unique to location history.
- `TAX_HOLD` — Tax clearance hold risk.
- `CAMERA_COVERAGE` — CCTV coverage risk (hotel-lounge).
- `ID_CHECK` — ID verification risk (hotel-lounge).
- `PATIO_BOUNDARY` — Patio boundary compliance risk (hotel-lounge).

### Verification Gap Codes
- `camera_evidence_missing` — No camera footage or coverage plan submitted.
- `food_service_evidence_missing` — No food-service documentation.
- `floor_plan_conflicting` — Submitted floor plan conflicts with site evidence.
- `late_night_monitoring_needed` — No late-night monitoring plan for high-risk hours.
- `tax_hold_unresolved` — Outstanding tax clearance issue.
- `control_signage_missing` — Required control signage not documented.
- `police_memo_identity_note` — Police memo identifies applicant concerns.
- `neighbor_notice_missing` — No neighbor notification on file.
- `site_photo_missing` — No current site photos submitted.

### Obligation and Control Codes (shared pool)
- `ID_CHECK` — ID verification requirement.
- `HOURS` — Operating-hour restriction.
- `SECURITY` — Security personnel or measures.
- `FOOD_SERVICE` — Food service requirement.
- `CCTV` — Camera/recording requirement.
- `PATIO` — Patio operation controls.
- `NOISE` — Noise mitigation controls.
- `DELIVERY` — Delivery operation controls.

### First-90-Day Check Codes
- `camera_export_test` — Verify camera footage can be exported.
- `food_service_service_area_check` — Verify food service is operational.
- `late_night_closing_visit` — Unannounced visit during closing hours.
- `noise_patio_boundary_check` — Noise measurement at patio boundary.
- `id_check_observation` — Observe ID checking practice.
- `control_signage_review` — Verify all required signage posted.
- `tax_clearance_review` — Verify tax hold resolved.
- `incident_log_review` — Review incident log for unreported events.

### Escalation Trigger Codes
- `after_hours_service` — Service observed outside permitted hours.
- `missing_camera_coverage` — Required camera coverage not maintained.
- `footage_not_produced` — Requested footage not provided.
- `food_service_not_available` — Required food service not operating.
- `noise_or_patio_breach` — Noise or patio boundary violation.
- `open_tax_hold_uncleared` — Tax hold remains after clearance deadline.
- `unreported_violent_incident` — Violent incident not reported.
- `minor_sale` — Sale to minor detected.
- `patio_boundary_failure` — Patio boundary non-compliant.
- `id_check_failure` — ID check practice failed observation.
