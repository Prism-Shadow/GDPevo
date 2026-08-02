# Investigation Review Hub — API reference

Read-only REST + SQL service (`"service":"investigation_review_hub",
"state_mode":"read_only"`). Get the base URL and credential header from
`environment_access.md` at runtime; send the credential on every request.

## Conventions

- GET list endpoints return `{"count": N, "rows": [ {...}, ... ]}`.
- Every business table has a `matter_id`; **always filter with
  `?matter_id=<MTR-...>`** so you don't mix matters (rows are deliberately
  shared across matters with similar labels).
- `GET /` returns the endpoint list and status. `GET /api/schema` returns the
  table/column catalog — call it first if column names may have drifted.
- `POST /api/query` body `{"sql":"SELECT ..."}` → `{columns, rows, row_count,
  truncated}`. **SELECT-only** (writes rejected: "only SELECT statements are
  permitted"). Best tool for looking up one record by id or aggregating counts.
- `GET /api/documents/search` caps at **100 rows**, supports `?q=<keyword>`, and
  **ignores unknown params** (e.g. `?doc_id=` is not honored). To fetch a
  specific `doc_id`, use SQL against `review_documents`.

## Endpoint → table → columns

| Endpoint | Table | Columns |
|---|---|---|
| `GET /api/matters` | `matters` | matter_id, name, agency, investigation_type, issued_date, **hold_date**, lead_partner, description, status |
| `GET /api/subpoena-categories` | `subpoena_categories` | matter_id, category_code, title, date_start, date_end, request_text, topic_tags |
| `GET /api/productions` | `production_stats` | matter_id, batch_id, batch_date, category_code, produced_count, withheld_count, responsive_count, nonresponsive_count, status, **zero_claim_reason**, notes |
| `GET /api/custodian-sources` | `custodian_sources` | source_id, matter_id, custodian_name, role, source_type, source_label, status, event_date, **post_hold**, category_impacts, issue_tags, notes |
| `GET /api/documents/search` | `review_documents` | doc_id, matter_id, title, doc_date, custodian_name, source_system, category_code, responsiveness, privilege_status, produced_status, issue_tags, summary |
| `GET /api/privilege-log` | `privilege_entries` | entry_id, matter_id, category_code, custodian_name, doc_count, **withheld_count**, **logged_count**, issue_type, **third_party**, notes |
| `GET /api/qc-findings` | `qc_findings` | finding_id, matter_id, batch_id, issue_type, doc_count, affected_category, source_ref, severity, notes |
| `GET /api/retention-events` | `retention_events` | event_id, matter_id, record_type, **event_date**, **hold_date**, policy_section, retention_period_months, volume_count, volume_unit, status, affected_categories, source_ref, notes |
| `GET /api/remediation-actions` | `remediation_actions` | action_id, matter_id, action_type, priority, severity, owner, **target_ref**, due_days, description |

`category_impacts`, `affected_categories`, `issue_tags`, `topic_tags` come back
as arrays.

## Observed raw field vocabularies (hub side — map to template enums)

These are the *hub's* strings; the answer template uses its own enums. Never
copy a raw hub string into an enum field unless it is literally in that enum.

- `custodian_sources.status`: available, collected, in_review, not_collected,
  partial_collection, lost
- `custodian_sources.source_type`: e.g. personal_messaging, teams_archive,
  cloud_mail_archive, mobile_backup, network_share, laptop, personal_email,
  offsite_records (varies by matter)
- `retention_events.status`: post_hold_loss, available, system_loss,
  should_exist_missing, and pre-hold policy-destroyed variants (varies)
- `privilege_entries.issue_type`: incomplete_log, over_designated,
  third_party_waiver, family_mismatch, clean
- `qc_findings.issue_type`: zero_claim_contradiction, miscoded_privilege,
  family_break, near_duplicate, duplicate_overlay, date_normalization,
  metadata_gap (only the first two are typically material)
- `remediation_actions.action_type`: supplemental_collection, privilege_rework,
  qc_remediation, retention_exception_review, custodian_followup,
  load_file_cleanup, sampling_review (last three are the noise actions)
- `remediation_actions.owner`: Forensics, Legal Hold Team, Privilege Team,
  Review Operations, Matter Associate, Vendor Team (last two flag noise)
- `remediation_actions.priority`: P1, P2, P3 (+ P0 in some templates)

## Useful SQL patterns

```sql
-- material remediation actions (drop noise, drop bare-category targets)
SELECT action_id,action_type,owner,priority,severity,due_days,target_ref
FROM remediation_actions
WHERE matter_id='<MTR>' AND action_id NOT LIKE '%NOISE%'
  AND target_ref LIKE '%-%';           -- specific record ids, not 'A'/'SEC-1'

-- privilege gap candidates with computed unlogged (then apply the note test)
SELECT entry_id, withheld_count-logged_count AS unlogged, issue_type, third_party, notes
FROM privilege_entries WHERE matter_id='<MTR>';

-- retention: classify pre vs post hold
SELECT event_id,status,event_date,hold_date,volume_count,volume_unit,notes
FROM retention_events WHERE matter_id='<MTR>';   -- post-hold: event_date >= hold_date

-- look up a specific referenced document
SELECT * FROM review_documents WHERE matter_id='<MTR>' AND doc_id='<DOC-ID>';
```
