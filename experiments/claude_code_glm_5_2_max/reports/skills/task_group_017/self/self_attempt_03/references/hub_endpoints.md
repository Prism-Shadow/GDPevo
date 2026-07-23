# Hub Endpoints Reference

Base URL: `http://task-env:9017/`
Auth (SQL endpoint only): header `X-API-Key: review-key-017`

## Resource endpoints (GET)

All return JSON. Collection endpoints return `{"count": N, "rows": [...]}`; filter by appending `?matter_id=<MTR-...>` where supported.

| Endpoint | Returns | Notes |
|---|---|---|
| `GET /api/schema` | `{tables:[{table, columns:[{name,type}]}]}` | Authoritative data model. Read first. |
| `GET /api/matters` | list of matters | Confirm matter, `hold_date`, `agency`, `investigation_type`. |
| `GET /api/subpoena-categories` | list | Category codes + titles + request text per matter. |
| `GET /api/productions` | list | `production_stats`: produced/withheld/responsive/nonresponsive counts, `zero_claim_reason`, status, batch. |
| `GET /api/custodian-sources` | list | Sources with `post_hold` flag, `status`, `source_type`, `category_impacts`, `issue_tags`. |
| `GET /api/documents/search` | list | `review_documents`: responsiveness, privilege_status, produced_status, issue_tags. |
| `GET /api/privilege-log` | list | `privilege_entries`: doc_count, withheld_count, logged_count, issue_type, third_party. |
| `GET /api/qc-findings` | list | `qc_findings`: issue_type, severity, affected_category, source_ref. |
| `GET /api/retention-events` | list | `retention_events`: status, event_date, hold_date, policy_section, retention_period_months, volume_count/unit. |
| `GET /api/remediation-actions` | list | `remediation_actions`: action_type, priority, severity, owner, target_ref, due_days. |

## Read-only SQL endpoint

`POST /api/query` — header `X-API-Key: review-key-017`, `Content-Type: application/json`.

**Body uses the `sql` key** (the server rejects `query`):
```json
{"sql": "SELECT category_code, title FROM subpoena_categories WHERE matter_id = ?", "params": ["MTR-ALLOYWORKS-GJ"]}
```
Response:
```json
{"columns": ["category_code","title"], "row_count": 6, "rows": [...], "truncated": false}
```
- Use `?` placeholders + `params` array; never string-interpolate matter IDs.
- When `"truncated": true`, narrow the WHERE clause or page — do not aggregate over a partial result set.
- Prefer SQL for cross-table aggregation (counts, sums, distinct categories); prefer GET endpoints for single-table pulls.
