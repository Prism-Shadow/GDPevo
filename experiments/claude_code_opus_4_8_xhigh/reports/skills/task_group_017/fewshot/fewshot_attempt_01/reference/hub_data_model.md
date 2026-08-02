# Investigation Review Hub — data model & access

Read-only HTTP API (`state_mode: read_only`). Authenticate with the `X-API-Key`
header from the run's `environment_access.md`. Every table endpoint accepts a
`?matter_id=<MATTER_ID>` filter — always use it. Confirm the live shape with
`GET /api/schema`.

## Endpoints → tables

| Endpoint | Table | Key columns (from `/api/schema`) |
|---|---|---|
| `GET /api/matters` | `matters` | `matter_id, name, agency, investigation_type, issued_date, hold_date, lead_partner, description, status` |
| `GET /api/subpoena-categories` | `subpoena_categories` | `matter_id, category_code, title, date_start, date_end, request_text, topic_tags` |
| `GET /api/productions` | `production_stats` | `matter_id, batch_id, batch_date, category_code, produced_count, withheld_count, responsive_count, nonresponsive_count, status, zero_claim_reason, notes` |
| `GET /api/custodian-sources` | `custodian_sources` | `source_id, matter_id, custodian_name, role, source_type, source_label, status, event_date, post_hold, category_impacts, issue_tags, notes` |
| `GET /api/documents/search` | `review_documents` | `doc_id, matter_id, title, doc_date, custodian_name, source_system, category_code, responsiveness, privilege_status, produced_status, issue_tags, summary` |
| `GET /api/privilege-log` | `privilege_entries` | `entry_id, matter_id, category_code, custodian_name, doc_count, withheld_count, logged_count, issue_type, third_party, notes` |
| `GET /api/qc-findings` | `qc_findings` | `finding_id, matter_id, batch_id, issue_type, doc_count, affected_category, source_ref, severity, notes` |
| `GET /api/retention-events` | `retention_events` | `event_id, matter_id, record_type, event_date, hold_date, policy_section, retention_period_months, volume_count, volume_unit, status, affected_categories, source_ref, notes` |
| `GET /api/remediation-actions` | `remediation_actions` | `action_id, matter_id, action_type, priority, severity, owner, target_ref, due_days, description` |
| `POST /api/query` | any (SQL) | body `{"sql":"SELECT ..."}` → `{columns,row_count,rows,truncated}` |

Responses are JSON `{"count":N,"rows":[...]}` for table endpoints.

## Field notes that matter for analysis

- `matters.hold_date` — the litigation-hold date. Losses/destruction **after**
  this date are preservation failures (disclosable); destruction **before** it
  under a retention policy is generally no-fault.
- `custodian_sources.post_hold` — `1` if the source event is after the hold.
  `category_impacts` and `issue_tags` are JSON arrays; `status` ∈
  {`lost`, `not_collected`, `partial_collection`, `in_review`, `collected`,
  `available`}.
- `privilege_entries`: `withheld_count` = withheld-as-privileged; `logged_count`
  = how many appear on the privilege log; **unlogged = withheld_count −
  logged_count**. `third_party = 1` flags a waiver-risk entry. `doc_count` is the
  category population and is usually **not** the count you report.
- `qc_findings.source_ref` names the affected doc(s) (comma-separated for
  multiple) or another record; `affected_category` is the single impacted
  category. `issue_type` distinguishes real defects from routine QC variance.
- `retention_events.volume_unit` ∈ {`boxes`, `days`, `months`, `records`,
  `mailboxes`, `files`, `exports`, `reports`, `system_window`, …}. Box-scoped
  metrics only sum rows where `volume_unit == "boxes"`.
- `remediation_actions` is the escalation anchor (see `material_vs_noise.md`).
  Its `owner`/`priority`/`action_type` use a hub vocabulary you must re-map to the
  template enums — do not copy verbatim.

## Query recipes (`POST /api/query`, SELECT-only)

`documents/search` caps at 100 rows; SQL does not. Examples:

```sql
-- distribution of source collection status
SELECT status, COUNT(*) c FROM custodian_sources
WHERE matter_id = '<M>' GROUP BY status;

-- privilege gaps with computed unlogged count
SELECT entry_id, category_code, issue_type, withheld_count, logged_count,
       (withheld_count - logged_count) AS unlogged
FROM privilege_entries WHERE matter_id='<M>' AND issue_type='incomplete_log';

-- retention losses after the hold date
SELECT event_id, status, record_type, volume_count, volume_unit, affected_categories
FROM retention_events
WHERE matter_id='<M>' AND status IN ('post_hold_loss','system_loss','should_exist_missing','auto_purged');

-- the escalation anchor, noise excluded
SELECT action_id, action_type, target_ref, priority, severity
FROM remediation_actions
WHERE matter_id='<M>' AND description NOT LIKE '%operational noise%';

-- look up a specific escalated document named by a QC finding
SELECT * FROM review_documents WHERE doc_id = '<DOC_ID>';
```

Use single quotes inside SQL. Filter every query by `matter_id` — the same issue
labels recur across matters by design.
