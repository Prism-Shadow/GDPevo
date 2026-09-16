# Restricted Liquor License Staff Package

## Data Sources

Fetch all records before making determinations:

1. `GET /api/policies` — current policy standards for restricted licenses
2. `GET /api/liquor/applications` — application details, license class, premises, applicant
3. `GET /api/liquor/settlements` — prior settlements and board orders related to applicant or location
4. `GET /api/liquor/privileges` — current license privileges and obligations attached to the premises
5. `GET /api/liquor/incidents` — police and field incident reports at the location
6. `GET /api/liquor/site-evidence` — floor plans, control signage, site photos, police memos, tax clearances
7. `POST /api/sql` — additional queries when the prompt authorizes SQL access

Use `POST /api/sql` with header `X-Task-Token` only when the prompt or environment instructions provide a credential.

## Recommended Posture

Three possible outcomes:

- **`issue_restricted`**: All site evidence verified, all risks covered by controls, no unresolved verification gaps, no open incidents requiring follow-up. Issuable with standard restricted-license obligations.

- **`request_follow_up`**: One or more verification gaps exist but are resolvable through staff follow-up (missing evidence, conflicting documents, open incident follow-up). The license should not issue until gaps are closed but denial is not warranted.

- **`deny`**: Unresolvable conflicts exist, such as a confirmed same-premises basis problem with an active board order, a tax hold that cannot be cleared, or a pattern of incidents that existing controls cannot cover.

## Same-Premises Basis

`same_premises_basis_applies` is `true` when the applicant or a related entity operates or has operated at the same physical location. Check:

- Settlements referencing the same location
- Privileges tied to the location
- Incident records at the same address
- Site evidence linking applicant to prior operations at the premises

It is `false` only when there is no evidence of prior or concurrent operation at the premises by the applicant or related parties.

## Covered Risk Codes

Covered risks are incident or operational risks that are already addressed by existing controls. For each risk code seen in incidents or site concerns, check whether the current privileges or site evidence include a mitigating control:

- `AFTER_HOURS` — covered when hours-of-operation controls or late-night monitoring are in place
- `ASSAULT` — covered when security staffing or CCTV covers the service area
- `FOOD_SERVICE_GAP` — covered when current food-service privileges are active
- `MINOR_SALE` / `SALE_TO_MINOR` — covered when ID-check controls are documented
- `NOISE` — covered when noise monitoring or patio boundary controls exist
- `PUBLIC_SAFETY` — covered when security or CCTV controls cover public access areas
- `SAME_PREMISES` — covered when board orders address same-premises conditions
- `TAX_HOLD` — covered when a tax clearance is on file

Only include risk codes that are *currently covered*. Uncovered risks should not appear in this list.

For the alternate code set (train_005 style), the coverage codes expand to include:
- `PATIO_BOUNDARY` — covered when patio measurement and signage are verified
- `CAMERA_COVERAGE` — covered when camera placement covers required zones and exports are available
- `ID_CHECK` — covered when ID-check procedures are documented in privileges

## Verification Gap Codes

Verification gaps are items of evidence that are missing, conflicting, or unresolved:

- `CONTROL_SIGNAGE_CONFLICTING` — signage shown in evidence conflicts with documented controls
- `CONTROL_SIGNAGE_CURRENT_MISSING` — required signage is absent from current site evidence
- `FLOOR_PLAN_CONFLICTING` — floor plan conflicts with privilege records or other evidence
- `FLOOR_PLAN_STALE` — floor plan is older than the policy recency threshold
- `NEIGHBOR_NOTICE_MISSING` — required neighbor notification is not on file
- `OPEN_INCIDENT_FOLLOW_UP` — an incident report requires staff follow-up that is not yet closed
- `POLICE_MEMO_CONFLICTING` — police memo details differ from application or other evidence
- `SITE_PHOTO_MISSING` — required site photographs are absent
- `TAX_CLEARANCE_MISSING` — tax clearance document not on file

For the alternate code set (train_005 style), additional codes include:
- `camera_evidence_missing` — camera coverage evidence not found
- `food_service_evidence_missing` — food-service area or menu evidence not found
- `late_night_monitoring_needed` — no late-night monitoring plan documented
- `tax_hold_unresolved` — tax hold is active with no clearance
- `police_memo_identity_note` — police memo raises identity concerns

Always use only the codes listed in the answer template. Different tasks use different code sets.

## Standard vs Location-Specific Controls

**Standard obligation codes** are obligations that apply to all licenses of this class. Check license class requirements from policies and application records. Common standard obligations: `CCTV`, `DELIVERY`, `FOOD_SERVICE`, `HOURS`, `ID_CHECK`, `NOISE`, `PATIO`, `SECURITY`.

**Location-specific control codes** are controls actively tied to this specific location's privileges. They come from the privileges endpoint, not from general class requirements. Common location-specific controls overlap with the same set: `CCTV`, `DELIVERY`, `FOOD_SERVICE`, `HOURS`, `ID_CHECK`, `NOISE`, `PATIO`, `SECURITY`.

The same code can appear in both arrays if the general obligation is also an active location-specific control.

## First 90-Day Monitoring Plan

Build a monitoring plan with check items spread across three windows. Base the plan on identified verification gaps and uncovered risks:

| Window | Label | Typical Use |
|---|---|---|
| `first_30_days` | Immediate verification | Signage checks, evidence collection, police memo follow-up, ID check observation, camera export tests, food service area checks, tax clearance |
| `days_31_60` | Operational observation | After-hours visits, CCTV walkthroughs, food service checks |
| `days_61_90` | Sustained compliance | Noise log reviews, patio boundary checks, incident log reviews |

Available check codes (use only codes in the answer template):
- `after_hours_visit`, `camera_export_test`, `control_signage_recheck`, `control_signage_review`, `food_service_check`, `food_service_service_area_check`, `id_check_observation`, `incident_log_review`, `late_night_closing_visit`, `noise_log_review`, `noise_patio_boundary_check`, `patio_boundary_check`, `police_memo_follow_up`, `security_cctv_walkthrough`, `tax_clearance_check`, `tax_clearance_review`

Order items by operational sequence: verification/collection first, observation next, sustained-compliance checks last. Within the same timing window, items may appear in any logical order.

## Escalation Trigger Codes

Escalation triggers are conditions that, if observed during the monitoring period, require field staff to escalate to the board:

Choose from the template's escalation codes based on risks, gaps, and the monitoring plan. Common triggers:
- `AFTER_HOURS_VIOLATION` / `after_hours_service` — after-hours operation detected
- `BOARD_ORDER_CONFLICT` — board order conditions violated
- `CONTROL_SIGNAGE_NOT_VERIFIED` — signage cannot be confirmed
- `MAJOR_INCIDENT_REPORTED` — new serious incident during monitoring
- `REFERRED_MINOR_SALE_UNRESOLVED` — minor-sale referral not resolved
- `SECURITY_CCTV_CONTROL_FAILURE` / `missing_camera_coverage` / `footage_not_produced` — camera issues
- `TAX_HOLD_REOPENED` / `open_tax_hold_uncleared` — tax issues
- `food_service_not_available`, `noise_or_patio_breach`, `patio_boundary_failure`, `id_check_failure`, `unreported_violent_incident`, `minor_sale`

Only include triggers that are plausible given the identified gaps and risks for this application.
