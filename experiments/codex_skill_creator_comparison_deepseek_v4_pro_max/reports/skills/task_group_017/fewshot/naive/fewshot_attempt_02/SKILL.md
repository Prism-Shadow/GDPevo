---
name: investigation-review-hub
description: |
  Structured legal investigation review using the Investigation Review Hub REST API.
  Use this skill when the task involves any of these review types for an identified
  matter and the task environment provides a `<TASK_ENV_BASE_URL>` to the
  Investigation Review Hub:

  - Rolling production gap analysis
  - Retention and litigation-hold gap review
  - Cross-system remediation dashboard
  - Production-readiness review
  - Privilege and QC remediation review

  The skill covers API discovery, SQL-style querying via `POST /api/query`, answer
  template compliance (ordering rules, enums, numeric precision), cross-referencing
  data across hub endpoints, metric computation, and risk/issue identification.
---

# Investigation Review Hub Skill

## Overview

The Investigation Review Hub exposes a fixed set of REST endpoints for legal-review
data: matters, subpoena/request categories, productions, custodian sources,
documents, privilege logs, QC findings, retention events, and remediation actions.
Every task requires a single structured JSON answer that strictly conforms to an
answer template provided in `input/payloads/answer_template.json`. The template
dictates the top-level keys, field names, enum values, ordering rules, and numeric
precision; the hub endpoints supply the evidence.

## The Four-Step Core Workflow

Execute these steps in order for every task:

1. **Read the template.** Read `input/payloads/answer_template.json` first. Note
   every required key, every enum, every ordering rule, and every field type. Do
   not guess at the schema later.

2. **Discover the hub.** Call `GET /` and `GET /api/schema` to confirm the live
   endpoints and their response shapes. Read `references/hub-schema.md` for the
   standard schemas; cross-check with what `/api/schema` returns.

3. **Pull evidence.** Call every endpoint that the answer template implies. Pull
   all data before computing anything. When raw GET endpoints are insufficient, use
   `POST /api/query` with SQL.

4. **Build the answer.** Cross-reference IDs across endpoints, compute metrics,
   assign severity/status from the evidence, populate every template field, apply
   all ordering rules, then emit exactly one JSON object with no prose outside it.

## API Endpoints

The base URL is always `<TASK_ENV_BASE_URL>`. Every request uses header
`X-API-Key: review-key-017`.

### Read endpoints (GET)

| Endpoint | Returns | Key fields |
|---|---|---|
| `GET /` | Health / available endpoints | Confirms the live API surface |
| `GET /api/schema` | Table schemas | Column names and types for SQL queries |
| `GET /api/matters` | Matter record | `matter_id`, `client`, `hold_date`, `agency`, `case_type` |
| `GET /api/subpoena-categories` | Request categories | `category_code`, `title`, `description`, `matter_id` |
| `GET /api/productions` | Production batches | `production_id`, `category_code`, `status`, `doc_count` |
| `GET /api/custodian-sources` | Custodian data sources | `source_id`, `custodian`, `source_type`, `collection_status`, `notes` |
| `GET /api/documents/search` | Document records | `doc_id`, `category_code`, `coding`, `produced_status`, `privilege_status` |
| `GET /api/privilege-log` | Privilege log entries | `privilege_id`, `doc_count`, `withheld_count`, `logged_count`, `third_party`, `notes` |
| `GET /api/qc-findings` | QC finding records | `finding_id`, `category_code`, `finding_type`, `severity`, `doc_count`, `status` |
| `GET /api/retention-events` | Retention/preservation events | `event_id`, `record_type`, `status`, `event_date`, `hold_date`, `volume_count`, `volume_unit`, `policy_section` |
| `GET /api/remediation-actions` | Remediation action records | `action_id`, `target_id`, `action_type`, `owner`, `priority` |

### SQL query endpoint

```
POST /api/query
Header: X-API-Key: review-key-017
Body: {"sql": "SELECT ... FROM ..."}
```

Call `GET /api/schema` before writing SQL to confirm table and column names. The
query endpoint is read-only. Prefer it when you need counts, aggregates, joins, or
filtered subsets that the raw GET endpoints do not return directly.

Common query patterns:

- **Aggregate counts:** `SELECT category_code, COUNT(*) FROM documents GROUP BY category_code`
- **Filter by status:** `SELECT * FROM custodian_sources WHERE collection_status = 'not_collected'`
- **Join for gaps:** Cross-reference production status against subpoena categories to find categories with zero documents produced.
- **QC-verified defects:** `SELECT * FROM qc_findings WHERE status = 'confirmed' ORDER BY severity`

## Answer Template Compliance

Every template uses these structural rules. Violating any one will produce a
malformed answer.

### Required keys and ordering

The `required_top_level_keys` list is authoritative -- every key must appear at the
top level, even if its value would be an empty list or zero. Lists must be sorted
per `ordering_rules`. Within each list item, list-valued fields (category codes,
source refs) must be sorted ascending.

### Enums

Every field marked `enum:` may only contain values from the corresponding enum list
in the template. If the evidence does not exactly match an enum, choose the closest
applicable value. Never invent a new enum value.

### Numeric precision

All counts are whole integers. Zero is the default when a count does not apply. The
template may name specific metric keys like `unlogged_privilege_docs` or
`destroyed_lab_archive_box_count` -- compute these from the hub data, do not
hard-code them.

### Boolean fields

Fields like `rolling_production_ready` or `production_ready` are set to `true` only
when zero categories have open gaps or blockers. Any open gap means `false`.

## Cross-Referencing Data

Hub records are linked by stable IDs. The critical cross-reference chains:

1. **matter_id** ties everything together. Always filter by the matter_id from the
   task prompt and the context payload file.

2. **category_code** links subpoena_categories to productions, documents,
   qc_findings, and privilege_log. To assess category-level status, pull all records
   that reference a given category_code and count open issues.

3. **source_id** links custodian_sources to retention_events to
   remediation_actions. When a source has `collection_status: 'not_collected'` or
   `'lost'`, every category that source should cover is affected.

4. **document IDs** (doc_id, privilege_id, finding_id) anchor individual defects.
   When a QC finding references a document, the document's category_code tells you
   which categories are impacted.

5. **event_id** links retention_events to communication_gaps to
   remediation_actions. The same event_id may appear in multiple endpoints with
   different facets.

When the template asks for `source_refs`, `issue_refs`, `blocking_refs`, or
`target_refs`, use the stable hub record IDs (not invented labels) and sort them
ascending.

## Metric Computation Rules

Compute every metric from the hub data; do not estimate or copy from training
answers.

### Counting gaps

A category has an open gap when any of: zero productions for that category, any
document with a confirmed QC finding, any custodian source not collected, any
retention event with `post_hold_loss` or `should_exist_missing` status, or any
privilege log gap (unlogged > 0).

### Privilege metrics

- `withheld_privileged_docs` / `withheld_privilege_doc_count`: sum of
  `withheld_count` from privilege-log records with an open gap (where `logged_count`
  < `withheld_count`, or where `unlogged_count` > 0).
- `logged_privilege_docs` / `logged_privilege_doc_count`: sum of `logged_count` from
  those same incomplete-log records.
- `unlogged_privilege_docs` / `unlogged_privilege_doc_count`: `withheld` minus
  `logged` for those same records. Can also be pulled directly if the hub stores
  `unlogged_count`.

### QC and miscoding metrics

- `miscoded_responsive_doc_count`: sum of `document_count` from QC findings where
  `finding_type` indicates a responsiveness miscode (e.g., `"responsiveness_miscode"`
  or a zero-claim contradiction pattern).
- `miscoded_privileged_doc_count`: sum of `document_count` from QC findings
  indicating privilege miscoding.

### Retention metrics

- `destroyed_box_count` / `destroyed_lab_archive_box_count`: sum `volume_count`
  where `volume_unit` is `"boxes"` and `status` is a destruction/loss status.
- `post_hold_loss_event_count`: count retention events with `status` =
  `"post_hold_loss"` AND `hold_date` <= `event_date`.
- `pre_hold_policy_destroyed_event_count`: count retention events with `status` =
  `"policy_destroyed_pre_hold"`.
- `available_archive_count`: count sources or archives with availability status
  `"available_archive"`.

### Source counts

- `uncollected_personal_source_count`: count custodian_sources where
  `collection_status` is `"not_collected"` and `source_type` is a personal device
  type (`personal_phone`, `personal_email`, `personal_messaging`, `personal_device`).
- `lost_personal_device_count`: count sources with `collection_status: "lost"`.
- `uncollected_board_source_count`: count sources with `collection_status` =
  `"not_collected"` and type indicating a board or shared drive source.

### Category counts

- `categories_with_open_gaps` / `affected_category_count`: count distinct
  category_codes that appear in any open issue, gap, or non-ready status.
- `categories_with_any_gap_or_loss`: the sorted list of those category codes.
- `nonready_category_count`: count categories whose readiness_status is not
  `"ready"`.

### Boolean readiness

- `rolling_production_ready` / `production_ready`: `true` only when zero categories
  have an open gap. Any open gap means `false`.

## Risk and Issue Identification

### Severity assignment

Assign severity by combining evidence signals from the hub:

- **critical:** post-hold destruction, any source loss that cannot be remediated
  from an available archive, or a combination of uncollected sources with no available
  archive for key categories.
- **high:** uncollected sources, incomplete privilege logs, confirmed QC miscodes,
  third-party waiver exposure, missing required records.
- **medium:** system auto-purge gaps with available archives, over-designation of
  privilege without production impact, policy-compliant pre-hold destruction.
- **low:** pre-hold policy-compliant destruction that no longer affects producible
  material.

### Issue types (cross-template mapping)

Templates use different enum names for the same underlying concepts. Map evidence to
the template's enum:

| Evidence pattern | Common enum values across templates |
|---|---|
| Post-hold data loss | `preservation_failure`, `post_hold_loss` |
| Source never collected | `collection_gap`, `personal_source_gap` |
| Archive exists but not searched | `archive_available` |
| Document coded non-responsive but is responsive | `responsiveness_miscode` |
| Withheld docs with incomplete log | `privilege_log_gap` |
| Third party on privilege comms | `third_party_waiver`, `privilege_waiver` |
| Privilege coded but shouldn't be | `privilege_miscoding`, `over_designation` |
| Record should exist but doesn't | `missing_required_record` |

### Building the risk/issue objects

For each material defect found in the hub data:

1. Pick a stable hub record ID as the anchor (`finding_id`, `risk_id`, `issue_id`).
2. Map the evidence to the correct template enum for `issue_type`, `severity`,
   `status`, `source_status`, and `production_impact`.
3. Trace `category_impacts` by following the category_code chain from the anchor
   record through documents, productions, and sources.
4. Collect `source_refs` / `record_refs` -- every hub record ID that supports the
   finding, sorted ascending.
5. Pull numeric counts (`document_count`, `withheld_count`, `logged_count`,
   `unlogged_count`) from the hub record itself or from aggregate queries on related
   records.
6. Assign `recommended_action` based on the defect type and available remediation
   paths.

## Action Plan Construction

Every answer template includes a prioritized action list. Build it by:

1. Collect every `recommended_action` from findings/risks/issues.
2. Group by action type and owner so related work is bundled.
3. Assign `priority_rank` starting at 1 for the most urgent (critical severity +
   disclosure obligations), then descending through high, medium, low.
4. Use `P0` for disclosure and critical-loss actions, `P1` for collection and
   privilege remediation, `P2` for QC and over-designation cleanup, `P3` for
   monitoring-only items.
5. Set `due_days` when the template requires it: 3 for P0 disclosures, 5 for
   privilege/recode work, 7-10 for collections and archive searches.
6. Populate `target_refs` with the hub record IDs the action addresses, sorted
   ascending.
7. Populate `category_impacts` / `affected_categories` with the category codes
   benefited, sorted ascending.

## Template-Specific Patterns

The five review types share the same hub API but differ in answer structure. When
you read the template, identify which review type you have:

### Gap analysis style

Top-level keys: `matter_id`, `critical_findings`, `category_statuses`, `metrics`,
`priority_actions`.

Key enumerations: `issue_type` includes `preservation_failure`, `collection_gap`,
`responsiveness_miscode`, `privilege_log_gap`, `retention_loss`. `finding_status`
includes `open`, `remediation_pending`, `protocol_noncompliant`.

### Retention review style

Top-level keys: `matter_id`, `retention_events`, `communication_gaps`,
`available_archives`, `metrics`, `recommended_actions`.

One event_id may appear in both `retention_events` and `communication_gaps` when the
loss has both a retention and a comms-system facet. The `available_archives` list
includes only sources that can still be collected and whose `archive_status` is
`"available_archive"`.

### Remediation dashboard style

Top-level keys: `matter_id`, `top_risks`, `category_coverage`,
`retained_or_available_sources`, `metrics`, `action_plan`.

`top_risks` items use `risk_id` instead of `finding_id`. `category_coverage`
summarizes each non-clean category. `retained_or_available_sources` lists sources
that provide a remediation path; it can be empty when nothing is available.
`action_plan` includes `due_days`.

### Production readiness style

Top-level keys: `matter_id`, `readiness_statuses`, `issue_ledger`,
`privilege_corrections`, `metrics`, `priority_actions`.

`readiness_statuses` are per-category and use `blocking_refs`. `issue_ledger` is the
most detailed issue format with `current_coding`, `produced_status`,
`corrected_disposition`, `missing_component`, and `third_party` fields.
`privilege_corrections` is a separate privilege-specific list with
`correction_type`.

## Validation Before Emitting

Before writing the final answer:

1. Verify every `required_top_level_key` from the template is present.
2. Verify every list is sorted per `ordering_rules`.
3. Verify every list-valued field within each object is sorted ascending.
4. Verify every enum field uses only values from the template's enum lists.
5. Verify all counts are whole integers (no decimals, no null where 0 is correct).
6. Verify all IDs (source_refs, target_refs, record_refs, blocking_refs, issue_refs)
   come from the hub, not invented.
7. Verify the `matter_id` matches the task's matter.
8. Verify boolean readiness fields are `false` when any gap exists.
9. Emit exactly one JSON object with no surrounding text, markdown fences, or
   commentary.

## Reference

See [references/hub-schema.md](references/hub-schema.md) for the standard endpoint
response schemas, table column definitions, and common SQL query patterns.
