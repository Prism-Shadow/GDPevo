# Environment access & data model

## Connecting

Read `environment_access.md` for the current task. It defines:

- `GDPEVO_ENV_BASE_URL` (all requests are relative to it).
- The token for SQL: `POST /api/sql` requires header `X-Task-Token: <token>`.
- The list of allowed endpoints (a subset may be listed per task).

## GET endpoints (⚠ 200-row cap)

Each `GET /api/...` returns a JSON **array** of rows. The list is **capped at 200
rows and truncated with no error**. Small target tables (a single batch's
applications) are fine, but shared tables (bonds, insurance, violations,
correspondence, license-history) routinely exceed 200 rows, so a plain GET can
drop rows for your targets and silently corrupt the answer.

**Rule of thumb:** use GET only for small/whole tables you know are < 200 rows
(e.g. `/api/policies`, `/api/renewal/rules`, one location's settlements). For
anything that can be large, use filtered SQL.

## POST /api/sql

Request body: `{"query": "<SQL SELECT>"}` (note the key is `query`).
Header: `X-Task-Token: <token>`. Response:
`{"columns":[...], "rows":[{...}], "row_count":N, "truncated":bool, "limit":200}`.

Notes:
- SQL results are **also capped at 200 rows** — always add a `WHERE` clause that
  restricts to your target ids so the full result fits (check `truncated`).
- Some constructs are blocked (e.g. `sqlite_master`, certain keywords); stick to
  plain `SELECT ... FROM <table> WHERE ... ORDER BY ...` with `LIKE` / `IN`.
- Quote string literals with single quotes inside the JSON, e.g.
  `{"query":"SELECT * FROM contractor_bonds WHERE application_id IN ('C-X-001','C-X-002')"}`.

### Table names (mirror the endpoints)

| Endpoint | Table |
| --- | --- |
| `/api/policies` | `policies` |
| `/api/contractor/applications` | `contractor_applications` |
| `/api/contractor/bonds` | `contractor_bonds` |
| `/api/contractor/insurance` | `contractor_insurance` |
| `/api/contractor/license-history` | `contractor_license_history` |
| `/api/contractor/violations` | `contractor_violations` |
| `/api/contractor/correspondence` | `contractor_correspondence` |
| `/api/contractor/inspections` | `contractor_inspections` |
| `/api/liquor/applications` | `liquor_applications` |
| `/api/liquor/settlements` | `liquor_settlements` |
| `/api/liquor/privileges` | `liquor_privileges` |
| `/api/liquor/incidents` | `liquor_incidents` |
| `/api/liquor/site-evidence` | `liquor_site_evidence` |
| `/api/alcohol/licensees` | `alcohol_licensees` |
| `/api/alcohol/violations` | `alcohol_violations` |
| `/api/renewal/rules` | `renewal_rules` |

## Join keys

**Contractor** (target = `application_id`s):
- `contractor_applications.application_id` is the anchor. Fields include
  `trade`, `requested_class`, `years_experience`, `endorsement_status`,
  `prior_license_id`.
- `contractor_bonds.application_id`, `contractor_insurance.application_id`.
- `contractor_violations.related_application_id`,
  `contractor_correspondence.related_application_id`,
  `contractor_inspections.related_application_id`.
- `contractor_license_history.license_id` == `applications.prior_license_id`.

**Liquor** (target = one `application_id` + `location_id`):
- `liquor_applications.location_id` is the anchor; also has `license_class`.
- `liquor_settlements.location_id`, `liquor_incidents.location_id`,
  `liquor_site_evidence.location_id`.
- `liquor_privileges.license_class` == `applications.license_class`.

**Alcohol / renewal** (target = `license_no`s + boundary date):
- `alcohol_licensees.license_no` is the anchor; `successor_to` points at a
  predecessor `license_no`; `address` supports address matching.
- `alcohol_violations.license_no` (also has `address`, `theme`, `severity`,
  `disposition`, `fine_balance`, `alert_flag`, `violation_date`).
- `renewal_rules.release_boundary` and `renewal_rules.details_json`.

## Parsing `policies`

`policies` rows have `family` (`contractor` | `liquor` | `renewal`), `rule_code`,
`effective_date`, and `details_json` (a JSON string — parse it).

- Contractor policy `rule_code` is `CON-<TRADE3>-<CLASS>` where TRADE3 is the
  3-letter trade code (Electrical→`ELE`, Plumbing→`PLU`, HVAC→`HVA`,
  General Building→`GEN`, Roofing→`ROO`, Solar→`SOL`) and CLASS is the class
  token (`Class A`→`ClassA`, `Class B`→`ClassB`, `Limited`, `Specialty`).
  `details_json` carries `minimum_bond`, `minimum_insurance`,
  `minimum_years_experience`, `required_endorsement`, `serious_open_violation_blocks`.
- `CON-LEGACY` is the **prior baseline** used for the `policy_impacted` comparison
  (`minimum_bond_reduction`, `endorsement_required_for_specialty`).
- Liquor policies carry review flags (same-premises history matters, major
  incidents trigger board review).
- Renewal rule carries `release_boundary` and `details_json`
  (`use_violations_on_or_before`, `alert_flag_requires_manual_review`,
  `unpaid_fines_require_hold`, `late_rows_are_distractors`).

Always read thresholds from the live `policies` / `renewal_rules` data rather than
assuming fixed numbers — they may differ per task.
