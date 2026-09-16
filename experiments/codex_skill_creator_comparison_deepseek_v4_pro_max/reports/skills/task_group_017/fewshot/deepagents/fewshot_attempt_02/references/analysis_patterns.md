# Analysis Patterns

These patterns apply across all review types. The key insight: every task produces a structured JSON answer against a template that defines every required key, every enum value, and every ordering rule. The agent's job is to gather evidence from the hub and populate the template correctly.

## General Approach

### Step 1: Absorb the template

Before calling any hub endpoint, read `answer_template.json` in full. Note:

- The `required_top_level_keys` — these must all be present in the output.
- The `ordering_rules` — apply these to every list.
- The `enums` section — these are the ONLY valid values for any enum field.
- The `fields` section — every object type has `item_required_keys` and `item_field_types`. Every object must include every required key.
- The `numeric_precision` — all counts are whole integers.

### Step 2: Identify the matter and scope

Read the request-context payload (typically `request_context.json`, `matter_context.json`, or `review_scope.json`). Extract:

- `matter_id` — use this as-is in the answer and in all hub queries.
- Category code list — these define the scope of the review.
- Any client/agency labels — use these to confirm the correct matter in hub data.

### Step 3: Gather all relevant hub data

Call every GET endpoint that could be relevant. Do not skip endpoints — a gap may only surface from one data source. At minimum, call:

- `/api/matters` — confirm matter metadata.
- `/api/subpoena-categories` — get the category codes and titles.
- `/api/productions` — get production status per category.
- `/api/custodian-sources` — get source collection status.
- `/api/documents/search` — get document coding and production status.
- `/api/privilege-log` — get privilege withholding and logging data.
- `/api/qc-findings` — get QC issues.
- `/api/retention-events` — get retention and preservation events.
- `/api/remediation-actions` — get existing remediation plans.

Use `POST /api/query` for joins when the GET endpoints do not provide cross-entity relationships directly.

### Step 4: Build the answer

Populate each section of the template with evidence-derived data. The order of population matters:

1. First, identify the individual findings/issues/risks from hub records.
2. Then, aggregate them into category-level statuses.
3. Then, compute metrics from the findings and category data.
4. Finally, build the priority action plan from the most critical findings.

## Review-Type Patterns

### Gap Analysis

Output keys: `critical_findings`, `category_statuses`, `metrics`, `priority_actions`.

Each finding maps to a hub record: a lost source (`SRC-*`), a miscoded document (`DOC-*`), a QC finding (`QC-*`), or a privilege log gap (`PRIV-*`). The `finding_id` is the hub record ID.

`category_statuses` aggregates findings per category. A category with multiple findings gets a combined status (e.g., `incomplete` when there are source gaps AND coding issues).

Metrics are counts: `unlogged_privilege_docs = withheld - logged`, `miscoded_responsive_doc_count` from QC findings with responsive coding issues, source counts from custodian-sources data.

### Retention and Hold Gap Review

Output keys: `retention_events`, `communication_gaps`, `available_archives`, `metrics`, `recommended_actions`.

`retention_events` are direct records from `/api/retention-events`. Map each event's status to the template's `retention_status` enum. Events with `active_system_loss` or `auto_purged` also appear in `communication_gaps`.

`available_archives` come from custodian-sources or remediation-actions where status is `available_archive`. Their `limits_irretrievable_loss_for_categories` should list the categories for which the archive can remediate a loss.

`metrics.destroyed_box_count` sums `volume_count` where `volume_unit` is `boxes`. `pre_hold_destroyed_box_count` counts only events with `status: policy_destroyed_pre_hold`. `post_hold_destroyed_box_count` counts events with `status: post_hold_loss`.

### Cross-System Remediation Dashboard

Output keys: `top_risks`, `category_coverage`, `retained_or_available_sources`, `metrics`, `action_plan`.

`top_risks` are the most severe findings sorted by priority_rank. Each risk uses a hub record as `risk_id`. The `status` field uses `risk_status` enums: `open` for unresolved source gaps, `protocol_noncompliant` for privilege log issues, `needs_recode` for coding errors.

`category_coverage` summarizes all issues per category. The `status` field picks from `category_status` enums based on the dominant problem: `preservation_loss` when sources are destroyed, `underproduced_privilege_corrections` when privilege issues exist, `responsiveness_gap` when responsive documents are miscoded, `source_gap_with_archive_available` when uncollected sources have an archive path.

`retained_or_available_sources` lists sources that are still available and can remediate losses. Each source declares which categories it can help (`limits_loss_for_categories`).

For metrics, compute `withheld_privileged_doc_count` and `logged_privilege_doc_count` from incomplete-log privilege entries only (not from entries with waived status). `unlogged_privilege_doc_count = withheld - logged` for those same entries. `third_party_waiver_doc_count` comes from privilege entries involving third parties.

### Production Readiness Review

Output keys: `readiness_statuses`, `issue_ledger`, `privilege_corrections`, `metrics`, `priority_actions`.

`readiness_statuses` covers categories that are not production-ready. The `readiness_status` enum is the primary signal: `not_ready_multiple_blockers` when a category has coding AND privilege issues, `not_ready_privilege_log_incomplete` for incomplete logs, `not_ready_privilege_waiver` for waived privilege, `not_ready_personal_source_gap` for uncollected personal sources.

`issue_ledger` is the authoritative itemized list. Each issue maps to a hub document, privilege entry, QC finding, or source. Include `current_coding`, `produced_status`, and `corrected_disposition` fields — these are unique to this review type and describe what the record IS coded as and what it SHOULD be coded as.

`privilege_corrections` is a separate privilege-specific section. It captures withheld/logged/unlogged counts for each privilege issue. The `correction_type` distinguishes `supplement_log` (incomplete log entries), `waiver_assessment` (third-party involvement), `privilege_recode` (miscoded privilege), and `downgrade` (over-designated privileged docs).

## Field Mapping

When populating an answer, map these hub fields to answer fields:

| Hub field | Answer field |
|---|---|
| `source_id` / `event_id` / `qc_finding_id` / `privilege_log_id` / `document_id` | `finding_id`, `issue_id`, `risk_id`, `correction_id` |
| `category_codes` (hub) | `affected_categories`, `category_impacts` (answer) — same codes, sorted ascending |
| `source_status` (hub) | `source_status` (answer) — match to template enum |
| `severity` / `risk_level` (hub) | `severity`, `risk_level` (answer) — match to template enum |
| `document_count` (hub, when available) | `document_count` (answer) — same value |
| `withheld_count` / `logged_count` (hub) | `withheld_count` / `logged_count` (answer) — same values |
| `withheld_count - logged_count` (computed) | `unlogged_count` (answer) |
| `volume_count` / `volume_unit` (hub) | `volume_count` / `volume_unit` (answer) — same values, use `0` and `not_applicable` when not present |
| `recommended_action` (hub, when available) | `recommended_action` (answer) — match to template enum |

## Priority Assignment

When creating action plans:

- **Priority rank 1 / P0**: Disclosure to government (preservation failures, post-hold losses). These have the highest legal exposure. Due in 3 days.
- **Priority rank 2+ / P1**: Immediate remediation — supplement privilege logs, recode and produce responsive docs, waiver assessments. Due in 3–7 days.
- **P2**: Important but lower urgency — QC remediation of over-designation, archive searches, locate missing records. Due in 5–10 days.
- **P3**: Monitoring items — document system gaps, policy-compliant pre-hold losses. Due in 10+ days.

Actions that combine multiple targets (e.g., one disclosure covering two lost sources) should list all affected categories in `category_impacts`.
