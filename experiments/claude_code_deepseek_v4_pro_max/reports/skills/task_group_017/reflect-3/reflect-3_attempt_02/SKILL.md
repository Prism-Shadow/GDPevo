# Investigation Review Hub — Structured Analysis Skill

## Purpose

Produce structured JSON deliverables for legal-matter investigations (gap analysis, retention review, remediation dashboard, production-readiness review) using a read-only Investigation Review Hub as the sole source of record.

## Data Sources

The Investigation Review Hub exposes these tables via a read-only SQL endpoint:

| Table | Key columns | Purpose |
|---|---|---|
| `matters` | matter_id, name, agency, hold_date, investigation_type, status | Matter metadata and hold date |
| `subpoena_categories` | matter_id, category_code, title, topic_tags | Request categories with scope dates |
| `production_stats` | matter_id, batch_id, category_code, produced_count, withheld_count, responsive_count, status | Production batch statistics per category |
| `custodian_sources` | source_id, matter_id, custodian_name, source_type, status, post_hold, category_impacts, issue_tags | Custodian data sources and collection status |
| `review_documents` | doc_id, matter_id, category_code, responsiveness, privilege_status, produced_status, issue_tags | Individual document review records |
| `privilege_entries` | entry_id, matter_id, category_code, doc_count, withheld_count, logged_count, issue_type, third_party | Privilege log entries with logging gaps |
| `qc_findings` | finding_id, matter_id, issue_type, doc_count, affected_category, severity | Quality-control findings per batch |
| `retention_events` | event_id, matter_id, record_type, event_date, hold_date, status, volume_count, volume_unit, affected_categories | Retention and destruction events |
| `remediation_actions` | action_id, matter_id, action_type, priority, severity, owner, target_ref, due_days | Prioritized remediation steps |

A REST schema endpoint (`GET /api/schema`) describes all columns. Use `POST /api/query` with `{"sql": "..."}` for arbitrary read-only queries.

## Core Workflow

### 1. Scope the Matter

Query the matter by its `matter_id` to get the hold date, agency, and investigation type. The hold date is the critical boundary: events before it may be policy-compliant losses; events after it are preservation failures.

### 2. Inventory All Related Records

For the target matter, query every table with `WHERE matter_id = '<id>' ORDER BY 1`. Read all rows from every table — apparent noise in one table often corroborates a material finding in another.

### 3. Identify Material Issues

Not every record is a material issue. Use these filters:

- **Remediation actions are the anchor**: Actions whose `action_id` contains `NOISE` (e.g., `ACT-...-NOISE-01`) are operational filler and should be disregarded. The remaining actions, ordered by priority (P1 before P2 before P3), identify the truly material targets.
- **Source severity**: A custodian source is material when (a) its `status` is `lost`, `not_collected`, or `partial_collection`, (b) `post_hold = 1`, and (c) its `issue_tags` do not include `routine` alone. Sources tagged `routine` or `scope_exception` without a corresponding remediation action are operational background.
- **Privilege entries**: Material when `issue_type` is `incomplete_log` (logged < withheld), `third_party_waiver` (third_party = 1), or `over_designated`. Entries marked `clean` or `family_mismatch` with notes indicating no escalation are lower priority.
- **QC findings**: Material when tied to a remediation action target. Findings described as "noisy," "corrected in later overlay," or "similar to escalated records in another matter" are often not actionable for this matter.
- **Retention events**: Material when `status` is `post_hold_loss`, `should_exist_missing`, or `auto_purged` with event date after hold date. Events marked `policy_destroyed_pre_hold` are policy-compliant (lower risk). Events with notes like "remediated by archive collection" are resolved.

### 4. Map Hub Values to Template Enums

Answer templates define their own enum sets. Hub status values do not always match template enum values one-to-one. Common mappings:

| Hub value | Typical template enum |
|---|---|
| `system_loss` (retention_events) | `active_system_loss` |
| `retained` (retention_events) | `preserved_available` |
| `available` (retention_events/custodian_sources) | `available_archive` |
| `post_hold_partial_recovery` (retention_events) | `post_hold_loss` |
| `miscoded_nonresponsive` (qc_findings) | `responsiveness_miscode` |
| `miscoded_privilege` (qc_findings) | `privilege_miscoding` |
| `zero_claim_contradiction` (qc_findings) | `missing_required_record` or `responsiveness_miscode` |
| `over_designated` (privilege_entries) | `over_designation` or `privilege_miscoding` |
| `incomplete_log` (privilege_entries) | `privilege_log_gap` |

**Always check the template's enum lists.** Volume units, action types, owner roles, and status labels vary across templates even for the same underlying concept.

### 5. Build the Answer Object

Follow the answer template's ordering rules exactly:
- Sort lists by the specified key (usually an ID or code), ascending.
- Sort category code lists within each item ascending.
- Priority ranks start at 1 (highest priority).

**Use stable hub record IDs** as finding/risk/issue/action identifiers throughout. Do not invent synthetic IDs.

**Numeric fields**: Use `0` when a count is not applicable; use `null` for optional string fields that have no value. All counts are whole integers.

**Category statuses/coverage**: Include only categories with a material non-ready or non-complete status unless the template explicitly calls for all categories. A category with no open issues typically receives status `no_current_gap` or `no_open_gap`.

### 6. Compute Metrics

Count metrics by querying the relevant hub records:

- **Privilege gaps**: Sum `withheld_count`, `logged_count`, and compute `unlogged = withheld - logged` from privilege entries with `issue_type = 'incomplete_log'`.
- **Post-hold losses**: Count retention events where `event_date > hold_date` OR `status = 'post_hold_loss'`.
- **Source gaps**: Count custodian sources with material gap status (`lost`, `not_collected`) and `post_hold = 1`.
- **Available archives**: Count sources with `status = 'available'` and archive-related `source_type` or `issue_tags`.
- **Affected categories**: Count distinct category codes appearing in any material finding. List them sorted ascending.
- **Document-level counts**: Use `doc_count` from QC findings or `document_count`/`withheld_count` from privilege entries.

### 7. Validate Before Submitting

- Every string value in the answer that represents a status, type, or role must appear verbatim in the template's corresponding enum list.
- Every required top-level key and nested required key is present.
- All ID references exist in the hub data for this matter.
- List ordering matches the template's ordering rules.
- Count fields are integers (not strings).
- Optional string fields use `null`, not empty strings.

## Common Pitfalls

1. **Enum drift**: Templates for different task types use different enum sets. Never carry enums from one template into another — read the current template's enums fresh each time.
2. **Noise inclusion**: Remediation actions, QC findings, and source records with `NOISE`, `routine`, or `scope_exception` labels are operational padding. Filter them out before building the answer.
3. **Pre-hold vs. post-hold**: An event date before the hold date does not automatically make a loss acceptable — but `policy_destroyed_pre_hold` events are generally low-risk while `post_hold_loss` events are always material.
4. **Over-inclusion**: Including every source gap or QC finding dilutes the answer. Focus on the items directly targeted by non-noise remediation actions.
5. **Category impact propagation**: When a source or finding impacts multiple categories, list all affected categories. When a risk affects a category, that category's status should reflect the aggregate of all risks touching it.
6. **Volume unit mismatch**: Hub data may use units like `files`, `exports`, `reports`, `mailboxes`, or `system_window` that are not valid template enum values. Map these to the nearest valid enum value (typically `records`, `documents`, `boxes`, `days`, or `not_applicable`).
