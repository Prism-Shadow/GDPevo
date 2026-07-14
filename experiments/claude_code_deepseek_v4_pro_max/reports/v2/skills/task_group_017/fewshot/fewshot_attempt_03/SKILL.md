# Investigation API Production-Review Skill

## API Usage

All endpoints live under `<TASK_ENV_BASE_URL>`. The API is read-only JSON.

### Standard endpoints (suffix with `?matter_id={id}`):
- `/api/matters/{id}` — matter metadata (hold_date, subpoena_date, deadline, agency, summary)
- `/api/subpoena_categories` — categories with `label`, `requested_sources`, `topic_tags`, `date_range`
- `/api/production_logs` — `produced_count`, `withheld_privileged_count`, `privilege_logged_count`, `review_status`, `batch`, `notes`
- `/api/privilege_logs` — `logged_status` (logged/not logged/partially logged), `overdesignation_flag`, `waiver_risk`, `privilege_status`, `production_status`, `record_count`
- `/api/qc_events` — `issue_type`, `affected_count`, `recovered_count`, `failed_count`, `related_document_ids`
- `/api/collection_events` — `status` (collected/unavailable/partial/pending/destroyed), `missing_count`, `hold_relation` (post-hold/pre-hold), `source_type`, `source_name`, `reason`
- `/api/documents` — `review_coding`, `privilege_coding`, `production_status`, `category_ids`, `tags`, `summary`
- `/api/custodians` — `role`, `status` (active/former), `known_gaps`, `relevant_sources`
- `/api/retention_rules` — `record_class`, `retention_period`, `archive_override`, `notes`
- `/api/destruction_events` — `pre_or_post_hold`, `quantity`, `recoverability`, `policy_basis`, `record_class`
- `/api/search?matter_id={id}&q=...` — cross-collection search returning documents, privilege_logs, production_logs

### API field conventions
- Event IDs use prefixes: `CE-` collection, `PL-` production log, `PV-` privilege log item, `QC-` QC event, `DE-` destruction, `RR-` retention rule, `DOC-` document
- Production log `batch` values distinguish current production (`"current"`) from noise/legacy batches (`"noise-1"` through `"noise-6"`, `"partial_batch_record"`, etc.)

## Category Filtering: Material vs. Noise

**Material categories** have a short prefix-number format: `CRN-01`, `N-02`, `G-04`, `R-10`, `P-03`.
**Noise categories** embed an "N" in the suffix: `CR-N001`, `NV-N002`, `GC-N005`, `RD-N001`.

### Exclusion rules
Exclude a category from findings when ALL of its records are noise:
- It only appears in production logs with `batch` starting with `"noise"` or in `partial_batch_record`/`in_review`/`batch_record` statuses without current-batch entries
- Its topic_tags include only non-material markers: `"obsolete policy"`, `"duplicate alias"`, `"logistics"`, `"archive"`, `"retention"`, `"review coding"`, `"vendor"` without accompanying material tags
- Its documents are all tagged with non-material tags and have `review_coding: "family member"` or `"stale coding"`
- Its QC events involve `"duplicate custodian alias"`, `"stale review coding"`, `"archive validation"`, `"duplicate family suppression"` without material impact

A category is **material** when it appears in:
- A production log with `batch: "current"` and a non-ready `review_status`
- A collection event with `hold_relation: "post-hold"` and `status` in `("unavailable", "destroyed after hold", "partial")`
- A privilege log with `logged_status: "not logged"` or `"partially logged"` and `overdesignation_flag: true`
- A QC event with `issue_type` like `"miscoded complaint"` (not `"duplicate custodian alias"` or `"stale review coding"`)
- Documents with `review_coding: "non-responsive"` but tags/content indicating they are responsive

## Severity Assignment

| Severity | When to use |
|----------|-------------|
| `critical` | Post-hold destruction/spoliation; device wipe after hold; factory reset of subpoenaed device; vendor destruction despite active hold; shared-drive deletion after hold with unrecovered loss |
| `high` | Uncollected source with responsive material; coding error blocking entire category production; privilege log gap where unlogged >> logged; miscoded complaint documents; personal email/channel gap |
| `medium` | Overdesignation without spoliation; processing failures (attachment, password, corrupt); pre-hold policy-driven destruction; coding errors with partial impact |
| `low` | Archive validation pending; stale coding on small sets; recoverable archive with no loss; policy gaps without destruction |

## Timing Classification

Derive `timing_class` from dates relative to the matter `hold_date`:
- `post_hold_spoliation` — destruction or loss event dated after hold_date, or collection event with `hold_relation: "post-hold"` and `status: "unavailable"/"destroyed after hold"`
- `pre_hold_policy` — destruction before hold_date under a documented retention policy; no remediation possible, only documentation
- `recoverable_archive` — source not in active collection but available in archive (e.g., seven-year email archive, Ironvault)
- `uncollected_source` — source in subpoena scope but never collected (no collection event, or event with `status: "pending"` and zero collected)
- `retained_missing` — should exist under retention policy but missing from collection
- `privilege_protocol_defect` — unlogged withholdings, overdesignation, privilege miscoding
- `coding_error` — responsive material miscoded non-responsive
- `processing_exception` — attachment failures, corrupt files, password-protected items
- `privilege_waiver` — privileged material forwarded to third party
- `not_applicable` — use when no timing dimension is relevant

## Notice Required Rules

Set `notice_required: true` when:
- `primary_action` is `regulator_notice`
- Post-hold spoliation is present (destruction/loss after hold date)
- Personal device/channel gaps exist (Signal, WhatsApp, personal phone uncollected after hold)
- Unlogged privilege counts exceed logged counts by a material margin
- Device wipe or factory reset after subpoena/hold date

Set `notice_required: false` when:
- Issue is a coding error correctable without withholding material
- Pre-hold policy-driven destruction (document, don't notice)
- Recoverable archive exists
- Processing/attachment failures that can be re-processed
- Overdesignation review without spoliation

## Action Ranking

When building ranked action lists, use this priority order:
1. `regulator_notice` — always first if any issue requires it; owner: `legal`
2. `supplemental_collection` / `forensic_recovery` — collect missing sources; owner: `client_it` or `e_discovery`
3. `hold_refresh` — fix hold notice defects; owner: `litigation_support`
4. `reprocess_qc` — fix coding errors; owner: `review_vendor`
5. `vendor_retrieval` — retrieve from vendor archives; owner: `records`
6. `privilege_log_supplement` — log unlogged privilege claims; owner: `privilege_team`
7. `privilege_review` — review overdesignation; owner: `privilege_team`
8. `clawback_check` / `clawback_review` — claw back miscoded privileged material; owner: `privilege_team`
9. `no_action` / `no_action_policy_gap` — document only; owner: `records`

### Owner queue mapping
| Action | Default owner_queue |
|--------|-------------------|
| `regulator_notice` | `legal` |
| `supplemental_collection`, `forensic_recovery` | `client_it` or `e_discovery` |
| `hold_refresh` | `litigation_support` |
| `reprocess_qc` | `review_vendor` |
| `privilege_log_supplement`, `privilege_review`, `clawback_check` | `privilege_team` |
| `vendor_retrieval` | `records` |
| `no_action`, `no_action_policy_gap` | `records` |
| `custodian_declaration` | `legal` |
| `waiver_assessment` | `privilege_team` |

Escalation target mapping (custodian-level reviews):
- `regulator_notice` → `regulator_notice_review`
- `forensic_recovery` → `forensic_vendor`
- `supplemental_collection` → `client_legal`
- `privilege_review`, `clawback_check`, `waiver_assessment` → `privilege_team`
- `reprocess_qc` → `review_vendor`
- `hold_refresh` → `client_legal`

## Count Field Conventions

- **affected_count**: total items impacted by an issue. From QC `affected_count`, collection `missing_count`, or privilege log `record_count`
- **produced_count**: items actually produced. From production log `produced_count`. Use 0 when nothing produced
- **withheld_count**: items withheld (not just privilege). From production log `withheld_privileged_count`
- **privilege_logged_count**: items actually on a privilege log. From production log `privilege_logged_count`
- **unlogged_privilege_count**: `withheld_privileged_count - privilege_logged_count` (from the relevant production log or privilege log item)
- **recovered_count**: items recovered after loss. From QC `recovered_count`. Use 0 if not applicable
- **unrecovered_count**: items not recovered. From QC `affected_count - recovered_count` or `failed_count`
- **missing_count**: items known missing from collection. From collection event `missing_count`
- Always use 0 (not null) when a count is not applicable. Never use negative values.

## Count Derivation Workflow

1. For each material category, find its `batch: "current"` production log — this is the authoritative source for produced_count, withheld_privileged_count, privilege_logged_count
2. Cross-reference with privilege log items (`PV-*`) for the same category to get record_count, logged_status, overdesignation_flag
3. Cross-reference with collection events (`CE-*`) for missing_count, status, hold_relation
4. Cross-reference with QC events (`QC-*`) for affected_count, recovered_count, failed_count
5. Cross-reference with documents for review_coding vs. actual content assessment

## Output Formatting Rules (universal)

1. **JSON only** — never include markdown fences, comments, or explanatory text outside the JSON object
2. **Integer counts only** — use 0 for N/A, never null or float
3. **Boolean true/false** — never string "true"/"false"
4. **Exact enum casing** — match the template's allowed_values exactly
5. **Sorting rules**:
   - category_ids: sort alphanumeric ascending
   - document_ids: sort ascending (numeric-aware)
   - issue_ids in findings: sort ascending lexicographic
   - source_event_ids in source_event_ids lists: sort by prefix group then numeric suffix (CE before DE before DOC before PL before PV before QC before RR)
   - affected_sources: sort alphabetically
   - secondary_actions: sort alphabetically by action enum
   - next_actions / ranked_escalations / remediation_plan: sort by rank ascending (consecutive integers from 1)
6. **Stable IDs**: use consistent ID patterns — `CF-{matter}-{descriptor}`, `PI-{matter}-{descriptor}`, `RC-{descriptor}`, `HD-{descriptor}`, `RS-{descriptor}`, `NA-{descriptor}`, `RA-{descriptor}`, `MF-{NN}`, `ACT-{NN}`
7. **disclosure_required**: true when any finding has notice_required: true OR post-hold spoliation is present
8. **due_basis**: short imperative phrase, e.g. "before SEC status call", "immediate post-hold destruction disclosure", "before production deadline"

## Source Event ID Selection

When populating `source_event_ids` for a finding, include:
- The collection event (`CE-*`) that recorded the gap/loss/collection
- The production log (`PL-*`) that documents the production status
- The privilege log item (`PV-*`) if privilege issue involved
- The QC event (`QC-*`) if coding/quality issue
- The retention rule (`RR-*`) if retention policy is relevant (train_002)
- The destruction event (`DE-*`) if destruction occurred
- The document ID (`DOC-*`) if a specific document is central to the finding

Only include IDs that are directly referenced in the API records for that finding. Do not invent IDs.

## Retrieval/Retention-Specific Patterns (train_002)

When reviewing retention and hold remediation:
- Map each `record_class` from retention_rules to collection events by `source_type` and `source_name`
- Derive `timing_class` by comparing `event_date` to `hold_date` and checking `hold_relation`
- `recoverability` from destruction events drives `recovery_status`: "not recoverable" → `retained_missing`; "recoverable from archive" → `partial`; "collected" → `available`
- Separate `policy_gap_category_ids` (pre-hold, no spoliation) from `blocked_category_ids` (post-hold, spoliation, missing, uncollected)
- `post_hold_spoliation_issue_ids` contains only issues with `timing_class: "post_hold_spoliation"`

## Custodian-Level Issue Enumeration (train_003)

When producing per-custodian issue_findings, enumerate all 13 possible issue_ids and set `present: true/false`:
- Use API data: custodian `known_gaps`, collection events, QC events, privilege logs, documents for that custodian
- `issue_type` maps to the nature: collection_gap, device_wipe, processing_failure, privilege_protocol_defect, review_coding_error, source_deletion, third_party_forward, uncollected_source
- Only include issues actually found in the records (present: true); skip absent issues unless the template explicitly requires them

## Collection Readiness Patterns (train_005)

- `overall_readiness` is the worst status across all categories:
  - `not_ready_post_hold_loss` if any post-hold destruction
  - `not_ready_supplemental_collection_required` if sources uncollected
  - `ready_with_retention_note` if only retention/policy gaps remain
  - `ready` if all categories production-ready
- `collection_plan` ranks actions by dependency: hold_refresh must precede supplemental_collection; collection/forensics before validation; validation before production
- `risk_flags` use stable flag_codes: `post_hold_loss`, `teams_pre_2022_gap`, `missing_local_pst`, `archive_recoverable_email`, `hold_notice_omitted_personal_cloud_text`, `former_personnel_retained`

## Production Tracker & Privilege Patterns (train_004)

- `affected_categories`: only categories whose production log `review_status` is not `"current_batch_record"` and not on noise-only batches
- `category_status` values determined by production log review_status:
  - `needs QC` → `blocked_zero_production` or `needs_qc`
  - `privilege log incomplete` → `privilege_log_incomplete`
  - `over-designation review` → `overdesignation_review`
  - `clawback review` → category needs clawback + privilege_log_supplement
- `privilege_metrics.unlogged_privileged_count` = withheld_privileged_count − privilege_logged_count for the log-gap category
- `miscoding_findings`: derived from documents where review_coding contradicts actual content tags/summary
- `actions`: deduplicate by action_type; sort by action_id; `required: true` when the action blocks production certification

## Common Pitfalls

1. **Don't include noise categories** — categories with `batch: "noise-*"` only, or tagged exclusively with non-material topics
2. **Don't double-count** — use the "current" batch production log as the single source of truth for counts; noise batches may overlap
3. **Don't treat partial_batch_record as blocked** — it's informational noise, not a production defect
4. **Don't confuse pre-hold policy destruction with spoliation** — pre-hold events don't require regulator notice
5. **Verify hold_date against event dates** — always compare to determine pre/post-hold classification
6. **Check archive_override in retention_rules** — a source marked "missing" may still be recoverable from archive
7. **Never use null for counts** — always 0 when N/A
8. **Never include markdown, code fences, or narrative text in output** — JSON only
