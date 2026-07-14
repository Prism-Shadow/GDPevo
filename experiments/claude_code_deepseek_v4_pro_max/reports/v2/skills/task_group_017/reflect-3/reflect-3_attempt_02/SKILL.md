# Legal E-Discovery Production Review Skill

## Overview

This skill covers structured JSON reviews for legal document production, privilege,
retention, collection readiness, and custodian-level gap analysis in response to
subpoenas and regulatory investigations. The shared investigation API exposes
matter records, subpoena categories, production logs, collection events, destruction
events, privilege logs, QC events, custodian records, retention rules, and document
summaries.

## Task Types and Their Domains

| Task Pattern | Focus | Key Outputs |
|---|---|---|
| Production gap review | First rolling or interim production completeness | Category findings, priority issues, next actions |
| Retention and hold remediation | Pre-hold vs post-hold destruction, hold defects | Record class findings, hold defects, recoverable sources, remediation plan |
| Custodian production review | Single custodian's gaps, privilege, attachment issues | Issue findings (present/absent per known type), privilege actions, escalations |
| Production privilege and miscoding review | Category-level privilege log gaps, miscoded docs | Affected categories, privilege metrics, miscoding findings, ranked actions |
| Collection readiness | Source-by-source readiness for production | Custodian statuses, retention gaps, collection plan, risk flags |

## API Usage Habits

### Endpoint Inventory

Always fetch these in parallel for a matter before building any answer:

```
/api/matters/{matter_id}
/api/subpoena_categories?matter_id=...
/api/production_logs?matter_id=...
/api/collection_events?matter_id=...
/api/destruction_events?matter_id=...
/api/privilege_logs?matter_id=...
/api/qc_events?matter_id=...
/api/custodians?matter_id=...
/api/retention_rules?matter_id=...
/api/documents?matter_id=...
```

### Filtering Production Logs

Production logs come in two varieties:
- **`"batch": "current"`** — material, reflects actual production status. Use these for findings.
- **`"batch": "noise-N"`** — stale, non-material, or from earlier subpoena waves. Exclude from findings unless a current batch is absent and the category has post-hold destruction events.

### Filtering Subpoena Categories

Categories follow two naming conventions:
- **Main subpoena categories**: Short prefix + numeric (e.g., `CRN-01`, `N-02`, `G-03`, `R-10`, `P-04`). These are the categories under active review.
- **Noise/stale categories**: Longer prefix with `N` (e.g., `CR-N001`, `NV-N003`, `GC-N005`, `RD-N001`, `PH-N002`). These represent stale, obsolete, or out-of-scope records. **Exclude them from findings** unless a task memo or hold defect explicitly references them.

### Source Event IDs

Use event IDs from the API in `source_event_ids` fields:
- **`CE-*`** — Collection events (most commonly used)
- **`DE-*`** — Destruction events (for post-hold spoliation issues)
- **`QC-*`** — QC events (for miscoding/review issues)
- Avoid using `PL-*` (production log) or `PV-*` (privilege log) IDs as source events; those are category-level aggregates, not events.

### Counting Conventions

- **affected_count**: From production log or QC event `affected_count`.
- **produced_count / withheld_privileged_count / privilege_logged_count**: From the production log for the current batch.
- **unlogged_privilege_count**: `withheld_privileged_count - privilege_logged_count` for the category.
- **recovered_count / unrecovered_count**: From QC events (recovered vs failed).
- Use `0` only when the field genuinely has no value, not as a default for unknown data. For genuinely unknown quantities where a count is expected, use `0` only when the field description says "use 0 if not applicable."

## Output Field Conventions

### Enum Discipline

Every schema enforces exact enum casing. Common enums across tasks:

**Severity**: `critical`, `high`, `medium`, `low`

**Timing classifications** (varies by task):
- `post_hold_spoliation` — destruction after the legal hold date
- `pre_hold_policy` — destruction before hold, within retention policy
- `privilege_protocol_defect` — privilege log errors, overdesignation
- `coding_error` — review miscoding
- `uncollected_source` — source never collected
- `recoverable_archive` — source exists in archive
- `retained_missing` — should exist under retention but missing

**Actions** (varies by task, common values):
- `regulator_notice` — disclosure to regulator required
- `supplemental_collection` — collect additional sources
- `supplemental_production` — produce additional documents
- `privilege_log_supplement` — fix incomplete privilege log
- `privilege_review` — review over-designated or questionable privilege claims
- `reprocess_qc` — re-run QC on miscoded documents
- `forensic_recovery` — attempt forensic recovery of wiped/lost data
- `clawback_check` — review for clawback of inadvertently produced privileged docs
- `hold_refresh` — reissue or expand legal hold notice
- `custodian_declaration` — obtain custodian affidavit
- `vendor_retrieval` — retrieve from vendor/archive
- `no_action` / `no_action_policy_gap` — no remediation needed

### ID Stability

Use stable, descriptive identifiers that survive across rolling productions:
- Issue IDs: `ISS-{MATTER}-NNN` (e.g., `ISS-CRN-001`)
- Action IDs: `ACT-{MATTER}-NNN` (e.g., `ACT-CRN-001`)
- Finding IDs: `CF-{CATEGORY}-NNN` (e.g., `CF-CRN-03-001`)
- Defect IDs: `DEF-{MATTER}-NNN`
- Source IDs: `REC-{MATTER}-NNN`
- Keep them consistent across the same answer.

### Sorting Rules (Nearly Universal)

- `category_findings`: sort by `category_id` ascending
- `priority_issues`: sort by `issue_id` ascending
- `next_actions` / `remediation_plan` / `ranked_escalations`: sort by `rank` ascending, consecutive starting at 1
- `category_ids` within items: sort ascending
- `document_ids` within items: sort ascending
- `custodian_ids`: sort ascending
- `secondary_actions`: sort ascending (alphabetically by enum value)
- `affected_sources`: sort alphabetically
- `source_event_ids`: sort by prefix group then numeric suffix

### Boolean and Count Hygiene

- Use JSON `true`/`false`, never strings
- All counts are integers, never floats or strings
- `notice_required` / `disclosure_required`: True when post-hold spoliation or unlogged privilege gap exists that must be disclosed to regulators

## Common Exclusion Rules

1. **Noise categories**: Exclude subpoena categories with `CR-N*`, `NV-N*`, `GC-N*`, `RD-N*`, `PH-N*` prefixes unless a task memo or hold defect explicitly references them.

2. **Noise batch production logs**: Exclude `"batch": "noise-N"` production logs from category-level counts. Only counts from `"batch": "current"` are reliable for findings.

3. **Non-material categories**: If a category has only noise-batch production logs and no collection/destruction/QC events, exclude it from findings entirely.

4. **Stale custodians**: QC events reference custodians not in the matter's custodian list — these are cross-matter noise. Only use custodians returned by `/api/custodians?matter_id=...`.

5. **Narrative fields**: Do not include unscored narrative, memo, or explanatory text. Return only the JSON contract.

## Remediation / Action Ranking Patterns

Rank remediation actions by urgency. The typical priority order:

1. **Post-hold spoliation requiring regulator notice** — Always rank 1. Destruction after the hold date demands immediate disclosure.
2. **Privilege log gaps with high unlogged counts** — Large gaps (hundreds or thousands unlogged) block production completeness.
3. **Privilege waiver or clawback** — Privileged documents inadvertently produced or forwarded externally.
4. **Source deletion / device wipe** — Forensic recovery attempts before declaring loss.
5. **Over-designation / overbroad withholding** — Categories with zero produced and all withheld need privilege review.
6. **Miscoding / review errors** — Reprocess QC before supplemental production.
7. **Uncollected sources / hold notice gaps** — Supplemental collection or hold refresh.
8. **Pre-hold policy destruction** — Note the gap but `no_action_policy_gap` if destruction was policy-compliant.

## Pitfalls

1. **Confusing pre-hold policy destruction with post-hold spoliation**: Check the hold date against destruction dates. Pre-hold destruction under a valid retention policy is not spoliation — it's a policy gap. Only destruction after the hold date is spoliation requiring notice.

2. **Mixing event types in source_event_ids**: Prefer `CE-*`, `DE-*`, `QC-*` IDs. Production log IDs (`PL-*`) and privilege log IDs (`PV-*`) describe aggregates, not discrete events.

3. **Over-including noise categories**: The API returns many obsolete/stale categories alongside the main subpoena categories. Filter by naming convention and batch type.

4. **Missing the hold_date**: For retention/hold tasks, the hold date is critical for classifying every finding as pre-hold or post-hold. Derive it from the matter record and cross-reference with the task memo.

5. **Wrong severity for privilege issues**: Unlogged privilege or privilege waiver is `critical`, not `high`. Over-designation without waiver is `high`. Routine miscoding is `high` if it blocks production, `medium` otherwise.

6. **Incorrect disclosure_required determination**: Disclosure is required when there is (a) post-hold spoliation/loss, or (b) a material privilege log gap that misrepresents the production to the regulator. Mere over-designation without spoliation does not trigger the disclosure flag by itself.

7. **Inconsistent ID formats**: Use a consistent prefix convention. Don't mix `ISS-001` with `ISSUE-CRN-01` in the same answer.

8. **Forgetting to sort**: Every list field in the output schema has a sort rule. Find it in the template's `ordering_rules` or field descriptions and apply it.

## Cross-Task Patterns

### Privilege Log Gap Analysis

For any category with `withheld_privileged_count > privilege_logged_count`:
- Calculate `unlogged_privileged_count = withheld_privileged_count - privilege_logged_count`
- If `unlogged_privileged_count > 0`, flag as `privilege_log_gap`
- If the gap is large (hundreds+) and `regulator_notice_flag` is true on the matter, `notice_required: true`

### Hold Defect → Spoliation Chain

When a task memo describes a hold defect (vendor not on distribution, source type omitted from notice):
1. Find the collection/destruction events affecting the impacted categories
2. Check if destruction dates fall after the hold date → post-hold spoliation
3. The hold defect is the root cause; the spoliation event is the consequence
4. Both should appear: the defect in `hold_defects`, the spoliation in `record_class_findings`

### Custodian-Issue Matrix

For custodian-level reviews, enumerate ALL known issue types from the schema (e.g., `archive_gap`, `laptop_wipe`, `privilege_waiver`, etc.) and set `present: true/false` for each. Issues present only for other custodians should be `present: false` with `severity: low`, `timing_class: not_applicable`. This ensures the output covers every possible issue dimension.

### Collection Readiness Triage

For each category/source:
- `ready` — source collected, no gaps
- `ready_after_archive_validation` — collected from archive, pending validation
- `ready_with_retention_note` — available but near retention boundary
- `blocked_source_gap` — material gap exists (pre-2022 Teams, missing PST, etc.)
- `blocked_hold_notice_gap` — source not included in hold notice

The `overall_readiness` is the worst of any individual readiness status.
