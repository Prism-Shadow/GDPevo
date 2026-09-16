---
name: investigation-review-hub
description: >
  Produce structured ediscovery investigation deliverables using the
  Investigation Review Hub REST API. Use this skill whenever the user
  mentions investigation review, gap analysis, privilege review,
  production readiness, remediation dashboard, retention review,
  custodian review, QC findings, subpoena categories, or any task
  that requires structured JSON output from a review-hub environment.
  Even when the user asks for a single metric or endpoint, consider
  whether the full hub workflow is needed — the task environment
  typically provides a `<TASK_ENV_BASE_URL>`, answer templates,
  and payload files that together demand end-to-end hub interaction.
---

# Investigation Review Hub

## Overview

The Investigation Review Hub is a read-only REST API that models an
ediscovery and investigation matter workspace. It surfaces matters,
subpoena categories, custodian sources, document metadata, privilege
logs, QC findings, retention events, remediation actions, and
production status. A companion SQL query endpoint (`POST /api/query`)
supports multi-table joins, aggregations, and complex filters.

The hub is deployed at a base URL the task provides — usually through a
`<TASK_ENV_BASE_URL>` placeholder in the prompt or a local payload file.
All business evidence lives in the hub; local payload files supply only
task-level context: matter ID, category labels, template schemas, and
deliverable type.

Common deliverables include rolling production gap analysis, retention
and litigation-hold gap review, cross-system remediation dashboards, and
production-readiness reviews. Each deliverable has its own answer
template JSON. The solver's job is to read the template, gather evidence
from the hub, and return a single JSON object that conforms exactly.

## Core Workflow

Follow these steps in order. Do not skip the payload reads or the schema
read.

### 1. Read every file in the task payload directory

Always read:

- `prompt.txt` — the request, matter context, and deliverable type
- `answer_template.json` — the exact output schema defining required
  top-level keys, enums, ordering rules, and field types
- Any context/scope files (`request_context.json`, `review_scope.json`,
  `matter_context.json`) — these provide the matter ID, client name,
  category-code synopses, and request parameters

Note the `<TASK_ENV_BASE_URL>` placeholder and the `X-API-Key` value
when one is specified for the SQL query endpoint.

### 2. Confirm the matter exists

```
GET <TASK_ENV_BASE_URL>/api/matters
```

Match the `matter_id` from the payload against the hub response. If the
hub includes a client name field, cross-check it against the payload
to confirm you are looking at the right matter.

### 3. Read the API schema

```
GET <TASK_ENV_BASE_URL>/api/schema
```

This returns the database table names, column definitions, and
relationships. Use it to understand which tables hold the evidence you
need before querying them. The schema tells you which columns join
across tables — essential for crafting correct SQL queries.

### 4. Gather evidence from every relevant hub endpoint

Pull data from these endpoints, in parallel when possible:

| Endpoint                    | Purpose                                    |
|-----------------------------|--------------------------------------------|
| `/api/matters`              | Matter confirmation and metadata           |
| `/api/subpoena-categories`  | Request category codes and descriptions    |
| `/api/productions`          | Per-category production status and volumes |
| `/api/custodian-sources`    | Source collection status, types, custodians|
| `/api/documents/search`     | Document coding, responsive status, produced/withheld flags |
| `/api/privilege-log`        | Withheld documents, logged entries, third-party recipients |
| `/api/qc-findings`          | Miscoded documents, zero-claim contradictions, quality flags |
| `/api/retention-events`     | Retention losses, policy destructions, hold dates |
| `/api/remediation-actions`  | Existing remediation plans and owners      |

Read the raw response of each endpoint carefully. The hub may return
arrays keyed by matter; filter to the current matter when needed.

### 5. Use the SQL endpoint for complex evidence

When simple GET endpoints do not provide enough cross-reference or
aggregation, use:

```
POST <TASK_ENV_BASE_URL>/api/query
Header: X-API-Key: review-key-017
Content-Type: application/json

{ "query": "SELECT ... FROM ... WHERE ..." }
```

Common scenarios that need SQL:
- Linking documents to categories and QC findings in one query
- Aggregating privilege-log counts (withheld vs. logged vs. unlogged)
- Finding document-to-category mappings for responsive miscodes
- Computing per-category open-issue counts

Use the schema from step 3 to write correct joins. Prefer simple,
auditable queries over monolithic ones.

### 6. Build the answer JSON

Construct the output by mapping hub records into the template shape:

**Stable IDs** — Every finding, risk, issue, action, and correction ID
in the answer must be a real hub record ID (`DOC-*`, `PRIV-*`, `QC-*`,
`SRC-*`, `RET-*`, or similar). Never invent IDs for evidence anchors.
When a single hub record is the primary anchor for a finding, use that
record's ID as the finding/risk/issue ID. For action IDs that do not
exist in the hub (`ACT-*`), construct them from the matter abbreviation
and a counter, but all `target_refs`, `source_refs`, and evidence IDs
must be real hub identifiers.

**Counts** — Derive every integer from hub data. Count documents,
withheld entries, logged entries, unlogged entries, sources, boxes,
and events directly from endpoint responses or SQL aggregation results.
Do not estimate or copy counts from template descriptions.

**Enums** — Use exactly the enum values defined in the answer template.
Every field that lists `enum:` or `enum_choices:` choices must take one
of those exact strings. Do not coin new statuses, issue types, or
action types. If the template says the valid values for `severity` are
`critical` / `high` / `medium` / `low`, use only those four strings.

**Ordering rules** — Follow the template's ordering directives
strictly. Sort by `finding_id`, `category_code`, `priority_rank`,
`event_id`, `source_id`, or `correction_id` as the template requires.
Category-code sets nested within lists must also be sorted ascending.

**Category codes** — Use uppercase category codes exactly as they
appear in the hub (`/api/subpoena-categories` or the SQL schema).
Codes may be single letters, numeric-prefixed, or agency-prefixed.
Always match the hub's exact representation; do not reformat them.

### 7. Validate before returning

Before finalizing, check:
- Every required top-level key is present
- Every nested object has all required keys from the template's item
  schema
- All enums match the template's allowed values
- All lists are sorted per ordering rules
- Numeric fields are whole integers (no floats)
- The answer is a single JSON object with no wrapping prose

## Hub Domain Model

Understanding entity relationships helps you navigate the evidence.

```
Matter
 ├── Subpoena Categories  (request categories under a subpoena)
 ├── Custodian Sources    (people/systems; each has collection status)
 │    └── Documents       (coding: responsive/nonresponsive,
 │                          privileged/nonprivileged, produced/withheld)
 ├── Privilege Log        (withheld documents logged or unlogged;
 │                          may include third-party recipients)
 ├── QC Findings          (review-quality flags linked to documents or
 │                          privilege entries; miscodes, contradictions)
 ├── Retention Events     (record-destruction events; pre-hold
 │                          policy-compliant or post-hold loss)
 ├── Remediation Actions  (already-planned corrective steps)
 └── Productions          (per-category volumes and status)
```

**Key joins for SQL queries:**

- Documents ↔ QC Findings: join on document ID or QC finding's
  document reference
- Subpoena Categories ↔ Documents: the hub typically maps categories
  to documents through a join table or category-code column
- Custodian Sources ↔ Documents: join on custodian/source ID
- Privilege Log ↔ Documents or Categories: join on privilege-log
  entry references
- Retention Events ↔ Categories: retention events reference affected
  category codes in their payload

## Answer Construction Rules

### Deriving findings from hub data

Every finding (gap, risk, defect) must be evidence-backed by hub
records. Look for:

1. **Retention losses** — retention-events with `post_hold_loss`,
   `active_system_loss`, `auto_purged`, or `should_exist_missing` status
2. **Collection gaps** — custodian-sources with `not_collected`,
   `partial`, or `lost` status
3. **Responsive miscodes** — QC findings flagging nonresponsive or
   zero-claim documents that are actually responsive; cross-check with
   documents/search
4. **Privilege log gaps** — privilege-log entries where withheld count
   exceeds logged count (unlogged > 0)
5. **Third-party waiver** — privilege-log entries showing third-party
   recipients on withheld communications
6. **Privilege miscoding** — QC findings flagging privileged documents
   coded nonprivileged, or nonprivileged documents coded privileged

For each finding include the anchor hub record ID, the correct
`issue_type` from the template's enum, a severity/risk_level based on
impact, all affected category codes, supporting source refs, and
accurate integer counts from the hub.

### Counting privilege-log gaps

When a privilege-log record shows withheld_count ≠ logged_count:
`unlogged_count = withheld_count - logged_count`. Report all three
integers.

### Building category statuses

For each subpoena category, determine its status by aggregating all
findings, sources, and production records that reference it:
- Uncollected/lost source → collection gap, preservation risk, or
  source missing
- Privilege-log gaps → privilege_log_gap, withheld_unlogged
- Responsive miscodes → responsiveness_gap, incomplete, underproduced
- Both preservation losses and privilege issues → combine into
  underproduced, multiple_blockers, or similar as the template allows
- Available remediation source → note as archive_available or similar

Use only statuses from the template's category_status/readiness_status
enum. Derive `open_issue_count` by counting distinct hub records that
reference the category and represent open issues.

### Building priority actions

Actions derive directly from findings:
- Critical findings need P0 actions
- High-severity findings need P1 actions
- Each action targets specific hub record IDs
- Assign owners from the template's `owner` enum based on action type
- Sort by priority_rank ascending

### Numeric precision

All counts are whole integers. Never use floats, decimals, or ranges.
When a template field says "use 0 when not applicable," use 0, not null
or omission.

## SQL Query Patterns

The SQL endpoint uses standard SQL syntax. Always read `/api/schema`
first to confirm table and column names, then use patterns like:

**Document-to-category mapping:**
```sql
SELECT d.id, d.coding, d.produced_status, c.category_code
FROM documents d
JOIN document_categories dc ON d.id = dc.document_id
JOIN subpoena_categories c ON dc.category_code = c.code
WHERE d.matter_id = '<MATTER_ID>'
```

**Privilege-log aggregation:**
```sql
SELECT id, withheld_count, logged_count,
       (withheld_count - logged_count) AS unlogged_count
FROM privilege_log
WHERE matter_id = '<MATTER_ID>'
```

**QC findings with document context:**
```sql
SELECT qc.id, qc.finding_type, qc.severity,
       d.id AS doc_id, d.coding, d.category_code
FROM qc_findings qc
LEFT JOIN documents d ON qc.document_id = d.id
WHERE qc.matter_id = '<MATTER_ID>'
```

Table and column names vary per deployment. The schema endpoint is
your authoritative reference for the current environment.

## Common Pitfalls

- **Inventing IDs**: Never create evidence IDs. All `target_refs`,
  `source_refs`, `issue_refs`, `blocking_refs`, and record references
  must be real hub IDs. The only IDs you may construct are action plan
  IDs (`ACT-*`) when the hub has no pre-existing action records.

- **Wrong enum values**: The template defines the exact set of allowed
  strings. Do not use near-misses like "missing_source" when the enum
  requires "source_missing", or "high_risk" when it requires "high".

- **Skipping the schema read**: Without `/api/schema`, SQL queries are
  guesswork. Always read it before writing any query.

- **Missing payload context**: `review_scope.json` or
  `matter_context.json` often contains the only human-readable mapping
  of category codes to topics. Without it, you cannot accurately
  assign categories to findings or write category summaries.

- **Ignoring ordering rules**: The template's `ordering_rules` block
  is part of the schema contract. Unsorted lists and category-code
  sets are incorrect.

- **Floating-point or null counts**: Every count field expects a whole
  integer. If a computation would produce a fraction, re-examine the
  hub records — something is miscounted. Never substitute null for zero.

- **Copying template descriptions as evidence**: The template describes
  the output shape, not the evidence. Derive all substantive values
  (IDs, counts, statuses, categories) from the hub, not from template
  field descriptions or enum lists.
