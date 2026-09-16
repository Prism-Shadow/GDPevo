---
name: investigation-review
description: >
  Produce structured JSON analysis reports for e-discovery matters using the
  Investigation Review Hub REST API. Use this skill whenever the task involves
  a matter ID, subpoena categories, production gaps, privilege logs, QC
  findings, retention events, remediation actions, custodian sources, or any
  structured gap, remediation, retention, or readiness review that references
  an answer_template.json and a <TASK_ENV_BASE_URL> placeholder. This
  applies to grand jury, SEC, DOJ, and any other investigation type served
  by the hub.
---

# Investigation Review Hub Analysis

## Overview

The Investigation Review Hub is a REST API that serves as the single source of
record for e-discovery matters. It exposes structured data about matters,
subpoena categories, productions, custodians, document review, privilege logs,
QC findings, retention events, and remediation actions, plus a read-only SQL
query endpoint for cross-entity joins.

Every task provides two critical inputs:

- **`<TASK_ENV_BASE_URL>`** — the hub base URL, resolved from the prompt or
  payload files. It is never a literal string to type; always resolve it from
  the task input.
- **`answer_template.json`** — a payload file that defines the exact output
  schema: required top-level keys, field types, allowed enum values, ordering
  rules, and numeric precision. This template is the single source of truth
  for the output shape.

Your job is to query the hub systematically, map the evidence into the
template, and return exactly one JSON object with no prose outside it.

## Endpoints

All endpoints return JSON. The base URL is `<TASK_ENV_BASE_URL>`.

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| GET | `/` | Health / connectivity check | none |
| GET | `/api/schema` | Full data model (tables, columns, relationships) | none |
| GET | `/api/matters` | Matter metadata (name, hold dates, status) | none |
| GET | `/api/subpoena-categories` | Request categories with codes and descriptions | none |
| GET | `/api/productions` | Rolling production status by category | none |
| GET | `/api/custodian-sources` | Custodian data sources (collected, not collected, lost) | none |
| GET | `/api/documents/search` | Reviewed documents with coding decisions | none |
| GET | `/api/privilege-log` | Privilege log entries (withheld, logged, unlogged) | none |
| GET | `/api/qc-findings` | QC findings (miscodes, contradictions, gaps) | none |
| GET | `/api/retention-events` | Retention events (destruction, purge, loss, missing) | none |
| GET | `/api/remediation-actions` | Remediation candidates and actions | none |
| POST | `/api/query` | Read-only SQL queries | `X-API-Key: review-key-017` |

The POST `/api/query` endpoint accepts a JSON body with a `"query"` field
containing a SQL `SELECT` statement. Always include the header
`X-API-Key: review-key-017`. Use this endpoint whenever you need to join
entities that the REST endpoints keep separate — for example, cross-referencing
QC findings with documents, retention events with categories, or computing
aggregate counts across multiple tables.

## Workflow

### Phase 1 — Orient

1. **Read the prompt** and every file under `input/payloads/`. Identify:
   - The matter ID (always present in the prompt or payloads).
   - The report type: gap analysis, retention review, remediation dashboard,
     or production readiness.
   - The answer template file (`answer_template.json`).

2. **Read the answer template thoroughly.** Note these four structural
   properties before touching the hub:
   - `required_top_level_keys` — the sections your output must contain.
   - `ordering_rules` — how to sort every list (by ID, by rank, by category
     code, or a combination).
   - `enums` — the exact allowed values for every coded field. A value not in
     the enum list is invalid no matter how well it describes the evidence.
   - `fields` — the required keys inside each list item and nested object.
     Every key listed as `required_keys` or `item_required_keys` is mandatory.

3. **Verify hub connectivity** with `GET /`. If the hub is unreachable, report
   the error; do not fall back to local files.

### Phase 2 — Discover

4. **Get the data model**: `GET /api/schema`. This tells you what entities
   exist, what columns they carry, and how they relate. Use this to plan which
   endpoints to query and what SQL joins are possible through
   `POST /api/query`.

5. **Confirm the matter**: `GET /api/matters`. Verify the matter ID from the
   prompt exists. Note its hold date (`hold_date`) and status — these anchor
   every retention timeline and preservation-risk assessment.

6. **Get request categories**: `GET /api/subpoena-categories`. Every finding,
   risk, or status entry must reference category codes from this endpoint.
   Use the exact codes (uppercase, as returned by the hub). The prompt or
   payloads may also carry a `category_synopsis` or similar block with
   human-readable descriptions; treat the hub codes as authoritative.

### Phase 3 — Gather Evidence

Query every endpoint relevant to the report type. The template's
`required_top_level_keys` and field-level schemas signal which entities matter.
At minimum, cover the endpoints listed below for each report type:

**Gap analysis and production readiness:**
- `/api/productions` — what has and has not been produced per category.
- `/api/documents/search` — reviewed documents, their coding decisions, and
  production status.
- `/api/privilege-log` — withheld and logged privilege documents.
- `/api/qc-findings` — miscodes, contradictions, and coding defects.
- `/api/custodian-sources` — collected, uncollected, and lost sources.

**Retention reviews:**
- `/api/retention-events` — every destruction, purge, system-loss, and
  missing-record event.
- `/api/custodian-sources` — communication systems (Teams, voicemail, email
  archives) whose retention windows or purge behavior create gaps.
- Cross-reference event dates against the matter hold date from
  `/api/matters` to classify each event as pre-hold or post-hold.

**Remediation dashboards:**
- `/api/retention-events`, `/api/privilege-log`, `/api/qc-findings`,
  `/api/custodian-sources`, `/api/remediation-actions`,
  `/api/documents/search`.

When REST endpoints return flat lists that need filtering or cross-joining,
use `POST /api/query` with a SQL query. Common use cases:

- Join QC findings to documents to confirm miscoded responsive documents and
  get exact document IDs and category assignments.
- Join retention events to subpoena categories to compute per-category loss
  and identify which categories are affected by each event.
- Count unlogged privilege documents: compare withheld totals from
  `/api/privilege-log` against logged entries. The hub often surfaces this as a
  dedicated aggregate record.

### Phase 4 — Synthesize

Map hub evidence into the answer template. Apply the following rules
universally, regardless of report type.

#### Stable Record IDs

Every finding, risk, issue, event, or action entry should be anchored by a
**stable hub record ID**. Use IDs exactly as returned by the hub — never
invent identifiers. Common ID prefixes:

- `DOC-*` — documents
- `PRIV-*` — privilege log entries or aggregate gap records
- `QC-*` — QC findings
- `SRC-*` — custodian sources
- `RET-*` — retention events

For the priority action plan, create stable action IDs following the
convention `ACT-<MATTER>-<NNN>` where `<MATTER>` is a short segment from the
matter ID (e.g., `SENT` from `MTR-SENTINEL-GJ`) and `<NNN>` is a zero-padded
sequence number matching the priority rank order.

#### Enum Values

Use only values from the template's `enums` section. When the evidence
suggests a concept that is not an exact enum value, find the closest match
that is present in the template. Common enum domains across report types:

- **Severity / risk level**: `critical` > `high` > `medium` > `low`
- **Priority**: `P0` > `P1` > `P2` > `P3`
- **Source status**: `lost`, `not_collected`, `partial`, `collected`,
  `destroyed`, `available_archive`, `not_applicable`
- **Production impact**: `source_lost`, `source_missing`, `not_produced`,
  `withheld_unlogged`, `privilege_exposure`, `underproduced`

#### Counts

All counts are whole integers. Use `0` when a count is zero or not applicable
— never use `null` or omit a count field. Every numeric field listed in the
template's field definitions must be present with an integer value.

Where the template defines `withheld_count`, `logged_count`, and
`unlogged_count` together, enforce the arithmetic relationship:
`unlogged_count = withheld_count - logged_count`.

#### Sorting and Ordering

Follow the template's `ordering_rules` exactly:

- Lists of findings, risks, or issues: sort by the key specified (commonly
  `finding_id`, `priority_rank`, `issue_id`, `event_id`, or `rank`).
- Lists of categories: sort by `category_code` ascending (lexicographic).
- Source ref and record ref lists within a single item: sort ascending.
- Category code lists within a single item: sort ascending.

#### Nullable Fields

Some string fields allow `null` — e.g., `third_party`, `event_date`,
`policy_section`, `cutoff_date`, `missing_component`. Use JSON `null` when the
value is genuinely absent or not applicable. Do not use an empty string `""`
unless the template explicitly lists it as an enum or permitted value.

### Phase 5 — Output

Return **exactly one JSON object** and nothing else — no markdown fences, no
explanatory prose, no trailing text. The JSON must satisfy every constraint:

- Contains every key listed in `required_top_level_keys`.
- Contains every required sub-key for each list item and nested object as
  defined in the template's `fields` section.
- Uses only values from the template's `enums` for every coded field.
- Applies the template's `ordering_rules` to every list.
- Uses whole integers for all count fields.
- Uses stable hub record IDs throughout.

If the task prompt names a specific output file (e.g., "Return only a JSON
object that conforms to..."), write the JSON directly in your response; do not
write it to a local file unless the prompt explicitly asks for a file write.

## Common Evidence Patterns

### Privilege Log Gaps

When the privilege log shows withheld documents that are not logged:

- `issue_type`: `privilege_log_gap`
- `severity` / `risk_level`: `high` (unlogged withholdings are a serious
  production defect)
- `production_impact`: `withheld_unlogged`
- `recommended_action`: `supplement_privilege_log`
- `unlogged_count = withheld_count - logged_count`

The hub typically surfaces this as a dedicated privilege-log record whose ID
contains `LOG-GAP`. Use that record's aggregate counts directly.

### Third-Party Waiver

When privilege-log or QC data shows communications shared with someone outside
the attorney-client relationship, privilege may be waived:

- `issue_type`: `third_party_waiver`
- `severity`: `high`
- `recommended_action`: `waiver_assessment_and_disclosure`
- `third_party`: the name from the hub record (not `null`)

### Responsiveness Miscodes

When QC findings or document review shows a responsive document coded as
non-responsive:

- `issue_type`: `responsiveness_miscode`
- `severity`: `high` (responsive material not produced)
- `production_impact`: `not_produced`
- `recommended_action`: `recode_and_produce`
- `source_refs`: include both the document ID and the QC finding ID

### Retention Events

Classify every retention event from `/api/retention-events` by comparing its
date against the matter hold date from `/api/matters`:

| Condition | Status | Risk | Typical Action |
|---|---|---|---|
| Destroyed before hold, policy-compliant | `policy_destroyed_pre_hold` | `low` | `no_action_policy_loss` |
| Destroyed or lost after hold | `post_hold_loss` | `high` or `critical` | `disclose_preservation_issue` |
| System auto-purge (e.g., voicemail, Teams) | `auto_purged` or `active_system_loss` | `medium` | `document_system_gap` |
| Record required by policy but not found | `should_exist_missing` | `high` | `locate_missing_record` |

### Custodian Sources

Map source status from `/api/custodian-sources`:

| Source Status | Meaning | Production Impact | Typical Action |
|---|---|---|---|
| `lost` or `destroyed` | Irrecoverable | `source_lost` | `disclose_to_government` or `disclose_preservation_issue` |
| `not_collected` | Never collected | `source_missing` | `collect_source` or `collect_personal_device` |
| `partial` | Some data collected | `partial_source_missing` or `underproduced` | `supplemental_collection` |
| `available_archive` | Archive exists | `source_available` | `search_archive` or `collect_archive` |

### QC Findings

QC findings from `/api/qc-findings` flag review defects. Cross-reference them
with `/api/documents/search` via `POST /api/query` to get exact document
counts and affected categories. Common patterns:

- **Responsiveness miscode**: a responsive document coded non-responsive.
- **Privilege miscode**: a document's privilege call was wrong in either
  direction.
- **Over-designation**: a document logged as privileged that contains only
  business content, not legal advice. Map as a `downgrade` correction.
- **Zero-claim contradiction**: a production claim of completeness is
  contradicted by QC sampling.

### Available Archives

When a source endpoint surfaces an archive that can partially remediate a loss
(e.g., an email archive that covers some communication categories despite the
live system having purged data), list it under the template's archive or
retained-sources section. Always note which categories it limits loss for
(`limits_irretrievable_loss_for_categories` or equivalent field).

## Pitfalls

- **Do not use local files as evidence.** The hub is the sole source of
  record. Ignore local environment files, database files, seed data,
  generation manifests, and hidden notes.
- **Do not guess enum values.** Check the template's `enums` block for every
  coded field assignment.
- **Do not write prose outside the JSON.** The output must be pure JSON.
  No markdown fences, no summaries, no sign-offs.
- **Do not omit required keys.** The template's `required_top_level_keys` and
  `item_required_keys` are mandatory. Produce every one.
- **Do not use `null` for integer counts.** Write `0` when the count is zero
  or not applicable.
- **Do not invent record IDs.** Use IDs from hub responses. For action-plan
  IDs, follow the `ACT-<MATTER>-<NNN>` convention.
- **Do not sort arbitrarily.** Follow the template's `ordering_rules`.
- **Do not forget the `X-API-Key: review-key-017` header on
  `POST /api/query`.**
- **Do not skip the schema endpoint.** `GET /api/schema` tells you what data
  exists and how entities relate; queries written without it are guessing.
- **Do not assume all categories have gaps.** Only include categories in
  status lists when the evidence shows a material non-ready or non-complete
  condition. A category with no evidence of gaps should either be omitted
  from the output or listed with an appropriate no-gap status as defined by
  the template.

## Report Type Quick Reference

| Report Type | Template Top-Level Keys | Primary Endpoints |
|---|---|---|
| Gap analysis | `matter_id`, `critical_findings`, `category_statuses`, `metrics`, `priority_actions` | productions, documents/search, privilege-log, qc-findings, custodian-sources |
| Retention review | `matter_id`, `retention_events`, `communication_gaps`, `available_archives`, `metrics`, `recommended_actions` | retention-events, custodian-sources, matters |
| Remediation dashboard | `matter_id`, `top_risks`, `category_coverage`, `retained_or_available_sources`, `metrics`, `action_plan` | retention-events, privilege-log, qc-findings, custodian-sources, remediation-actions, documents/search |
| Production readiness | `matter_id`, `readiness_statuses`, `issue_ledger`, `privilege_corrections`, `metrics`, `priority_actions` | productions, privilege-log, qc-findings, documents/search, custodian-sources |
