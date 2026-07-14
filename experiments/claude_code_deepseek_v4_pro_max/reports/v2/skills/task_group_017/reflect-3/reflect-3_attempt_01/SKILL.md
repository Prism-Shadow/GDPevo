# E-Discovery Production Review Skill

## Overview

This skill covers structured JSON reviews for legal production matters: gap reviews,
retention/hold remediation, custodian-level issue analysis, production-readiness
assessments, and collection-readiness evaluations. All work uses a shared
investigation API that exposes matter metadata, subpoena categories, production
logs, collection events, privilege logs, QC events, custodian records, retention
rules, destruction events, document summaries, and a cross-collection search.

## API Usage

### Endpoints

| Endpoint | Query Parameter |
|---|---|
| `/api/matters/{matter_id}` | — |
| `/api/subpoena_categories` | `?matter_id=...` |
| `/api/production_logs` | `?matter_id=...` |
| `/api/collection_events` | `?matter_id=...` |
| `/api/privilege_logs` | `?matter_id=...` |
| `/api/qc_events` | `?matter_id=...` |
| `/api/custodians` | `?matter_id=...` |
| `/api/retention_rules` | `?matter_id=...` |
| `/api/destruction_events` | `?matter_id=...` |
| `/api/documents` | `?matter_id=...` |
| `/api/search` | `?matter_id=...&q=<terms>` |

### Query Strategy

1. Always begin by fetching `/api/matters/{matter_id}` and the matter-specific
   payload file (partner request, hold memo, etc.) from `input/payloads/`.
2. Query all list endpoints in parallel for the target matter.
3. Use `/api/search` with keywords from the prompt and partner memo to surface
   documents and cross-collection records that keyword-only filtering would miss.
4. When a task targets a specific custodian, filter collection events, privilege
   logs, QC events, and documents to that custodian's ID.

## Core vs Noise Categories

Subpoena categories follow a two-tier naming convention:

- **Core categories**: Short prefix + numeric (e.g., `CRN-01`, `N-01`, `G-01`,
  `R-01`, `P-01`). These directly correspond to subpoena requests and are always
  in scope.
- **Noise categories**: Extended prefix with "N" (e.g., `CR-N001`, `NV-N001`,
  `GC-N001`, `RD-N001`, `PH-N001`). These represent ancillary, stale, or
  duplicate records.

**Exclusion rule**: Exclude noise categories from findings unless they contain
an explicit post-hold spoliation event or are cross-referenced by a core-category
production log or QC event. A category present only in noise-batch production
logs with review_status values like "partial_batch_record", "in_review", or
"batch_record" is not material.

## Batch Classification

Production logs carry a `batch` field. Only two batch values are material:

- **`"current"`**: The active production batch. All current-batch entries are in
  scope for findings. Their `review_status` drives the category-level assessment.
- **`"noise-X"`**: Stale, duplicate, or reconciliation-only records. Exclude
  these unless a post-hold destruction event or collection event with
  `status: "unavailable"` ties the category to a material defect.

## Materiality Thresholds

A category is **materially deficient** (include it in findings) when at least
one of these holds:

| Condition | Evidence |
|---|---|
| Zero production despite responsive documents | `produced_count: 0` in current-batch log + QC event showing miscoded docs |
| Privilege log incomplete | `withheld_privileged_count > privilege_logged_count` by a material margin |
| Over-designation | `review_status: "over-designation review"` or `overdesignation_flag: true` |
| Post-hold spoliation | Collection event with `hold_relation: "post-hold"` and `status: "unavailable"` or `"destroyed after hold"` |
| Post-hold source deletion | Destruction event with `pre_or_post_hold: "post-hold"` tied to a core category |
| Privilege waiver | Privilege log with `waiver_risk: true` or `production_status: "produced"` + privileged status |
| Miscoding/Clawback | QC event type `"privilege miscoding"` or `"miscoded complaint"` in a core category |

Do **not** include categories where the only evidence is:
- A noise-batch production log with stale-coding notes
- A privilege log entry flagged as "unrelated privilege row from overlapping review batch"
- A QC event referencing a custodian ID that does not appear in the matter's custodian list

## Count Derivation

| Metric | Formula |
|---|---|
| Unlogged privileged records | `withheld_privileged_count - privilege_logged_count` |
| Unrecovered count | `affected_count - recovered_count` (from QC events) |
| Attachment failures | `password_protected + corrupt` (from production log notes) |

Always use integer counts. Use `0` only when the API provides no count or the
count is truly zero. Never use `null`.

## Severity Assignment

| Severity | When to Use |
|---|---|
| `critical` | Post-hold spoliation, privilege waiver (produced privileged material), blocked zero production with responsive docs held back, laptop wipe after hold |
| `high` | Privilege log gap > 100 records, uncollected source (personal email/device), shared-drive deletion with unrecovered records, attachment processing failures blocking production |
| `medium` | Privilege overdesignation (over-withholding), pre-hold policy destruction, duplicate alias issues |
| `low` | Pre-hold policy gaps where the destruction was lawful, voicemail/auto-deletion under standard retention, archive validation pending with no loss confirmed |

## Timing Classification

| Class | Meaning | Typical Primary Action |
|---|---|---|
| `post_hold_spoliation` | Destruction/loss after legal hold date | `regulator_notice`, `forensic_recovery` |
| `pre_hold_policy` | Destruction before hold under valid retention policy | `no_action_policy_gap` |
| `privilege_protocol_defect` | Privilege log gap or over-designation | `privilege_log_supplement`, `privilege_review` |
| `coding_error` | Miscoded responsive material | `reprocess_qc`, `clawback_check` |
| `recoverable_archive` | Source lost from active system but available in archive | `supplemental_collection`, `vendor_retrieval` |
| `uncollected_source` | Source never collected (personal device, Gmail) | `supplemental_collection`, `hold_refresh` |
| `privilege_waiver` | Privileged material inadvertently produced | `waiver_assessment`, `clawback_check` |

## Action Ranking

When building `next_actions` or `remediation_plan` lists, rank by this priority:

1. **`regulator_notice`** — Always first when post-hold spoliation or privilege waiver exists. Requires disclosure.
2. **`forensic_recovery`** / **`waiver_assessment`** — Tied for second; recovery for device/data loss, waiver assessment for produced privileged material.
3. **`clawback_check`** / **`clawback_review`** — Recover inadvertently produced privileged documents.
4. **`supplemental_collection`** / **`vendor_retrieval`** — Collect missing sources or retrieve from vendors.
5. **`privilege_log_supplement`** — Fix incomplete privilege logs.
6. **`reprocess_qc`** / **`coding_correction`** — Fix coding errors.
7. **`privilege_review`** — Review over-designation.
8. **`hold_refresh`** — Update hold notices.
9. **`custodian_declaration`** — Obtain declarations.
10. **`no_action`** / **`no_action_policy_gap`** — Lawful pre-hold gaps requiring no action.

## Output Field Conventions

### Sorting Rules (apply to every answer)

| Field | Sort Order |
|---|---|
| `category_ids` | Ascending (lexicographic) |
| `document_ids` | Ascending |
| `custodian_ids` | Ascending |
| `source_event_ids` | By prefix group then numeric suffix (e.g., CE-0001 before CE-0010 before DE-0001) |
| `issue_ids` | Ascending (unless overridden by rank in an action plan) |
| `secondary_actions` | Ascending alphabetically |
| `affected_sources` | Ascending alphabetically |
| Category findings list | By `category_id` ascending |
| Priority issues list | By `issue_id` ascending |
| Next actions / remediation plan | By `rank` ascending (consecutive integers starting at 1) |
| Miscoding findings | By `finding_id` ascending |

### Enum Casing

All enums use `snake_case` exactly as shown in the answer template. Common
mistake: using `snake-case` or `camelCase`. Always match the template's
`allowed_values` list character-for-character.

### Boolean Fields

Use JSON `true` and `false` (lowercase). Never use string `"true"` or `"false"`.

### Required Keys

Every object in the answer template has a `required_object_keys` (or
`required_item_keys`) list. Include every listed key, even when the value is
empty (`[]`, `0`, `false`). For issue-finding lists that enumerate all possible
issue types, include every issue type with `"present": false` for absent ones —
the template expects a complete enumeration.

## Business Rules by Task Type

### First Rolling Production Gap Review

- Scope to categories in the `"current"` production batch.
- Also include any core category with a post-hold collection event showing
  `status: "unavailable"` or a destruction event with `pre_or_post_hold: "post-hold"`.
- `disclosure_required: true` when any post-hold spoliation or unlogged-privilege
  gap exceeds 100 records.
- `category_status` maps directly from production log `review_status`:
  - `"needs QC"` → `needs_supplemental_production`
  - `"privilege log incomplete"` → `needs_privilege_correction`
  - `"over-designation review"` → `needs_privilege_review`
  - Collection event `"unavailable"` → `blocked`

### Retention and Hold Remediation

- Separate findings into three buckets: `pre_hold_policy`, `post_hold_spoliation`,
  and `recoverable_archive`.
- Cross-reference the hold exception memo facts with API retention rules and
  destruction events.
- `blocked_category_ids` in the overall section: categories with post-hold
  spoliation where the source is not recoverable.
- `policy_gap_category_ids`: categories where pre-hold policy gaps exist
  (destruction was lawful under then-current retention policy).
- Hold defects are distinct from record-class findings: a hold defect is a
  failure in the hold process itself (vendor omitted, personal devices not
  covered), while a record-class finding describes what happened to the records.
- `recoverable_sources` should list every source that can still be collected:
  archives, vendor portals, partial summaries. Use `recovery_status: "available"`
  for fully reachable sources, `"partial"` for partial availability.

### Custodian-Level Production Issue Review

- Include ALL 13 issue types in `issue_findings`, marking `"present": false` for
  absent issues with `"severity": "low"`, `"timing_class": "not_applicable"`,
  `"primary_action": "no_action"`, empty arrays, and zero counts.
- `overall_status` is `"blocked"` when post-hold spoliation exists; use
  `"needs_escalation"` when multiple high/critical issues exist but no spoliation.
- The `privilege_actions` object has three sub-objects, each with distinct
  scopes:
  - `waiver_forward`: privileged material forwarded to an external party (banker,
    consultant, opposing party). Use the specific count and recipient role from
    the privilege log.
  - `overdesignation_review`: business-only material incorrectly marked
    privileged. Set `overdesignation_flag: true` and `privilege_status: "business_only"`.
  - `miscoding_clawback`: privileged material miscoded as non-privileged and
    produced. Set `first_pass_coding: "non_privileged"` and `clawback_required: true`.
- `attachment_failures`: sum `password_protected` and `corrupt` from the
  production log notes.
- `ranked_escalations` targets: `regulator_notice_review` for notice-triggering
  issues, `case_team` for waiver, `review_vendor` for coding/clawback,
  `forensic_vendor` for recovery, `client_it` for collection gaps,
  `privilege_team` for privilege review.

### Production Readiness and Privilege Review

- `affected_categories`: only categories with a current-batch production log
  showing a material defect. Sort ascending.
- `category_status.status` maps to the most severe condition:
  - Zero production + miscoded docs → `blocked_zero_production`
  - Withheld > logged by significant margin → `privilege_log_incomplete`
  - All withheld, zero produced, overdesignation flag → `overdesignation_review`
- `privilege_metrics`: derive `unlogged_privileged_count` as
  `withheld_privileged_count - privilege_logged_count` for the gap category.
  Set `clawback_required: true` when any privileged-coded documents were
  produced or miscoded as non-privileged.
- `miscoding_findings`: each QC event of type "miscoded complaint" or
  "privileged coded non-privileged" maps to one finding. Use the document IDs
  from the QC event's `related_document_ids`. The `corrected_status` for
  miscoded complaints is `"responsive"`; for miscoded privilege it is
  `"privileged"`.
- `actions`: each action maps to one or more categories. Critical actions
  (coding correction, clawback) come before high-priority actions
  (log supplement, privilege review). All `required: true` in a production
  review context.

### Collection Readiness

- `overall_readiness`: aggregate from the worst individual source status.
  - All sources ready → `ready`
  - Only archive-validation pending → `ready_with_retention_note`
  - Any source blocked but recoverable → `not_ready_supplemental_collection_required`
  - Post-hold loss confirmed → `not_ready_post_hold_loss`
- `custodian_statuses`: for each custodian, assess every subpoena category source.
  Map source-level statuses to `readiness_status`:
  - `available`/`collected` with zero missing → `ready`
  - Archive source collected but validation pending → `ready_after_archive_validation`
  - Missing records from a recoverable source → `blocked_source_gap`
  - Hold notice defect (source never noticed) → `blocked_hold_notice_gap`
- `retention_gaps`: one entry per subpoena category, describing the worst source
  in that category. `timing_classification` uses `pre_2022_teams_gap` for Teams
  retention gaps, `within_retention_available` for sources within retention,
  `hold_notice_defect` for notice omissions, `uncollected_source` for missing
  devices/files.
- `collection_plan`: rank so that notice/regulatory actions come first, then
  collection actions by criticality, then validation. Set
  `required_before_production: true` for any action that must complete before
  the production can proceed.
- `risk_flags`: enumerate every flag that applies, one per distinct risk. Severity
  follows the standard assignment. Only set `requires_regulator_notice: true`
  for post-hold spoliation flags.

## Common Pitfalls

1. **Noise-category inclusion**: Including CR-N*, NV-N*, GC-N*, RD-N*, or
   PH-N* categories in findings dilutes the answer. Only include them when a
   post-hold destruction event explicitly names them.

2. **Missing the unlogged-privilege calculation**: Always compute
   `withheld_privileged_count - privilege_logged_count`. Both values come from
   the production log, not the privilege log.

3. **Wrong severity for overdesignation**: Overdesignation (over-withholding
   business records as privileged) is `medium`, not `high` or `critical`. It
   is correctable through privilege review without regulator notice.

4. **Using privilege log counts instead of production log counts**: The
   production log is the authoritative source for category-level counts. The
   privilege log provides per-item detail. When they conflict, prefer the
   production log for aggregate numbers and the privilege log for specific
   document-level detail.

5. **Sorting errors**: Pay special attention to `source_event_ids` sorting —
   sort by prefix group (CE before DE before QC) then by numeric suffix. For
   `secondary_actions`, sort alphabetically by the enum string.

6. **Omitting required keys**: Every object in the answer template has
   `required_object_keys`. Include all of them. For absent issues, use `0`
   counts, `[]` arrays, and `false` booleans.

7. **Wrong `overall_status` in custodian reviews**: `blocked` means post-hold
   spoliation exists; `needs_escalation` means multiple issues without
   spoliation; `ready` means no material issues. Do not use `blocked` for
   correctable coding or privilege issues.

8. **Hold date precision**: The hold date must match the matter record exactly.
   When a hold exception memo provides a different date, the matter record
   takes precedence unless the memo explicitly corrects it.

9. **Document ID format in findings**: Use the exact `document_id` values from
   the API. Document IDs follow patterns like `DOC-{MATTER}-{TYPE}-{NUM}`.
   When a QC event lists `related_document_ids`, use those exact IDs in the
   miscoding finding.

10. **Missing cross-references**: A collection event, destruction event, QC
    event, and privilege log entry often describe the same underlying issue
    from different angles. Cross-reference all four before finalizing counts
    and category assignments.
