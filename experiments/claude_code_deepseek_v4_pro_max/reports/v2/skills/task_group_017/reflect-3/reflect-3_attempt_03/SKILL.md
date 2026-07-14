# eDiscovery Production Review Skill

## Core Principle: Template-First Answer Construction

When given an answer template with explicit enum lists of issue types, categories,
or finding types, **include every entry from the enum** in the output. Use a
boolean or status field (e.g., `present: false`) to mark absent items rather
than omitting them. Filtering to "only material" items produces structurally
incomplete answers.

## API Usage Habits

### Endpoint Discovery
The investigation API exposes these standard endpoints per matter:
- `/api/matters/{matter_id}` — matter metadata (hold date, subpoena date, flags)
- `/api/subpoena_categories?matter_id={id}` — category definitions and sources
- `/api/production_logs?matter_id={id}` — production counts and review status
- `/api/collection_events?matter_id={id}` — collection status and gaps
- `/api/privilege_logs?matter_id={id}` — privilege designations and waiver risks
- `/api/qc_events?matter_id={id}` — QC findings and recovery counts
- `/api/custodians?matter_id={id}` — custodian roles, sources, and known gaps
- `/api/documents?matter_id={id}` — document-level coding and production status
- `/api/retention_rules?matter_id={id}` — retention periods and archive overrides
- `/api/destruction_events?matter_id={id}` — pre/post-hold destruction records
- `/api/search?matter_id={id}&q={query}` — keyword search across collections

### Batch Filtering Rule
Production logs carry a `batch` field. Only **`"current"`** batch entries
represent active production data. Entries labeled `"noise-1"` through
`"noise-7"` and similar are stale, duplicate, or otherwise non-material
distraction records. **Exception**: a `noise-N` production log may still be
material if corroborated by a collection event, destruction event, or privilege
log entry in the same category.

### Data Joins
- Join collection events to subpoena categories via `related_category_ids`
- Join privilege logs to categories via `category_id` and to custodians via `custodian_id`
- Join QC events to categories via the category IDs implied by `related_document_ids`
- Cross-reference destruction events with hold date to classify pre-hold vs post-hold

## Output Field Conventions

### Enum Casing
**Always use exact enum casing** as shown in the answer template. Common values:
- Severity: `critical`, `high`, `medium`, `low`
- Boolean: `true` / `false` (JSON literals, not strings)
- Counts: integer (use `0` when not applicable, never `null`)

### Sorting Rules (Apply Without Exception)
- Category IDs: ascending lexicographic (e.g., `CRN-03` before `CRN-04`)
- Issue IDs, finding IDs, action IDs: ascending lexicographic
- Rank values: consecutive integers starting at 1
- Document IDs: ascending within each finding
- Custodian IDs: ascending within each issue
- Source names: alphabetical
- Action enums in secondary lists: alphabetical

### Stable Identifiers
Use descriptive, stable identifiers for findings and actions that encode the
relevant category or issue (e.g., `ISS-CRN-04-001` or `ISS-001`). The template
typically requires `string` type with no mandated format, but consistency within
a single answer is expected.

## Classification Rules

### Pre-Hold vs Post-Hold
- Compare event dates against `hold_date` from the matter record
- Pre-hold destruction under routine retention policy → `timing_class: pre_hold_policy`
- Post-hold destruction or deletion → `timing_class: post_hold_spoliation`
- Sources destroyed pre-hold that are partially recoverable → `timing_class: recoverable_archive`

### Category Status Mapping
Map `review_status` from production logs to `category_status` in answers:
| Production Log review_status   | Category Status               |
|-------------------------------|-------------------------------|
| `needs QC` or miscoding note  | `needs_supplemental_production` or `blocked` |
| `privilege log incomplete`    | `needs_privilege_correction`  |
| `over-designation review`     | `needs_privilege_review`      |
| `source gap`                  | `blocked` (if zero produced) or `needs_supplemental_production` |
| `waiver review`               | `needs_privilege_review`      |
| `clawback review`             | `needs_privilege_review`      |
| `blocked_zero_production`     | Category has 0 produced count |

### Issue Type Mapping
Map QC event `issue_type` values to answer template enum values:
- `miscoded complaint` / `miscoded complaint documents` → `review_coding_error`
- `privileged coded non-privileged` → `privilege_miscoding`
- `privilege overlay mismatch` → `privilege_log_gap`
- `shared-drive deletion recovery` → `source_deletion`
- `attachment processing` → `processing_failure`
- `stale review coding` → `review_coding_error`

### Device/Source Gap Classification
- Factory reset / device wipe after hold → `device_wipe`, `post_hold_spoliation`
- Personal email/device not collected → `uncollected_source`
- Shared drive files deleted → `source_deletion`
- Teams/chat pre-policy gap → `pre_hold_policy` or `pre_2022_teams_gap`
- Archived source available despite active-system purge → `recoverable_archive`
- Hold notice omitted source → `hold_notice_defect`

## Privilege Handling Patterns

### Waiver Assessment Triggers
A privilege waiver assessment is required when:
- Privilege status is `privileged-coded`, `work product`, or `counsel communications`
  AND production status is `produced` → clawback check needed
- Privilege log shows `waiver_risk: true`
- Notes mention "forwarded to outside [banker/consultant]" → `recipient_role: outside_banker`
- `overdesignation_flag: true` with `privilege_status: business_only` → over-designation review

### Privilege Count Formulas
- `unlogged_privileged_count` = `withheld_privileged_count` − `privilege_logged_count`
- `privileged_coded_nonprivileged_count` = count from QC events where `issue_type` is privilege miscoding
- Counsel over-designation: when all responsive records are withheld with zero produced

## Remediation Action Ranking

Rank remediation actions by severity and urgency:
1. **Regulator notice** — always rank #1 when post-hold spoliation or privilege waiver requires disclosure. Tied to `regulator_notice_flag` from matter record.
2. **Clawback review** — privileged material already produced must be addressed before regulator sees it
3. **Forensic recovery / vendor retrieval** — attempt to recover lost sources before declaring final loss
4. **Privilege log supplement** — complete the privilege log before production is considered done
5. **Supplemental collection / hold refresh** — fix hold notice gaps, then collect missing sources
6. **QC reprocessing** — fix coding errors after privilege issues are resolved
7. **Privilege review** — over-designation review for all-withheld categories

### Action ↔ Owner Mapping
| Action                      | Owner Queue       |
|-----------------------------|-------------------|
| `regulator_notice`          | `legal`           |
| `privilege_log_supplement`  | `privilege_team`  |
| `privilege_review`          | `privilege_team`  |
| `clawback_check` / clawback | `review_vendor`   |
| `reprocess_qc`              | `review_vendor`   |
| `supplemental_collection`   | `e_discovery`     |
| `forensic_recovery`         | `client_it` or `forensic_vendor` |
| `vendor_retrieval`          | `e_discovery`     |
| `hold_refresh`              | `legal`           |

## Common Exclusion Rules

1. **Noise-only categories**: Do not include categories whose only production logs
   are `noise-N` batches, unless corroborated by a collection event, destruction
   event, or privilege log entry showing a material defect.
2. **Stale/non-material records**: Categories tagged with `obsolete policy`,
   `duplicate alias`, or `stale review coding` as their only issue are
   non-material. Exclude unless a current-batch production log also exists.
3. **Zero-count no-action items**: When an issue type is absent for a custodian
   or category, set `affected_count: 0`, `severity: low`, `timing_class:
   not_applicable`, and `primary_action: no_action`.

## Pitfalls

1. **Filtering the enum**: If the answer template lists explicit allowed values
   for `issue_id` or `issue_type`, include ALL of them in the output list with
   an appropriate boolean flag. Omitting absent items produces structurally
   invalid answers.
2. **Wrong batch filter**: Including `noise-N` production logs as material
   inflates category counts and introduces false issues.
3. **Enum case mismatch**: Answer validation uses exact string comparison. `post_hold_spoliation`
   ≠ `post-hold-spoliation` ≠ `Post Hold Spoliation`.
4. **Sort order violations**: Failing to sort category IDs, document IDs, or
   action enums ascending will cause field-level mismatches.
5. **Count type errors**: All counts must be integers. Use `0`, not `null` or
   omitted fields, when a count does not apply.
6. **Missing source_event_ids**: Every issue should reference its originating
   collection event IDs (`CE-xxxx`) and/or destruction event IDs (`DE-xxxx`)
   from the API data. Empty `[]` is acceptable when no event is identifiable.
7. **Over-narrowing materiality**: A single miscoded document in a category with
   hundreds of produced records is still a material finding for that category.
   Do not drop categories because the issue "seems small."
8. **Ignoring the hold date**: The `hold_date` from the matter record is the
   single most important date for classifying events as pre-hold or post-hold.
   Always fetch and use it.
