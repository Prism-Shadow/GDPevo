# Restricted Liquor License Staff Package

## Data Sources

Fetch these endpoints (use fetch_data.py --domain liquor):

- `/api/policies` - Current policy baseline.
- `/api/liquor/applications` - Application record for the target application_id.
- `/api/liquor/settlements` - Settlement and enforcement history.
- `/api/liquor/privileges` - License privileges and conditions.
- `/api/liquor/incidents` - Incident records tied to the application or location.
- `/api/liquor/site-evidence` - Site-level evidence: photos, floor plans, signage
  records, police memos, neighbor notices, tax clearances.

Use `POST /api/sql` when the REST endpoints need a direct query for records
that cannot be retrieved by ID alone. Send the SQL as a JSON body with a
`query` key and `Content-Type: application/json`.

## Recommended Posture

Assign one of three postures based on the aggregate record:

- **issue_restricted**: All statutory requirements are met. Key risks are covered
  by active controls or standard obligations. Remaining verification gaps are
  resolvable within a 90-day monitoring window. The same-premises basis is
  applicable and the location controls are in place.
- **request_follow_up**: One or more material verification gaps exist, but they
  are correctable with additional evidence or follow-up actions. The application
  is not ready for issuance but is not fundamentally defective.
- **deny**: Statutory requirements are not met and the gaps are not correctable.
  The same-premises basis does not apply or critical controls are absent.

## Same-Premises Basis

Set `same_premises_basis_applies` to `true` when the application site shares
physical premises with an existing licensed entity and the shared-premises
controls (joint CCTV, shared security, coordinated hours) are in place or can
be established. Set to `false` when the site is standalone or when shared
controls are impossible.

## Risk Coverage

Review incident records, settlement history, and site evidence to identify which
risks are already covered by current controls. Covered risks are those where an
active control (CCTV, security, noise monitoring, ID check, food service,
patio boundary) is documented and operational.

Allowed risk codes vary by task instance. Check the answer_template.json for
the exact set. Common examples include: NOISE, AFTER_HOURS, ASSAULT,
MINOR_SALE, TAX_HOLD, FOOD_SERVICE_GAP, CAMERA_COVERAGE, SAME_PREMISES.

## Verification Gaps

Identify evidence that is missing, stale, conflicting, or unverifiable. Common
gap codes include:

- `CONTROL_SIGNAGE_CONFLICTING` or `control_signage_missing` - Signage records
  conflict with the application or are absent.
- `CONTROL_SIGNAGE_CURRENT_MISSING` - Current signage is not on file.
- `FLOOR_PLAN_CONFLICTING` or `floor_plan_conflicting` - Floor plan conflicts
  with site evidence or prior records.
- `FLOOR_PLAN_STALE` - Floor plan is outdated.
- `NEIGHBOR_NOTICE_MISSING` or `neighbor_notice_missing` - Required neighbor
  notification is not recorded.
- `OPEN_INCIDENT_FOLLOW_UP` - An incident record is open and unresolved.
- `POLICE_MEMO_CONFLICTING` or `police_memo_identity_note` - Police memo
  contains conflicting information or an unresolved identity note.
- `SITE_PHOTO_MISSING` or `site_photo_missing` - Required site photographs are
  absent.
- `TAX_CLEARANCE_MISSING` or `tax_hold_unresolved` - Tax clearance is not on
  file or a tax hold is unresolved.
- `camera_evidence_missing` - Camera or CCTV evidence is not provided.
- `food_service_evidence_missing` - Food service evidence is not provided.
- `late_night_monitoring_needed` - Late-night monitoring plan is required but
  not documented.

Always consult the answer_template.json for the exact allowed gap codes.

## Standard Obligations

Standard obligations are the ordinary requirements for the license class,
independent of the specific location. Common codes: ID_CHECK, HOURS, SECURITY,
FOOD_SERVICE, CCTV, PATIO, NOISE, DELIVERY.

## Location-Specific Controls

Location-specific controls are controls actively tied to the specific premises.
These may overlap with standard obligations but represent location-tied
conditions. Common codes mirror the obligation codes: CCTV, HOURS, SECURITY,
FOOD_SERVICE, NOISE, PATIO, DELIVERY, ID_CHECK.

Distinguish obligations (what the license class requires everywhere) from
controls (what is specifically configured for this location). An obligation
becomes a location-specific control only when there is site-level evidence that
the control is configured at this location.

## First 90-Day Monitoring Plan

Build a sequence of monitoring checks for the first 90 days after issuance.
Each check has a `check_code` and a `timing` in one of three windows:
`first_30_days`, `days_31_60`, `days_61_90`.

Check codes vary by task instance. Consult the answer_template.json for the
exact allowed set. Common examples:

- `after_hours_visit` - Unannounced after-hours compliance visit.
- `control_signage_recheck` or `control_signage_review` - Re-verify signage.
- `food_service_check` or `food_service_service_area_check` - Verify food
  service availability.
- `id_check_observation` - Observe ID verification practices.
- `noise_log_review` or `noise_patio_boundary_check` - Review noise logs or
  patio boundary compliance.
- `police_memo_follow_up` - Follow up on police memo concerns.
- `security_cctv_walkthrough` or `camera_export_test` - Verify CCTV coverage
  and footage export capability.
- `late_night_closing_visit` - Observe late-night closing procedures.
- `tax_clearance_review` or `tax_clearance_check` - Verify tax clearance.
- `incident_log_review` - Review incident logs.

Order checks in the intended operational sequence, with higher-priority checks
(control signage, ID check, camera tests) in the first 30 days and follow-up
checks in later windows.

## Escalation Triggers

Escalation triggers are conditions that, if observed during the 90-day window,
require field staff to escalate. Common codes include:

- `AFTER_HOURS_VIOLATION` or `after_hours_service` - After-hours service
  observed.
- `BOARD_ORDER_CONFLICT` - Board order conflict detected.
- `CONTROL_SIGNAGE_NOT_VERIFIED` - Signage could not be verified.
- `MAJOR_INCIDENT_REPORTED` or `unreported_violent_incident` - Major incident.
- `REFERRED_MINOR_SALE_UNRESOLVED` or `minor_sale` - Minor sale concern.
- `SECURITY_CCTV_CONTROL_FAILURE` or `missing_camera_coverage` - CCTV failure.
- `TAX_HOLD_REOPENED` or `open_tax_hold_uncleared` - Tax hold issue.
- `footage_not_produced` - CCTV footage not produced on request.
- `food_service_not_available` - Food service not available.
- `noise_or_patio_breach` - Noise or patio boundary breach.
- `patio_boundary_failure` - Patio boundary violation.
- `id_check_failure` - ID check failure.

Consult the answer_template.json for the exact set of escalation codes.

## Output Ordering

- All code arrays sorted ascending by code value and deduplicated.
- When the template specifies ascending sort, use standard string sort.
- When the template specifies operational sequence for 90-day plan items,
  order by the intended operational sequence, not alphabetically.
- Use empty arrays when no codes apply.
