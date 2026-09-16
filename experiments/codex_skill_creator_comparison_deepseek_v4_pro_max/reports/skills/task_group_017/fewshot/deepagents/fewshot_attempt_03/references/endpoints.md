# Investigation Review Hub – Endpoint Reference

## Base URL
The base URL is always provided in the task prompt or request context as
`<TASK_ENV_BASE_URL>`. It is a read-only REST API returning JSON.

## Endpoints

### GET /
Landing page listing available endpoints and confirming service status.

### GET /api/schema
Returns the complete table schema: table names, column names, and column types.
Call this first to understand the data model before making business queries.

Tables:
- `matters` – matter_id, name, agency, investigation_type, issued_date, hold_date, lead_partner, description, status
- `subpoena_categories` – matter_id, category_code, title, date_start, date_end, request_text, topic_tags
- `production_stats` – matter_id, batch_id, batch_date, category_code, produced_count, withheld_count, responsive_count, nonresponsive_count, status, zero_claim_reason, notes
- `custodian_sources` – source_id, matter_id, custodian_name, role, source_type, source_label, status, event_date, post_hold, category_impacts, issue_tags, notes
- `review_documents` – doc_id, matter_id, title, doc_date, custodian_name, source_system, category_code, responsiveness, privilege_status, produced_status, issue_tags, summary
- `privilege_entries` – entry_id, matter_id, category_code, custodian_name, doc_count, withheld_count, logged_count, issue_type, third_party, notes
- `qc_findings` – finding_id, matter_id, batch_id, issue_type, doc_count, affected_category, source_ref, severity, notes
- `retention_events` – event_id, matter_id, record_type, event_date, hold_date, policy_section, retention_period_months, volume_count, volume_unit, status, affected_categories, source_ref, notes
- `remediation_actions` – action_id, matter_id, action_type, priority, severity, owner, target_ref, due_days, description

### GET /api/matters
Returns all matter records. Filter by `matter_id` from the task context.

### GET /api/subpoena-categories
Returns all request categories across all matters. Filter by `matter_id`.
`category_code` is the stable identifier. `topic_tags` is a JSON array.

### GET /api/productions
Returns production batch statistics with `batch_id`, `category_code`,
`produced_count`, `withheld_count`, `responsive_count`, `nonresponsive_count`,
`status`, `zero_claim_reason`. Non-ready statuses include
`zero_claim_contradicted`, `supplement_pending`, `rolling_review`. A
`zero_claim_reason` with zero produced does not guarantee no gap; check
`status` and cross-reference QC findings.

### GET /api/custodian-sources
Returns custodian source records keyed by `source_id`. `category_impacts` is a
JSON string array. Issue tags: `archive_available`, `deleted_channel`,
`personal_phone`, `personal_email`, `lost`, `not_collected`. `post_hold` is
integer 0/1.

### GET /api/documents/search
Returns review documents keyed by `doc_id` with `category_code`,
`responsiveness`, `privilege_status`, `produced_status`, `issue_tags`, `summary`.

### GET /api/privilege-log
Returns privilege log entries keyed by `entry_id`. `issue_type`:
`incomplete_log`, `third_party_waiver`, `over_designated`. `third_party` is
0/1 integer. Compute `unlogged_count = withheld_count - logged_count`.

### GET /api/qc-findings
Returns QC findings keyed by `finding_id`. `issue_type`:
`zero_claim_contradiction`, `family_break`, `date_normalization`, `near_duplicate`,
`responsive_miscoding`, `privilege_miscoding`. `source_ref` may be
comma-separated doc IDs. `severity`: `critical`, `high`, `medium`, `low`.

### GET /api/retention-events
Returns retention events keyed by `event_id`. `affected_categories` is a JSON
string array. `status` values: `policy_destroyed_pre_hold`, `post_hold_loss`,
`auto_purged`, `active_system_loss`, `should_exist_missing`, `available_archive`.
`volume_unit`: `boxes`, `days`, `records`, `reports`, `exports`.

### GET /api/remediation-actions
Returns pre-computed actions keyed by `action_id`. Use as cross-reference, not
as the sole source for your action plan.

### POST /api/query
SQL access. Header: `X-API-Key: review-key-017`. Body: `{"query": "SELECT ..."}`.
Always scope with `WHERE matter_id = '...'`. Use for joins or aggregations.

## Data Model Notes

- `category_impacts` / `affected_categories` are JSON string arrays in GET
  responses. In SQL queries use `LIKE '%"CODE"%'` pattern matching or filter
  post-query.
- `source_ref` may contain comma-separated IDs from other hub records.
- Always filter all hub data by the task's `matter_id`.
