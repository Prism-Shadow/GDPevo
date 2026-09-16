# Investigation Review Hub API Reference

This is the standard endpoint surface for the Investigation Review Hub. Confirm available endpoints by calling `GET /` and `GET /api/schema` at the task-provided base URL, as instances may differ.

## Standard endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Health check and API version |
| GET | `/api/schema` | Full endpoint and field schema for this instance |
| GET | `/api/matters` | Matter metadata: matter ID, client, agency, hold dates, case type |
| GET | `/api/subpoena-categories` | Request category codes, titles, and descriptions |
| GET | `/api/productions` | Production status by category, rolling production metadata |
| GET | `/api/custodian-sources` | Custodian data sources, collection status, device/media types |
| GET | `/api/documents/search` | Document coding, responsiveness, production status, privilege flags |
| GET | `/api/privilege-log` | Withheld documents, logged/unlogged counts, privilege designations, third-party waiver indicators |
| GET | `/api/qc-findings` | QC defects, miscoding, responsiveness contradictions, privilege recoding flags |
| GET | `/api/retention-events` | Retention losses, destruction dates, hold timelines, policy sections, volume counts |
| GET | `/api/remediation-actions` | Existing or recommended remediation actions, owners, priorities |
| POST | `/api/query` | Read-only SQL query endpoint; send header `X-API-Key: review-key-017` |

## Query endpoint usage

The `POST /api/query` endpoint accepts a JSON body with a `query` field containing a SQL SELECT statement. Use this only when the structured GET endpoints are insufficient. Always send the `X-API-Key` header.

Example:

```json
{"query": "SELECT * FROM retention_events WHERE matter_id = 'MTR-EXAMPLE' ORDER BY event_id"}
```

## Response shapes

Exact field names and response shapes vary between hub instances. Always read `GET /api/schema` first and match the actual response fields rather than relying on this reference. Key fields commonly include:

- `matter_id`, `client`, `agency` (matters)
- `category_code`, `title` (subpoena categories)
- `source_id`, `custodian`, `source_type`, `collection_status` (custodian sources)
- `doc_id`, `coding`, `responsiveness`, `produced_status`, `category_codes` (documents)
- `log_id`, `withheld_count`, `logged_count`, `unlogged_count`, `third_party`, `waiver_flag` (privilege log)
- `finding_id`, `issue_type`, `severity`, `status`, `doc_refs` (QC findings)
- `event_id`, `retention_status`, `risk_level`, `affected_categories`, `volume_count`, `volume_unit`, `hold_date`, `event_date` (retention events)
