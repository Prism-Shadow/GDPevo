# Restricted Liquor License Review Rules

## Recommended Posture Decision Tree

```
Check for critical gaps:
  - Unresolved tax hold?
  - Serious violent incident history?
  - Multiple verification gaps with no site evidence at all?
    → If any: "deny"

Check for moderate gaps:
  - Verification gaps that can be addressed (missing photos, stale floor plan)?
  - Open incident follow-up needed?
  - Conflicting signage or police memo?
    → If any: "request_follow_up"

Otherwise:
  - All critical evidence present, minor or no gaps
    → "issue_restricted"
```

## Same-Premises Basis

Check `GET /api/liquor/privileges` for any record referencing the same location identifier. If a privilege (active, expired, or conditional) exists for the same premises, `same_premises_basis_applies` is `true`. This means the application inherits risk context from the prior use.

## Covered Risk Codes

These risks have controls already in place that demonstrably mitigate them:

| Risk Code | What It Covers | When It Is Covered |
|---|---|---|
| `AFTER_HOURS` | Late-night service risk | Operating-hours restrictions on the license/privilege |
| `ASSAULT` | Violent incident risk | Security detail requirement or CCTV coverage |
| `FOOD_SERVICE_GAP` | Insufficient food service | Food service obligation on the license class |
| `MINOR_SALE` | Sale-to-minor risk | ID-check obligation on the license class |
| `NOISE` | Noise complaints | Noise obligation or patio restriction |
| `PUBLIC_SAFETY` | Public safety incidents | Security or CCTV controls |
| `SALE_TO_MINOR` | Underage sales | ID-check obligation |
| `SAME_PREMISES` | Inherited risk from prior use | Same-premises basis applies |
| `TAX_HOLD` | Tax clearance issues | Settlement record shows cleared status |
| `PATIO_BOUNDARY` | Patio boundary issues | Patio control obligation |
| `CAMERA_COVERAGE` | Camera coverage gaps | CCTV obligation |
| `ID_CHECK` | ID verification gaps | ID_CHECK obligation |

Only include a risk code when the control is active and demonstrably adequate.

## Verification Gap Codes

Compare site evidence (from `GET /api/liquor/site-evidence`) against requirements:

| Gap Code | Evidence Check |
|---|---|
| `CONTROL_SIGNAGE_CONFLICTING` | Signage exists but conflicts with license conditions |
| `CONTROL_SIGNAGE_CURRENT_MISSING` | Required signage not found in current evidence |
| `FLOOR_PLAN_CONFLICTING` | Floor plan conflicts with application or privilege description |
| `FLOOR_PLAN_STALE` | Floor plan older than policy freshness threshold |
| `NEIGHBOR_NOTICE_MISSING` | Required neighbor notification not in evidence |
| `OPEN_INCIDENT_FOLLOW_UP` | Incident record open, needs police memo follow-up |
| `POLICE_MEMO_CONFLICTING` | Police memo contradicts application or incident record |
| `SITE_PHOTO_MISSING` | Required site photographs absent from evidence |
| `TAX_CLEARANCE_MISSING` | Tax clearance certificate not in settlements or evidence |
| `camera_evidence_missing` | Camera placement/export evidence absent |
| `food_service_evidence_missing` | Food service setup evidence absent |
| `floor_plan_conflicting` | Floor plan conflicts (lowercase variant for train 005 schema) |
| `late_night_monitoring_needed` | Late-night controls not evidenced |
| `tax_hold_unresolved` | Tax hold still active |
| `control_signage_missing` | Signage missing (lowercase variant) |
| `police_memo_identity_note` | Police memo has identity discrepancy note |
| `neighbor_notice_missing` | Notice missing (lowercase variant) |
| `site_photo_missing` | Photo missing (lowercase variant) |

Use the exact code format from the answer template (UPPER_SNAKE vs lower_snake depending on the task).

## Standard Obligations vs Location-Specific Controls

**Standard obligations** are class-default requirements. They apply to all licenses of this class regardless of location. Common ones:
- `ID_CHECK` — required ID verification for all restricted licenses
- `HOURS` — operating-hours restrictions for the license class
- `FOOD_SERVICE` — food-service requirement for restaurant/hotel licenses
- `SECURITY` — security detail for certain license classes
- `CCTV` — camera coverage for certain license classes

**Location-specific controls** are conditions tied to this particular premises, found in privilege conditions or site-evidence records:
- `CCTV` — if the premises has a specific CCTV condition
- `HOURS` — if the premises has tighter hours than class default
- `SECURITY` — if the premises has a specific security condition
- `NOISE` — if the premises has a specific noise control
- `PATIO` — if the premises has a patio-specific control
- `DELIVERY` — if the premises has a delivery restriction

A code can appear in both lists if the location-specific control supplements the class default.

## 90-Day Plan Construction

Build the plan from verification gaps. Urgency mapping:

| Gap | Check Code | Default Timing |
|---|---|---|
| Control signage issues | `control_signage_recheck` | `first_30_days` |
| Camera evidence missing | `camera_export_test` / `security_cctv_walkthrough` | `first_30_days` |
| Police memo conflicting | `police_memo_follow_up` | `first_30_days` |
| Tax clearance missing | `tax_clearance_review` | `first_30_days` |
| Food service evidence missing | `food_service_service_area_check` | `first_30_days` |
| ID check needed | `id_check_observation` | `first_30_days` |
| After-hours concerns | `after_hours_visit` | `days_31_60` |
| Late-night monitoring | `late_night_closing_visit` | `days_31_60` |
| Noise/patio concerns | `noise_patio_boundary_check` / `noise_log_review` | `days_61_90` |
| Incident log review | `incident_log_review` | `days_61_90` |

Each plan item must have a `check_code` and `timing`. Order items in the intended operational sequence (earliest first). Check codes differ between task schemas; use exactly the codes from the answer template.

## Escalation Triggers

Triggers define events that cause field-staff escalation. Derive from uncovered risks and verification gaps:

| Trigger Code | Condition |
|---|---|
| `AFTER_HOURS_VIOLATION` | After-hours service detected during monitoring |
| `BOARD_ORDER_CONFLICT` | License conditions conflict with a board order |
| `CONTROL_SIGNAGE_NOT_VERIFIED` | Signage still not verified after recheck window |
| `MAJOR_INCIDENT_REPORTED` | New major incident reported after issuance |
| `REFERRED_MINOR_SALE_UNRESOLVED` | Referred minor-sale case still unresolved |
| `SECURITY_CCTV_CONTROL_FAILURE` | CCTV or security control fails audit |
| `TAX_HOLD_REOPENED` | Previously cleared tax hold reopens |
| `after_hours_service` | After-hours service detected (lowercase variant) |
| `missing_camera_coverage` | Camera coverage gap found |
| `footage_not_produced` | Licensee fails to produce requested footage |
| `food_service_not_available` | Food service not operational during check |
| `noise_or_patio_breach` | Noise complaint or patio boundary violation |
| `open_tax_hold_uncleared` | Tax hold not cleared within timeline |
| `unreported_violent_incident` | Violent incident not reported to board |
| `minor_sale` | Minor-sale incident |
| `patio_boundary_failure` | Patio boundary control failure |
| `id_check_failure` | ID check failure during observation |

Use the exact code format from the answer template.

## Sorting

All code arrays should be sorted ascending (lexical) and deduplicated. Plan items should be in operational sequence, not alphabetical.
