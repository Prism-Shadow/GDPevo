# Investigation Review Hub -- Standard Schemas

These are the canonical response shapes for the hub endpoints. The live
`GET /api/schema` endpoint returns current column definitions; cross-check with
what the schema endpoint returns.

## GET /api/matters

```json
{
  "matter_id": "string",
  "client": "string",
  "agency": "string or null",
  "case_type": "string",
  "hold_date": "string YYYY-MM-DD or null",
  "description": "string or null"
}
```

## GET /api/subpoena-categories

```json
[
  {
    "category_code": "string",
    "title": "string",
    "description": "string or null",
    "matter_id": "string"
  }
]
```

Category codes follow patterns like `R01`-`R15`, `A`-`I`, `SEC-1`-`SEC-4`,
`SEC-A`-`SEC-D`, `A`-`F`. Sort codes lexicographically ascending.

## GET /api/productions

```json
[
  {
    "production_id": "string",
    "matter_id": "string",
    "category_code": "string",
    "status": "string",
    "doc_count": "integer",
    "produced_date": "string YYYY-MM-DD or null"
  }
]
```

Production `status` values include `"produced"`, `"pending"`, `"not_produced"`.
Use `doc_count` to verify whether a category has had any material produced.

## GET /api/custodian-sources

```json
[
  {
    "source_id": "string",
    "matter_id": "string",
    "custodian": "string",
    "source_type": "string",
    "collection_status": "string",
    "category_coverage": ["string category_code"],
    "notes": "string or null"
  }
]
```

`collection_status` values: `"collected"`, `"not_collected"`, `"partial"`,
`"lost"`, `"pending"`. `source_type` values: `"laptop"`, `"personal_phone"`,
`"personal_email"`, `"personal_messaging"`, `"shared_drive"`, `"email"`,
`"teams_archive"`, `"cloud_mail_archive"`, `"offsite_records"`,
`"lab_results_archive"`.

## GET /api/documents/search

```json
[
  {
    "doc_id": "string",
    "matter_id": "string",
    "category_code": "string or null",
    "coding": "string",
    "produced_status": "string",
    "privilege_status": "string or null",
    "title": "string or null",
    "custodian": "string or null"
  }
]
```

`coding` values: `"responsive"`, `"nonresponsive"`, `"privileged"`,
`"nonprivileged"`, `"unknown"`. `produced_status` values: `"produced"`,
`"not_produced"`, `"withheld"`, `"unknown"`.

## GET /api/privilege-log

```json
[
  {
    "privilege_id": "string",
    "matter_id": "string",
    "category_code": "string or null",
    "doc_count": "integer",
    "withheld_count": "integer",
    "logged_count": "integer",
    "unlogged_count": "integer or null",
    "third_party": "string or null",
    "privilege_type": "string or null",
    "notes": "string or null"
  }
]
```

A privilege-log gap exists when `logged_count` < `withheld_count` (i.e.
`unlogged_count` > 0). `third_party` being non-null indicates potential waiver
exposure.

## GET /api/qc-findings

```json
[
  {
    "finding_id": "string",
    "matter_id": "string",
    "category_code": "string or null",
    "finding_type": "string",
    "severity": "string",
    "status": "string",
    "document_count": "integer",
    "doc_id_refs": ["string doc_id"],
    "description": "string or null"
  }
]
```

`finding_type` values include `"responsiveness_miscode"`,
`"privilege_miscoding"`, `"over_designation"`, `"zero_claim_contradiction"`,
`"other"`. `status` values: `"confirmed"`, `"open"`, `"cleared"`. `severity`:
`"critical"`, `"high"`, `"medium"`, `"low"`.

## GET /api/retention-events

```json
[
  {
    "event_id": "string",
    "matter_id": "string",
    "record_type": "string",
    "status": "string",
    "risk_level": "string or null",
    "event_date": "string YYYY-MM-DD or null",
    "hold_date": "string YYYY-MM-DD or null",
    "policy_section": "string or null",
    "retention_period_months": "integer or null",
    "volume_count": "integer or null",
    "volume_unit": "string or null",
    "cutoff_date": "string YYYY-MM-DD or null",
    "affected_categories": ["string category_code"],
    "notes": "string or null"
  }
]
```

`status` values: `"policy_destroyed_pre_hold"`, `"post_hold_loss"`,
`"auto_purged"`, `"active_system_loss"`, `"should_exist_missing"`,
`"available_archive"`, `"preserved_available"`, `"collection_pending"`.
`volume_unit` values: `"boxes"`, `"days"`, `"months"`, `"records"`,
`"documents"`, `"emails"`, `"sources"`, `"not_applicable"`.

## GET /api/remediation-actions

```json
[
  {
    "action_id": "string",
    "matter_id": "string",
    "target_id": "string",
    "action_type": "string",
    "owner": "string",
    "priority": "string",
    "affected_categories": ["string category_code"],
    "notes": "string or null"
  }
]
```

## POST /api/query -- SQL Schema

Tables exposed via `POST /api/query` mirror the GET endpoints. Common table names
and columns:

### matters
`matter_id`, `client`, `agency`, `case_type`, `hold_date`, `description`

### subpoena_categories
`category_code`, `title`, `description`, `matter_id`

### productions
`production_id`, `matter_id`, `category_code`, `status`, `doc_count`, `produced_date`

### custodian_sources
`source_id`, `matter_id`, `custodian`, `source_type`, `collection_status`, `notes`

Note: `category_coverage` may be a JSON array or a join table; check the live
schema.

### documents
`doc_id`, `matter_id`, `category_code`, `coding`, `produced_status`,
`privilege_status`, `title`, `custodian`

### privilege_log
`privilege_id`, `matter_id`, `category_code`, `doc_count`, `withheld_count`,
`logged_count`, `unlogged_count`, `third_party`, `privilege_type`, `notes`

### qc_findings
`finding_id`, `matter_id`, `category_code`, `finding_type`, `severity`, `status`,
`document_count`, `description`

### retention_events
`event_id`, `matter_id`, `record_type`, `status`, `risk_level`, `event_date`,
`hold_date`, `policy_section`, `retention_period_months`, `volume_count`,
`volume_unit`, `cutoff_date`, `notes`

### remediation_actions
`action_id`, `matter_id`, `target_id`, `action_type`, `owner`, `priority`, `notes`

## Common SQL Query Patterns

### Find categories with zero production
```sql
SELECT sc.category_code, sc.title
FROM subpoena_categories sc
LEFT JOIN productions p ON sc.category_code = p.category_code AND sc.matter_id = p.matter_id
WHERE sc.matter_id = 'MTR-...'
GROUP BY sc.category_code
HAVING COUNT(p.production_id) = 0 OR SUM(p.doc_count) = 0
```

### Count uncollected personal sources
```sql
SELECT COUNT(*) AS uncollected_personal
FROM custodian_sources
WHERE matter_id = 'MTR-...'
  AND collection_status = 'not_collected'
  AND source_type IN ('personal_phone', 'personal_email', 'personal_messaging')
```

### Privilege log gap summary
```sql
SELECT
  COUNT(*) AS gap_entries,
  SUM(withheld_count) AS total_withheld,
  SUM(logged_count) AS total_logged,
  SUM(withheld_count - logged_count) AS total_unlogged
FROM privilege_log
WHERE matter_id = 'MTR-...'
  AND logged_count < withheld_count
```

### QC miscoded responsive documents
```sql
SELECT SUM(document_count) AS miscoded_responsive
FROM qc_findings
WHERE matter_id = 'MTR-...'
  AND finding_type IN ('responsiveness_miscode', 'zero_claim_contradiction')
  AND status = 'confirmed'
```

### Post-hold loss events with volume
```sql
SELECT event_id, status, event_date, hold_date, volume_count, volume_unit
FROM retention_events
WHERE matter_id = 'MTR-...'
  AND status = 'post_hold_loss'
```

### Documents with responsiveness issues across categories
```sql
SELECT d.category_code, COUNT(*) AS affected_docs
FROM documents d
JOIN qc_findings qc ON d.doc_id = qc.doc_id_refs
WHERE d.matter_id = 'MTR-...'
  AND qc.finding_type = 'responsiveness_miscode'
GROUP BY d.category_code
```
