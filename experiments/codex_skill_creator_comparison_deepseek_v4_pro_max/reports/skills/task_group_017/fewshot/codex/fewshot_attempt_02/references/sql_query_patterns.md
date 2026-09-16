# SQL Query Patterns

Use `POST /api/query` with header `X-API-Key: review-key-017` when GET endpoints cannot express the needed query. Always confirm table and column names with `GET /api/schema` first.

## Schema discovery

```bash
curl "$BASE/api/schema"
```

Expected table names: `matters`, `subpoena_categories`, `productions`, `custodian_sources`, `documents`, `privilege_log`, `qc_findings`, `retention_events`, `remediation_actions`.

## Common queries

### Document counts by coding and production status

```sql
SELECT coding, produced_status, COUNT(*) AS cnt
FROM documents
WHERE matter_id = '<MATTER_ID>'
GROUP BY coding, produced_status
```

### Privilege-log gap counts

```sql
SELECT
  COUNT(DISTINCT d.doc_id) AS withheld_total,
  COUNT(DISTINCT p.doc_id) AS logged_total
FROM documents d
LEFT JOIN privilege_log p ON p.doc_id = d.doc_id AND p.matter_id = d.matter_id
WHERE d.matter_id = '<MATTER_ID>'
  AND d.coding = 'privileged'
  AND d.produced_status = 'withheld'
```

### Unlogged withheld documents

```sql
SELECT d.doc_id, d.title, d.custodian, d.categories
FROM documents d
WHERE d.matter_id = '<MATTER_ID>'
  AND d.coding = 'privileged'
  AND d.produced_status = 'withheld'
  AND d.doc_id NOT IN (
    SELECT doc_id FROM privilege_log WHERE matter_id = '<MATTER_ID>'
  )
```

### QC findings by issue type

```sql
SELECT finding_id, issue_type, severity, status, doc_id
FROM qc_findings
WHERE matter_id = '<MATTER_ID>'
ORDER BY issue_type, finding_id
```

### Sources by collection status

```sql
SELECT source_id, custodian_name, source_type, collection_status, categories
FROM custodian_sources
WHERE matter_id = '<MATTER_ID>'
  AND collection_status IN ('not_collected', 'lost', 'partial', 'destroyed')
ORDER BY collection_status, source_id
```

### Retention events grouped by status

```sql
SELECT status, COUNT(*) AS event_count, SUM(volume_count) AS total_volume
FROM retention_events
WHERE matter_id = '<MATTER_ID>'
GROUP BY status
```

### Documents with miscoding (QC-linked)

```sql
SELECT DISTINCT d.doc_id, d.title, d.custodian, d.coding, d.categories, q.finding_id, q.issue_type
FROM documents d
JOIN qc_findings q ON q.doc_id = d.doc_id AND q.matter_id = d.matter_id
WHERE d.matter_id = '<MATTER_ID>'
  AND q.issue_type IN ('responsiveness_miscode', 'zero_claim_contradiction')
```

### Documents behind privilege-log gaps for a specific block

To quantify a specific privilege-log gap identified from the privilege_log and documents endpoints, use a targeted query filtered by the relevant log_id or doc_id pattern.

### Third-party privilege waiver documents

```sql
SELECT p.log_id, p.doc_id, p.third_party, p.description, d.categories
FROM privilege_log p
JOIN documents d ON d.doc_id = p.doc_id AND d.matter_id = p.matter_id
WHERE p.matter_id = '<MATTER_ID>'
  AND p.third_party IS NOT NULL
  AND p.third_party != ''
```

### Retrieved/available archives

```sql
SELECT source_id, source_type, collection_status, categories, notes
FROM custodian_sources
WHERE matter_id = '<MATTER_ID>'
  AND collection_status = 'available_archive'
```

## Query construction rules

- Substitute `<MATTER_ID>` with the literal matter_id from the prompt.
- Filter every query by `matter_id` unless aggregating across matters.
- Use `COUNT(*)` not `COUNT(1)` — the evaluator expects consistent behavior.
- Sort results with `ORDER BY` matching the template's ordering rules.
- Prefer `LEFT JOIN` for gap detection (missing records in the right table indicate gaps).
- Always send the body as `{"sql": "<statement>"}` — a JSON object, not raw SQL text.
