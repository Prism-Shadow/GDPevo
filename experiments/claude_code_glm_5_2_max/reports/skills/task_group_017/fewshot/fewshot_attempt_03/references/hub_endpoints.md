# Investigation Review Hub — Endpoints & SQL

All access is over the network only. Read `environment_access.md` (repo root) for the base
URL, API key, and allowed endpoint list. The values below are the reusable shape; confirm
the base URL and key from `environment_access.md` and the task's context payload each run.

## Base URL & auth

- Base URL: given in `environment_access.md` (e.g. `http://task-env:9017/`).
- The read-only SQL endpoint requires header `X-API-Key: <key from environment_access.md>`.
- The nine GET endpoints are read-only and do not require the API key (they accept query
  filters). Confirm per `environment_access.md`.

## GET endpoints (one per hub table)

Each GET endpoint returns `{"count": N, "rows": [...]}` and accepts a `matter_id` query
parameter to scope to the matter under review. Always filter by the task's `matter_id`.

| Endpoint                      | Hub table            | Use for |
|-------------------------------|----------------------|---------|
| `GET /api/matters`            | `matters`            | Matter metadata: agency, investigation type, issued/hold dates, status. |
| `GET /api/subpoena-categories`| `subpoena_categories`| Request category codes + titles (the category frame). |
| `GET /api/productions`        | `production_stats`   | Per-batch production counts: produced/withheld/responsive/nonresponsive, `status`, `zero_claim_reason`. |
| `GET /api/custodian-sources`  | `custodian_sources`  | Custodian sources: `source_type`, `status`, `event_date`, `post_hold`, `category_impacts`, `issue_tags`. |
| `GET /api/documents/search`   | `review_documents`   | Review docs: `responsiveness`, `privilege_status`, `produced_status`, `issue_tags`, category. |
| `GET /api/privilege-log`      | `privilege_entries`  | Privilege log entries: `doc_count`, `withheld_count`, `logged_count`, `issue_type`, `third_party`. |
| `GET /api/qc-findings`        | `qc_findings`        | QC findings: `issue_type`, `doc_count`, `affected_category`, `source_ref`, `severity`. |
| `GET /api/retention-events`   | `retention_events`   | Retention/preservation events: status, risk, dates, hold date, policy section, volume. |
| `GET /api/remediation-actions`| `remediation_actions`| Remediation candidates / available archives. |

## SQL endpoint

`POST /api/query` — read-only SQL over the same nine tables.

- Header: `X-API-Key: <key>`, `Content-Type: application/json`.
- Body: `{"sql": "SELECT ... FROM <table> WHERE matter_id = '...' "}`.
  - The body field is **`sql`** (a string), not `query`.
- Response: `{"columns": [...], "row_count": N, "rows": [...], "truncated": bool}`.
- Use it for joins and aggregates (e.g. privilege withheld/logged totals by category,
  counting sources by status). For simple whole-table reads, prefer the GET endpoints.
- Watch `truncated`: if true, page or filter more narrowly.

## Tables & key columns

- `matters`: `matter_id`, `agency`, `investigation_type`, `issued_date`, `hold_date`, `status`.
- `subpoena_categories`: `matter_id`, `category_code`, `title`, `date_start`, `date_end`, `request_text`.
- `production_stats`: `matter_id`, `batch_id`, `batch_date`, `category_code`, `produced_count`,
  `withheld_count`, `responsive_count`, `nonresponsive_count`, `status`, `zero_claim_reason`.
- `custodian_sources`: `source_id`, `matter_id`, `custodian_name`, `role`, `source_type`,
  `source_label`, `status`, `event_date`, `post_hold`, `category_impacts`, `issue_tags`.
- `review_documents`: `doc_id`, `matter_id`, `title`, `doc_date`, `custodian_name`,
  `source_system`, `category_code`, `responsiveness`, `privilege_status`, `produced_status`, `issue_tags`.
- `privilege_entries`: `entry_id`, `matter_id`, `category_code`, `custodian_name`, `doc_count`,
  `withheld_count`, `logged_count`, `issue_type`, `third_party` (0/1).
- `qc_findings`: `finding_id`, `matter_id`, `batch_id`, `issue_type`, `doc_count`,
  `affected_category`, `source_ref`, `severity`.
- `retention_events`: `event_id`, `matter_id`, `record_type`, `event_date`, … status/risk/volume/policy fields.
- `remediation_actions`: remediation candidates and available archive sources.

## Stable ID families (use exactly as in the hub)

`matter_id`, `category_code`, `source_id`, `doc_id`, `entry_id`, `finding_id`, `event_id`,
`batch_id`, plus any remediation/archive IDs. Never rename, reformat, or synthesize these.
