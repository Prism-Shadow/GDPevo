# Investigation Review Hub — Endpoint Reference

This documents what each hub endpoint provides, generically. The **base URL, the SQL
API key, and the exact allow-list of endpoints are read from `environment_access.md` at
run time** — do not hardcode them. If `environment_access.md` does not list an endpoint
below, treat the live allow-list as authoritative and skip the missing endpoint.

All endpoints are matter-scoped: filter results to the target `matter_id` unless the
endpoint already takes a matter parameter.

| Endpoint | Returns | Use it for |
|---|---|---|
| `GET /api/schema` | Tables, columns, relationships | Understanding the data model before querying |
| `GET /api/matters` | Matter records | Confirming `matter_id`, hold date, review cutoff, client |
| `GET /api/subpoena-categories` | Request category codes + labels | The authoritative category-code family for the answer |
| `GET /api/productions` | Production status per category | What is produced / withheld / not produced |
| `GET /api/custodian-sources` | Custodian source records | Source type, custodian, collection status (collected / partial / not_collected / lost) |
| `GET /api/documents/search` | Review documents | Document coding (responsive / nonresponsive / privileged), produced status, category linkage |
| `GET /api/privilege-log` | Privilege log entries | Withheld vs logged counts, log completeness, third-party recipients, waiver flags |
| `GET /api/qc-findings` | QC findings | Responsive miscodes, privilege miscodes, zero-claim contradictions, over-designation |
| `GET /api/retention-events` | Retention/preservation events | Event date, hold date, policy section, status (pre-hold policy loss / post-hold loss / auto-purge / active system loss / should-exist-missing), volume |
| `GET /api/remediation-actions` | Candidate remediation actions | Action type, owner, priority, target refs |
| `POST /api/query` | Arbitrary read-only SQL result | Cross-table aggregation when list endpoints are insufficient. **Requires the `X-API-Key` header** whose name and value are in `environment_access.md`. Read-only — never issue writes. |

## Querying discipline

- Prefer the typed list endpoints first; they encode the hub's intended access patterns.
- Reach for `POST /api/query` only for a genuine cross-table rollup (e.g. withheld minus
  logged grouped by category, or distinct personal sources by status). Keep queries
  read-only `SELECT`s.
- Always scope by `matter_id`. Mixing records across matters is the most common source
  of wrong counts.
- Re-derive every value from the hub response. Do not cache counts between runs or
  assume a value from a prior matter.
