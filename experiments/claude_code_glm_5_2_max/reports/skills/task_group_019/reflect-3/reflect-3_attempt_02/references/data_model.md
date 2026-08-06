# Data model and endpoints

The shared environment serves one JSON array per endpoint and one SQL table per endpoint
(table name = endpoint path with `/` → `_`, e.g. `/api/contractor/license-history` →
`contractor_license_history`). Every endpoint returns the **full** dataset for that
resource, including distractor records (see `distractors.md`) — you filter locally to the
target ids named in the prompt.

## Contractor family

`GET /api/policies` → policy rows; contractor policies carry a `details_json` with
`minimum_bond`, `minimum_insurance`, `minimum_years_experience`, `required_endorsement`
(`null` when the class needs no endorsement), and `serious_open_violation_blocks: true`.
A `CON-LEGACY` / prior-baseline policy carries `endorsement_required_for_specialty: false`
and `minimum_bond_reduction`, used to decide the `policy_impacted` flag.

`GET /api/contractor/applications` → `application_id, applicant_name, trade, county,
submitted_date, years_experience, endorsement_status, prior_license_id, requested_class,
self_disclosed_issue`. `endorsement_status` is one of `verified / pending / missing /
not_required`. `requested_class` + `trade` together select the applicable policy.

`GET /api/contractor/bonds` → `bond_id, application_id, amount, status, effective_date,
cancel_date, source_date, surety`. `status` ∈ `active / cancelled / expired`. Multiple
bond rows per application (current + historical); pick the active one.

`GET /api/contractor/insurance` → `insurance_id, application_id, amount, status,
verified_date, expiration_date, insurer`. `status` ∈ `active / pending / expired`.

`GET /api/contractor/license-history` → `license_id, applicant_name, status, status_date,
trade, notes`. `status` ∈ `active / expired / suspended`. Join by `prior_license_id`.

`GET /api/contractor/violations` → `violation_id, related_application_id, license_id,
violation_date, severity, theme, status, resolved_date`. `severity` ∈ `minor / medium /
serious`; `status` ∈ `open / resolved / dismissed`. Only `status == "open"` matters for an
eligibility block.

`GET /api/contractor/correspondence` → `correspondence_id, related_application_id,
received_date, subject, assertion_type, assertion_value, verified_by_agency (0/1), notes`.
Used for the `stale_or_unverified_correspondence_ids` summary list.

`GET /api/contractor/inspections` → `inspection_id, related_application_id,
inspection_date, result, finding_code, notes`. `finding_code` ∈
`NONE / DOC_GAP / SAFETY_RECHECK / UNVERIFIED_SITE`; `result` ∈ `pass / fail / conditional`.

## Liquor family

`GET /api/liquor/applications` → `application_id, agency, applicant_name, dba, address,
license_class, location_id, submitted_date, requested_posture`. `license_class` ∈
`Tavern / Restaurant / BeerWine / Package`.

`GET /api/liquor/settlements` → `settlement_id, location_id, effective_date,
settlement_type, basis_code, controls_json, source_name`. `controls_json` is a JSON string
with `active (bool), controls (list), expires (YYYY-MM-DD), review_required (bool)`.
**Only `active: true` settlements supply current location controls.** `basis_code` ∈
`NOISE / SAME_PREMISES / PUBLIC_SAFETY / SALE_TO_MINOR`.

`GET /api/liquor/privileges` → `privilege_id, license_class, obligation_code, description,
standard_required (0/1)`. The obligations with `standard_required == 1` for the
application's license class are the **standard obligations** for that class.

`GET /api/liquor/incidents` → `incident_id, location_id, incident_date, risk_code,
severity, status, source_name`. `risk_code` ∈ `AFTER_HOURS / ASSAULT / MINOR_SALE / NOISE /
PUBLIC_SAFETY / SAME_PREMISES / TAX_HOLD / FOOD_SERVICE_GAP / SALE_TO_MINOR`; `status` ∈
`open / referred / closed / dismissed`.

`GET /api/liquor/site-evidence` → `evidence_id, location_id, evidence_date, evidence_code,
status, notes`. `evidence_code` ∈ `CONTROL_SIGNAGE / POLICE_MEMO / FLOOR_PLAN / ...`;
`status` ∈ `verified / conflicting / missing`. Evidence statuses drive the verification-gap
codes.

## Alcohol renewal family

`GET /api/alcohol/licensees` → `license_no, agency, facility_name, address, channel_type,
active (0/1), location_id, successor_to`. `successor_to` points to a prior (old) license
number whose violations may carry forward — those matches are marked `uncertain`.

`GET /api/alcohol/violations` → `violation_id, license_no, facility_name, address,
violation_date, theme, severity, disposition, fine_balance, alert_flag (0/1), source_name`.
`disposition` ∈ `open / pending / warning / paid / settled`. `source_name` flags feeds:
`post_boundary_feed` rows are post-boundary and **must be excluded** (the `*-LATE` rows);
`legacy_successor_feed` rows attach to old/successor permits.

`GET /api/renewal/rules` → `rule_id, agency, effective_date, release_boundary, title,
details_json`. `details_json` carries `alert_flag_requires_manual_review`,
`late_rows_are_distractors`, `unpaid_fines_require_hold`, and `use_violations_on_or_before`
(the boundary date). The prompt names the active boundary.

## SQL convenience

`POST /api/sql` with body `{"query": "<SELECT ...>"}` (and any required auth header).
Returns `{columns, rows, row_count, truncated}`. Allowed: `SELECT`, joins, subqueries,
aggregates, `WHERE`, `ORDER BY`, `LIMIT`. Blocked: `sqlite_master`, `PRAGMA`, `ATTACH`,
and any non-`SELECT` statement. Default limit ~200 rows; raise with `LIMIT` or filter by id
when you need a full target slice.
