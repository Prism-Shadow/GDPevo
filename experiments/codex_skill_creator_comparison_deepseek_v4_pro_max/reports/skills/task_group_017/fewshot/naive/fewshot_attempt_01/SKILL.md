---
name: investigation-review-hub
description: Solve Investigation Review Hub tasks for legal eDiscovery matters. Use hub REST API endpoints to gather evidence, read answer templates to understand output schemas, and produce structured JSON analysis reports for gap analyses, retention reviews, remediation dashboards, and production-readiness assessments.
---

# Investigation Review Hub Solver

This skill covers solving structured eDiscovery analysis tasks against a shared Investigation Review Hub. Every task provides a matter ID, an answer template, and a prompt describing the review type. Use the hub API as the sole source of evidence and return a single JSON object conforming to the template.

## Hub Access

The hub is a REST API running at a task-provided base URL. The prompt contains `<TASK_ENV_BASE_URL>` as a placeholder for the actual URL. Use the actual value from the task prompt when making requests.

Authentication for the SQL query endpoint:

- Header: `X-API-Key`
- Value: `review-key-017`

All other endpoints are unauthenticated GET requests.

## Available Endpoints

Use these endpoints to gather all business evidence. Never inspect local environment files, database files, source code, seed files, or manifests.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Health check / root |
| GET | `/api/schema` | Data model schema for the hub |
| GET | `/api/matters` | List all matters; use to confirm the target matter ID |
| GET | `/api/subpoena-categories` | Request categories for a matter with their codes and labels |
| GET | `/api/productions` | Production status across categories |
| GET | `/api/custodian-sources` | Custodian sources linked to the matter (collection status, source type) |
| GET | `/api/documents/search` | Document records with coding and production status |
| GET | `/api/privilege-log` | Privilege log entries (logged, withheld, waiver status) |
| GET | `/api/qc-findings` | QC findings (miscoded documents, zero-claim contradictions) |
| GET | `/api/retention-events` | Retention events (destruction, auto-purge, system losses, hold dates) |
| GET | `/api/remediation-actions` | Existing remediation action records |
| POST | `/api/query` | Read-only SQL endpoint for cross-entity queries; requires `X-API-Key` header |

## Workflow

Follow these steps in order for every task.

### 1. Read the task materials

From the task's `input/` directory, read three things:

- **prompt.txt**: Identifies the matter ID, client, review type, and delivery requirements. It always tells you to use the hub and return JSON conforming to the template.
- **answer_template.json**: The exact output schema you must populate. It defines required top-level keys, field types, enum choices, ordering rules (ascending sort), and numeric precision (all counts are whole integers).
- **Any context payload** (e.g. `request_context.json`, `review_scope.json`, `matter_context.json`): May provide category synopses, the matter ID, allowed endpoints, and output contracts. Use these for orientation; the business evidence still comes from the hub.

### 2. Confirm the matter and explore the schema

Start by fetching the hub schema and the matter record:

```
GET <BASE_URL>/api/schema
GET <BASE_URL>/api/matters
```

Confirm the target matter ID appears in the matters list. Note any matter-level metadata that may inform the review.

### 3. Gather business evidence

Based on the review type described in the prompt, query the relevant hub endpoints. Do not call them all blindly; call the ones whose data shapes match the template's required sections.

**For gap analysis / production readiness** (templates with sections like `critical_findings`, `issue_ledger`, `readiness_statuses`, `priority_actions`):

- `/api/subpoena-categories` for category codes and labels
- `/api/productions` for production status per category
- `/api/custodian-sources` for collection gaps, lost devices, uncollected sources
- `/api/documents/search` for document coding, production status, responsive/nonresponsive flags
- `/api/privilege-log` for withheld counts, logged counts, waiver flags, incomplete logs
- `/api/qc-findings` for miscoding issues, zero-claim contradictions
- `/api/remediation-actions` for existing action records

**For retention / hold gap reviews** (templates with sections like `retention_events`, `communication_gaps`, `available_archives`):

- `/api/subpoena-categories` for category codes
- `/api/retention-events` for destruction events, hold dates, policy sections, box counts, cutoff dates
- `/api/custodian-sources` for available archives and their type/retention metadata

**For cross-system remediation dashboards** (templates with `top_risks`, `category_coverage`, `retained_or_available_sources`, `action_plan`):

- All of the above endpoints as needed, since these dashboards synthesize retention, privilege, QC, and source data into one view.

When an endpoint returns data keyed by matter, pass the target matter ID as a query parameter if the endpoint supports filtering (many endpoints accept `?matter_id=MTR-...`).

### 4. Use SQL queries for complex cross-referencing

If you need to join data across entity types (e.g. count withheld-but-unlogged privilege documents for a specific matter, or find all QC findings linked to a category), use `POST /api/query` with the `X-API-Key: review-key-017` header. Send a read-only SQL SELECT statement in the request body. The `/api/schema` response tells you the available tables and columns.

### 5. Populate the answer

Build the JSON output by filling the template structure with evidence from the hub. Follow these rules exactly:

**Stable IDs**: Use record IDs exactly as they appear in hub responses (e.g. `DOC-SENT-ALDEN-DEALER-ESC`, `PRIV-GRAY-WINSLOW`). Do not invent new IDs. For action IDs, use the pattern `ACT-{CLIENT_ABBREV}-{NNN}` with a zero-padded sequence number.

**Enums only**: Every string field with a constrained vocabulary must use one of the values listed in the template's `enums` (or `enum_choices`) block. Do not invent enum values.

**Ordering**: Every list section must be sorted as specified in the template's `ordering_rules`. This is always ascending sort by the designated key (e.g. `finding_id` ascending, `category_code` ascending, `priority_rank` ascending with 1 as highest priority). Category code lists within items must also be sorted ascending.

**Numeric precision**: All counts are whole integers. Use `0` when a count is not applicable; never use `null` for count fields that the template defines as integer type.

**Null handling**: Some string fields (like `third_party`, `policy_section`, `event_date`, `cutoff_date`) may be `null` when the hub has no value. Use `null` only where the template field description implies it is acceptable and the hub has no data.

**Boolean fields**: Use JSON `true` or `false`, never `"yes"` / `"no"` or `1` / `0`.

**Required keys**: Every section must include all required keys specified in the template. If a section is empty (no relevant data), return an empty list `[]`, not `null`.

**Single JSON output**: Return exactly one JSON object. No markdown, no prose, no code fences wrapping the JSON.

### 6. Validate before returning

Check the output against these rules before delivering:

- Every top-level key in the template's `required_top_level_keys` is present.
- Every list is sorted per the template's `ordering_rules`.
- Every enum field uses a valid value from the template's `enums` block.
- All counts are whole integers.
- Stable IDs are verbatim from hub responses.
- No prose or formatting surrounds the JSON.

## ID Conventions

Hub record IDs follow these naming patterns:

| Prefix | Entity | Example |
|--------|--------|---------|
| `MTR-` | Matter | `MTR-SENTINEL-GJ` |
| `DOC-` | Document | `DOC-SENT-ALDEN-DEALER-ESC` |
| `SRC-` | Custodian source | `SRC-SENT-ALDEN-PHONE` |
| `PRIV-` | Privilege log record | `PRIV-SENT-LOG-GAP` |
| `QC-` | QC finding | `QC-SENT-R09-NR` |
| `RET-` | Retention event | `RET-HARB-EHS-POST` |
| `ACT-` | Action (generated) | `ACT-SENT-001` |

Document, source, privilege, QC, and retention IDs are read from the hub. Action IDs are synthesized in the answer following the convention `ACT-{CLIENT_ABBREV}-{NNN}` where NNN is a three-digit zero-padded sequence starting at 001.

## Review Types and Their Evidence Maps

### Gap Analysis (Sentinel-style)

Produces `critical_findings` and `category_statuses` with privilege and source metrics.

Key evidence endpoints: `/api/productions`, `/api/custodian-sources`, `/api/privilege-log`, `/api/qc-findings`, `/api/documents/search`.

Look for: withheld-but-unlogged privilege documents, miscoded responsive documents, lost personal devices, uncollected board/executive sources.

### Retention and Hold Gap Review (HarborStone-style)

Produces `retention_events`, `communication_gaps`, `available_archives`, and per-event recommended actions.

Key evidence endpoints: `/api/retention-events`, `/api/custodian-sources`, `/api/subpoena-categories`.

Look for: post-hold destruction, pre-hold policy-compliant destruction, auto-purged records, active system losses, missing required records, and available archives that can partially remediate losses.

Classify each event: post-hold loss is high/critical risk; pre-hold policy-compliant destruction is low risk; auto-purge and active system loss are medium risk; missing records that should exist are high risk.

### Cross-System Remediation Dashboard (Graycliff/AlloyWorks-style)

Produces `top_risks`, `category_coverage`, `retained_or_available_sources`, `metrics`, and `action_plan`.

Key evidence endpoints: all hub endpoints may be relevant. This is a comprehensive review.

Look for: post-hold losses, personal source gaps (uncollected phones, personal email, Signal/SMS), privilege log gaps, third-party waiver issues, miscoded privilege documents, responsiveness miscodes, available archives, and deleted collaboration channels.

Assign priority: P0 for disclosures and critical preservation issues, P1 for privilege corrections and source collection, P2 for QC remediation on lower-risk items, P3 for monitoring-only items. Due days typically range from 3 (disclosures) to 10 (archive searches).

### Production Readiness Review (Northbay-style)

Produces `readiness_statuses`, `issue_ledger`, `privilege_corrections`, `metrics`, and `priority_actions`.

Key evidence endpoints: `/api/documents/search`, `/api/privilege-log`, `/api/qc-findings`, `/api/custodian-sources`.

Look for: non-ready categories with blocking issues, miscoded responsive documents, privilege log incompleteness, waiver concerns, over-designation, privilege documents miscoded as nonprivileged, and missing personal sources.

## Common Enum Vocabularies

The templates share overlapping enum sets. When a template uses a given enum name, use only its listed values. Below are the most common families:

**Severity / risk levels**: `critical`, `high`, `medium`, `low`

**Priority levels**: `P0`, `P1`, `P2`, `P3`

**Production impacts**: `source_lost`, `source_missing`, `source_available`, `not_produced`, `withheld_unlogged`, `privilege_exposure`, `recode_needed`, `missing_record`, `underproduced`, `no_production_impact`, `multiple_impacts`

**Source statuses**: `lost`/`destroyed`, `not_collected`, `partial`/`partial_collection`, `collected`, `available_archive`, `should_exist_missing`, `not_applicable`, `unknown`, `pending`

**Action types**: `disclose_to_government`/`disclose_preservation_issue`, `forensic_recovery`, `collect_source`/`collect_personal_device`/`collect_personal_email`/`collect_signal_messages`, `recode_and_produce`, `supplement_privilege_log`, `quality_control_review`/`qc_remediation`, `privilege_re_review`/`privilege_recode_and_log`, `waiver_assessment_and_disclosure`, `search_archive`, `locate_missing_record`, `monitor_only`, `production_readiness_hold`, `no_action`/`no_action_policy_loss`, `investigate`, `document_system_gap`, `restore_from_backup`, `custodian_followup`, `escalate_to_counsel`

**Owner roles**: `outside_counsel`/`litigation_counsel`, `client_legal`, `client_it`, `forensics`, `ediscovery_vendor`, `review_vendor`/`review_qc`/`review_operations`, `privilege_team`, `privilege_counsel`, `records_vendor`/`records_management`, `compliance_audit`, `it_messaging`, `investigation_team`, `legal_operations`

Always defer to the specific enum list in the task's answer template. These common families are a guide, not a substitute.

## Gotchas

- **Category codes vary by matter**: Some use `R01`-`R15` style, others use `SEC-1` through `SEC-4`, others use single letters `A` through `I`. Read them from `/api/subpoena-categories`.
- **Box counts vs document counts**: Retention events are often measured in boxes; privilege issues are measured in documents. Match the `volume_unit` enum to the evidence.
- **"Destroyed lab archive box count"**: The metrics section in dashboard templates has a field `destroyed_lab_archive_box_count`. This refers to boxes destroyed from the specific records archive named in the task's facts. If the destroyed records are not measured in boxes, use `0`.
- **Unlogged = withheld minus logged**: When a privilege log record has a withheld count and a logged count, `unlogged_count` is the difference. Compute it from hub data rather than reading it directly if the hub does not expose it.
- **Empty arrays, not null**: When no entities match a list section (e.g. `retained_or_available_sources` is empty), return `[]`, not `null`.
- **Template field names are exact**: The template's field names are the JSON keys you must use. Do not rename them or use camelCase variants.

## Example Workflow Summary

```
1. Read prompt.txt, answer_template.json, and any context payload
2. GET /api/schema to learn the data model
3. GET /api/matters to confirm the matter ID
4. Identify the review type from the prompt and template structure
5. Query the relevant evidence endpoints (filtered by matter ID where supported)
6. Use POST /api/query for complex cross-entity aggregations
7. Populate the template following ordering, enum, and precision rules
8. Validate: required keys, sorting, enum validity, integer counts
9. Return the single JSON object
```
