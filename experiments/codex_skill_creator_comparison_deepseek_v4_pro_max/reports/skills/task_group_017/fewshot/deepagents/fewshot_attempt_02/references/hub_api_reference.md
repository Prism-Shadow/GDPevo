# Hub API Reference

## Access

All endpoints are under the base URL provided as `<TASK_ENV_BASE_URL>` in task payloads. Replace the placeholder before calling any endpoint.

No authentication is required for GET endpoints. The SQL query endpoint requires an `X-API-Key` header whose value is read from task payloads — typically `query_api_key`, `query_header.value`, or similar fields.

## Endpoint Catalog

### GET /

Returns available endpoint paths and hub metadata as JSON. Call this first to confirm which endpoints are live.

### GET /api/schema

Returns the full data schema: tables, columns, types, and relationships. Call this second to understand field names before writing queries or interpreting endpoint responses.

### GET /api/matters

Returns all matter records as a JSON array. Each record includes `matter_id`, `matter_name`, `client`, `agency`, `case_type`, and related metadata. Filter by `matter_id` to find the current matter.

### GET /api/subpoena-categories

Returns request/subpoena categories as a JSON array. Each record includes `category_code`, `category_title`, `matter_id`, and optional `description`. Category codes appear in answer templates (e.g., `R07`, `R11`, `SEC-1`, `SEC-C`, `A`, `B`).

### GET /api/productions

Returns production records as a JSON array. Each record includes `production_id`, `matter_id`, `production_label`, `production_date`, `category_codes` (list), `document_count`, and `status`.

### GET /api/custodian-sources

Returns custodian source records as a JSON array. Each record includes `source_id`, `matter_id`, `custodian_name`, `source_type`, `source_status`, `category_codes`, `collection_status`, and optional `notes`. Source types include email, laptop, shared_drive, personal_phone, personal_email, personal_messaging, teams_archive, offsite_records, and others.

Source status values follow the template enums (e.g., `lost`, `not_collected`, `partial`, `collected`, `pending`, `not_applicable`).

### GET /api/documents/search

Returns document records as a JSON array. Each record includes `document_id`, `matter_id`, `document_title`, `category_codes`, `custodian`, `coding` (responsive/nonresponsive/privileged/nonprivileged), `produced_status` (produced/not_produced/withheld), `source_id`, and optional `privilege_log_id`.

### GET /api/privilege-log

Returns privilege log entries as a JSON array. Each record includes `privilege_log_id`, `matter_id`, `document_count`, `withheld_count`, `logged_count`, `category_codes`, `privilege_type`, `third_party` (nullable), and `log_status` (complete/incomplete_log/waived).

Use `unlogged_count = withheld_count - logged_count` when not provided directly.

### GET /api/qc-findings

Returns QC finding records as a JSON array. Each record includes `qc_finding_id`, `matter_id`, `finding_type`, `severity`, `status`, `category_codes`, `document_ids` (list), `affected_privilege_log_id` (nullable), `document_count`, `description`, and `recommended_action`.

Common finding types: `zero_claim_contradiction`, `responsive_miscoding`, `privilege_miscoding`, `over_designation`, `privilege_log_gap`, `privilege_log_incomplete`.

### GET /api/retention-events

Returns retention event records as a JSON array. Each record includes `event_id`, `matter_id`, `event_type`, `status`, `risk_level`, `category_codes`, `record_type`, `event_date` (nullable), `hold_date` (nullable), `policy_section` (nullable), `retention_period_months` (nullable), `volume_count` (nullable), `volume_unit`, and `cutoff_date` (nullable).

Event status values include `policy_destroyed_pre_hold`, `post_hold_loss`, `auto_purged`, `active_system_loss`, `should_exist_missing`, `available_archive`, `preserved_available`, `collection_pending`.

### GET /api/remediation-actions

Returns remediation action records as a JSON array. Each record includes `action_id`, `matter_id`, `action_type`, `owner`, `priority`, `target_ids` (list), `category_codes` (list), and `status`.

### POST /api/query

Send a JSON body: `{"query": "<SQL query>"}` with header `X-API-Key: <key from task payloads>`.

The underlying data model follows the schema from `GET /api/schema`. Common tables include `matters`, `productions`, `custodian_sources`, `documents`, `privilege_log`, `qc_findings`, `retention_events`, `remediation_actions`, and `subpoena_categories`.

Always scope queries to the current matter: `WHERE matter_id = '<id>'`.

## Common Query Patterns

Count documents by category and coding:
```sql
SELECT category_code, coding, COUNT(*) as cnt
FROM documents
WHERE matter_id = 'MTR-X'
GROUP BY category_code, coding
```

Join QC findings to documents:
```sql
SELECT q.qc_finding_id, q.finding_type, d.document_id, d.document_title, d.coding
FROM qc_findings q
JOIN documents d ON d.matter_id = q.matter_id
  AND d.document_id IN (SELECT value FROM json_each(q.document_ids))
WHERE q.matter_id = 'MTR-X'
```

Count privilege log gaps:
```sql
SELECT p.privilege_log_id, p.category_codes, p.withheld_count, p.logged_count,
       (p.withheld_count - p.logged_count) as unlogged_count
FROM privilege_log p
WHERE p.matter_id = 'MTR-X' AND p.log_status != 'complete'
```
