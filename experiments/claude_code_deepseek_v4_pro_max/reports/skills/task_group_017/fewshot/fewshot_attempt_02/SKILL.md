# Investigation Review Hub — Structured JSON Deliverable

Use the shared **Investigation Review Hub** as the exclusive source of record to
produce a structured JSON deliverable for an eDiscovery / legal-investigation
matter (gap analysis, retention review, remediation dashboard,
production-readiness review, or a similar workstream).

## 1. Discover the environment

Read `environment_access.md` for the live base URL and API credentials.
The file supplies:

- `base_url` — the root of the Investigation Review Hub (e.g. `http://task-env:9017/`)
- `credentials.sql_endpoint_header` — the HTTP header name used to authenticate
  read-only SQL queries (e.g. `X-API-Key`)
- `credentials.sql_endpoint_api_key` — the API key value for that header
- `allowed_endpoints` — the REST endpoints available in this deployment

Every REST endpoint call is unauthenticated; only the SQL endpoint requires the
header.

**Do not use local environment files, database files, source code, generation
manifests, seeds, or setup scripts.**  The hub is the canonical data source;
`environment_access.md` always overrides any `<TASK_ENV_BASE_URL>` placeholder
or localhost reference found in task inputs.

## 2. Understand the task

Read every file in the task's `input/` directory.  Typical contents:

- **`prompt.txt`** — the natural-language brief naming the client, matter,
  workstream, and deliverable.  Extract the matter ID, review type, and any
  special focus areas (e.g. "first rolling production gap analysis", "retention
  and litigation-hold gap review", "cross-system remediation dashboard").
- **Payload files** (e.g. `request_context.json`, `review_scope.json`,
  `matter_context.json`) — static client-facing context: matter identifier,
  category synopses, review labels, and any per-task constraints.  Use these
  for framing only; **do not treat them as evidence**.
- **`answer_template.json`** — the required output schema.  See §3.

## 3. Master the answer template

`answer_template.json` defines the contract for the deliverable.  Read it
carefully before touching a single endpoint.  Pay attention to:

### 3a. Required top-level keys

`required_top_level_keys` lists every key that must appear at the root of the
returned JSON object.  Missing keys make the answer invalid.

### 3b. Ordering rules

`ordering_rules` tells you how to sort every list in the output.  The
convention is always **ascending** by the designated sort key.  Category codes
are sorted alphanumerically.  Priority/rank fields use `1` as highest priority;
sort `1, 2, 3, …`.

### 3c. Enums

Every enum block (keyed by `enums`, `enum_choices`, or inside `fields.*.item_fields`)
lists the **only** valid string values for that field.  Never invent a value
outside the enumerated set.  When a field's enum includes a sentinel like
`"not_applicable"`, `"unknown"`, `"no_action"`, or `"no_production_impact"`,
use it when the hub data does not supply a positive value — do not omit the
field.

### 3d. Field definitions

The `fields` block defines each top-level key's shape:

- `item_required_keys` — every object in a list must include these keys.
- `item_fields` / `item_field_types` — type and semantics of each field.
- Numeric fields use `0` when not applicable (never `null` for counts).
- List fields like `source_refs`, `category_impacts` must be sorted ascending.

### 3e. Numeric precision

All counts are **whole integers**.  Metric fields (document counts, source
counts, event counts, box counts) come from the hub's own record counts or
from explicit volume fields.

## 4. Query the hub

The endpoints listed in `environment_access.md`'s `allowed_endpoints` are the
surface area of the hub.  Each deployment includes at least:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Health / index |
| GET | `/api/schema` | Table/view schemas for `POST /api/query` |
| GET | `/api/matters` | Matters including the target matter |
| GET | `/api/subpoena-categories` | Request / subpoena categories |
| GET | `/api/productions` | Production status records |
| GET | `/api/custodian-sources` | Custodian and source records |
| GET | `/api/documents/search` | Document records (can filter by matter, category, coding, privilege status, etc.) |
| GET | `/api/privilege-log` | Privilege-log entries |
| GET | `/api/qc-findings` | QC findings (miscodes, zero-claim contradictions, etc.) |
| GET | `/api/retention-events` | Retention events (losses, purges, pre/post-hold destruction) |
| GET | `/api/remediation-actions` | Remediation-action records |
| POST | `/api/query` | Read-only SQL queries (include the credential header) |

### 4a. REST endpoints — GET with query parameters

Most GET endpoints accept query-string filters (e.g. `?matter_id=…`,
`?category_code=…`, `?status=…`).  Exploit these to narrow results to the
target matter before inspecting the JSON.  If an endpoint returns paginated
results, follow the pagination links or use the SQL endpoint for a single-shot
aggregate query.

### 4b. SQL endpoint — POST /api/query

Use `POST /api/query` when you need cross-entity counts, grouped aggregates, or
complex filters.  Send the `X-API-Key` (or the header name from
`environment_access.md`) with the key value.  The request body is a JSON object
with a `"query"` field containing the SQL string.

Examples of useful SQL queries:

- Count withheld vs logged privilege documents per category.
- Count QC findings by type and severity for the target matter.
- Count custodian sources by collection status.
- Sum volumes (boxes, documents) for retention events broken out by pre-hold vs
  post-hold.

Always query by the matter ID to scope results to the current engagement.

### 4c. Hub record IDs are stable

Every entity returned by the hub has a stable ID (e.g. `SRC-*-*`, `DOC-*-*`,
`PRIV-*-*`, `QC-*-*`, `RET-*-*`).  Use these IDs **exactly as they appear** for
`finding_id`, `risk_id`, `issue_id`, `source_refs`, `target_refs`, and any other
reference field in the answer.  Do not manufacture IDs.

## 5. Assemble the deliverable

### 5a. Map the evidence to the answer structure

For each required key in the answer template, pull the relevant evidence from
the hub:

- **Critical findings / Top risks / Issue ledger** — one object per material
  gap, defect, or risk.  Anchor each to a stable hub record ID.  Derive counts
  (document_count, withheld_count, logged_count, unlogged_count) from the hub's
  own fields; use `0` when the field is not applicable.
- **Category / Readiness statuses** — every subpoena category with a
  non-complete or non-ready status gets an entry.  Aggregate supporting
  references from the findings/issues that impact that category.
- **Retention events / Communication gaps / Available archives / Retained
  sources** — hub entities describing preservation state.  Distinguish
  pre-hold policy destruction from post-hold losses.  Flag available archives
  that can still mitigate gaps.
- **Privilege corrections** — privilege-specific entities (log gaps, waivers,
  miscodes, over-designations) that need remediation.
- **Metrics** — numeric rollup computed from the evidence above.  All metric
  values are whole integers.  Boolean metrics (`production_ready`,
  `rolling_production_ready`) are `true` when zero material blockers remain.
- **Priority actions / Action plan** — ranked remediation steps.  Assign
  `priority_rank`/`rank` starting at `1` (highest priority).  Map each action
  to the exact target record IDs it addresses and the affected categories.
  Use only `action_type` and `owner` values from the template enums.

### 5b. Choose correct enum values

Match the evidence to the best-fitting enum value.  If the evidence supports
multiple plausible values, pick the most specific one.  When no positive enum
fits, use the template's fallback sentinel (e.g. `"not_applicable"`,
`"no_action"`, `"no_production_impact"`, `"unknown"`).

### 5c. Apply ordering rules

Sort every list exactly as the template's `ordering_rules` specify.  If a rule
says "Sort by category_code ascending", the list must be in strict
alphanumeric order by that field.  Within each object, list-type fields like
`category_impacts` and `source_refs` are sorted ascending as well.

### 5d. Validate before returning

Before returning, verify:

- Every `required_top_level_key` is present.
- Every list is sorted per `ordering_rules`.
- Every enum field uses only values from the template's enum set.
- Every count field is a whole integer (not a float, not `null`).
- Every `finding_id` / `risk_id` / `issue_id` / `source_id` / `correction_id`
  is a stable hub record ID, not a fabricated string.
- The JSON is valid and contains no prose outside the JSON.

## 6. Return format

Return **only** the JSON object.  No markdown fences, no preamble, no
commentary.  The output must parse as JSON directly.
