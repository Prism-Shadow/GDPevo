# Investigation Review Hub — API Usage Guide

## Endpoint Reference

All endpoints are read-only GET (except POST `/api/query`). All return `{"rows": [...], "count": N}`.

### GET /api/matters
Returns all matters. Filter in memory by `matter_id`.

### GET /api/subpoena-categories
Optional query param: `?matter_id=MTR-EXAMPLE-GJ`

### GET /api/productions
Optional query param: `?matter_id=MTR-EXAMPLE-GJ`
Returns production batch stats per category.

### GET /api/custodian-sources
Optional query param: `?matter_id=MTR-EXAMPLE-GJ`
Returns custodian data sources with collection status, category impacts, and issue tags.

### GET /api/documents/search
Optional query param: `?matter_id=MTR-EXAMPLE-GJ`
Returns review documents. Defaults to first 100 rows; use SQL for larger result sets.

### GET /api/privilege-log
Optional query param: `?matter_id=MTR-EXAMPLE-GJ`
Returns privilege entries with doc_count, withheld_count, logged_count, issue_type, and third_party flag.

### GET /api/qc-findings
Optional query param: `?matter_id=MTR-EXAMPLE-GJ`
Returns QC findings with issue_type, doc_count, affected_category, severity, and source_ref.

### GET /api/retention-events
Optional query param: `?matter_id=MTR-EXAMPLE-GJ`
Returns retention events with status, affected_categories, volume_count, volume_unit, and policy/date details.

### GET /api/remediation-actions
Optional query param: `?matter_id=MTR-EXAMPLE-GJ`
Returns pre-registered remediation actions with priority, severity, owner, target_ref, and due_days.

### GET /api/schema
Returns the full data model: table names, column names, and column types.

### POST /api/query
Send `{"sql": "..."}` with header `X-API-Key: review-key-017`. Use when standard GET endpoints return truncated results or when cross-table joins are needed.

## Common Query Patterns

### Find privilege log gaps (unlogged withheld documents)
```sql
SELECT entry_id, category_code, withheld_count, logged_count,
       withheld_count - logged_count AS unlogged_count
FROM privilege_entries
WHERE matter_id = 'MTR-EXAMPLE-GJ'
AND withheld_count > logged_count
```

### Find responsiveness miscodes
```sql
SELECT f.finding_id, f.source_ref, f.affected_category, f.doc_count,
       d.responsiveness, d.produced_status
FROM qc_findings f
JOIN review_documents d ON f.source_ref = d.doc_id
WHERE f.matter_id = 'MTR-EXAMPLE-GJ'
AND f.issue_type IN ('responsiveness_miscode', 'zero_claim_contradiction')
```

### Find uncollected personal sources
```sql
SELECT source_id, custodian_name, source_type, category_impacts
FROM custodian_sources
WHERE matter_id = 'MTR-EXAMPLE-GJ'
AND status = 'not_collected'
AND (source_type LIKE '%personal%' OR source_type LIKE '%phone%' OR source_type LIKE '%messaging%')
```

### Find post-hold loss events
```sql
SELECT event_id, record_type, volume_count, volume_unit, affected_categories
FROM retention_events
WHERE matter_id = 'MTR-EXAMPLE-GJ'
AND status = 'post_hold_loss'
```

### Aggregate production status by category
```sql
SELECT category_code,
       SUM(produced_count) AS total_produced,
       SUM(responsive_count) AS total_responsive,
       SUM(withheld_count) AS total_withheld
FROM production_stats
WHERE matter_id = 'MTR-EXAMPLE-GJ'
GROUP BY category_code
ORDER BY category_code
```

## Data Interpretation Notes

- **JSON arrays in TEXT columns**: Columns like `category_impacts`, `affected_categories`, `issue_tags`, and `topic_tags` store JSON arrays as TEXT. Parse with `json.loads()` in Python.
- **Nullable fields**: `event_date`, `policy_section`, `retention_period_months`, and `zero_claim_reason` are often null. Use `COALESCE` in SQL or None checks in code.
- **Stable IDs**: All IDs (doc_id, entry_id, finding_id, event_id, source_id, action_id) are stable cross-run identifiers. Use them as the primary record keys in output deliverables.
- **Category codes**: Vary by matter (e.g. `R01`-`R15` for grand jury matters, `SEC-A` through `SEC-D` for SEC matters, `A`-`I` for environmental matters). Always pull from the hub, do not hardcode.
