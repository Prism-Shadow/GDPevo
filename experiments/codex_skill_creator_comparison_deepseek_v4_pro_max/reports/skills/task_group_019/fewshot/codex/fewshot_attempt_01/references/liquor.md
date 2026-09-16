# Restricted Liquor License Staff Package

## Endpoint Catalog

| Endpoint | Returns | Key Fields |
|---|---|---|
| `GET /api/policies` | Current policy baseline | Control thresholds, hotel-lounge rules, food-service requirements |
| `GET /api/liquor/applications` | Application records | `application_id`, location, premise type, license class, applicant |
| `GET /api/liquor/settlements` | Settlement agreements | `application_id`, settlement terms, control obligations, dates |
| `GET /api/liquor/privileges` | Privilege grants | `application_id`, privilege type, conditions, effective dates |
| `GET /api/liquor/incidents` | Incident reports | `application_id`, location, incident type, date, status |
| `GET /api/liquor/site-evidence` | Site evidence files | `application_id`, file type (camera, food_service, floor_plan, signage, police_memo, site_photo, neighbor_notice, tax_clearance), date, status |
| `POST /api/sql` | SQL queries | Requires `X-Task-Token` header |

## Cross-Referencing Rules

Always pull `/api/policies` first to understand the current risk threshold and control expectations.

### Same-Premises Basis

Check whether the application relates to an existing license at the same location. Pull applications and look for prior license records at the same location or with a `same_premises` flag. Set `same_premises_basis_applies: true` when there is a prior license history at the same address.

### Covered Risk Codes

Map incident types and site-evidence findings to the template's allowed `covered_risk_codes`:

- **AFTER_HOURS** — Incident or evidence of after-hours service.
- **ASSAULT** — Incident report of assault at the premises.
- **MINOR_SALE / SALE_TO_MINOR** — Incident or settlement reference to sale to minor.
- **NOISE** — Noise complaint incident or settlement reference.
- **PUBLIC_SAFETY** — Police memo or incident referencing public safety concern.
- **FOOD_SERVICE_GAP** — Site evidence or application shows insufficient food-service documentation.
- **SAME_PREMISES** — Prior license history at the same location exists.
- **TAX_HOLD** — Tax clearance missing or unresolved.

### Verification Gap Codes

Check site-evidence files for gaps:

- **CONTROL_SIGNAGE_CONFLICTING** — Signage evidence conflicts with application claims.
- **CONTROL_SIGNAGE_CURRENT_MISSING** — No current signage documentation on file.
- **FLOOR_PLAN_CONFLICTING** — Floor plan does not match application description.
- **FLOOR_PLAN_STALE** — Floor plan date is significantly older than the application.
- **NEIGHBOR_NOTICE_MISSING** — No neighbor-notice documentation.
- **OPEN_INCIDENT_FOLLOW_UP** — Incident with open status needing follow-up.
- **POLICE_MEMO_CONFLICTING** — Police memo conflicts with application or site evidence.
- **SITE_PHOTO_MISSING** — No site photos on file.
- **TAX_CLEARANCE_MISSING** — No tax clearance document.

### Standard vs. Location-Specific Controls

- **Standard obligations**: Obligations that apply to all licenses of this class (from policies, settlements, or privilege conditions). Include only codes from the template's allowed list: CCTV, DELIVERY, FOOD_SERVICE, HOURS, ID_CHECK, NOISE, PATIO, SECURITY.
- **Location-specific controls**: Controls tied to this specific location via settlements, site evidence, or police memos. Use the same code set but only include controls specific to this location.

### First 90-Day Plan

Build a plan from the template's allowed `check_code` and `timing` values. Sequence checks operationally:

- **First 30 days**: Items that verify basic compliance (signage, ID checks, police memo follow-ups, security/cctv walkthroughs).
- **Days 31-60**: Mid-period checks (after-hours visits, food service checks).
- **Days 61-90**: Late-period checks that need operational history (noise log review, patio boundary checks, tax clearance).

Only include checks relevant to the risks and gaps found. Do not include checks for risks already fully covered by existing controls.

### Escalation Triggers

Map risks and gaps to the template's allowed escalation codes. A trigger is warranted when a verification gap or uncovered risk could lead to a compliance failure:

- **AFTER_HOURS_VIOLATION** — After-hours risk with no current control.
- **BOARD_ORDER_CONFLICT** — Settlement or privilege condition that conflicts with board orders.
- **CONTROL_SIGNAGE_NOT_VERIFIED** — Signage gap.
- **MAJOR_INCIDENT_REPORTED** — Open incident with serious classification.
- **REFERRED_MINOR_SALE_UNRESOLVED** — Minor sale incident without resolution.
- **SECURITY_CCTV_CONTROL_FAILURE** — CCTV evidence missing and security risk present.
- **TAX_HOLD_REOPENED** — Tax clearance gap.

### Recommended Posture

1. **deny** — Unresolvable conflicts (board order conflict, criminal history, major unresolved incident with no path to mitigation).
2. **request_follow_up** — Verification gaps exist that can be resolved with additional evidence or follow-up checks, or risks are present that need controls before issuance.
3. **issue_restricted** — All risks are covered by current controls, all verification items are complete, and a reasonable 90-day plan covers residual monitoring.
