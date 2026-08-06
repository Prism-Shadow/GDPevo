# Environment access & data model

## Reaching the service

`environment_access.md` (in the task root) holds the live connection details. Read it
each run — the base URL and token may differ per deployment. It provides:

- `GDPEVO_ENV_BASE_URL` — base URL, e.g. `http://task-env:9019/`.
- The `X-Task-Token` value required for `POST /api/sql` (e.g. `licensing-review-019`).
- The exact list of allowed endpoints. Only call those.

### GET
`GET <base>/api/<path>` → JSON array of records. Reference tables are small and
authoritative here: `/api/policies`, `/api/liquor/privileges`, `/api/renewal/rules`.

### SQL
```
POST <base>/api/sql
Header: X-Task-Token: <token>
Body:   {"query":"SELECT ... FROM <table> WHERE <id-col> LIKE '<PREFIX>-%'"}
```
Response: `{"columns":[...],"rows":[...],"row_count":N,"truncated":bool,"limit":200}`.

Constraints:
- **Row cap ~200 with truncation** — always narrow with `WHERE`, never depend on a
  bare `SELECT *` for a big table.
- **Schema introspection is blocked** (`sqlite_master`, `PRAGMA`, `information_schema`
  all rejected as "blocked SQL construct"). Use the known table names below.
- Standard `SELECT`, `WHERE ... LIKE`, `IN`, `ORDER BY`, `COUNT(*)` work. Quote string
  literals with single quotes inside the JSON body.

## Why SQL is the source of truth

The GET business feeds return only a *slice* of each table (one batch's early rows
plus unrelated distractor rows). Your specific targets are routinely missing from the
GET feed but present in SQL. **For target records (applications, bonds, insurance,
violations, incidents, site-evidence, licensees, correspondence, license-history),
query SQL filtered by your target id prefix.** Cross-check counts if unsure.

## Table names (GET path → table)

| GET path | SQL table | primary join key to a target |
|---|---|---|
| `/api/contractor/applications` | `contractor_applications` | `application_id` |
| `/api/contractor/bonds` | `contractor_bonds` | `application_id` |
| `/api/contractor/insurance` | `contractor_insurance` | `application_id` |
| `/api/contractor/license-history` | `contractor_license_history` | `license_id` = application's `prior_license_id` |
| `/api/contractor/violations` | `contractor_violations` | `related_application_id` |
| `/api/contractor/correspondence` | `contractor_correspondence` | `related_application_id` |
| `/api/contractor/inspections` | `contractor_inspections` | `related_application_id` |
| `/api/liquor/applications` | `liquor_applications` | `application_id` / `location_id` |
| `/api/liquor/settlements` | `liquor_settlements` | `location_id` |
| `/api/liquor/privileges` | `liquor_privileges` | `license_class` |
| `/api/liquor/incidents` | `liquor_incidents` | `location_id` |
| `/api/liquor/site-evidence` | `liquor_site_evidence` | `location_id` |
| `/api/alcohol/licensees` | `alcohol_licensees` | `license_no` |
| `/api/alcohol/violations` | `alcohol_violations` | `license_no` (+ predecessor via `successor_to`) |
| `/api/policies`, `/api/renewal/rules` | `policies`, `renewal_rules` | reference tables |

## Distractor patterns — exclude unless the join proves otherwise

- Id infixes `-DIS-`, `-TE2-`, `-TE5-` are **other batches**. They share your street
  addresses and mirror your numeric suffixes. Never join by address alone.
- Alcohol `AV-...-LATE` violations and any liquor/alcohol row **dated after the
  boundary/review date** are deliberate distractors — exclude them from matched sets
  (they may still be reported in the template's "excluded" summary list).
- `AL-...-OLD-...` licensees/violations belong to a *predecessor* permit. Attach them
  to a target **only** through that target's `successor_to` field (see
  `renewal_queue.md`), not by address.
- `contractor` `CV-DIS-*`, `COR-DIS-*`, `CI-DIS-*` rows *do* attach when their
  `related_application_id` equals a target id — check the field, don't assume from the
  name.

## Common field value sets (observed)

- contractor bond/insurance `status`: `active`, `pending`, `expired`, `cancelled`.
  Treat coverage currency by **date vs. review date**, not the status word alone (an
  `active` policy can be past its `expiration_date`).
- contractor inspection `result`: `pass`, `conditional`, `fail`; `finding_code`:
  `NONE`, `DOC_GAP`, `SAFETY_RECHECK`, `UNVERIFIED_SITE`.
- contractor violation `severity`: `minor`, `medium`, `serious`; `status`: `open`,
  `resolved`, `dismissed`.
- contractor correspondence `verified_by_agency`: `0`/`1`; watch `notes` for stale
  wording ("predates", "Applicant copy only; no agency confirmation").
- liquor settlement `controls_json`: `{"active":bool,"controls":[...],"expires":...,
  "review_required":bool}`. Site-evidence `status`: `verified`, `conflicting`,
  `missing`. Incident `status`: `open`, `referred`, `closed`, `dismissed`;
  `severity`: `low`, `medium`, `high`.
- alcohol violation `disposition`: `open`, `pending`, `warning`, `settled`, `paid`,
  `dismissed`; `alert_flag`: `0`/`1`; `fine_balance`: number.

## Helper
`scripts/env_query.sh` wraps both call types:
```
scripts/env_query.sh get  /api/policies
scripts/env_query.sh sql  "SELECT * FROM contractor_bonds WHERE application_id LIKE 'C-TR1-%'"
```
It reads the base URL and token from `environment_access.md`. Pipe to `jq` as needed.
