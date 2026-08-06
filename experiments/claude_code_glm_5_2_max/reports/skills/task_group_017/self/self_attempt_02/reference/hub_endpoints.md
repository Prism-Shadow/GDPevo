# Hub Endpoints & Network Access

The Review Hub is the sole source of business evidence. Network access details live in `environment_access.md` at the work root; this file restates the operational usage so you do not need to re-derive it per task.

## Base URL & auth

- Base URL: `http://task-env:9017/`
- Read-only SQL endpoint: `POST /api/query`, requires header `X-API-Key: review-key-017`.
- All GET list endpoints accept a `matter_id` query parameter to filter to the matter under review. Always filter by `matter_id` rather than pulling the full corpus and filtering client-side.

## Endpoint catalog

| Method | Path | Returns | Primary key | Use for |
|---|---|---|---|---|
| GET | `/api/schema` | list of tables + columns | — | confirm available tables/columns before writing SQL |
| GET | `/api/matters` | matters (paginated: `{count, rows}`) | `matter_id` | `hold_date`, `issued_date`, agency, status, description |
| GET | `/api/subpoena-categories` | request categories | `category_code` | universe of category codes + titles |
| GET | `/api/productions` | production batches | `batch_id` | produced/withheld/responsive counts, `status`, `zero_claim_reason` |
| GET | `/api/custodian-sources` | custodian/source records | `source_id` | `source_type`, `status`, `post_hold`, `category_impacts`, `issue_tags` |
| GET | `/api/documents/search` | review documents | `doc_id` | coding (`responsiveness`, `privilege_status`, `produced_status`), `issue_tags` |
| GET | `/api/privilege-log` | privilege entries | `entry_id` | `doc_count`, `withheld_count`, `logged_count`, `issue_type`, `third_party` |
| GET | `/api/qc-findings` | QC defect findings | `finding_id` | `issue_type`, `doc_count`, `affected_category`, `severity` |
| GET | `/api/retention-events` | retention/preservation events | `event_id` | `status`, `hold_date`, `policy_section`, `volume_count`/`volume_unit`, `affected_categories` |
| GET | `/api/remediation-actions` | proposed actions | `action_id` | `action_type`, `priority`, `owner`, `target_ref`, `due_days` |
| POST | `/api/query` | SQL result rows | — | aggregates / counts not pre-computed by the list endpoints |

## Practical calling pattern

1. `GET /api/matters?matter_id=<MTR-...>` → confirm the matter exists and capture `hold_date`.
2. `GET /api/subpoena-categories?matter_id=<MTR-...>` → capture the full set of `category_code` values. This is the universe every `category_impacts` / `affected_categories` value must come from.
3. Pull each evidence endpoint filtered by `matter_id`: productions, custodian-sources, documents/search, privilege-log, qc-findings, retention-events, remediation-actions. Pull all of them even for narrow deliverables — dashboards cross-reference everything.
4. Use `POST /api/query` for aggregates, e.g. privilege unlogged totals, document counts by coding, category open-issue counts. Keep the SQL read-only (`SELECT` only).

## SQL request shape

```bash
curl -s -X POST http://task-env:9017/api/query \
  -H 'X-API-Key: review-key-017' \
  -H 'Content-Type: application/json' \
  -d '{"query": "SELECT category_code, SUM(withheld_count - logged_count) AS unlogged FROM privilege_entries WHERE matter_id = :mid GROUP BY category_code"}'
```

Pass `matter_id` as a bind parameter when supported, or inline it as a quoted string literal after confirming the value matches a known matter ID. Never `SELECT *` for the final answer — name the columns you need so the row order and shape are stable.

## Discipline reminders

- Do not read environment source files, database files, seeds, manifests, setup scripts, generated data, hidden notes, or task answer/evaluation files. The hub is the only business-evidence source.
- `environment_access.md` is for network access only; it is not a data source.
- If the hub returns an unexpected structure or an unknown matter, treat that as a signal to re-check the `matter_id` from the payload — do not fabricate records to fill the gap.
