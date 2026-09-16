---
name: investigation-review-hub
description: Provides a disciplined workflow for querying an Investigation Review Hub REST API to build structured e-discovery review deliverables (gap analyses, privilege audits, production-readiness assessments, retention reviews, cross-system remediation dashboards). Use this skill whenever the user mentions subpoena response, litigation-hold review, privilege-log analysis, production readiness, retention gap assessment, QC remediation, or any investigation/e-discovery review task that references a shared hub API with endpoints like /api/matters, /api/documents/search, /api/privilege-log, /api/qc-findings, /api/retention-events, /api/custodian-sources, and /api/query.
---

# Investigation Review Hub Skill

## What this skill does

Teaches a repeatable method for turning a shared Investigation Review Hub REST API into structured review deliverables. The solver's job is to gather evidence from the hub, map it into a client-provided answer template, and return exactly one JSON object. The approach works for gap analyses, retention reviews, privilege audits, production-readiness checklists, remediation dashboards, and similar structured review tasks.

## High-level workflow

Every task in this family follows the same five-stage pattern. Execute stages in order and do not skip discovery.

### Stage 1: Understand the output contract

The answer template is the single source of truth for what to return. Read it first.

Locate the answer template file -- it is always a JSON file staged under `input/payloads/` with a name like `answer_template.json` or `answer.json`. Study it end to end:

- **required_top_level_keys**: Every key listed here must appear in the final answer. If any is omitted the output is invalid.
- **ordering_rules**: Sort every list exactly as stated (usually ascending by a stable key or rank field).
- **enums / enum_choices**: Every categorical field must use only the values listed. Inventing a new status, severity, or action type will break validation.
- **item_required_keys**: Every object inside a list must include every key in this list -- even when the value feels like zero or null for that record.
- **field_types / item_field_types**: Note which fields expect integers, strings, lists, or booleans. Numeric fields default to `0` when not applicable, not `null`. Nullable strings use `null` explicitly when the template allows it.
- **numeric_precision**: Counts are always whole integers. Never use decimal places for document counts, source counts, or day counts.

### Stage 2: Read any context payloads

Some tasks include a second payload file -- names vary (`request_context.json`, `review_scope.json`, `matter_context.json`). This file provides task-specific framing:

- The `matter_id` to review
- Category codes and their descriptive titles
- The `environment_base_url` placeholder (usually `<TASK_ENV_BASE_URL>`)
- Optional API key header instructions (`X-API-Key: review-key-017` or similar)
- Any source constraints or category synopses

Use this context to know which matter to target and which categories are in scope. Never assume a matter ID or category code from a previous task.

### Stage 3: Discover the hub schema

Before querying for specific answers, explore the hub to understand what data is available and what fields each endpoint returns.

1. Call `GET /` on the hub base URL to confirm connectivity.
2. Call `GET /api/schema` to see available endpoints and field listings. This reveals which endpoints exist, what query parameters they accept, and what fields their responses contain.
3. Optionally call `GET /api/matters` to list available matters and confirm the target matter exists.

Treat the schema as an inventory. It tells you:
- Which endpoints carry retention events, which carry privilege data, which carry QC findings, etc.
- What ID field types each record uses (e.g., `event_id`, `source_id`, `document_id`, `finding_id`)
- What status fields and date fields are available
- Which fields are nullable and which are always present

### Stage 4: Gather evidence from the hub

Query every endpoint that the answer template's structure implies. The template's keys and enum values tell you which hub resources matter.

Common evidence-gathering patterns, mapped to answer-template concerns:

| Template concern | Hub endpoint to query |
|---|---|
| Documents, coding, responsiveness | `GET /api/documents/search` |
| Privilege log, withheld/logged counts | `GET /api/privilege-log` |
| QC findings, miscodes | `GET /api/qc-findings` |
| Retention events, destruction, purges | `GET /api/retention-events` |
| Custodian sources, collections | `GET /api/custodian-sources` |
| Production status | `GET /api/productions` |
| Subpoena/request categories | `GET /api/subpoena-categories` |
| Remediation actions | `GET /api/remediation-actions` |
| Complex joins or aggregations | `POST /api/query` (SQL-style, use `X-API-Key` header when required) |

Query in parallel where possible. Multiple GET requests to different endpoints are independent and can fire at once.

For `POST /api/query`:
- Use it when the template requires counts that span multiple resources or when you need to join records.
- Include the `X-API-Key` header only when the context payload explicitly provides one (commonly `review-key-017`). If no key is mentioned, the query endpoint may not be available.
- Write simple, targeted SQL queries. Start with `SELECT` to explore table schemas, then build aggregation queries.

### Stage 5: Map evidence to the template

Build the answer from the evidence, one top-level key at a time.

**Stable IDs are non-negotiable.** Every reference in the answer (`finding_id`, `risk_id`, `issue_id`, `event_id`, `source_id`, `correction_id`, `target_refs`, `source_refs`, `blocking_refs`, `issue_refs`) must be the exact identifier string returned by the hub. Never abbreviate, renumber, or invent IDs. When a finding is anchored by a document record, use that document's ID. When anchored by a retention event, use that event's ID.

**Count fields.** Every numeric count must come from the hub evidence, not from guesswork:

- `document_count`, `withheld_count`, `logged_count`, `unlogged_count` come from privilege-log and document-search responses.
- `volume_count` and `volume_unit` come from retention-event and source records.
- Source counts (personal device, board, archive) come from custodian-sources.
- When a record does not carry a count payload, use `0` -- never invent a number.

**Category codes.** Use the exact codes from the hub or the context payload's category synopsis. Sort category code lists ascending (lexicographically) everywhere the ordering rules say so.

**Enums are closed sets.** Consult the template's enum or choices list before assigning any categorical field. Common families seen across review-hub tasks include:

- **Issue/risk types**: `post_hold_loss`, `personal_source_gap`, `responsiveness_miscode`, `privilege_log_gap`, `third_party_waiver`, `privilege_miscoding`, `preservation_failure`, `collection_gap`, `missing_required_record`, and others defined in the template.
- **Severity/risk levels**: `critical`, `high`, `medium`, `low`.
- **Action types**: `disclose_preservation_issue`, `supplement_privilege_log`, `recode_and_produce`, `collect_personal_device`, `search_archive`, `waiver_assessment_and_disclosure`, `privilege_recode_and_log`, `qc_remediation`, `collect_source`, `locate_missing_record`, `forensic_recovery`, and others defined in the template.
- **Owners**: `outside_counsel`, `privilege_counsel`, `privilege_team`, `review_qc`, `ediscovery_vendor`, `forensics`, `compliance_audit`, `client_legal`, `client_it`, `records_management`, `it_messaging`, `litigation_counsel`, `legal_operations`, and others.
- **Priority**: `P0`, `P1`, `P2`, `P3` (with `P0` as the most urgent).

**Sorting and ordering.** Respect every ordering rule in the template:

- Lists of findings, risks, issues, and statuses are sorted by their primary ID field ascending unless the template specifies a rank field.
- Action plans are sorted by `priority_rank` or `rank` ascending.
- Category code arrays within objects are sorted ascending.

**Metrics.** Build the `metrics` object last, after all evidence is in. Every metric field listed in the template's `required_keys` must appear in the output. Derive counts from the evidence already captured:

- Sum counts across records of the same type.
- `affected_category_count` is the count of distinct category codes that appear in any finding.
- `categories_with_open_risk` or `categories_with_open_gaps` is the list of those distinct codes sorted ascending.
- Boolean fields like `production_ready` or `rolling_production_ready` are `false` when any material gap exists.

**Action plans.** Derive each action from a finding or risk record. Actions should:

- Point `target_refs` at the hub record IDs that need attention.
- List `category_impacts` (or `affected_categories`) from the affected categories of the source finding.
- Assign realistic `due_days` (3 for critical disclosure, 5-7 for collection/recode, 10 for archive search) when the template includes a `due_days` field.
- Use the exact `action_type` and `owner` enums from the template.

### Output rule

Return exactly one JSON object and nothing else. No markdown fences, no explanatory prose, no trailing text. If the prompt says "Return only a JSON object" or "no prose outside the JSON," comply exactly.

## Common pitfall checklist

- **Skipping the template read:** Not reading the answer template carefully before querying the hub leads to gathering the wrong evidence or missing required fields.
- **Inventing IDs:** Every reference must be a stable hub ID. If the hub does not provide an ID for something, that thing does not belong in a reference field.
- **Mixing enum sets:** Each answer template defines its own enum values. Do not carry enums from memory or from another task's template.
- **Omitting zero-count fields:** `item_required_keys` means every key must be present, even when the value is `0`, `null`, or an empty list `[]`.
- **Wrong sort direction:** Ordering rules say "ascending" -- verify sort direction before writing the answer.
- **Narrative instead of JSON:** The deliverable is always structured JSON. Never produce a memo, summary, or explanation unless the prompt explicitly asks for both.
- **Partial evidence:** Templates often require data from four or more hub endpoints. Query them all. A gap analysis that only checks documents but misses retention events is incomplete.
- **Ignoring the base URL:** The prompt always contains `<TASK_ENV_BASE_URL>` as a placeholder. Replace it with the actual environment URL before making any API call. If no URL is visible in the prompt text, check payload files.
