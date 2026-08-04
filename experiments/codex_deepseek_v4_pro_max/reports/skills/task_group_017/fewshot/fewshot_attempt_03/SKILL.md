---
name: investigation-review-hub
description: |
  Complete legal e-discovery review tasks using the Investigation Review Hub
  API. Use this skill for production gap analyses, retention and litigation-hold
  reviews, cross-system remediation dashboards, and production-readiness reviews.
  The skill covers API setup, endpoint usage, SQL query patterns, and structured
  JSON answer assembly from hub data.
---

# Investigation Review Hub Skill

## Overview

The Investigation Review Hub is a shared API environment that serves as the
source of record for legal e-discovery matters. It provides read-only REST
endpoints and a parameterized SQL query endpoint. The hub exposes matter
metadata, subpoena/request categories, production status, custodian sources,
review documents, privilege-log data, QC findings, retention events, and
remediation candidates.

Use the hub endpoints as the primary evidence source. Do **not** inspect local
environment source files, database files, generation manifests, hidden notes,
standard-answer files, or task-evaluation files. The hub is the single source
of truth.

## Environment Setup

The base URL for the hub is provided as the template variable
`<TASK_ENV_BASE_URL>` in task prompts and payloads. Before making any API call,
resolve this variable to the actual base URL by checking the task-provided
context (e.g., `environment_access.md` or a `matter_context.json` payload).

### Required Headers

Every request to `POST /api/query` **must** include:

```
X-API-Key: review-key-017
Content-Type: application/json
```

The `X-API-Key` header is **not** required for GET endpoints, which are
readable without authentication in the task environment.

### Quick Start

1. Read the task `prompt.txt` to understand the review type and matter.
2. Read all JSON payloads from `input/payloads/`:
   - `answer_template.json` — the required output schema.
   - `request_context.json`, `review_scope.json`, or `matter_context.json` —
     task-specific context like the matter ID, client name, category labels,
     and environment configuration.
3. Query the hub for the matter's data (see Endpoint Reference below).
4. Assemble the answer as a **single JSON object** conforming exactly to the
   answer template schema.
5. Return **only** the JSON object with no surrounding prose.

## Endpoint Reference

### GET Endpoints

| Endpoint | Returns |
|---|---|
| `GET /` | Hub health / root |
| `GET /api/schema` | Available database tables and column definitions |
| `GET /api/matters` | All matters with IDs, names, statuses |
| `GET /api/subpoena-categories` | Request/subpoena categories per matter |
| `GET /api/productions` | Production records and status |
| `GET /api/custodian-sources` | Custodian data sources (devices, accounts, archives) |
| `GET /api/documents/search` | Review-document metadata and coding |
| `GET /api/privilege-log` | Privilege assertions, log entries, waivers |
| `GET /api/qc-findings` | Quality-control findings on coding/privilege |
| `GET /api/retention-events` | Retention events, destruction, and hold-related losses |
| `GET /api/remediation-actions` | Existing or proposed remediation action records |

### POST /api/query

Parameterized read-only SQL. Use for cross-table joins, aggregations, or
filtering not supported by the GET endpoints.

```
POST /api/query
Content-Type: application/json
X-API-Key: review-key-017

{"sql": "<SELECT statement>", "params": ["value1", "value2"]}
```

Example:

```bash
curl -sS -X POST "${BASE_URL}/api/query" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: review-key-017" \
  -d '{"sql":"SELECT * FROM matters WHERE matter_id = ?","params":["MTR-EXAMPLE-001"]}'
```

### Data Model Notes

Study `GET /api/schema` first to understand the available tables and their
relationships. Common joins across review tasks include:

- **Matter → Subpoena Categories**: filter categories for the target matter.
- **Matter → Custodian Sources**: identify collected, missing, lost, or
  destroyed sources.
- **Matter → Documents**: review coding statuses (responsive, nonresponsive,
  privileged, nonprivileged).
- **Matter → Privilege Log**: withheld counts, logged counts, unlogged gaps,
  third-party recipients.
- **Matter → QC Findings**: miscoding flags, zero-claim contradictions,
  privilege miscoding.
- **Matter → Retention Events**: destruction events, hold dates, pre/post-hold
  classification, volume counts.
- **Matter → Remediation Actions**: existing action records linked to sources,
  documents, or events.

Use **stable record IDs exactly as they appear in the hub** for all fields
that reference sources, documents, events, QC findings, privilege records, and
remediation actions. Never fabricate IDs.

## Answer Assembly Rules

### Schema Compliance

Every task includes an `answer_template.json` that defines:

- `required_top_level_keys` — the top-level keys that must appear in the
  output.
- `ordering_rules` — how to sort list items (e.g., by category code ascending,
  by priority rank ascending).
- `enums` — the allowed values for each enumerated field.
- `fields` — the type, description, required sub-keys, and sub-field types for
  every object.
- `numeric_precision` — all counts must be whole integers.

**Always read the template before assembling the answer.** The template is the
contract; the answer must conform exactly.

### Stable IDs

Use identifiers exactly as returned by the hub. When a hub record naturally
anchors a finding, risk, or issue, prefer using that record's ID as the
`finding_id`, `risk_id`, `issue_id`, or similar primary key. When an
action-plan item needs a synthetic ID (e.g., `ACT-SENT-001`), construct it from
the matter abbreviation and a zero-padded sequence number.

### Sorting

Follow the template's `ordering_rules` exactly:

- Category codes are sorted ascending as strings (e.g., `"R07"` before
  `"R09"`).
- Priority ranks are sorted ascending with 1 as the highest priority.
- Within equal sort keys, use the stable ID ascending as a secondary sort.

### Metrics

Metrics objects aggregate counts across the matter. Derive each metric from hub
data:

- Count records, documents, sources, events, or categories as appropriate.
- Use `0` when a metric is not applicable rather than omitting it.
- Count only records that are material to the review (open issues, confirmed
  findings, non-cleared statuses).

### Counts and Nulls

- All numeric counts must be whole integers.
- Use `null` for string fields that genuinely have no value (e.g.,
  `event_date`, `policy_section`, `third_party`).
- Use `0` for numeric counts when not applicable, not `null`.
- Use `"not_applicable"` for enum fields that do not apply to the record.

## Review-Type Patterns

### Production Gap Analysis

Identify production readiness by crossing subpoena categories against
documents, privilege log, custodial sources, and QC findings.

Key data sources:
- `GET /api/subpoena-categories` for the matter's request categories.
- `GET /api/documents/search` for document coding and production status.
- `GET /api/privilege-log` for withheld/unlogged privilege gaps.
- `GET /api/custodian-sources` for collection gaps and lost sources.
- `GET /api/qc-findings` for miscoding and responsiveness issues.

### Retention and Litigation-Hold Review

Map every retention event to its affected subpoena categories, classify
pre-hold vs. post-hold losses, identify communication gaps (auto-purge, system
cutoff), and inventory available archives.

Key data sources:
- `GET /api/retention-events` for all destruction, purge, and loss events.
- `GET /api/custodian-sources` for archives and backup sources.
- `GET /api/subpoena-categories` for category-to-event mapping.

### Cross-System Remediation Dashboard

Produce a prioritised risk inventory spanning retention, privilege, source
collection, coding, and QC dimensions. Rank risks from most critical
(post-hold loss, waiver exposure) to least urgent. Identify retained or
available sources that can partially mitigate losses.

Key data sources:
- All GET endpoints; cross-reference with `POST /api/query` for joins.
- `GET /api/remediation-actions` for existing action records.

### Production-Readiness Review

Evaluate each request category's readiness for production. Flag categories
blocked by responsive miscoding, privilege-log gaps, waiver issues, and
collection gaps. Provide a privilege-correction package and a prioritised
action plan.

Key data sources:
- `GET /api/documents/search` for coding and production status.
- `GET /api/privilege-log` for withheld/logged/unlogged counts and waivers.
- `GET /api/qc-findings` for miscoding and privilege errors.
- `GET /api/custodian-sources` for source gaps.

## Enum Reference

Below are the union enum sets observed across all review types. Use the exact
string values defined in each task's `answer_template.json` — individual tasks
may use a subset.

### Issue / Risk Types

`preservation_failure`, `collection_gap`, `responsiveness_miscode`,
`privilege_log_gap`, `retention_loss`, `privilege_waiver`,
`over_designation`, `miscoded_privilege`, `post_hold_loss`,
`third_party_waiver`, `privilege_miscoding`, `personal_source_gap`,
`zero_claim_contradiction`, `personal_email_gap`, `personal_phone_gap`,
`other`

### Severity / Risk Level

`critical`, `high`, `medium`, `low`

### Status Values

**Finding/Issue Status**: `open`, `remediation_pending`,
`protocol_noncompliant`, `ready`, `no_gap`, `confirmed`, `not_collected`,
`partial_collection`, `incomplete_log`, `waived`, `cleared`, `unknown`,
`needs_recode`

**Source Status**: `lost`, `not_collected`, `partial`, `collected`,
`pending`, `not_applicable`, `destroyed`, `unknown`

**Category Status**: `complete`, `incomplete`, `collection_gap`,
`preservation_risk`, `responsiveness_gap`, `privilege_log_gap`,
`withholding_gap`, `no_current_gap`, `preservation_loss`,
`underproduced_privilege_corrections`, `source_gap_with_archive_available`,
`archive_available`

**Readiness Status**: `ready`, `not_ready_zero_claim_contradicted`,
`not_ready_personal_source_gap`, `not_ready_privilege_log_incomplete`,
`not_ready_privilege_waiver`, `not_ready_multiple_blockers`, `unknown`

**Retention Status**: `policy_destroyed_pre_hold`, `post_hold_loss`,
`auto_purged`, `active_system_loss`, `should_exist_missing`,
`available_archive`, `preserved_available`, `collection_pending`,
`not_applicable`

**Archive Status**: `available_archive`, `unavailable`, `unknown`

### Production Impact

`underproduced`, `not_produced`, `withheld_unlogged`, `source_missing`,
`source_lost`, `recode_needed`, `no_production_impact`, `privilege_exposure`,
`privilege_waiver`, `multiple_impacts`, `source_available`, `unknown`,
`no_current_gap`, `partial_source_missing`

### Action Types

`disclose_to_government`, `disclose_preservation_issue`,
`forensic_recovery`, `collect_source`, `recode_and_produce`,
`supplement_privilege_log`, `quality_control_review`, `privilege_re_review`,
`investigate`, `no_action`, `no_action_policy_loss`,
`document_system_gap`, `collect_archive`, `restore_from_backup`,
`locate_missing_record`, `custodian_followup`, `escalate_to_counsel`,
`waiver_assessment_and_disclosure`, `privilege_recode_and_log`,
`collect_personal_device`, `collect_personal_email`,
`collect_signal_messages`, `qc_remediation`, `production_readiness_hold`,
`search_archive`

### Owners / Responsible Parties

`outside_counsel`, `litigation_counsel`, `client_legal`, `client_it`,
`ediscovery_vendor`, `review_vendor`, `review_qc`, `privilege_team`,
`privilege_counsel`, `records_vendor`, `records_management`,
`investigation_team`, `it_messaging`, `compliance_audit`,
`legal_operations`, `forensics`, `review_operations`

### Priority Levels

`P0`, `P1`, `P2`, `P3`

### Volume Units

`boxes`, `days`, `months`, `records`, `documents`, `emails`,
`sources`, `not_applicable`

### Source Types

`email_archive`, `teams_archive`, `personal_device`,
`corporate_laptop`, `personal_email`, `signal_messages`,
`sms_messages`, `voicemail`, `shared_drive`,
`not_applicable`

### Gap / Communication Types

`auto_purge`, `active_system_loss`, `uncollected_source`,
`missing_required_record`, `not_applicable`

### Coding Values

`responsive`, `nonresponsive`, `privileged`, `nonprivileged`,
`unknown`, `not_applicable`

### Produced Status

`produced`, `not_produced`, `withheld`, `unknown`, `not_applicable`

### Corrected Disposition

`responsive_produce`, `supplement_log`, `waiver_assessment`,
`supplemental_collection`, `no_change`, `not_applicable`

### Privilege Correction Types

`supplement_log`, `waiver_assessment`, `privilege_recode`,
`downgrade`, `no_action`

### Privilege Status

`incomplete_log`, `waived`, `logged`, `over_designated`,
`no_issue`, `unknown`

## API Interaction Pattern

### Step 1: Discover Schema

```bash
curl -sS "${BASE_URL}/api/schema"
```

Inspect the returned tables and columns to understand what data is available
and how tables relate.

### Step 2: Fetch Matter Metadata

```bash
curl -sS "${BASE_URL}/api/matters"
```

Identify the target matter by its stable ID (e.g., `MTR-EXAMPLE-001`).

### Step 3: Fetch Domain Data

Based on the review type, fetch the relevant domain endpoints:

```bash
# Categories in the subpoena/request
curl -sS "${BASE_URL}/api/subpoena-categories"

# Custodian data sources
curl -sS "${BASE_URL}/api/custodian-sources"

# Document coding
curl -sS "${BASE_URL}/api/documents/search"

# Privilege log
curl -sS "${BASE_URL}/api/privilege-log"

# QC findings
curl -sS "${BASE_URL}/api/qc-findings"

# Retention events
curl -sS "${BASE_URL}/api/retention-events"

# Existing remediation actions
curl -sS "${BASE_URL}/api/remediation-actions"
```

### Step 4: Run Targeted SQL Queries

Use `POST /api/query` for cross-table joins, filtered lookups, and
aggregations. Always parameterize queries:

```bash
curl -sS -X POST "${BASE_URL}/api/query" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: review-key-017" \
  -d '{"sql":"SELECT ... WHERE matter_id = ?","params":["MTR-EXAMPLE-001"]}'
```

Filter by the target `matter_id` to scope results to the matter under review.
Count records, sum volumes, and join across tables as needed for metrics.

### Step 5: Assemble and Return

Build the JSON object conforming to `answer_template.json`. Follow the
template's `required_top_level_keys`, field types, enum choices, and ordering
rules exactly. Output **only** the JSON object.

## Common Pitfalls

- **Wrong API key header name**: The header is `X-API-Key` (with a capital K
  and a hyphen), not `X-API-Key` variants. Verify the exact header from the
  task payload or `environment_access.md`.
- **Forgetting Content-Type on POST**: The `/api/query` endpoint requires
  `Content-Type: application/json`.
- **Hardcoding IDs**: Always use stable IDs from the hub. If a record anchor
  does not have a single obvious ID, use the most specific hub record ID.
- **Missing template keys**: Every `required_top_level_key` must appear in the
  output, even if its value is an empty list `[]`.
- **Enum mismatches**: Use the exact string values from the template's `enums`
  section. Do not invent or abbreviate enum values.
- **Wrong sort order**: Follow `ordering_rules` exactly. Category codes sort
  as strings, not numerically.
- **Null vs. zero**: Use `null` for genuinely absent string/date fields and
  `0` for numeric counts that are not applicable.
- **Including prose**: The output must be pure JSON. Do not wrap with
  markdown code fences or add explanatory text.
- **Inspecting local files**: Do not read environment source files, database
  files, manifests, or answer files. All evidence comes from the hub API.
