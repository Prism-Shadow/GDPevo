---
name: investigation-review-hub
description: Query an Investigation Review Hub REST API to produce structured JSON review dashboards for e-discovery, legal-hold gap analysis, privilege review, production readiness, and cross-system remediation. Use this skill whenever the task mentions an Investigation Review Hub, a matter-based subpoena or regulatory review, legal-hold gap analysis, production readiness review, privilege-log QC, retention-event tracking, or remediation dashboards tied to REST endpoints at a provided base URL. Trigger even when the user describes ediscovery workstreams, grand jury or SEC subpoena reviews, or asks for a structured JSON deliverable from review-hub endpoints.
---

# Investigation Review Hub

Produce structured JSON dashboards by querying a read-only Investigation Review
Hub REST API. The hub exposes matter metadata, subpoena categories, production
stats, custodian sources, review documents, privilege-log entries, QC findings,
retention events, and remediation actions — all scoped by matter_id or
queryable through a SQL endpoint.

## When to use this skill

Use this skill when all of these conditions hold:

1. The task references an "Investigation Review Hub" and provides a base URL.
2. The deliverable is a structured JSON object that synthesizes evidence from
   multiple hub endpoints.
3. An answer template (JSON schema file) is provided in the task payloads.

If any condition is absent, handle the task with your general tools instead.

## Workflow

### Phase 1 — Discover and validate the environment

1. **GET /** from the base URL. Confirm the service is up and note the
   response service field to confirm it is the Investigation Review Hub.
2. **GET /api/schema** to learn the available table structures. This endpoint
   lists every table, its columns and column types. Use it to understand what
   fields are available before writing SQL queries.
3. If the task payload refers to a query_api_key_header (typically
   X-API-Key), save that header name and value. All POST /api/query calls
   must include it.

### Phase 2 — Scope and gather

Identify the matter_id from the task prompt or payload. Every hub endpoint
that supports a ?matter_id= filter should be called with that value.

Call these GET endpoints, each filtered by matter_id when supported:

| Endpoint | What it provides |
|---|---|
| /api/matters | Matter metadata (agency, hold date, lead partner, status) |
| /api/subpoena-categories | Request categories with codes, date ranges, descriptions |
| /api/productions | Per-category production batches with produced/withheld/responsive counts and status |
| /api/custodian-sources | Custodian device/source records with collection status, post-hold flag, and category impacts |
| /api/documents/search | Individual review documents with responsiveness coding, privilege status, issue tags |
| /api/privilege-log | Privilege entries with withheld/logged counts, issue types, third-party flags |
| /api/qc-findings | QC findings with issue types, affected categories, severity, doc counts |
| /api/retention-events | Retention events with status, policy sections, volume counts, affected categories |
| /api/remediation-actions | Pre-existing remediation action records with owners, priorities, target refs |

Some of these endpoints may require matter_id as a query parameter. The hub
returns {"count": N, "rows": [...]} for each. Process every row.

For queries that need filtering beyond what the GET endpoints support, use:

    POST /api/query
    Headers: Content-Type: application/json, X-API-Key: <key>
    Body: {"sql": "<SQL query using tables from /api/schema>"}

Always scope SQL queries to the task matter_id in the WHERE clause. Use
column names exactly as they appear in /api/schema.

### Phase 3 — Cross-reference evidence

The hub record IDs form a web of relationships. When you assemble findings:

- A doc_id from /api/documents/search may be referenced in
  /api/qc-findings via source_ref.
- A source_id from /api/custodian-sources may be referenced in
  /api/retention-events via source_ref.
- A privilege entry_id from /api/privilege-log is the canonical reference
  for privilege-linked metrics.
- A batch_id from /api/productions may appear as the batch_id in
  /api/qc-findings.
- A retention event_id may be cross-referenced in
  /api/remediation-actions via target_ref.

When the answer template asks for source_refs, record_refs, issue_refs,
blocking_refs, or target_refs, use the stable hub IDs you observed — not
invented values. Sort them ascending.

When category codes are listed in the answer, use the exact codes from
/api/subpoena-categories (or from the task-provided payloads if they override
labels). Sort category codes ascending.

### Phase 4 — Fill the template

Read the answer template JSON file from the task payloads. It defines:

- required_top_level_keys — every top-level key must appear in your answer.
- fields — the type, sub-keys, and constraints for each section.
- enums — the allowed values for each enum field. Pick values only from
  these lists.
- ordering_rules — how to sort lists within the answer.

Rules for filling the template:

1. **Match key names exactly.** If the template expects category_code, do not
   call it code or category.
2. **Use enum values verbatim.** If the template defines severity as
   ["critical", "high", "medium", "low"], use those strings, not variants
   like "Critical" or "CRITICAL".
3. **Sort lists per ordering rules.** If the template says sort by
   priority_rank ascending, do that.
4. **Use integers for counts.** All document_count, withheld_count,
   volume_count, and similar fields are whole integers. Use 0 when not
   applicable, never null.
5. **Use null for optional fields only when the template allows it.** String
   fields like third_party or missing_component may be null when no value
   exists; numeric fields default to 0.
6. **Only include list items that have a material status.** The template
   description often says "one object per category with a material non-complete
   status" or similar. Do not include categories or items that have no
   findings.
7. **Return exactly one JSON object and no prose outside the JSON.** The
   answer must be parseable as JSON without any surrounding text.

### Phase 5 — Verify

Before finishing:

- Confirm every required top-level key is present.
- Confirm every nested object has all required keys.
- Confirm all enum values match the template allowed lists.
- Confirm sorting follows the template ordering rules.
- Confirm all record IDs are actual hub IDs, not invented.
- Confirm numeric counts are whole integers.
- Run a quick JSON parse to catch syntax errors.

## Using the SQL endpoint

When the GET endpoints do not provide the needed aggregation or filtering, use
POST /api/query. The schema from /api/schema defines available tables and
columns. Build queries that:

- Scope to the task matter_id.
- Use standard SQL compatible with SQLite (the hub backend).
- Keep queries simple — SELECT with WHERE, GROUP BY, ORDER BY. Avoid CTEs or
  window functions unless you have confirmed they work.

If a query returns truncated: true, refine the WHERE clause or add LIMIT.

## Reference: API guide

For detailed endpoint descriptions, response shapes, and cross-referencing
patterns read [references/api-guide.md](references/api-guide.md).

## Common pitfalls

- **Not filtering by matter_id.** The hub contains records for many matters.
  Always scope your requests.
- **Inventing record IDs.** Every ID must come from the hub. If you cannot find
  a stable ID for a finding, use the most specific hub record that anchors it.
- **Using the wrong enum values.** Enum lists in the answer template are
  authoritative. Do not use synonyms or variants.
- **Including non-material items.** If a category has no gaps, do not include
  it in the category_statuses list unless the template explicitly requires all
  categories.
- **Skipping cross-references.** A template field like source_refs often
  needs IDs from multiple endpoints — cross-reference before writing.
- **Returning prose with the JSON.** The final answer must be a single JSON
  object with no markdown fences, no commentary, no trailing text.
