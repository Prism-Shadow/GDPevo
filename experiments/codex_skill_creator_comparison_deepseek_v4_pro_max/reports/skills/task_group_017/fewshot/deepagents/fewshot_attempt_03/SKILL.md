---
name: investigation-review-hub
description: Structured gap analysis, remediation dashboards, production-readiness reviews, and retention-hold assessments using the Investigation Review Hub REST API for eDiscovery and legal hold matters. Use when the task provides a matter_id and asks for a structured JSON deliverable covering privilege log gaps, responsive coding defects, personal source gaps, retention events, QC findings, production stats, or cross-system remediation action plans. Trigger phrases include gap analysis, remediation dashboard, production readiness review, retention hold review, privilege log supplement, rolling production assessment, and any task directing the agent to the Investigation Review Hub via TASK_ENV_BASE_URL.
license: MIT
compatibility: designed for deepagents-code
---

# Investigation Review Hub

Use the Investigation Review Hub as the source of record for eDiscovery analysis.
The hub is a read-only REST API; its base URL is always provided in the task
context.

## Core Rules

1. **Never inspect local files for business evidence.** The hub is the only
   source of record for matter metadata, subpoena categories, production stats,
   custodian sources, review documents, privilege-log data, QC findings,
   retention events, and remediation actions.
2. **Filter everything by matter_id.** Every hub response spans all matters;
   filter client-side or in SQL with `WHERE matter_id = '...'`.
3. **Follow the answer template exactly.** Every task provides an
   `input/payloads/answer_template.json`. Use its field names, types, enums,
   and ordering rules. Never invent keys or enum values.
4. **Use stable hub record IDs.** Every finding, issue, risk, source, event,
   and privilege entry has a stable identifier (`doc_id`, `finding_id`,
   `source_id`, `entry_id`, `event_id`, `action_id`). Use these IDs in your
   output, not synthetic or generated keys.
5. **Return only the JSON object.** No prose outside the JSON.

## Workflow

1. Read `input/prompt.txt` for the task description and `matter_id`.
2. Read `input/payloads/answer_template.json` for the exact output schema.
3. Read any context payloads (`request_context.json`, `review_scope.json`,
   `matter_context.json`) for category labels and task framing.
4. Call `GET /api/schema` to understand the data model.
5. Pull matter-level data: `GET /api/matters` and `GET /api/subpoena-categories`.
6. Pull domain evidence from the relevant endpoints, filtered by `matter_id`.
   Use `POST /api/query` with `X-API-Key: review-key-017` for joins or aggregations.
7. Cross-reference records by stable IDs from the hub.
8. Fill the template with sorts and enum choices per its ordering rules.
9. Return the single JSON object.

## Endpoint Reference

See [references/endpoints.md](references/endpoints.md) for the full endpoint catalog and data model notes.

## Task-Type Patterns

See [references/analysis_patterns.md](references/analysis_patterns.md) for detailed analysis patterns covering:

- Rolling production gap analysis
- Retention and litigation-hold gap review
- Cross-system remediation dashboard
- Production-readiness review

## Key Analysis Rules

### Computing unlogged privilege documents
For every privilege entry with `issue_type = incomplete_log`:
`unlogged_count = withheld_count - logged_count`.

### Classifying retention events
- `post_hold_loss` -> critical risk, requires `disclose_preservation_issue`.
- `should_exist_missing` -> high risk.
- `active_system_loss` / `auto_purged` -> medium risk.
- `policy_destroyed_pre_hold` -> low risk, `no_action_policy_loss`.

### Identifying production gaps
- `production_stats.status = zero_claim_contradicted` with matching QC findings -> responsive documents exist but were not produced. Action: `recode_and_produce`.
- `production_stats.status = supplement_pending` -> incomplete production.
- `production_stats.status = rolling_review` -> still in review.

### Identifying source gaps
- `custodian_sources` with `issue_tags` containing `lost` -> `source_lost`.
- `custodian_sources` with `not_collected` and `personal_phone` or `personal_email` -> `source_missing`, action `collect_personal_device`.
- `custodian_sources` with `archive_available` -> remediation path via `search_archive`.

### Privilege analysis
- `privilege_entries.third_party = 1` -> `third_party_waiver`, action `waiver_assessment_and_disclosure`.
- `privilege_entries.issue_type = over_designated` -> documents withheld as privileged that may not be. Action: `qc_remediation` or `privilege_recode_and_log`.

### QC finding cross-referencing
- `qc_findings.source_ref` may contain comma-separated doc IDs. Split and include all.
- `qc_findings.issue_type = zero_claim_contradiction` -> confirms responsive documents exist for a zero-production claim.
- `qc_findings.issue_type = responsive_miscoding` -> document miscoded as non-responsive. Action: `recode_and_produce`.

## SQL Query Patterns

Use `POST /api/query` with `X-API-Key: review-key-017` for:

- Counting documents by category and responsiveness
- Aggregating withheld/logged/unlogged documents from privilege entries
- Joining production_stats with qc_findings on category_code
- Filtering custodian_sources by issue_tags (use `LIKE '%tag%'`)

Always scope queries with `WHERE matter_id = '...'`.
