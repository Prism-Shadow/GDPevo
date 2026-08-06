# Investigation Review Hub — API reference

Read-only service (`"state_mode":"read_only"`). Send the `X-API-Key` header (value
from `environment_access.md`) on every request. Base URL is also from
`environment_access.md` — do not hardcode it. The hub holds **many matters**;
filter every read to the matter under review.

`GET /` returns the service banner and the live `business_endpoints` list.
`GET /api/schema` returns every table's columns — call it first to confirm shapes
for the current run (schema below is the observed baseline; verify if a task
looks different).

## Endpoint → table map

| Endpoint | Table | Key columns |
|---|---|---|
| `GET /api/matters` | `matters` | matter_id, name, agency, investigation_type, issued_date, **hold_date**, lead_partner, description, status |
| `GET /api/subpoena-categories` | `subpoena_categories` | matter_id, category_code, title, date_start, date_end, request_text, topic_tags |
| `GET /api/productions` | `production_stats` | matter_id, batch_id, batch_date, category_code, produced_count, withheld_count, responsive_count, nonresponsive_count, status, zero_claim_reason, notes |
| `GET /api/custodian-sources` | `custodian_sources` | source_id, matter_id, custodian_name, role, source_type, source_label, status, event_date, post_hold, category_impacts, issue_tags, notes |
| `GET /api/documents/search` | `review_documents` | doc_id, matter_id, title, doc_date, custodian_name, source_system, category_code, responsiveness, privilege_status, produced_status, issue_tags, summary |
| `GET /api/privilege-log` | `privilege_entries` | entry_id, matter_id, category_code, custodian_name, doc_count, withheld_count, logged_count, issue_type, third_party, notes |
| `GET /api/qc-findings` | `qc_findings` | finding_id, matter_id, batch_id, issue_type, doc_count, affected_category, source_ref, severity, notes |
| `GET /api/retention-events` | `retention_events` | event_id, matter_id, record_type, event_date, hold_date, policy_section, retention_period_months, volume_count, volume_unit, status, affected_categories, source_ref, notes |
| `GET /api/remediation-actions` | `remediation_actions` | action_id, matter_id, action_type, priority, severity, owner, target_ref, due_days, description |
| `POST /api/query` | (any, read-only SQL) | body `{"sql":"SELECT ... FROM <table> WHERE matter_id='...'"}` → `{columns,row_count,rows,truncated}` |

## Filtering & shapes
- `GET` endpoints accept `?matter_id=<id>` and additional column filters
  (e.g. `documents/search?matter_id=..&responsiveness=responsive&produced_status=not_produced`).
  They return `{count, rows:[...]}` with list-typed columns (`affected_categories`,
  `category_impacts`, `issue_tags`) already normalized to JSON arrays.
- `POST /api/query` returns those same list columns as raw comma-separated
  **strings** — split on `,` yourself. Watch `truncated`; page/aggregate if set.
- Table names for SQL are the *table* names above (`production_stats`,
  `review_documents`, `privilege_entries`), not the endpoint paths.

## Useful query recipes (parameterize `:m` = matter_id)

Privilege log gaps and unlogged counts:
```sql
SELECT entry_id, category_code, issue_type, third_party,
       doc_count, withheld_count, logged_count,
       (withheld_count - logged_count) AS unlogged_count
FROM privilege_entries WHERE matter_id=':m' ORDER BY entry_id;
```

Retention events split by hold pivot (pre-hold policy loss vs post-hold loss):
```sql
SELECT event_id, record_type, status, event_date, hold_date,
       retention_period_months, volume_count, volume_unit, affected_categories
FROM retention_events WHERE matter_id=':m' ORDER BY event_id;
```

Responsive-but-not-produced (miscode / underproduction candidates):
```sql
SELECT doc_id, category_code, responsiveness, privilege_status,
       produced_status, issue_tags
FROM review_documents
WHERE matter_id=':m' AND responsiveness='responsive'
      AND produced_status='not_produced';
```

Candidate remediation actions (map owner/action_type/priority to template enums,
drop `*-NOISE-*`/sampling rows unless the template scopes them in):
```sql
SELECT action_id, action_type, priority, severity, owner, target_ref, due_days
FROM remediation_actions WHERE matter_id=':m' ORDER BY priority, action_id;
```

Per-category production status and any zero-production claims:
```sql
SELECT category_code, produced_count, withheld_count, responsive_count,
       status, zero_claim_reason
FROM production_stats WHERE matter_id=':m' ORDER BY category_code;
```

## Field-semantics notes
- `matters.hold_date` — litigation-hold date; the pivot for pre/post-hold
  retention classification.
- `custodian_sources.status` ∈ e.g. `available`, `partial_collection`,
  `not_collected`, `in_review`; `post_hold` is 0/1; `issue_tags` flags
  `collection_gap`, `scope_exception`, `routine`, etc.
- `retention_events.status` ∈ e.g. `policy_destroyed_pre_hold`, `post_hold_loss`,
  `system_loss`, `auto_purged`, `should_exist_missing`, `retained`.
- `privilege_entries.issue_type` ∈ e.g. `incomplete_log`, `over_designated`,
  `third_party_waiver`, `family_mismatch`; `third_party` is 0/1.
- `qc_findings.issue_type` — material (`miscoded_privilege`, responsiveness
  miscodes) vs routine noise (`metadata_gap`, `duplicate_overlay`).
- `production_stats.zero_claim_reason` non-empty = a zero-production claim to
  test against responsive docs.
