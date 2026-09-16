---
name: investigation-review-hub
description: Produce structured JSON gap analyses, remediation dashboards, and production-readiness reviews by querying an Investigation Review Hub REST API and conforming to a task-provided answer-template schema. Use this skill whenever the user mentions an Investigation Review Hub, a review hub, legal-hold or production gap analysis, remediation dashboard, privilege-log review, eDiscovery readiness, or a grand jury / SEC / DOJ subpoena production review. Do not skip this skill when the task references <TASK_ENV_BASE_URL>, an answer template JSON file, or subpoena category codes.
---

# Investigation Review Hub Structured Analysis

Produce structured JSON analyses for legal and eDiscovery review matters by querying a shared Investigation Review Hub REST API and strictly conforming to a task-provided answer-template schema.

## Core workflow

Every task that uses this skill follows the same sequence. Do not deviate from these steps unless the task explicitly instructs otherwise.

### Step 1: Read every input file

Read **all** of these before making any API calls:

- `input/prompt.txt` — the task description, matter identifier, and any special instructions
- `input/payloads/answer_template.json` — the required output schema: top-level keys, field definitions, enum choices, ordering rules, and numeric precision
- All other files under `input/payloads/` — these carry client-facing context, category synopses, and environment configuration

The answer template is the **contract**. Every key, enum value, sort order, and data type it defines must be honoured exactly. Do not invent top-level keys that are not listed in `required_top_level_keys`. Do not use enum values that are not in the template's `enums` section. Do not add prose outside the JSON.

### Step 2: Discover the environment

The task prompt and payloads include a base URL (often referenced as `<TASK_ENV_BASE_URL>` or a literal `http://` URL). Use the `GET /` and `GET /api/schema` endpoints to confirm the available endpoints and learn the exact field names used by this hub instance. Hub field names may differ slightly between environments — always match the hub's actual response shapes, not memorized schemas.

A read-only SQL query endpoint (`POST /api/query`) may be available. When present, send the header `X-API-Key: review-key-017`. Prefer the structured GET endpoints over raw SQL; use `POST /api/query` only when the task explicitly requires it or when the GET endpoints are insufficient.

### Step 3: Gather evidence from the hub

Query every endpoint relevant to the task's domain. Typical endpoints include:

| Endpoint | Use for |
|---|---|
| `GET /api/matters` | Matter metadata, hold dates, case type |
| `GET /api/subpoena-categories` | Request category codes and descriptions |
| `GET /api/productions` | Production status by category, rolling production metadata |
| `GET /api/custodian-sources` | Custodian data sources, collection status, device types |
| `GET /api/documents/search` | Document coding, responsiveness, production status, document-level findings |
| `GET /api/privilege-log` | Withheld documents, logged/unlogged counts, privilege designations, waiver issues |
| `GET /api/qc-findings` | QC defects, miscoding, responsiveness contradictions |
| `GET /api/retention-events` | Retention losses, destruction dates, hold timelines, policy sections |
| `GET /api/remediation-actions` | Existing remediation actions, owners, priorities |

For more detail on each endpoint, the query endpoint, and typical response shapes, see [references/endpoints.md](references/endpoints.md).

Query each relevant endpoint at least once. Read entire response bodies — do not truncate. Cross-reference records: a QC finding may reference a privilege-log entry which references a document. Follow these chains.

Record every **stable hub ID** (record IDs, source IDs, event IDs, document IDs, etc.) exactly as they appear in API responses. These become `source_refs`, `issue_refs`, `target_refs`, `blocking_refs`, and similar fields in the output.

### Step 4: Assemble the answer

Build the JSON output by following the answer template's contract:

**Top-level keys.** Only include keys listed in `required_top_level_keys`. Do not add extra keys, even if they seem useful.

**Enum values.** Every string field that has an `enum` or `enum_choices` constraint must use exactly one of the listed values. When the template defines enums like `issue_type`, `severity`, `status`, `action_type`, or `owner`, pick the value that best matches the evidence. Do not coin new values.

**Ordering.** Sort lists exactly as `ordering_rules` dictates. Typically this means: sort by a primary key ascending, sort category codes ascending within a list, sort actions by priority rank ascending where 1 is highest.

**Stable IDs.** Use hub record IDs as `finding_id`, `risk_id`, `issue_id`, `action_id`, `correction_id`, and in reference lists (`source_refs`, `record_refs`, `target_refs`, `blocking_refs`, `issue_refs`). These IDs must appear in hub responses. Do not fabricate IDs.

**Numeric precision.** All counts are whole integers. Do not use floats or decimals. Fields like `document_count`, `withheld_count`, `logged_count`, `unlogged_count`, `volume_count` must be integers, using `0` when the concept is not applicable to the record.

**Boolean and null.** Use JSON `true`/`false` for boolean fields. Use `null` for optional fields whose value is genuinely absent (not `"N/A"`, not `0`).

### Step 5: Validate and output

Before returning the answer, verify:

- Every `required_top_level_keys` key is present
- Every list is sorted per `ordering_rules`
- Every enum field uses a value from the template's enums
- All counts are whole integers
- All stable IDs match hub responses exactly (case-sensitive)
- The output is a single JSON object with no surrounding prose, markdown fences, or commentary

The final answer is the JSON object and nothing else.

## Handling specific analysis types

The answer template's `required_top_level_keys` signals which analysis type the task expects. Let the template drive every structural decision:

- **Gap analysis** (keys like `critical_findings`, `category_statuses`, `metrics`, `priority_actions`): Focus on production gaps, source collection gaps, privilege-log gaps, and remediation priorities. Map each finding to a stable hub record.
- **Retention review** (keys like `retention_events`, `communication_gaps`, `available_archives`, `metrics`, `recommended_actions`): Distinguish pre-hold policy destruction from post-hold loss. Flag communication system gaps and identify archives that can mitigate losses.
- **Remediation dashboard** (keys like `top_risks`, `category_coverage`, `retained_or_available_sources`, `metrics`, `action_plan`): Rank risks by severity, summarize category coverage, list retained/available remediation sources, and provide a prioritized action plan with due-days.
- **Production-readiness review** (keys like `readiness_statuses`, `issue_ledger`, `privilege_corrections`, `metrics`, `priority_actions`): Report non-ready categories, log material issues with coding and privilege fields, package privilege corrections, and prioritize readiness actions.

When the template includes fields you cannot populate from hub data, use `0` for integer counts, `null` for optional string fields, and an empty list `[]` for list fields that have no applicable entries — but only if the template explicitly allows those values.

## Common pitfalls

- **Ignoring the template's enums.** Even if a hub response uses a different word, map it to the template's vocabulary. The template is the contract.
- **Fabricating IDs.** Every `finding_id`, `risk_id`, `issue_id`, etc. must be traceable to a hub record. If no single record anchors a finding, use the most specific hub record available.
- **Including prose outside JSON.** The output must be pure JSON. No markdown wrappers, no explanatory text.
- **Sorting errors.** Re-read `ordering_rules` before finalizing. Ascending sort means lexicographic for strings, numeric for integers.
- **Mixing up counts.** Distinguish `withheld_count` (documents withheld), `logged_count` (documents on the privilege log), and `unlogged_count` (withheld minus logged). These must be internally consistent where the template ties them together.
