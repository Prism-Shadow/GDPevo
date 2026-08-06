# Investigation Review Hub — API reference

## Connection
- Base URL: value of `GDPEVO_ENV_BASE_URL` in `environment_access.md` (read it at runtime; it
  may change per run/task group).
- Auth header on **every** request: `X-API-Key: <key from environment_access.md>`.
- Service is **read-only**. `GET /` returns a health/endpoint list; `GET /api/schema` returns
  the table/column catalog. Use these to confirm reachability and exact column names before pulling.

## Endpoints
Business endpoints (all require the API key):

```
GET  /                       # health + endpoint list
GET  /api/schema             # {tables:[{table, columns:[{name,type}]}]}
GET  /api/matters
GET  /api/subpoena-categories
GET  /api/productions            # -> production_stats table
GET  /api/custodian-sources
GET  /api/documents/search       # -> review_documents table
GET  /api/privilege-log          # -> privilege_entries table
GET  /api/qc-findings
GET  /api/retention-events
GET  /api/remediation-actions
POST /api/query                  # read-only SQL, best for precise pulls
```

- REST GET endpoints accept a `?matter_id=<MTR-…>` filter and return
  `{"count": N, "rows": [ ... ]}`. On these, list/array columns (e.g. `affected_categories`,
  `category_impacts`, `issue_tags`) come back as JSON arrays.
- `POST /api/query` body: `{"sql": "SELECT ... FROM <table> WHERE matter_id='MTR-…'"}`
  → `{"columns": [...], "row_count": N, "rows": [ {col:val} ]}`. Via SQL, array columns come
  back as **comma-joined strings** (e.g. `"A,C,F"`) — split on `,` yourself. Errors return
  `{"error":"query failed","detail":"..."}`; if a column name is rejected, re-check `/api/schema`.

## Tables and columns
Names come from `/api/schema` (verify at runtime; this is the observed catalog):

| table (endpoint) | columns |
|---|---|
| `matters` (`/api/matters`) | matter_id, name, agency, investigation_type, issued_date, **hold_date**, lead_partner, description, status |
| `subpoena_categories` (`/api/subpoena-categories`) | matter_id, category_code, title, date_start, date_end, request_text, topic_tags |
| `production_stats` (`/api/productions`) | matter_id, batch_id, batch_date, category_code, produced_count, withheld_count, responsive_count, nonresponsive_count, **status**, **zero_claim_reason**, notes |
| `custodian_sources` (`/api/custodian-sources`) | source_id, matter_id, custodian_name, role, source_type, source_label, **status**, event_date, **post_hold**, category_impacts, **issue_tags**, notes |
| `review_documents` (`/api/documents/search`) | doc_id, matter_id, title, doc_date, custodian_name, source_system, category_code, **responsiveness**, **privilege_status**, **produced_status**, **issue_tags**, summary |
| `privilege_entries` (`/api/privilege-log`) | entry_id, matter_id, category_code, custodian_name, doc_count, **withheld_count**, **logged_count**, **issue_type**, **third_party**, notes |
| `qc_findings` (`/api/qc-findings`) | finding_id, matter_id, batch_id, **issue_type**, doc_count, affected_category, source_ref, severity, notes |
| `retention_events` (`/api/retention-events`) | event_id, matter_id, record_type, event_date, hold_date, policy_section, retention_period_months, volume_count, volume_unit, **status**, affected_categories, source_ref, notes |
| `remediation_actions` (`/api/remediation-actions`) | action_id, matter_id, action_type, priority, severity, owner, target_ref, due_days, description |

Bolded columns carry the strongest materiality signal (see `domain_playbook.md`).

## Field-value cheatsheet (observed)
- `retention_events.status`: `available` (fine), `policy_destroyed`/pre-hold policy loss (benign),
  `post_hold_loss`, `post_hold_partial_recovery`, `should_exist_missing`, `system_loss`,
  `auto_purged`.
- `custodian_sources.status`: `available`, `lost`, `not_collected`; `post_hold` is `0/1`;
  `issue_tags` include `routine` (decoy), `archive_available`, `deleted_channel`, etc.
- `review_documents.produced_status`: `produced` (no gap), `not_produced`, `withheld`,
  `unrecovered`. `responsiveness`: `responsive`, `nonresponsive`, `needs_review`.
- `privilege_entries.issue_type`: `incomplete_log`, `third_party_waiver`, `over_designated`;
  `third_party` is `0/1`. Note `doc_count` ≥ `withheld_count`; use `withheld_count` /
  `logged_count` for privilege math, not `doc_count`.
- `qc_findings.issue_type`: material `miscoded_nonresponsive`, `miscoded_privilege`,
  `zero_claim_contradiction`; noise `family_break`, `date_normalization`, `near_duplicate`.
- `production_stats.status`: material `zero_claim_contradicted` (with `zero_claim_reason` set);
  benign `produced`, `closed`, `rolling_review`, `supplement_pending`.

## Handy queries
```sql
-- Candidate material records (short matter token; exclude full-name+number decoys):
SELECT event_id  FROM retention_events   WHERE matter_id='MTR-X' AND event_id  NOT LIKE '%FULLNAME%';
SELECT source_id FROM custodian_sources  WHERE matter_id='MTR-X' AND source_id NOT LIKE '%FULLNAME%';
SELECT finding_id FROM qc_findings        WHERE matter_id='MTR-X' AND finding_id NOT LIKE '%FULLNAME%';
SELECT entry_id  FROM privilege_entries  WHERE matter_id='MTR-X' AND entry_id  NOT LIKE '%FULLNAME%';
SELECT doc_id    FROM review_documents   WHERE matter_id='MTR-X' AND doc_id    NOT LIKE '%FULLNAME%';
-- Responsiveness gap signal:
SELECT category_code,status,zero_claim_reason FROM production_stats WHERE matter_id='MTR-X';
```
Replace `FULLNAME` with the long matter name (e.g. `ALLOYWORKS`, `GRAYCLIFF`); the short token
(e.g. `ALLOY`, `GRAY`) is what survives and marks material records. Always corroborate the
survivors with their attribute fields before treating them as material.
