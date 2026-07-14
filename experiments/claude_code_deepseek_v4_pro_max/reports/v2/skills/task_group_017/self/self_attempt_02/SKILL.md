# E-Discovery Investigation API Skill

## Environment

Base URL: `<TASK_ENV_BASE_URL>` (resolved from `environment_access.md`).
All endpoints return JSON. No authentication required.

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `/api/matters` | List all matters (includes `hold_date`, `subpoena_date`, `deadline`, `agency`, `investigation_type`) |
| `/api/matters/{matter_id}` | Single matter detail |
| `/api/subpoena_categories?matter_id=...` | Category definitions with `label`, `requested_sources`, `date_range`, `topic_tags` |
| `/api/production_logs?matter_id=...` | Production status per category: `batch`, `produced_count`, `withheld_privileged_count`, `privilege_logged_count`, `review_status` |
| `/api/collection_events?matter_id=...` | Collection event records: `custodian_id`, `source_name`, `source_type`, `status`, `collected_count`, `missing_count`, `hold_relation`, `reason` |
| `/api/custodians?matter_id=...` | Custodian records: `role`, `status`, `relevant_sources`, `known_gaps` |
| `/api/privilege_logs?matter_id=...` | Privilege entries: `record_count`, `privilege_status`, `production_status`, `logged_status`, `waiver_risk`, `overdesignation_flag` |
| `/api/qc_events?matter_id=...` | QC exceptions: `issue_type`, `affected_count`, `failed_count`, `recovered_count`, `related_document_ids` |
| `/api/documents?matter_id=...` | Document summaries: `document_id`, `title`, `summary`, `tags`, `review_coding`, `privilege_coding`, `production_status`, `category_ids` |
| `/api/retention_rules?matter_id=...` | Retention policies: `record_class`, `retention_period`, `trigger`, `archive_override` |
| `/api/destruction_events?matter_id=...` | Destruction records: `event_date`, `quantity`, `pre_or_post_hold`, `recoverability`, `record_class` |
| `/api/search?matter_id=...&q=...` | Cross-collection keyword search (returns results grouped by collection type) |

## Core vs. Noise: The Most Critical Business Rule

Every endpoint mixes **material (core)** records with **noise** records. You MUST filter to core only. Use these signals in combination:

### 1. Production Log `batch` field (PRIMARY FILTER)
- `batch: "current"` → **material/category-defining**. Only these count.
- `batch: "noise-1"` through `"noise-7"` → stale/irrelevant. **Exclude entirely.**

### 2. Category ID naming pattern
- **Core**: Simple prefix-hyphen-number: `CRN-01`, `N-02`, `G-03`, `R-04`, `P-01`
- **Noise**: Prefix with embedded `-N`: `CR-N001`, `NV-N008`, `GC-N003`, `RD-N002`, `PH-N001`

### 3. Category topic_tags
- **Core tags**: Matter-specific substance tags (e.g., "market manipulation", "lab data", "whistleblower", "personnel", "advisory fees", "counsel communications")
- **Noise tags**: Generic markers: `obsolete policy`, `duplicate alias`, `stale review coding`, `logistics`, `retention` without matter connection. Tags like `"board"` or `"communications"` alone are ambiguous — use batch + category ID + label context.

### 4. Category labels
- **Core**: Specific to the investigation (e.g., "Market-manipulation communications", "Environmental lab data", "Advisory fee communications", "Whistleblower complaints and compliance escalations", "Former compliance custodian personnel file")
- **Noise**: Generic/repeated (e.g., "Draft policy revisions", "Pricing committee notes", "Sales forecast workpapers", "Regional operations chat", "Invoice exception escalations")

### 5. Custodian filtering
- **Core custodians**: Named explicitly in the task prompt OR have specific, matter-relevant `known_gaps` (e.g., "personal phone factory reset six days after subpoena", "work laptop replaced after hold; old laptop wiped")
- **Noise custodians**: Generic `known_gaps` like "duplicate alias appears in review platform", "stale review-guide coding from prior subpoena", "obsolete retention label in collection memo"

### 6. Collection event filtering
- **Core events**: Detailed, specific `reason` text tied to the matter. Custodian matches the task's target custodian or a core custodian. `hold_relation` is "post-hold" or "pre-hold destruction identified" with substantive content.
- **Noise events**: Generic reasons: "No material exception in current collection log", "Collection note references broader subpoena scope than review-guide coding", "Stale review coding may understate responsive material", "Duplicate custodian alias created overlapping source names", "Archive validation pending before final source status"

### 7. Privilege log filtering
- **Core entries**: Category matches a core category ID. Custodian matches a core custodian. Notes contain specific matter-relevant privilege issues.
- **Noise entries**: Generic notes: "Review note references stale privilege taxonomy", "Unrelated privilege row from overlapping review batch", "Business-only logistics thread may be over-designated", "Forwarded thread requires waiver analysis"

### 8. Document filtering
- **Core documents**: Document ID contains matter-specific markers (e.g., `DOC-CRN-TEST-ACC-001`, `DOC-GCF-PRIV-001`, `DOC-RDL-COMP-001`). Summary text is specific to the matter. Category IDs are core.
- **Noise documents**: Generic summaries: "Noisy document with overlapping tags across subpoena categories". Tags include "obsolete policy", "duplicate alias".

### Decision tree for category inclusion
1. Is the production log `batch` == `"current"`? If no → **exclude**.
2. Does the category ID follow the core pattern (no embedded `-N`)? If no → **exclude**.
3. Does the label match the investigation subject? If no → likely noise.
4. Are the tags matter-specific rather than generic? Confirm → **include**.

## Task Type Patterns

### 1. Production Gap Review (train_001 pattern)
Focus: subpoena categories, production completeness, collection events, privilege logs, QC events.
- Identify categories with `batch: "current"` in production logs
- Cross-check production_log `produced_count` against collection event data
- For each material category, check: blocked status, privilege gaps, overcoding, miscoding
- **Unlogged privilege gap** = `withheld_privileged_count` - `privilege_logged_count` (from current batch production log)
- Use QC events to find miscoded documents (especially for "miscoded complaint" type issues)
- Use collection events to find blocked sources: `status` of "unavailable", "wiped", "destroyed after hold", "not collected"

### 2. Retention & Hold Remediation (train_002 pattern)
Focus: retention rules, destruction events, collection events, hold defects, memo facts.
- Get `hold_date` from matter record
- Classify destruction events: `pre_or_post_hold` field determines timing
- Cross-reference with retention_rules for policy basis vs. hold obligations
- **Pre-hold policy destruction**: destruction before hold_date, per standard retention policy → `timing_class: "pre_hold_policy"`, `severity: "low"` unless critical records
- **Post-hold spoliation**: destruction after hold_date → `timing_class: "post_hold_spoliation"`, `severity: "critical"`, `notice_required: true`
- **Recoverable archive**: archive_override indicates data exists elsewhere → `timing_class: "recoverable_archive"`
- Memo facts supplement API records for hold notice defects (e.g., vendor not on hold distribution, personal devices omitted from notice)
- Hold defects are separate from record class findings: they describe process failures in the hold itself

### 3. Custodian Production Issue (train_003 pattern)
Focus: single custodian, their collection events, privilege issues, attachment failures.
- Filter collection events to the target custodian ID only
- Filter privilege logs to the target custodian
- Filter documents to the target custodian
- Check each collection event status: "wiped", "not collected", "partial", "collected with gap"
- Identify privilege issues: waiver_risk entries, overdesignation_flag entries, miscoded privilege
- Attachment failures: count password-protected and corrupt documents from document records with `source_type: "attachment"`
- **Issue presence**: for each possible issue_id (archive_gap, attachment_failure, date_range_gap, laptop_wipe, personal_email_gap, privilege_miscoding, privilege_overdesignation, privilege_waiver, shared_drive_deletion, etc.), set `present: true/false` based on evidence
- Rank escalations: post-hold spoliation first, then collection gaps, then privilege/protocol issues, then coding issues

### 4. Production & Privilege Review (train_004 pattern)
Focus: subpoena categories, production vs. privilege status, miscoding, remediation actions.
- Identify categories needing action from production_logs (only `batch: "current"`)
- **Blocked categories**: `produced_count == 0` despite responsive material existing
- **Privilege log gap**: `withheld_privileged_count > privilege_logged_count`
- **Overdesignation risk**: `produced_count == 0` and `withheld_privileged_count > 0` for counsel-communications category, or `overdesignation_flag: true`
- **Miscoding**: privileged documents coded non-privileged (from QC events with issue_type "privileged coded non-privileged") → clawback required
- **Privilege metrics object**: compute unlogged gap, check counsel category for overdesignation, count privileged-coded-nonprivileged documents
- Category status enum captures the dominant issue per category: `blocked_zero_production`, `privilege_log_incomplete`, `overdesignation_review`, `needs_qc`, `source_gap`, `ready`

### 5. Collection Readiness (train_005 pattern)
Focus: custodians, sources, retention rules, collection status.
- Parse retention rules to understand what should exist vs. what was collected
- For each custodian, assess each relevant source's collection status
- **Readiness**: `ready` only if all sources collected with no material gaps
- **Blocked**: if source has status "not collected", "not noticed", "wiped", "destroyed after hold"
- **Retention-gated**: if source is available but requires archive validation
- Retention gaps are categorized by source_type with timing_classification
- Risk flags capture specific risk patterns with severity and regulator-notice assessment
- Collection plan actions are ranked by priority (highest severity + blocking status first)

## Severity Assignment Rules

| Severity | When to use |
|---|---|
| `critical` | Post-hold spoliation/destruction; regulator notice required; privileged material produced without protection; complete source unavailability for key category |
| `high` | Significant unlogged privilege gap (>100 records); overdesignation blocking production; uncollected personal device/email; missing PST; destroyed recoverable records |
| `medium` | Partial collection gaps; privilege log incompleteness (<100 records); QC issues needing reprocessing; archive validation pending; miscoded responsive documents |
| `low` | Obsolete policy references; minor reconciliation issues; pre-hold policy destruction of non-critical records; stale coding with minimal impact |
| `none` | Category is production-ready with no material issues |

## Timing Classification Rules

| Timing Class | Criteria |
|---|---|
| `post_hold_spoliation` | Destruction/wipe/loss occurred AFTER `hold_date` |
| `pre_hold_policy` | Destruction BEFORE hold_date, consistent with retention policy |
| `coding_error` | Review coding was incorrect (miscoded responsive, miscoded privilege) |
| `privilege_protocol_defect` | Privilege log incomplete, overdesignation, or waiver risk |
| `uncollected_source` | Source known to exist but not collected |
| `recoverable_archive` | Primary source lost but archive/backup may exist |
| `retained_missing` | Should be retained per policy but cannot be located |
| `processing_exception` | Technical failure during processing (attachment, corruption) |
| `not_applicable` | Issue doesn't involve timing (e.g., stale coding from prior wave) |

## Remediation Actions Reference

| Action | When to use |
|---|---|
| `regulator_notice` | Post-hold spoliation; disclosure required to regulator/opposing party |
| `supplemental_collection` | Source exists but wasn't collected; need to collect now |
| `supplemental_production` | Produce corrected/reprocessed documents |
| `reprocess_qc` | Documents miscoded; need re-review |
| `privilege_log_supplement` | Privilege log missing entries; must supplement |
| `privilege_review` | Overdesignation suspected; review privilege calls |
| `produce_nonprivileged` | Business-only documents withheld as privileged; produce them |
| `forensic_recovery` | Wiped/destroyed device; attempt forensic recovery |
| `custodian_declaration` | Custodian-level gap requiring sworn statement |
| `hold_refresh` | Hold notice didn't cover all sources; re-issue |
| `clawback_check` / `clawback_review` | Privileged material produced; attempt clawback |
| `waiver_assessment` | Privileged communication forwarded externally; assess waiver |
| `vendor_retrieval` / `vendor_archive_retrieval` | Records held by vendor/archive; retrieve |
| `archive_validation` | Check archive before concluding loss |
| `teams_gap_assessment` | Teams data pre-2022 may be purged; assess gap |
| `laptop_pst_forensics` | Missing local PST on returned laptop; forensic check |
| `no_action` | No remediation needed (pre-hold policy gap, stale noise) |
| `coding_correction` | Fix review coding errors |

## Common Remediation Ranking

Rank actions by severity and blocking status:
1. **Regulator notice** (post-hold spoliation, critical) — always first
2. **Forensic recovery** (attempt before concluding loss)
3. **Supplemental collection** (fill gaps that block production)
4. **Hold refresh** (fix hold notice defects for future collections)
5. **Privilege review** / **privilege_log_supplement** (fix privilege defects)
6. **Clawback review** / **waiver_assessment** (address privilege risks in produced material)
7. **Reprocess QC** / **coding_correction** (fix review coding errors)
8. **Supplemental production** (produce corrected material)
9. **Archive validation** / **vendor retrieval** (confirm archive status)
10. **Custodian declaration** (documents gaps for record)

## Output Field Conventions

### Ordering rules (universal across all templates)
- **category_ids**: sort ascending lexicographically
- **document_ids**: sort ascending lexicographically
- **source_event_ids**: sort ascending by prefix group then numeric suffix
- **issue_ids**: sort ascending unless rank defines order
- **affected_sources**: sort alphabetically
- **secondary_actions**: sort action enums ascending (alphabetically)
- **Lists of objects**: sort by their primary ID field ascending unless rank column present
- **next_actions / ranked lists**: sort by `rank` ascending, consecutive integers starting at 1

### Enum casing
Always use exact casing from the answer_template.json enums. Common values: `snake_case` for statuses, `lowercase` for severities.

### Count fields
- Always integers, never null. Use `0` when not applicable (not `null` or omitted).
- **Unlogged privilege count** = `withheld_privileged_count - privilege_logged_count` (never negative; if logs exceed withheld, investigate for data inconsistency)
- **unrecovered_count** = `affected_count - recovered_count` for QC-attested issues
- `missing_count` from collection events is the source of truth for gaps

### Boolean fields
Use JSON `true`/`false`, never strings. `notice_required: true` when post-hold spoliation or regulator-notice-triggering event occurred.

## API Usage Workflow

### For any task:
1. **GET `/api/matters/{matter_id}`** — capture `hold_date`, `deadline`, `subpoena_date`, `agency`, `production_protocol_flag`, `regulator_notice_flag`
2. **GET `/api/subpoena_categories?matter_id=...`** — understand category scope and labels
3. **GET `/api/production_logs?matter_id=...`** — filter to `batch: "current"` only
4. **GET `/api/custodians?matter_id=...`** — identify core custodians (matter-specific gaps)
5. **GET `/api/collection_events?matter_id=...`** — filter by core custodian + core category
6. **GET `/api/privilege_logs?matter_id=...`** — filter by core custodian + core category
7. **GET `/api/qc_events?matter_id=...`** — identify miscoding and quality issues
8. **GET `/api/documents?matter_id=...`** — spot-check for document-level details

### For retention/hold tasks additionally:
9. **GET `/api/retention_rules?matter_id=...`** — understand what should be retained
10. **GET `/api/destruction_events?matter_id=...`** — classify pre/post-hold destruction

### For custodian-specific tasks:
- Filter **every** endpoint result to the target custodian ID before analysis
- Cross-reference collection events with custody records for completeness

## Critical Pitfalls

1. **DON'T include noise categories in findings.** Always filter production logs to `batch: "current"` first, then verify category ID pattern.
2. **DON'T treat all production log entries for a category as separate.** The `batch: "current"` entry is the authoritative record; noise-batch entries for the same category are stale/reconciling.
3. **DON'T confuse pre-hold policy destruction with post-hold spoliation.** The `hold_date` from the matter record is the bright line. Destruction before = policy gap (low severity unless critical records). Destruction after = spoliation (critical, notice required).
4. **DON'T use noise custodians.** Custodians with generic `known_gaps` like "duplicate alias appears in review platform" or "stale review-guide coding from prior subpoena" are not material to the investigation.
5. **DON'T include all privilege log entries.** Filter to core custodians + core categories. Entries with generic notes ("stale privilege taxonomy", "unrelated privilege row", "forwarded thread requires waiver analysis") are noise.
6. **DON'T include all collection events.** Filter by core custodian IDs and core category IDs. Events with generic reasons are noise.
7. **DO check archive availability before concluding a source is lost.** Retention rules with `archive_override` values of "archive copy", "email archive overrides active-server purge", "vendor copy required", or "legal hold suspends destruction" mean data may still exist.
8. **DO use the memo/partner_request facts** as supplements to API data — they provide hold implementation details not captured in API records.
9. **DO compute unlogged privilege counts** as `withheld_privileged_count - privilege_logged_count` using the current-batch production log.
10. **DO return only the JSON object** matching the answer template — no markdown, no comments, no explanatory text.
11. **DO sort all lists** according to the template's ordering rules — even if the template doesn't explicitly state it for every list.

## Search Tips

- Use `/api/search?matter_id=...&q=...` for keyword-based cross-collection lookups
- Search returns results grouped by collection type with up to 25 results per collection
- Useful for finding specific custodians, sources, or document patterns across collections
- Search hits in collection_events and custodians help confirm core vs. noise classification
