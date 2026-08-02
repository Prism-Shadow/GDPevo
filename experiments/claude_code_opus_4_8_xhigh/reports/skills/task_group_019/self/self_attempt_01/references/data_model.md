# Data model reference

The licensing environment exposes read-only endpoints plus a SQL endpoint over
the same tables. Field names and code sets below were observed from the live
service; **re-verify at runtime** (a probe of `/api/policies` and one row of
each table you need confirms the shape quickly). Treat the enumerated field
values as "what shows up in practice," not as the answer vocabulary — the answer
vocabulary always comes from the task's `answer_template.json`.

## Access

- `GET <base>/api/<path>` → JSON array of rows.
- `POST <base>/api/sql`, header `X-Task-Token: <token from environment_access.md>`,
  body `{"query": "SELECT ..."}`.
  - SELECT-only. `PRAGMA` and `sqlite_master` are blocked constructs.
  - Response: `{columns, rows, row_count, limit, truncated}`; default `LIMIT 200`.
- SQL table name = endpoint path with `/api/` stripped and `-`/`/` → `_`:
  - `contractor/applications` → `contractor_applications`
  - `contractor/license-history` → `contractor_license_history`
  - `liquor/site-evidence` → `liquor_site_evidence`
  - `alcohol/violations` → `alcohol_violations`
  - `renewal/rules` → `renewal_rules`, `policies` → `policies`, etc.

## policies  (families A & B; parse `details_json`)

Columns: `policy_id, agency, family, effective_date, title, citation, rule_code, details_json`.

- `family` ∈ {contractor, liquor, renewal}.
- **Contractor rules** — one per trade+class; `rule_code` encodes the pair:
  `CON-ELE-ClassA` (Electrical/Class A), `CON-PLU-ClassB` (Plumbing/Class B),
  `CON-HVA-ClassB` (HVAC/Class B), `CON-GEN-ClassA` (General Building/Class A),
  `CON-ROO-Limited` (Roofing/Limited), `CON-SOL-Specialty` (Solar/Specialty).
  `details_json`: `minimum_bond`, `minimum_insurance`,
  `minimum_years_experience`, `required_endorsement` (may be null),
  `serious_open_violation_blocks`.
  Not every trade+class combination has a rule — if none matches, only universal
  checks apply.
- **Contractor legacy baseline** `CON-LEGACY` / `POL-CON-LEGACY`:
  `endorsement_required_for_specialty`, `minimum_bond_reduction`,
  `use_for_prior_rule_comparison` → used to compute `policy_impacted`
  (a deficiency that exists only under the current standard, not the legacy one).
- **Liquor** policies: `LIQ-SETTLEMENT-CONTROLS` (`current_site_evidence_required`,
  `same_premises_history_matters`, `standard_privileges_separate_from_controls`)
  and `LIQ-RISK-MATRIX` (`major_incidents_trigger_board_review`).

## Contractor tables (family A)

- `contractor_applications`: `application_id, applicant_name, trade, county,
  submitted_date, years_experience, endorsement_status(verified|pending|missing|
  not_required), prior_license_id, requested_class(Class A|Class B|Limited|
  Specialty), self_disclosed_issue`.
- `contractor_bonds`: `bond_id, application_id, amount, status(active|cancelled|
  expired), effective_date, cancel_date, source_date, surety`.
- `contractor_insurance`: `insurance_id, application_id, amount, status(active|
  expired|pending), expiration_date, verified_date, insurer`.
- `contractor_license_history`: `license_id, applicant_name, trade, status,
  status_date, notes`. (Look for suspension/discipline history here.)
- `contractor_violations`: `violation_id, license_id, related_application_id,
  severity(minor|medium|serious), status(open|resolved|dismissed), theme,
  violation_date, resolved_date`.
- `contractor_correspondence`: `correspondence_id, related_application_id,
  subject, assertion_type(endorsement_status|bond_amount|prior_license_match|
  experience_update|discipline_response|insurance_amount), assertion_value,
  received_date, verified_by_agency(0|1), notes`.
- `contractor_inspections`: `inspection_id, related_application_id, finding_code
  (NONE|DOC_GAP|UNVERIFIED_SITE|SAFETY_RECHECK|WRONG_TRADE), result(pass|fail|
  conditional|no access), inspection_date, notes`.

**Contractor joins:** applications↔bonds/insurance on `application_id`;
applications.`prior_license_id`↔license_history/violations `license_id`;
violations/correspondence/inspections also carry `related_application_id`.
Match violations by both `license_id` and `related_application_id`.

## Liquor tables (family B)

- `liquor_applications`: `application_id, applicant_name, dba, address, agency,
  license_class(Tavern|Restaurant|BeerWine|Package), location_id,
  requested_posture(new|transfer|renewal_with_controls|settlement_review),
  submitted_date`.
- `liquor_settlements`: `settlement_id, location_id, basis_code(NOISE|
  SAME_PREMISES|PUBLIC_SAFETY|SALE_TO_MINOR), settlement_type(warning|restricted|
  historic refusal|conditional approval), source_name, effective_date,
  controls_json`. `controls_json` = `{active, controls[], expires,
  review_required}`; `controls` drawn from {ID_CHECK, HOURS, SECURITY, CCTV,
  NOISE, PATIO, FOOD_SERVICE}.
- `liquor_privileges`: `privilege_id, license_class, obligation_code(ID_CHECK|
  HOURS|SECURITY|CCTV|NOISE|FOOD_SERVICE|PATIO|DELIVERY), standard_required(0|1),
  description`. The ordinary obligations for a class are those with
  `standard_required=1`.
- `liquor_incidents`: `incident_id, location_id, risk_code(ASSAULT|MINOR_SALE|
  TAX_HOLD|NOISE|AFTER_HOURS|FOOD_SERVICE_GAP), severity(low|medium|high),
  status(referred|open|dismissed|closed), source_name, incident_date`.
- `liquor_site_evidence`: `evidence_id, location_id, evidence_code(SITE_PHOTO|
  NEIGHBOR_NOTICE|CONTROL_SIGNAGE|POLICE_MEMO|FLOOR_PLAN|TAX_CLEARANCE),
  status(verified|conflicting|stale|missing), evidence_date, notes`.

**Liquor joins:** applications↔settlements/incidents/site_evidence on
`location_id`; applications.`license_class`↔privileges.`license_class`.

## Alcohol / renewal tables (family C)

- `alcohol_licensees`: `license_no, facility_name, address, agency, active(0|1),
  channel_type(bar|restaurant|event|convenience|grocery), location_id,
  successor_to(nullable)`.
- `alcohol_violations`: `violation_id, license_no, facility_name, address,
  violation_date, severity(minor|medium|serious), theme(noise|missing posting|
  unpaid fine|tax hold|sale to minor|late renewal|after hours),
  disposition(warning|settled|open|pending|paid|dismissed), fine_balance,
  alert_flag(0|1), source_name(renewal_case_export|post_boundary_feed|
  legacy_feed|public_feed|legacy_successor_feed)`.
- `renewal_rules`: `rule_id, agency, title, effective_date, release_boundary,
  details_json`. `details_json`: `use_violations_on_or_before` (= the boundary
  date, filter on `violation_date`), `alert_flag_requires_manual_review`,
  `late_rows_are_distractors`, `unpaid_fines_require_hold`.
  Select the rule whose `release_boundary` matches the prompt's boundary.

**Alcohol joins/matching:** violations↔licensee by `license_no` (exact match →
confidence `exact`); fall back to `address` (→ `close_address`); a licensee with
non-null `successor_to` is a successor match (→ `uncertain`).
**The boundary filters on `violation_date`, never on `source_name`.**
