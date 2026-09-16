---
name: investigation-review-hub
description: Solve Investigation Review Hub tasks by querying REST endpoints, mapping hub records into a task-provided answer template, and returning a single JSON object with stable record IDs, enumerated values, sorted lists, and whole-integer metrics.
---

# Investigation Review Hub Solver

Use this skill when the task asks for a structured JSON deliverable anchored to
an Investigation Review Hub matter and provides an `answer_template.json` (or
equivalent) schema file in the input payloads. The hub is a read-only REST API
that serves eDiscovery / litigation review evidence: matters, subpoena
categories, custodian sources, productions, documents, privilege-log data, QC
findings, retention events, and remediation actions.

## High-Level Workflow

1. **Read the prompt.** Identify the matter ID (e.g. `MTR-CLIENT-GJ`), the
   review type (gap analysis, retention review, production-readiness review, or
   cross-system remediation dashboard), and the deliverable format.

2. **Read the answer template.** The task provides a JSON schema file (commonly
   `input/payloads/answer_template.json`) that defines required top-level keys,
   field types, enum choices, ordering rules, and numeric precision. This is
   the authoritative output contract; every field name, enum value, and sort
   order comes from the template, never from invention.

3. **Read every task-local payload.** If the input directory contains
   `request_context.json`, `review_scope.json`, `matter_context.json`, or
   similar, read them. They often carry the client name, category synopses or
   labels, and task-scope notes.

4. **Discover the hub schema.** Call `GET /api/schema` first to learn what
   fields each endpoint returns. This avoids query-time field-name mistakes.

5. **Query the hub endpoints.** Use the full set of available business endpoints
   as the source of record. Filter by the task's matter ID. The standard
   endpoints are:

   - `GET /` – health / server root
   - `GET /api/schema` – data model discovery
   - `GET /api/matters` – matter metadata
   - `GET /api/subpoena-categories` – request categories and codes
   - `GET /api/productions` – production records
   - `GET /api/custodian-sources` – custodian-specific data sources
   - `GET /api/documents/search` – individual documents
   - `GET /api/privilege-log` – privilege claims and log entries
   - `GET /api/qc-findings` – QC issue findings
   - `GET /api/retention-events` – retention and preservation events
   - `GET /api/remediation-actions` – known or proposed remediation actions
   - `POST /api/query` – read-only SQL endpoint (see below)

6. **Map hub records to the template.** Build the output JSON object by
   populating every required key with data drawn from hub endpoints and
   task-local payloads. Use stable record IDs from the hub exactly as they
   appear.

7. **Sort, validate, and return.** Apply the template's ordering rules. Check
   that every enum value matches one of the template's allowed choices, every
   numeric field is a whole integer, and that no prose appears outside the JSON.

## Environment Access

The hub base URL is provided in the task prompt (commonly `TASK_ENV_BASE_URL`
or `task-env:9017`). The read-only SQL endpoint requires:

```
POST /api/query
Header: X-API-Key: review-key-017
```

Other GET endpoints do not require authentication headers. Do not call
`POST /api/judge` or `POST /admin/reset`.

## Template-Driven Output Rules

These rules apply every time regardless of the specific template shape.

### Enforce the template's enums literally

Every field that is declared as an enum must use one of the values listed in
the template for that enum. Never improvise a value; if the data does not match
any enum choice, use the template's catch-all (such as `"other"`, `"unknown"`,
or `"not_applicable"` as defined).

### Honor ordering rules without exception

Templates declare ordering rules such as:

- `critical_findings`: sort by `finding_id` ascending.
- `category_statuses`: sort by `category_code` ascending.
- `priority_actions` / `action_plan`: sort by `priority_rank` ascending.
- Lists of category codes: sort ascending.
- Lists of record IDs: sort ascending.

Sort strictly per the template's rules in every list field.

### Use stable record IDs as anchors

Hub record ID patterns include:

- `DOC-*` – individual documents
- `PRIV-*` – privilege-log entries or privilege-blocker records
- `QC-*` – QC finding records
- `RET-*` – retention events
- `SRC-*` – custodian sources or archive sources
- `ACT-*` – remediation or priority action records

A finding, risk, or issue should use a single hub record ID as its primary key
(`finding_id`, `risk_id`, `issue_id`) when one record anchors the item.
Supporting record refs should use `source_refs` / `record_refs` / `issue_refs`
lists drawn from the same set of hub IDs. Cross-reference consistently: if a QC
finding affects a privilege-log record, both IDs appear where appropriate.

### Numeric precision

All counts are whole integers. Use `0` when a metric is not applicable (e.g. no
withheld documents, no third-party waiver). Use `null` for non-numeric optional
fields that are not applicable (e.g. `third_party`, `missing_component`,
`event_date`, `policy_section`).

### Production readiness boolean

When the template includes a `production_ready` or `rolling_production_ready`
boolean in metrics, set it to `false` if any category has an open gap, loss,
incomplete log, or non-ready status. Set it to `true` only when every category
is confirmed ready with no open issues.

### Action priority mapping

Templates use either a `priority` enum (`P0`, `P1`, `P2`, `P3`) or implied
ranking within `priority_rank` / `rank` integers (1 is highest priority). Match
the priority level to the risk/criticality of the finding:

- `P0` – critical preservation failures, post-hold losses, mandatory
  disclosures to the government.
- `P1` – high-severity privilege-log gaps, privilege waivers, responsive
  miscodes, collection gaps.
- `P2` – medium-severity QC issues, over-designation corrections.
- `P3` – low-severity monitoring items or policy-compliant pre-hold losses.

### Due days (remediation dashboards)

When the template requires `due_days` in the action plan, use short horizons
for critical items and longer horizons for lower-priority remediation:

- Critical / P0 disclosure actions: 3 days.
- High / P1 privilege/QC corrections: 3-5 days.
- Medium / P1 collection actions: 5-7 days.
- Lower / P2 archive searches: 7-10 days.

### Category coverage

Every subpoena/request category from the hub should be represented in the
output's category list. A category with no open issues gets a status of
`"complete"`, `"ready"`, `"no_open_gap"`, or the template's equivalent
no-gap status. Categories with open issues get the specific status that best
describes the dominant blocker.

### Third party fields

When a privilege waiver or exposure involves a third party, populate the
`third_party` field with the name or role of the third party as reported by the
hub (e.g. `a third party name from the hub`, `role descriptor from the hub`,
`role descriptor from the hub`). Set to `null` otherwise.

## Querying the Hub

### GET endpoint queries

Use `curl` with the hub base URL. For matter-scoped endpoints, filter server-side
when the endpoint supports query parameters (e.g.
`?matter_id=MTR-CLIENT-GJ`). When server-side filtering is unavailable,
retrieve the full collection and filter in your mapping step.

### POST /api/query (SQL)

Use the read-only SQL endpoint for joins or complex filters that the REST
endpoints cannot express directly. Send JSON with a `"query"` field:

```bash
curl -s -X POST "$BASE_URL/api/query" \
  -H "X-API-Key: review-key-017" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM documents WHERE matter_id = '\''MTR-EXAMPLE-GJ'\''"}'
```

Parameters: use `'` for string literals in SQL, escaped as `'\''` when passing
through bash single-quoted strings. Use parameterized WHERE clauses sparingly
because the endpoint is read-only and intended for simple filtering and joins.

## Common Task Archetypes

### Gap analysis / Production-readiness review

Output structures include `critical_findings` / `issue_ledger`,
`category_statuses` / `readiness_statuses`, `privilege_corrections` (when
privilege issues are segregated), `metrics`, and `priority_actions`. Map each
hub record that signals a gap to a finding or issue entry, then roll up to
category-level statuses.

### Cross-system remediation dashboard

Output structures include `top_risks`, `category_coverage`,
`retained_or_available_sources`, `metrics`, and `action_plan`. Rank risks by
severity, identify any available archives or sources that can remediate losses,
and provide an action plan with `due_days`.

### Retention and litigation-hold review

Output structures include `retention_events`, `communication_gaps`,
`available_archives`, `metrics`, and `recommended_actions`. Classify each
retention event by whether the loss was policy-compliant pre-hold, a post-hold
loss, an auto-purge, or a missing record that should still exist.

## Final Output Contract

- Return exactly **one JSON object**.
- No prose, commentary, markdown fences, or explanation outside the JSON.
- Every top-level key listed in the template's `required_top_level_keys` must
  be present.
- Every item list must be sorted per the template's `ordering_rules`.
- Every enum field must use one of the template's explicit enum choices.
- All counts are whole integers.
- All IDs are stable strings drawn verbatim from hub responses.

## Anti-Patterns

- Do not invent field names, enum values, or record IDs not present in the
  template or hub.
- Do not use local environment files, database files, seed data, or manifests
  as evidence sources; the hub is the sole source of record.
- Do not copy train-answer values into new task answers.
- Do not call `POST /api/judge` or `POST /admin/reset`.
- Do not skip the schema-discovery step (`GET /api/schema`).
- Do not return prose or markdown wrapping around the JSON output.
- Do not omit categories that have no gaps; include them with the appropriate
  no-gap status.
