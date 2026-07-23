# Investigation Review Hub — Structured Review Skill

## Purpose

Generate structured JSON review deliverables for legal e-discovery matters by querying the Investigation Review Hub API and conforming to task-provided answer templates. Covers gap analyses, retention reviews, remediation dashboards, and production-readiness assessments.

## When to Use

Invoke this skill when the task involves:
- An Investigation Review Hub at a resolvable base URL
- A `prompt.txt` describing the review deliverable
- An `input/payloads/answer_template.json` defining the output schema
- Legal e-discovery review types: gap analysis, retention/hold review, remediation dashboard, or production readiness

## Operating Rules

These rules are distilled from repeated successful reviews and apply to every task regardless of matter, client, or review type.

### R1 — Single Source of Truth

The Investigation Review Hub API is the **only authoritative source** for business data. Never inspect, read, or rely on:
- Local environment files, source code, or database files
- Generated manifests, seeds, setup scripts, or hidden notes
- Standard answer files, evaluation files, or any non-hub artifact
- `localhost`, `127.0.0.1`, or any URL other than the resolved hub base

Local payload files (`input/payloads/*.json`) provide task framing (matter ID, client name, category synopses, review scope) but are **not** a substitute for hub evidence. Counts, statuses, events, and record identifiers must come from API responses.

### R2 — Template-First Output

Read `input/payloads/answer_template.json` before querying the hub. The template defines:
- **Required top-level keys** — every key must appear in the output
- **Field types and descriptions** — what each field means and what shape it takes
- **Enum choices** — the exact set of allowed values for every categorical field
- **Ordering rules** — which key to sort by and in which direction (always ascending)
- **Numeric precision** — all counts are whole integers

The answer object must contain every required key and conform to every constraint in the template. Do not add extra keys. Do not omit required keys. Do not substitute types.

### R3 — API Discovery

Always call `GET /api/schema` first to discover available endpoints, field names, and data shapes. The schema teaches which endpoints carry which data and how records relate to each other. Do not assume endpoint behavior from training tasks — the schema is authoritative for the running instance.

After schema discovery, confirm the matter by calling `GET /api/matters` and locating the matter ID from the prompt or payload context.

### R4 — Enum Compliance

Every categorical field in the answer must use a value from the template's enum list for that field. Never:
- Invent an enum value not present in the template
- Use a value from the wrong enum list (e.g., a `severity` value in a `risk_level` field)
- Approximate or paraphrase an enum value

When mapping hub data to an enum, choose the closest match based on the evidence. If no enum value fits, prefer the most general applicable value (e.g., `"other"`) rather than fabricating one.

### R5 — Ordering Discipline

Apply the template's ordering rules exactly:

| List key | Sort direction | Sort key |
|---|---|---|
| As specified in `ordering_rules` | Always ascending | As specified |
| Category codes within any list | Always ascending | Code string |
| Record ID lists (source_refs, target_refs, etc.) | Always ascending | ID string |

Numeric ranks (`priority_rank`, `rank`) are sorted with 1 first (ascending). Category codes use natural string sort (e.g., `"A"` before `"B"`, `"SEC-1"` before `"SEC-2"`).

### R6 — Stable Identifiers

Use hub-provided identifiers exactly as they appear in API responses:
- Matter IDs (e.g., `MTR-*-GJ`, `MTR-*-SEC`)
- Source IDs, event IDs, document IDs, QC finding IDs, action IDs
- Category codes (e.g., `A`, `B`, `SEC-FIN`, `DOJ-ANTITRUST-1`)

These identifiers anchor findings to their evidence records (`source_refs`, `target_refs`, `issue_refs`, `blocking_refs`, `record_refs`). Every finding, risk, or issue must reference at least one hub record ID so the deliverable is auditable.

### R7 — Numeric Precision

All count fields are whole integers. Use `0` when a count is not applicable (not `null`, not omitted). Examples:
- A finding about a lost personal device that involves no documents: `document_count: 0`
- A matter with no withheld documents for a given issue: `withheld_count: 0`
- Boolean fields use JSON `true`/`false`, never `1`/`0` or strings

### R8 — JSON-Only Output

Return exactly one JSON object. No:
- Prose before, after, or interspersed with the JSON
- Markdown code fences around the JSON
- Comments or annotations inside the JSON
- Multiple JSON objects or arrays at the top level

The output must parse as valid JSON with no trailing content.

### R9 — Environment Resolution

`<TASK_ENV_BASE_URL>` in prompts and payloads is resolved via `environment_access.md` when present in the working directory. The file provides:
- `base_url` — the actual hub URL to call
- `credentials` — header name and API key for the SQL endpoint
- `allowed_endpoints` — the complete list of available endpoints

The SQL query endpoint (`POST /api/query`) uses the header specified in `environment_access.md` (typically `X-API-Key: review-key-017`). All other endpoints are read-only GET requests with no authentication.

## Task Archetypes

The hub supports these review types. The answer template's `required_top_level_keys` signals which archetype applies:

### Archetype A — Gap Analysis

**Template keys**: `matter_id`, `critical_findings`, `category_statuses`, `metrics`, `priority_actions`

**Purpose**: Identify production gaps and defects in a rolling production. Assess which request categories are complete vs. have gaps, quantify privilege and QC metrics, and prioritize remediation actions.

**Key endpoints**: `/api/subpoena-categories`, `/api/productions`, `/api/custodian-sources`, `/api/documents/search`, `/api/privilege-log`, `/api/qc-findings`, `/api/remediation-actions`

**Signature enums**: `issue_type` (preservation_failure, collection_gap, responsiveness_miscode, privilege_log_gap, etc.), `finding_status` (open, remediation_pending, protocol_noncompliant, etc.), `category_status` (complete, incomplete, collection_gap, preservation_risk, etc.)

### Archetype B — Retention & Hold Review

**Template keys**: `matter_id`, `retention_events`, `communication_gaps`, `available_archives`, `metrics`, `recommended_actions`

**Purpose**: Assess retention policy compliance, distinguish pre-hold policy-compliant destruction from post-hold losses, identify communication gaps, and locate available archives for remediation.

**Key endpoints**: `/api/retention-events`, `/api/custodian-sources`, `/api/subpoena-categories`, `/api/documents/search`

**Signature enums**: `retention_status` (policy_destroyed_pre_hold, post_hold_loss, auto_purged, active_system_loss, should_exist_missing, available_archive, etc.), `gap_type` (auto_purge, active_system_loss, uncollected_source, missing_required_record), `archive_status` (available_archive, unavailable, unknown)

### Archetype C — Remediation Dashboard

**Template keys**: `matter_id`, `top_risks`, `category_coverage`, `retained_or_available_sources`, `metrics`, `action_plan`

**Purpose**: Rank material risks across the matter, summarize category-by-category coverage, identify retained or available remediation sources, report numeric metrics, and provide a prioritized action plan with due dates.

**Key endpoints**: `/api/retention-events`, `/api/custodian-sources`, `/api/documents/search`, `/api/privilege-log`, `/api/qc-findings`, `/api/remediation-actions`, `/api/subpoena-categories`

**Signature enums**: `risk_level` (critical, high, medium, low), `risk_status` (open, protocol_noncompliant, remediation_available, needs_recode, should_exist_missing, closed), `category_status` (preservation_loss, missing_required_record, personal_source_gap, source_gap_with_archive_available, archive_available, privilege_log_gap, responsiveness_gap, etc.), `source_type` (lab_results_archive, personal_phone, cloud_mail_archive, email, privilege_log, qc_finding, qa_audit, offsite_records, personal_messaging, teams_archive, etc.)

### Archetype D — Production Readiness

**Template keys**: `matter_id`, `readiness_statuses`, `issue_ledger`, `privilege_corrections`, `metrics`, `priority_actions`

**Purpose**: Assess per-category production readiness, catalog material issues (non-privilege and privilege-related), identify privilege corrections needed (supplemental logs, waiver assessments, recoding), and plan readiness actions.

**Key endpoints**: `/api/productions`, `/api/subpoena-categories`, `/api/documents/search`, `/api/privilege-log`, `/api/qc-findings`, `/api/custodian-sources`

**Signature enums**: `readiness_status` (ready, not_ready_zero_claim_contradicted, not_ready_personal_source_gap, not_ready_privilege_log_incomplete, not_ready_privilege_waiver, not_ready_multiple_blockers), `privilege_correction_type` (supplement_log, waiver_assessment, privilege_recode, downgrade), `privilege_status` (incomplete_log, waived, logged, over_designated, no_issue)

## Workflow

Follow this sequence for every review. Do not skip phases.

### Phase 1 — Orient

1. Read `prompt.txt` to understand the review type, matter, and deliverable
2. Read every file in `input/payloads/` — at minimum `answer_template.json` and any context file (`request_context.json`, `review_scope.json`, `matter_context.json`)
3. Read `environment_access.md` if present — resolve `<TASK_ENV_BASE_URL>`, note API credentials, confirm allowed endpoints
4. Identify which archetype the template's `required_top_level_keys` matches

### Phase 2 — Discover

1. Call `GET /api/schema` to learn available data shapes, field names, and relationships
2. Call `GET /api/matters` to confirm the matter ID exists and retrieve matter-level metadata
3. Call `GET /api/subpoena-categories` to retrieve all request categories with their codes, titles, and scope

### Phase 3 — Collect

Query each relevant endpoint for the archetype. Build complete picture before assembling:

| Endpoint | Archetypes that need it | What it provides |
|---|---|---|
| `GET /api/productions` | A, D | Production counts, produced/withheld status per category |
| `GET /api/custodian-sources` | A, B, C, D | Source collection status, gaps, device types, archive references |
| `GET /api/documents/search` | A, B, C, D | Document-level details, coding, privilege assertions |
| `GET /api/privilege-log` | A, C, D | Withheld documents, logged vs. unlogged, waiver events, privilege bases |
| `GET /api/qc-findings` | A, C, D | Miscoded documents, responsiveness errors, privilege coding issues |
| `GET /api/retention-events` | B, C | Retention losses, purge events, hold dates, policy sections |
| `GET /api/remediation-actions` | A, C | Existing remediation actions, owners, statuses |

For cross-cutting questions (e.g., "how many documents match criteria X across categories Y and Z"), use `POST /api/query` with SQL. Send the API key header from `environment_access.md`. Keep queries read-only.

### Phase 4 — Map

For each section of the answer template, map hub evidence to template fields:

1. **Identify the hub records** that anchor each finding/risk/issue/event — use their stable IDs
2. **Choose the correct enum value** from the template's enum list based on the evidence in the hub record
3. **Count precisely** — document counts, withheld counts, logged counts, unlogged counts, source counts — from hub data, not estimates
4. **Trace category impacts** — which request categories does each finding affect? Use category codes from the hub
5. **Assign owners** — use the template's owner enum; match to the role that can actually remediate the issue

When a hub record doesn't perfectly match one enum value, pick the closest one from the allowed list. Prefer specificity over generality, but never invent values.

### Phase 5 — Assemble

Build the JSON object:

1. Create the top-level object with every `required_top_level_key` from the template
2. Populate each section with objects conforming to the template's `item_required_keys` and `item_fields`
3. Apply `ordering_rules` — sort each list by its specified sort key, ascending
4. Sort all category-code lists within objects ascending
5. Set all inapplicable counts to `0` (not `null`, not omitted)
6. Use `true`/`false` for boolean fields

### Phase 6 — Validate

Before returning, verify:

- [ ] Every `required_top_level_key` from the template is present
- [ ] Every list is sorted per `ordering_rules`
- [ ] Every categorical value matches an enum in the template
- [ ] All counts are whole integers
- [ ] All IDs are stable strings from hub responses (not invented)
- [ ] `0` is used for inapplicable counts, not `null` or omission
- [ ] Category codes are uppercase and sorted ascending within lists
- [ ] The output is exactly one JSON object with no surrounding text
- [ ] `source_refs`, `target_refs`, `issue_refs`, `blocking_refs`, `record_refs` lists are sorted ascending and non-empty where the template implies they should be

## Common Enum Reference

These enum categories appear across multiple archetypes. See `references/enum-usage.md` for detailed mapping guidance.

### Severity / Risk Levels

`critical` > `high` > `medium` > `low`

Use `critical` for issues that create legal exposure (spoliation risk, privilege waiver to adversaries, inability to comply with production obligations). Use `high` for material gaps without immediate legal jeopardy. Use `medium` for gaps with available remediation. Use `low` for administrative or policy deviations.

### Issue Types

Common across templates:
- **preservation_failure** / **post_hold_loss**: Data destroyed after a litigation hold was in effect
- **collection_gap** / **personal_source_gap**: Custodian source not collected (personal device, personal email, messaging)
- **responsiveness_miscode**: Document coded non-responsive but is actually responsive
- **privilege_log_gap**: Documents withheld but not logged, or logged with insufficient detail
- **privilege_miscoding** / **miscoded_privilege**: Document incorrectly coded privileged, or privilege coding errors
- **third_party_waiver**: Privilege waived through third-party disclosure
- **missing_required_record**: Record that should exist per policy but cannot be located
- **archive_available**: Loss is mitigated by an available archive or backup

### Production Impact

- **source_lost** / **source_missing**: The source data is gone and cannot be recovered
- **not_produced**: Responsive documents exist but have not been produced
- **underproduced**: Some documents produced but material ones missing
- **withheld_unlogged**: Documents withheld from production without corresponding log entries
- **privilege_exposure**: Documents produced that may contain privileged material
- **recode_needed**: Documents require recoding before production
- **no_production_impact** / **no_current_gap**: No impact on current production

### Action Types

- **disclose_to_government** / **disclose_preservation_issue**: Notify the requesting authority of a preservation or production issue
- **forensic_recovery** / **restore_from_backup**: Attempt technical recovery of lost data
- **collect_source** / **collect_personal_device** / **collect_personal_email**: Collect a previously uncollected source
- **recode_and_produce**: Fix coding errors and include in next rolling production
- **supplement_privilege_log**: Add missing entries to the privilege log
- **waiver_assessment_and_disclosure**: Assess whether privilege has been waived and disclose if so
- **privilege_re_review** / **privilege_recode_and_log**: Re-review privilege designations and correct the log
- **search_archive** / **collect_archive**: Search or collect from an available archive
- **qc_remediation**: Remediate quality-control findings
- **locate_missing_record**: Locate a record that should exist
- **monitor_only** / **no_action**: Monitor status only or no action required

## Supporting Files

- `references/api-endpoints.md` — Full reference for each hub API endpoint, including query parameters, response shapes, and usage notes
- `references/enum-usage.md` — Detailed guidance for choosing the correct enum value based on hub evidence
