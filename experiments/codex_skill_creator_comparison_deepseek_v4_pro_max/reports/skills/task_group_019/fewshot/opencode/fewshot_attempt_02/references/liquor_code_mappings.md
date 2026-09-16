# Liquor License Code Mappings

This reference covers the code systems for liquor license staff packages.

## Covered Risk Codes

Codes that represent risks with adequate existing controls or documentation:

| Code | Evidence Source | Typical Context |
|---|---|---|
| `AFTER_HOURS` | Incident records showing after-hours activity with monitoring in place | Late-night venues |
| `ASSAULT` | Incident records with security controls documented | High-traffic venues |
| `MINOR_SALE` | Age-verification protocols documented and confirmed | All license classes |
| `SALE_TO_MINOR` | Same as MINOR_SALE but from enforcement perspective | Enforcement findings |
| `NOISE` | Noise complaints with monitoring/logging controls | Outdoor or music venues |
| `PATIO_BOUNDARY` | Patio boundary demarcation with monitoring | Venues with outdoor service |
| `SAME_PREMISES` | Prior license or settlement at same physical location | Transfer applications |
| `TAX_HOLD` | Tax clearance documentation provided | Applications with financial flags |
| `FOOD_SERVICE_GAP` | Food service requirements met per site evidence | Restaurant/hotel licenses |
| `PUBLIC_SAFETY` | General public safety controls documented | Any license class |

## Verification Gap Codes

Codes for what is missing, conflicting, or unverified:

| Gap Code | What to Look For |
|---|---|
| `CONTROL_SIGNAGE_CONFLICTING` | Signage records contradict each other or the site evidence |
| `CONTROL_SIGNAGE_CURRENT_MISSING` | Current signage documentation not provided |
| `FLOOR_PLAN_CONFLICTING` | Floor plan does not match site photos or inspection notes |
| `FLOOR_PLAN_STALE` | Floor plan is outdated relative to known renovations |
| `NEIGHBOR_NOTICE_MISSING` | Required neighbor notification not documented |
| `OPEN_INCIDENT_FOLLOW_UP` | An incident is unresolved and requires further action |
| `POLICE_MEMO_CONFLICTING` | Police memo information conflicts with application claims |
| `SITE_PHOTO_MISSING` | Site photographs not provided |
| `TAX_CLEARANCE_MISSING` | Tax clearance certificate not on file |
| `camera_evidence_missing` | CCTV coverage spec or footage not provided |
| `food_service_evidence_missing` | Food service operational evidence not provided |
| `floor_plan_conflicting` | Floor plan conflicts (snake_case variant) |
| `late_night_monitoring_needed` | No late-night monitoring plan in place |
| `tax_hold_unresolved` | Tax hold has not been cleared |

## Standard Obligations vs Location-Specific Controls

Both use the same code vocabulary but differ in source:

| Obligation/Control Code | Standard (license-class) | Location-Specific (premises) |
|---|---|---|
| `ID_CHECK` | Required for all on-premises licenses | Rarely location-specific |
| `HOURS` | Standard hours restriction | Restricted by board order or settlement |
| `FOOD_SERVICE` | Required for hotel/restaurant licenses | Required by settlement terms |
| `CCTV` | Required by policy for some classes | Required by settlement or incident pattern |
| `SECURITY` | Required for large-capacity venues | Required by incident history |
| `NOISE` | Standard noise ordinance compliance | Specific monitoring mandated for this site |
| `PATIO` | Not always standard | Required when outdoor service area exists |
| `DELIVERY` | Standard for off-premises licenses | Location-specific delivery restrictions |

## 90-Day Monitoring Plan Checks

| Check Code | Typical Timing | Purpose |
|---|---|---|
| `control_signage_recheck` | `first_30_days` | Verify signage is posted correctly |
| `id_check_observation` | `first_30_days` | Observe age verification in practice |
| `security_cctv_walkthrough` | `first_30_days` | Confirm CCTV and security controls operational |
| `police_memo_follow_up` | `first_30_days` | Resolve conflicting police memo items |
| `food_service_check` | `first_30_days` | Verify food service operating as claimed |
| `camera_export_test` | `first_30_days` | Test CCTV export capabilities |
| `food_service_service_area_check` | `first_30_days` | Inspect service area setup |
| `tax_clearance_check` | `first_30_days` | Verify tax clearance final |
| `after_hours_visit` | `days_31_60` | Conduct unannounced after-hours visit |
| `late_night_closing_visit` | `days_31_60` | Visit during late-night closing period |
| `noise_log_review` | `days_61_90` | Review accumulated noise complaint logs |
| `noise_patio_boundary_check` | `days_61_90` | Verify patio boundary and noise compliance |
| `patio_boundary_check` | `days_61_90` | Inspect patio boundary demarcation |

## Escalation Trigger Codes

| Trigger Code | Escalation Condition |
|---|---|
| `AFTER_HOURS_VIOLATION` | After-hours service observed during monitoring |
| `BOARD_ORDER_CONFLICT` | Board order terms violated |
| `CONTROL_SIGNAGE_NOT_VERIFIED` | Signage cannot be confirmed after monitoring visit |
| `MAJOR_INCIDENT_REPORTED` | New major incident at the premises |
| `REFERRED_MINOR_SALE_UNRESOLVED` | Referred minor-sale investigation remains open |
| `SECURITY_CCTV_CONTROL_FAILURE` | CCTV or security controls found non-operational |
| `TAX_HOLD_REOPENED` | Tax hold reinstated after clearance |
| `after_hours_service` | After-hours service detected (snake_case variant) |
| `missing_camera_coverage` | Required camera coverage absent |
| `footage_not_produced` | CCTV footage not produced upon request |
| `food_service_not_available` | Food service not operational as required |
| `noise_or_patio_breach` | Noise complaint or patio boundary violation |
| `open_tax_hold_uncleared` | Tax hold remains unresolved |

## Recommended Posture Decision Logic

```
Has unresolvable risk + board order conflict?       → deny
Has verifiable gaps the applicant can resolve?       → request_follow_up
Has covered risks only + standard obligations?       → issue_restricted
Default when gaps present and resolvable:            → request_follow_up
```
