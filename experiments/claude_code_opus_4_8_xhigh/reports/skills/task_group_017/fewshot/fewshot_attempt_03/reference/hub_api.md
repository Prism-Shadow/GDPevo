# Investigation Review Hub — API & data model

The hub is a read-only service (`"state_mode":"read_only"`). Obtain the base URL and API key for
the current run from `environment_access.md` (or the matter-context payload). Send the API key
header on every request (it is required for the SQL endpoint and harmless on the GET endpoints):

```
X-API-Key: <value from environment_access.md, e.g. review-key-017>
```

## Endpoints

| Method & path                 | Returns (`{count|row_count, rows:[...]}`) | Backing table        |
|-------------------------------|-------------------------------------------|----------------------|
| `GET /`                       | service banner + endpoint list            | —                    |
| `GET /api/schema`             | table + column definitions                | —                    |
| `GET /api/matters`            | matter metadata                           | `matters`            |
| `GET /api/subpoena-categories`| request/subpoena category catalog         | `subpoena_categories`|
| `GET /api/productions`        | production batch stats                    | `production_stats`   |
| `GET /api/custodian-sources`  | custodian data sources                    | `custodian_sources`  |
| `GET /api/documents/search`   | reviewed documents                        | `review_documents`   |
| `GET /api/privilege-log`      | privilege log entries                     | `privilege_entries`  |
| `GET /api/qc-findings`        | QC findings                               | `qc_findings`        |
| `GET /api/retention-events`   | retention / destruction events            | `retention_events`   |
| `GET /api/remediation-actions`| candidate remediation actions             | `remediation_actions`|
| `POST /api/query`             | run one read-only `SELECT`                | any (SQLite)         |

Most GET endpoints accept `?matter_id=<M>`; `documents/search` also accepts `&category_code=<C>`.
Responses can be large — filter server-side or with the SQL endpoint.

## SQL endpoint

```
POST /api/query
Content-Type: application/json
{ "sql": "SELECT ... WHERE matter_id = ?", "params": ["MTR-...."] }
```

Returns `{columns, row_count, rows, truncated}`. **Only `SELECT` is permitted** (any write returns
`{"error":"only SELECT statements are permitted"}`). Positional `?` params are supported. This is
the fastest way to filter (e.g. pull non-noise remediation targets, or count rows).

## Tables & columns (from `/api/schema`)

- **matters**: `matter_id, name, agency, investigation_type, issued_date, hold_date, lead_partner,
  description, status`
- **subpoena_categories**: `matter_id, category_code, title, date_start, date_end, request_text,
  topic_tags`
- **production_stats**: `matter_id, batch_id, batch_date, category_code, produced_count,
  withheld_count, responsive_count, nonresponsive_count, status, zero_claim_reason, notes`
- **custodian_sources**: `source_id, matter_id, custodian_name, role, source_type, source_label,
  status, event_date, post_hold, category_impacts, issue_tags, notes`
- **review_documents**: `doc_id, matter_id, title, doc_date, custodian_name, source_system,
  category_code, responsiveness, privilege_status, produced_status, issue_tags, summary`
- **privilege_entries**: `entry_id, matter_id, category_code, custodian_name, doc_count,
  withheld_count, logged_count, issue_type, third_party, notes`
- **qc_findings**: `finding_id, matter_id, batch_id, issue_type, doc_count, affected_category,
  source_ref, severity, notes`
- **retention_events**: `event_id, matter_id, record_type, event_date, hold_date, policy_section,
  retention_period_months, volume_count, volume_unit, status, affected_categories, source_ref,
  notes`
- **remediation_actions**: `action_id, matter_id, action_type, priority, severity, owner,
  target_ref, due_days, description`

Notes:
- `category_impacts`, `affected_categories`, `issue_tags`, `topic_tags` come back as arrays via the
  GET endpoints (they are stored as text; via raw SQL you may get the serialized form).
- `post_hold` is `1` when the source's loss/collection issue post-dates the legal hold.
- Record-id conventions: material anchor records use **descriptive slug ids** (`SRC-<NAME>-PHONE`,
  `PRIV-<M>-LOG-GAP`, `RET-<M>-BOX-POST`, `QC-<M>-ZERO-CLAIM`, `DOC-<M>-<TOPIC>`). Distractor
  records use **sequential ids** of the form `TYPE-<MATTERTOKEN>-NNN` (e.g. `SRC-SENTINELGJ-007`,
  `PRIV-NORTHBAYSE-005`). See `materiality_and_mapping.md`.

## Cross-references between tables

- `qc_findings.source_ref` → a `review_documents.doc_id` (the document the finding is about).
- `retention_events.source_ref` → a records-schedule label (not always a hub id); the `notes` may
  name linked documents or the unrecovered volume.
- `remediation_actions.target_ref` → the id of the anchor record it remediates (a source, event,
  privilege entry, QC finding, or a bare category code for NOISE rows).
- `privilege_entries` with `issue_type = incomplete_log` carry `withheld_count`/`logged_count`;
  unlogged = withheld − logged.
