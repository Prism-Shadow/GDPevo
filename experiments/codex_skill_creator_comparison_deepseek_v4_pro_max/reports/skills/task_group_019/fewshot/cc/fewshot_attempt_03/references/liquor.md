# Restricted Liquor License Review — Domain Reference

Load this reference when the task involves a restricted liquor license
application review, staff package preparation, or location-specific liquor
controls. Use it alongside the main SKILL.md workflow.

## Endpoints

| Endpoint | What it returns |
|---|---|
| GET /api/policies | Current policy baseline |
| GET /api/liquor/applications | Application records for the target application |
| GET /api/liquor/settlements | Prior settlements tied to the applicant or location |
| GET /api/liquor/privileges | Existing privilege records at the location |
| GET /api/liquor/incidents | Incident history at the location |
| GET /api/liquor/site-evidence | Site photos, floor plans, signage evidence, neighbor notices, police memos |
| POST /api/sql | Arbitrary SQL when needed |

## Recommended Posture

Assign the issuance posture using evidence from all endpoints:

1. **deny** — the application has an unresolvable blocking condition such as an
   unresolved tax hold, a board order conflict, or evidence of a major incident
   that makes the location unsuitable

2. **request_follow_up** — the application can proceed but has material
   verification gaps or unresolved evidence questions that need to be cleared
   before a restricted issuance is appropriate

3. **issue_restricted** — all verification gaps are closed, controls are in
   place, and all risk codes are covered; the application is ready to issue
   with restrictions

## Same-Premises Basis

Set same_premises_basis_applies to true when the existing premises
privilege, incident, or settlement records indicate the location has operated
under a previous license and the current application is within the same
premises scope. Set to false when the application is for a net-new location
with no prior licensing footprint at that address.

## Covered Risk Codes

These represent risks that are already addressed by existing controls or
obligations. Include only codes for which you found affirmative evidence of
coverage. Sort ascending, no duplicates.

Allowed values (task-dependent; check the answer template for the exact list):

- AFTER_HOURS — after-hours service risk covered
- ASSAULT — assault/violence risk covered
- CAMERA_COVERAGE — camera coverage risk addressed
- FOOD_SERVICE_GAP — food service gap covered
- ID_CHECK — ID checking risk covered
- MINOR_SALE — minor sale risk covered
- NOISE — noise risk covered
- PATIO_BOUNDARY — patio boundary risk covered
- PUBLIC_SAFETY — public safety risk addressed
- SALE_TO_MINOR — sale-to-minor risk tracked
- SAME_PREMISES — same-premises risk covered
- TAX_HOLD — tax hold resolved/covered

## Verification Gap Codes

These represent evidence or documentation gaps found during the review. Include
only gaps you actually observed. Sort ascending, no duplicates.

Allowed values (task-dependent; check the answer template):

- camera_evidence_missing — no camera footage or export records
- control_signage_missing — required control signage absent
- CONTROL_SIGNAGE_CONFLICTING — train-002 vocabulary for conflicting signage
- CONTROL_SIGNAGE_CURRENT_MISSING — train-002 vocabulary for missing signage
- floor_plan_conflicting — floor plan inconsistent with application
- FLOOR_PLAN_STALE — train-002 vocabulary for stale floor plan
- food_service_evidence_missing — no food service documentation
- late_night_monitoring_needed — no evidence of late-night monitoring capability
- NEIGHBOR_NOTICE_MISSING — train-002 vocabulary for missing neighbor notice
- OPEN_INCIDENT_FOLLOW_UP — train-002 vocabulary for incident follow-up needed
- POLICE_MEMO_CONFLICTING — train-002 vocabulary for conflicting police memo
- police_memo_identity_note — police memo notes identity concern
- site_photo_missing — SITE_PHOTO_MISSING in train-002 vocabulary
- tax_hold_unresolved — tax clearance not confirmed
- TAX_CLEARANCE_MISSING — train-002 vocabulary for missing tax clearance

Always match the code vocabulary to the task answer_template.json. Different
tasks use different string formats (SCREAMING_SNAKE_CASE vs snake_case) for the
same concept — follow the template, not the other task.

## Standard Obligation Codes

These are ordinary required obligations for the license class — the baseline
controls every licensee of this type must maintain. Use the allowed values from
the task answer template. Typical values:

- CCTV — closed-circuit television
- DELIVERY — delivery controls
- FOOD_SERVICE — food service requirement
- HOURS — operating hours restrictions
- ID_CHECK — ID checking requirement
- NOISE — noise controls
- PATIO — patio controls
- SECURITY — security personnel requirement

## Location-Specific Control Codes

These are active controls tied specifically to this location, as distinct from
the standard obligations that apply to the license class generally. Use the same
allowed values as standard obligations but populate only those that are
location-specific. This distinction matters: standard obligations come from the
license class rules; location-specific controls come from site evidence and
privilege records for this address.

## First 90-Day Monitoring Plan

Build the plan from observed verification gaps and risk codes. Each entry has a
check_code and timing. The plan should be operationally sequenced: earlier
checks (first_30_days) should address the most urgent gaps, later checks can
verify ongoing compliance.

Allowed check_code values (task-dependent):

- after_hours_visit — inspect after-hours operations
- camera_export_test — verify camera footage exports work
- control_signage_recheck / control_signage_review — recheck signage compliance
- food_service_check / food_service_service_area_check — verify food service
- id_check_observation — observe ID checking in practice
- incident_log_review — review incident logs
- late_night_closing_visit — visit during late closing hours
- noise_log_review — review noise complaint logs
- noise_patio_boundary_check — check noise at patio boundary
- patio_boundary_check — verify patio boundary compliance
- police_memo_follow_up — follow up on police memo issues
- security_cctv_walkthrough — walk through security/CCTV setup
- tax_clearance_check / tax_clearance_review — confirm tax clearance

Allowed timing values:

- first_30_days — highest urgency, do immediately
- days_31_60 — medium-term follow-up
- days_61_90 — longer-term verification

## Escalation Trigger Codes

Conditions that would cause field staff to escalate. Include triggers that match
the observed risk profile and verification gaps. Sort ascending, no duplicates.

Task-dependent allowed values include:

- AFTER_HOURS_VIOLATION / after_hours_service
- BOARD_ORDER_CONFLICT
- CONTROL_SIGNAGE_NOT_VERIFIED
- MAJOR_INCIDENT_REPORTED / unreported_violent_incident
- REFERRED_MINOR_SALE_UNRESOLVED / minor_sale
- SECURITY_CCTV_CONTROL_FAILURE / missing_camera_coverage / footage_not_produced
- TAX_HOLD_REOPENED / open_tax_hold_uncleared
- noise_or_patio_breach / patio_boundary_failure
- food_service_not_available
- id_check_failure

Always match the code vocabulary to the task answer_template.json.
