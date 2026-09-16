# Investigation Review Hub — API Guide

## Base URL

The task prompt provides a base URL, typically via a placeholder like
`<TASK_ENV_BASE_URL>` or an explicit URL.

## Authentication

Most GET endpoints are unauthenticated. The SQL endpoint `POST /api/query`
requires an API key header (usually `X-API-Key: review-key-017`) as specified
in the task payload.

---

## GET Endpoints

Every GET endpoint returns `{"count": N, "rows": [...]}`.

### GET /

Confirms the service is alive. Returns `service`, `status`, and
`business_endpoints`.

### GET /api/schema

Returns `{"tables": [...]}` where each table has a `table` name and a
`columns` array with `name` and `type`. Use this to understand available
fields before writing SQL queries.

#### Tables

| Table | Key columns |
|---|---|
| matters | matter_id, name, agency, investigation_type, issued_date, hold_date, lead_partner, description, status |
| subpoena_categories | matter_id, category_code, title, date_start, date_end, request_text, topic_tags |
| production_stats | matter_id, batch_id, batch_date, category_code, produced_count, withheld_count, responsive_count, nonresponsive_count, status, zero_claim_reason, notes |
| custodian_sources | source_id, matter_id, custodian_name, role, source_type, source_label, status, event_date, post_hold, category_impacts, issue_tags, notes |
| review_documents | doc_id, matter_id, title, doc_date, custodian_name, source_system, category_code, responsiveness, privilege_status, produced_status, issue_tags, summary |
| privilege_entries | entry_id, matter_id, category_code, custodian_name, doc_count, withheld_count, logged_count, issue_type, third_party, notes |
| qc_findings | finding_id, matter_id, batch_id, issue_type, doc_count, affected_category, source_ref, severity, notes |
| retention_events | event_id, matter_id, record_type, event_date, hold_date, policy_section, retention_period_months, volume_count, volume_unit, status, affected_categories, source_ref, notes |
| remediation_actions | action_id, matter_id, action_type, priority, severity, owner, target_ref, due_days, description |

### GET /api/matters

Returns all matters. Filter with `?matter_id=MTR-EXAMPLE`.

Each row: matter_id, name, agency, investigation_type, issued_date, hold_date,
lead_partner, description, status.

### GET /api/subpoena-categories

Returns all subpoena categories across all matters. Filter with
`?matter_id=MTR-EXAMPLE`.

Each row: matter_id, category_code, title, date_start, date_end, request_text,
topic_tags (array).

Category codes are typically alphanumeric (A, B, R01, SEC-A, etc.) and must
be used verbatim in answers.

### GET /api/productions

Returns production batches. Filter with `?matter_id=MTR-EXAMPLE`.

Each row: matter_id, batch_id, batch_date, category_code, produced_count,
withheld_count, responsive_count, nonresponsive_count, status, zero_claim_reason,
notes.

Production status values: rolling_review, produced, supplement_pending, etc.

### GET /api/custodian-sources

Returns custodian device and data-source records. Filter with
`?matter_id=MTR-EXAMPLE`.

Each row: source_id (stable), matter_id, custodian_name, role, source_type,
source_label, status, event_date, post_hold (0 or 1 integer), category_impacts
(array of category codes), issue_tags (array), notes.

Source status values: available, in_review, collected, lost, not_collected, etc.
`post_hold: 1` means the event occurred after the litigation hold was in place.

### GET /api/documents/search

Returns review documents. Requires `?matter_id=MTR-EXAMPLE` or `?q=searchterm`.

Each row: doc_id, matter_id, title, doc_date, custodian_name, source_system,
category_code, responsiveness (responsive, nonresponsive), privilege_status
(privileged, nonprivileged, unknown), produced_status (produced, not_produced,
withheld), issue_tags (array), summary.

### GET /api/privilege-log

Returns privilege log entries. Filter with `?matter_id=MTR-EXAMPLE`.

Each row: entry_id, matter_id, category_code, custodian_name, doc_count,
withheld_count, logged_count, issue_type (clean, family_mismatch,
incomplete_log, waiver, etc.), third_party (0 or 1 integer), notes.

When issue_type is "incomplete_log", the difference between withheld_count
and logged_count represents unlogged privilege documents.

Third-party waiver: when `third_party: 1` and issue_type is "waiver" or
similar, the documents have been shared with an external party and privilege
may be waived.

### GET /api/qc-findings

Returns QC findings. Filter with `?matter_id=MTR-EXAMPLE`.

Each row: finding_id, matter_id, batch_id, issue_type, doc_count,
affected_category, source_ref (references a doc_id or other record),
severity, notes.

### GET /api/retention-events

Returns retention events. Filter with `?matter_id=MTR-EXAMPLE`.

Each row: event_id, matter_id, record_type, event_date, hold_date,
policy_section, retention_period_months, volume_count, volume_unit, status,
affected_categories (array), source_ref, notes.

Retention status values: policy_destroyed (pre-hold destruction under normal
policy), post_hold_loss (destruction after the hold was in place), system_loss
(active system auto-purge or data loss), should_exist_missing (record that
should exist but cannot be located).

### GET /api/remediation-actions

Returns pre-existing remediation action records. Filter with
`?matter_id=MTR-EXAMPLE`.

Each row: action_id, matter_id, action_type, priority (P0-P3), severity, owner,
target_ref (references another record ID), due_days, description.

---

## POST /api/query

Send SQL queries against the hub database. The database engine is SQLite.

Headers: Content-Type: application/json, plus the API key header from the task.

Body: `{"sql": "SELECT ... FROM ... WHERE matter_id = 'MTR-EXAMPLE'"}`

Response: `{"columns": [...], "row_count": N, "rows": [...], "truncated": false}`

If `truncated` is true, the result was cut off; add a LIMIT or more specific
WHERE clause.

Table names for SQL match the /api/schema table keys: matters, subpoena_categories,
production_stats, custodian_sources, review_documents, privilege_entries,
qc_findings, retention_events, remediation_actions.

---

## Cross-Reference Patterns

Record IDs link across endpoints. Common patterns:

| This field | May reference | Found in endpoint |
|---|---|---|
| qc_findings.source_ref | doc_id (review_documents) | /api/documents/search |
| qc_findings.batch_id | batch_id (production_stats) | /api/productions |
| retention_events.source_ref | source_id (custodian_sources) or system name | /api/custodian-sources |
| remediation_actions.target_ref | any event_id, source_id, entry_id, finding_id | varies |
| custodian_sources.category_impacts | category_code | /api/subpoena-categories |
| privilege_entries.category_code | category_code | /api/subpoena-categories |

When building answer objects, use the stable IDs found through this
cross-referencing. Sort all ID lists ascending.

---

## Counting and Metrics

When computing metrics:

- **withheld_count** from privilege_entries is the total documents withheld.
- **logged_count** from privilege_entries is the subset that appears on the log.
- **unlogged_count** = withheld_count - logged_count (compute it).
- **third_party waiver docs** = sum of doc_count for entries where
  third_party = 1.
- **post_hold_loss events** = count of retention_events where the event_date is
  after the hold_date (or where status indicates post-hold loss).
- **miscoded responsive docs** = documents where responsiveness is
  "nonresponsive" but an issue_tag or QC finding indicates it should be
  responsive.
- **uncollected personal sources** = custodian_sources where source_type
  indicates personal device/email/messaging and status is not_collected.

All metric counts must be whole integers. Use 0 when no instances exist.
