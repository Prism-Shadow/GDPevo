---
name: investigation-review
description: Analyze e-discovery review hub data for production gap analysis, retention and litigation-hold reviews, cross-system remediation dashboards, and production-readiness assessments. Use when the task requires structured JSON gap/remediation deliverables from the Investigation Review Hub — matters, subpoena categories, productions, custodian sources, review documents, privilege logs, QC findings, retention events, and remediation actions.
---

# Investigation Review Hub

## Overview

Use the Investigation Review Hub REST API as the sole source of record for e-discovery review tasks. Every task produces a single JSON object conforming to an answer template. The hub provides nine read-only GET endpoints, a schema endpoint, and a POST `/api/query` endpoint for SQL queries.

## Quick-Start Workflow

1. **Read the task prompt and answer template** — the template defines required keys, ordering rules, enums, field types, and numeric precision. It is the output contract.
2. **Fetch the matter** — call `GET /api/matters`, filter by `matter_id` from the prompt, and confirm the matter exists.
3. **Fetch subpoena categories** — call `GET /api/subpoena-categories?matter_id=...` to get all request category codes and their titles.
4. **Fetch all evidence tables** — call every evidence GET endpoint for the matter, or use `POST /api/query` when cross-table joins or full result sets (beyond GET pagination) are needed.
5. **Analyze gaps and risks** — cross-reference the evidence tables to find material gaps: privilege log gaps, responsiveness miscodes, collection gaps, preservation failures, retention losses, third-party waivers, over-designations, and zero-claim contradictions.
6. **Build the answer JSON** — use stable hub record IDs for all keys, sort lists per the template's ordering rules, use only the template's enum values, and compute metrics as whole integers.

## Evidence-Gathering Pattern

For every review, call every GET endpoint filtered by `matter_id`:

```
GET /api/matters
GET /api/subpoena-categories?matter_id=<id>
GET /api/productions?matter_id=<id>
GET /api/custodian-sources?matter_id=<id>
GET /api/documents/search?matter_id=<id>
GET /api/privilege-log?matter_id=<id>
GET /api/qc-findings?matter_id=<id>
GET /api/retention-events?matter_id=<id>
GET /api/remediation-actions?matter_id=<id>
```

When GET results are incomplete (e.g. `documents/search` truncates) or cross-table joins are needed, use:

```
POST /api/query
Header: X-API-Key: review-key-017
Body: {"sql": "SELECT ..."}
```

See [references/api-guide.md](references/api-guide.md) for common SQL query patterns and [references/schema.md](references/schema.md) for the full data model.

## Review-Type Guidance

Match the task prompt to one of these review types. Each type emphasizes different hub tables and gap classifications.

### Rolling Production Gap Analysis

Focus: production stats, QC findings, privilege log, custodian sources. Identifies categories not ready for production certification.

- Compare `production_stats.produced_count` against expected coverage per category
- Cross-reference `qc_findings` with `review_documents` to find responsiveness miscodes and zero-claim contradictions
- Check `privilege_entries` for `withheld_count > logged_count` (log gaps)
- Check `custodian_sources` for `status = not_collected` or `status = lost`
- Anchor findings on stable hub record IDs (doc, QC finding, source, or privilege entry IDs)

### Retention and Litigation-Hold Gap Review

Focus: retention events, custodian sources with collection status. Classifies losses as policy-compliant pre-hold vs. post-hold preservation failures.

- Primary table: `retention_events` — check `status` field for `policy_destroyed_pre_hold`, `post_hold_loss`, `auto_purged`, `active_system_loss`, `should_exist_missing`
- For each retention event, compare `event_date` against `hold_date` from `matters`
- Check `communication_gaps`: retention events where `status = auto_purged` or `active_system_loss` indicate system-level gaps (purge windows, deleted channels)
- Identify `available_archives`: custodian sources or archive records that can partially remediate losses
- Metric categories: pre-hold policy-compliant losses, post-hold preservation failures, system gaps, missing records, available remediation archives

### Cross-System Remediation Dashboard

Focus: all tables. Ranks material risks across production, privilege, retention, and collection systems.

- `top_risks`: Rank by severity (critical > high > medium > low). Each risk anchors on a hub record ID and references supporting IDs
- `category_coverage`: One object per category with a material non-complete status
- `retained_or_available_sources`: Sources that can still be collected or searched for remediation
- `metrics`: Roll up counts from all risk categories
- `action_plan`: Prioritized actions with due_days, owners, and target refs from the hub

### Production Readiness Review

Focus: production stats, review documents, QC findings, privilege entries. Determines which request categories are ready to certify.

- `readiness_statuses`: Per-category readiness with blocking refs from the hub
- `issue_ledger`: Material non-privilege and privilege-readiness issues keyed by stable hub IDs
- `privilege_corrections`: Separate correction package for withheld, logged, waiver, downgrade, and recoding issues
- Production-ready is false when any category has an open blocker

## Gap and Risk Classification Rules

Use these rules to classify findings consistently from hub evidence:

| Hub Evidence | Classification |
|-------------|---------------|
| `privilege_entries.withheld_count > logged_count` | privilege_log_gap / withheld_unlogged |
| `qc_findings.issue_type = responsiveness_miscode` + doc coded nonresponsive | responsiveness_miscode / not_produced |
| `qc_findings.issue_type = zero_claim_contradiction` | responsiveness_miscode / not_produced |
| `custodian_sources.status = lost` | preservation_failure / source_lost |
| `custodian_sources.status = not_collected` (with production obligation) | collection_gap / source_missing |
| `retention_events.status = post_hold_loss` | post_hold_loss / source_lost |
| `retention_events.status = should_exist_missing` | missing_required_record / missing_record |
| `retention_events.status = policy_destroyed_pre_hold` (date < hold_date) | retention_loss / no_production_impact (policy-compliant) |
| `retention_events.status = auto_purged` or `active_system_loss` | collection_gap / source_lost (system-level) |
| `privilege_entries.third_party = 1` with logged documents | third_party_waiver / privilege_exposure |
| `privilege_entries.issue_type = over_designated` | over_designation / privilege_exposure |
| `qc_findings.issue_type = privilege_miscoding` | miscoded_privilege / recode_needed |

## Answer Construction Rules

1. **Stable IDs**: Always use hub record IDs (doc_id, entry_id, finding_id, event_id, source_id, action_id) as finding/risk/issue keys. Do not invent new identifiers.
2. **Enum compliance**: Use only values from the answer template's enum lists. Do not invent category statuses, issue types, or action types.
3. **Sorting**: Follow the template's ordering rules. Sort by the specified key ascending within each list. Sort category codes ascending within every category list.
4. **Cross-referencing**: A finding's `source_refs` should list all hub records that support it. A category status's `source_refs` should list all findings/records affecting that category. An action's `target_refs` should list the specific hub records it targets.
5. **Counts**: All numeric fields are whole integers. `document_count`, `withheld_count`, `logged_count`, `unlogged_count` must be derived from hub data, not estimated.
6. **Boolean fields**: Use JSON `true`/`false` (not strings).
7. **Null fields**: Use JSON `null` (not the string "null") when a field is not applicable.
8. **JSON arrays in TEXT columns**: Hub columns like `category_impacts`, `affected_categories`, `issue_tags`, and `topic_tags` store JSON arrays as TEXT strings. Parse them with `json.loads()` before use.

## Script

- `scripts/query_hub.py` — Execute arbitrary SQL against the hub's POST `/api/query` endpoint. Run with `python3 scripts/query_hub.py "<SQL>"` or `python3 scripts/query_hub.py --file query.sql`. See [scripts/query_hub.py](scripts/query_hub.py).

## References

- [references/schema.md](references/schema.md) — Full data model: all tables, columns, types, joins, and business rules.
- [references/api-guide.md](references/api-guide.md) — Endpoint reference, common query patterns, and data interpretation notes.
