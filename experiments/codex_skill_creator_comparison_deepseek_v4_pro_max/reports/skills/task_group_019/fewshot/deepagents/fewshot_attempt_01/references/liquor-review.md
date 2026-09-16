# Restricted-Liquor Staff Package Review

## Endpoints

| Endpoint | What It Supplies |
|----------|-----------------|
| GET /api/policies | Regulatory rules for liquor control review |
| GET /api/liquor/applications | Application identity, applicant, address, license_class, location_id |
| GET /api/liquor/settlements | Prior settlements or board orders tied to a location |
| GET /api/liquor/privileges | Standard license privileges for the class |
| GET /api/liquor/incidents | Reported incidents at the location |
| GET /api/liquor/site-evidence | Site photos, floor plans, control signage, police memos |
| POST /api/sql | Targeted queries (use X-Task-Token header) |

## Application & Location Identity

Read the application record to confirm:
- `application_id` matches the task target
- `location_id` matches the task target
- `license_class` and `requested_posture` inform what obligations apply

## Policy Baseline

Policy `POL-LIQ-001` (LIQ-SETTLEMENT-CONTROLS) establishes:
- `current_site_evidence_required: true` -- missing site evidence is a gap
- `same_premises_history_matters: true` -- prior incidents or settlements at
  the same physical premises carry forward to the current review
- `standard_privileges_separate_from_controls: true` -- obligations tied to
  the license class (standard_obligation_codes) are distinct from controls
  imposed on this specific location (location_specific_control_codes)

## Same-Premises Basis

Set `same_premises_basis_applies` to `true` when any settlement, incident,
or site evidence record references the same physical premises as the current
application location. This is almost always true when the policy
`same_premises_history_matters` is set and history records exist.

## Covered Risk Codes

Identify risks that current controls already address. Look at:
- Site evidence showing active controls (CCTV, security, signage)
- Settlement terms that impose specific operating conditions
- Privilege records showing what the license class ordinarily authorizes

A risk code goes into `covered_risk_codes` when the current regulatory
posture already accounts for it -- it is "covered" by existing measures.

## Verification Gap Codes

Identify verification gaps from site evidence and incident records:

- Missing police memo or conflicting police memo -> `POLICE_MEMO_CONFLICTING`
- Missing site photo -> `SITE_PHOTO_MISSING`
- Missing or conflicting control signage -> `CONTROL_SIGNAGE_CONFLICTING`, `CONTROL_SIGNAGE_CURRENT_MISSING`
- Floor plan stale or conflicting -> `FLOOR_PLAN_CONFLICTING`, `FLOOR_PLAN_STALE`
- Missing neighbor notice -> `NEIGHBOR_NOTICE_MISSING`
- Open incident requiring follow-up -> `OPEN_INCIDENT_FOLLOW_UP`
- Missing tax clearance -> `TAX_CLEARANCE_MISSING`
- Missing camera evidence -> `camera_evidence_missing`
- Missing food service evidence -> `food_service_evidence_missing`
- Late-night monitoring not established -> `late_night_monitoring_needed`
- Unresolved tax hold -> `tax_hold_unresolved`

The answer template's `allowed_values` for `verification_gap_codes` defines
the exact code set for the task at hand. Match to the template.

## Standard Obligation Codes

Standard obligations are tied to the license class itself -- things every
licensee of that class must do regardless of location:

| License Class | Typical Standard Obligations |
|---------------|------------------------------|
| Tavern | ID_CHECK, HOURS, FOOD_SERVICE |
| Restaurant | ID_CHECK, HOURS, FOOD_SERVICE |
| BeerWine | ID_CHECK, HOURS |
| Package | HOURS, ID_CHECK |
| Hotel Lounge | ID_CHECK, HOURS, FOOD_SERVICE |

The exact codes come from the `/api/liquor/privileges` endpoint.

## Location-Specific Control Codes

Location-specific controls are conditions imposed on this particular
premises, drawn from settlement terms, incident history, or board orders.
These come from `/api/liquor/settlements` and `/api/liquor/site-evidence`.

## First 90-Day Plan

Build a monitoring plan ordered by operational sequence. Each entry has a
`check_code` and a `timing` (first_30_days, days_31_60, days_61_90).

Map verification gaps to checks:
- Signage issues -> `control_signage_recheck` early (first_30_days)
- Camera gaps -> `camera_export_test` early (first_30_days)
- Food service gaps -> `food_service_service_area_check` early (first_30_days)
- Police memo issues -> `police_memo_follow_up` early (first_30_days)
- ID check concerns -> `id_check_observation` (any window)
- CCTV/security -> `security_cctv_walkthrough` early (first_30_days)
- After-hours risk -> `after_hours_visit` in days 31-60
- Late-night monitoring -> `late_night_closing_visit` in days 31-60
- Noise/patio -> `noise_patio_boundary_check` in days 61-90
- Tax issues -> `tax_clearance_check` or `tax_clearance_review` early
- Incident log -> `incident_log_review` in days 61-90

Use the answer template's `allowed_values` for `check_code` and `timing` to
select the right codes.

## Escalation Trigger Codes

Escalation triggers are conditions that would cause field staff to escalate:

- After-hours violations -> `AFTER_HOURS_VIOLATION` / `after_hours_service`
- Camera control failure -> `SECURITY_CCTV_CONTROL_FAILURE` / `missing_camera_coverage` / `footage_not_produced`
- Control signage not verified -> `CONTROL_SIGNAGE_NOT_VERIFIED`
- Major incident reported -> `MAJOR_INCIDENT_REPORTED`
- Minor sale unresolved -> `REFERRED_MINOR_SALE_UNRESOLVED` / `minor_sale`
- Board order conflict -> `BOARD_ORDER_CONFLICT`
- Tax hold reopened -> `TAX_HOLD_REOPENED` / `open_tax_hold_uncleared`
- Food service not available -> `food_service_not_available`
- Noise or patio breach -> `noise_or_patio_breach`
- Unreported violent incident -> `unreported_violent_incident`
- ID check failure -> `id_check_failure`

## Posture Determination

- If gap codes are critically blocking (missing core evidence, unresolved
  serious incidents, active tax hold) -> `deny`
- If gaps exist but are resolvable with follow-up -> `request_follow_up`
- If no gaps and all controls verified -> `issue_restricted`

Most tasks with any verification gap codes result in `request_follow_up`.
Reserve `deny` for active settlement violations or unresolvable conflicts.
