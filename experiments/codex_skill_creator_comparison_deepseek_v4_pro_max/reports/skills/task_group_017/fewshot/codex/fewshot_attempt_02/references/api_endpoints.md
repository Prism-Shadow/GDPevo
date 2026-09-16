# Investigation Review Hub API Endpoints

Base URL: provided as `<TASK_ENV_BASE_URL>` in the prompt or review-scope payload. Substitute the literal placeholder with the actual base URL before making requests.

All GET endpoints return JSON arrays. The POST query endpoint returns a JSON array of rows.

## Endpoints

### GET /

Root health-check endpoint. Returns server status.

### GET /api/schema

Returns the database schema: table names, column names, and column types. Use this to confirm table and column names before writing any SQL query.

### GET /api/matters

Returns an array of matter objects.

Response fields: `matter_id`, `matter_name`, `client`, `agency`, `status`, `open_date`.

Filter by `matter_id` to isolate the target matter.

### GET /api/subpoena-categories

Returns subpoena/request categories for matters.

Response fields: `category_code`, `title`, `description`, `matter_id`.

Filter by `matter_id` to get the categories for the target matter. Category codes may be numeric (R01, R02...), alphabetic (A, B, C...), or prefixed (SEC-1, SEC-2...). Use the exact codes as returned.

### GET /api/productions

Returns production batch records.

Response fields: `production_id`, `matter_id`, `batch_label`, `date`, `doc_count`, `categories_covered`, `status`.

### GET /api/custodian-sources

Returns custodian data sources and their collection status.

Response fields: `source_id`, `matter_id`, `custodian_name`, `source_type`, `collection_status`, `notes`, `categories`.

Common `source_type` values: `email`, `laptop`, `personal_phone`, `personal_email`, `personal_messaging`, `shared_drive`, `offsite_records`, `teams_archive`, `cloud_mail_archive`.

Common `collection_status` values: `collected`, `not_collected`, `partial`, `lost`, `destroyed`, `available_archive`, `pending`.

### GET /api/documents/search

Returns documents and their review coding.

Response fields: `doc_id`, `matter_id`, `title`, `custodian`, `source_id`, `categories`, `coding` (responsive/nonresponsive/privileged/nonprivileged), `produced_status` (produced/not_produced/withheld), `notes`.

### GET /api/privilege-log

Returns privilege-log entries for withheld documents.

Response fields: `log_id`, `matter_id`, `doc_id`, `privilege_type`, `description`, `logged_date`, `third_party`, `notes`.

### GET /api/qc-findings

Returns QC review findings.

Response fields: `finding_id`, `matter_id`, `doc_id`, `issue_type`, `severity`, `status`, `description`, `recommended_action`.

Common `issue_type` values: `responsiveness_miscode`, `privilege_miscoding`, `zero_claim_contradiction`, `third_party_waiver`, `over_designation`.

### GET /api/retention-events

Returns retention and preservation events.

Response fields: `event_id`, `matter_id`, `record_type`, `event_date`, `hold_date`, `status`, `policy_section`, `retention_period_months`, `volume_count`, `volume_unit`, `affected_categories`, `notes`.

Common `status` values: `policy_destroyed_pre_hold`, `post_hold_loss`, `auto_purged`, `active_system_loss`, `should_exist_missing`, `available_archive`, `preserved_available`.

### GET /api/remediation-actions

Returns recommended or in-progress remediation actions.

Response fields: `action_id`, `matter_id`, `target_type`, `target_id`, `action_type`, `owner`, `priority`, `status`, `affected_categories`, `notes`.

### POST /api/query

Read-only SQL query endpoint. Use when GET endpoints cannot express the needed query.

- **Header**: `X-API-Key: review-key-017` (include only when the prompt supplies this key)
- **Body**: `{"sql": "<SQL statement>"}`
- **Returns**: JSON array of row objects

Refer to `GET /api/schema` for exact table and column names before writing queries. Common table names: `matters`, `subpoena_categories`, `productions`, `custodian_sources`, `documents`, `privilege_log`, `qc_findings`, `retention_events`, `remediation_actions`.
