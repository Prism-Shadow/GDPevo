# Investigation Production Review Skill

## Environment

Base URL from `environment_access.md`: `http://34.46.77.124:9017`. Use this for all API calls.

Available JSON endpoints:
- `GET /api/matters` — list all matters (12 total; 5 train matters + 7 others incl. noisy comparators)
- `GET /api/matters/{matter_id}` — single matter metadata
- `GET /api/subpoena_categories?matter_id={id}` — subpoena categories
- `GET /api/production_logs?matter_id={id}` — production tracking logs
- `GET /api/privilege_logs?matter_id={id}` — privilege log entries
- `GET /api/collection_events?matter_id={id}` — collection events
- `GET /api/destruction_events?matter_id={id}` — destruction events
- `GET /api/retention_rules?matter_id={id}` — retention rules
- `GET /api/custodians?matter_id={id}` — custodian records
- `GET /api/qc_events?matter_id={id}` — QC event records
- `GET /api/documents?matter_id={id}` — document summaries
- `GET /api/search?matter_id={id}&q={query}` — free-text search

## Universal Rules

1. **Output JSON only** — no markdown, comments, memo text, or explanatory prose.
2. **Follow the answer_template.json contract exactly** — use the exact top-level keys, object shapes, enums, and field names specified.
3. **Use exact enum casing** from the template. Never invent new enum values.
4. **All counts are integers**, never null. Use 0 when no count is available.
5. **Booleans** are JSON `true`/`false`, never strings.
6. **Omit narrative fields** not in the template (notes, comments, descriptions).

## Filtering: Material vs Noise

The API contains intentional noise records. Filter aggressively:

### Noise Category IDs
Categories whose IDs match patterns like `CR-N*`, `GC-N*`, `N-*` (where * is 3+ digits, not 2-digit material codes) are **non-material noise**. Exclude them from all lists. Only include categories whose IDs follow the **material prefix pattern matching the matter** (e.g., `CRN-0[1-6]`, `N-0[1-6]`, `G-0[1-6]`, `R-0[1-2]`, `P-0[1-5]`).

Heuristic: material category IDs have a short alphabetic prefix followed by a **2-digit** numeric suffix (e.g., `CRN-03`, `G-05`). Noise categories have longer prefixes with 3+ digit suffixes or different formats (e.g., `CR-N001`, `GC-N004`).

### Noise Production Logs
Production log entries with `batch` starting with `"noise-"` are non-material. Only use entries with `batch: "current"` for counts and status. Do not include noise-batch counts in your tallies.

### Noise QC Events
QC events referencing only noise category IDs, or with generic issue types like `"duplicate custodian alias"`, `"stale review coding"`, `"duplicate family suppression"`, `"archive validation"` — weigh these lower. Only elevate QC events that directly link to material categories with specific, actionable defect types (`"miscoded complaint"`, `"privilege overlay mismatch"`, `"missing attachment text"`).

### Noise Documents
Documents whose `category_ids` are exclusively noise categories, or documents with `review_coding: "stale coding"` | `"family member"` that only touch noise categories, should be excluded from document_id lists.

### Noise Custodians
Custodians with `known_gaps` containing `"obsolete retention label"` or `"duplicate alias"` without material category impact are lower priority. Focus on custodians linked by material production log entries.

## Count Derivation Patterns

### For Production Gap Reviews (train_001 pattern)
- **affected_count**: from QC event `affected_count` or production log `withheld_privileged_count` for the relevant material category
- **produced_count**: from production log `produced_count` (material batch only)
- **withheld_count**: from production log `withheld_privileged_count` (material batch only)
- **privilege_logged_count**: from production log `privilege_logged_count` (material batch only)
- **unlogged_privilege_count**: `withheld_privileged_count - privilege_logged_count`

### For Retention/Hold Reviews (train_002 pattern)
- **quantity**: from collection event `collected_count` or `missing_count` (use 0 only when no count is available)
- **count** in recoverable_sources: from collection event or document summaries

### For Custodian Reviews (train_003 pattern)
- **affected_count**: from QC events and document counts in affected categories
- **recovered_count**: from QC `recovered_count` or collection event status
- **unrecovered_count**: from QC `failed_count` or computed as `affected - recovered`

### For Privilege/Production Reviews (train_004 pattern)
- **unlogged_privileged_count**: `withheld_privileged_count - privilege_logged_count` for the gap category
- **privileged_coded_nonprivileged_count**: count of documents where `privilege_coding` says privileged but `review_coding` says responsive/non-privileged and `production_status` is produced

### For Collection Readiness (train_005 pattern)
- **missing_count**: from collection event `missing_count`, or count of documents with status indicating unavailability

## ID Generation Conventions

Generate stable identifiers consistent across the output:

- **Finding IDs**: `CF-{category_abbrev}-{descriptor}` (e.g., `CF-CRN-03-MISCODED-COMPLAINT`)
- **Issue IDs**: `PI-{matter_abbrev}-{descriptor}` (e.g., `PI-CRN-COUNSEL-OVERBROAD`)
- **Action IDs**: `NA-{descriptor}` or `RA-{descriptor}` or `ACT-{NN}`
- **Recovery source IDs**: `RS-{descriptor}`
- **Hold defect IDs**: `HD-{descriptor}`
- **Record class IDs**: `RC-{descriptor}`
- **Flag codes**: Lowercase snake_case descriptive of the risk

## Severity Assignment Rules

| Condition | Severity |
|---|---|
| Post-hold spoliation (factory reset, deletion after hold date, off-site vendor destruction after hold) | `critical` |
| Uncollected sources, privilege log gaps, miscoded privileged documents produced, source deletions with some recovery | `high` |
| Processing failures, privilege overdesignation, pre-hold policy gaps, stale coding | `medium` |
| Recoverable archives, retention-note-only sources, collected-and-valid sources with minor gaps | `low` |

## Action Type Selection

Map defects to primary actions:

| Defect | Primary Action |
|---|---|
| Post-hold spoliation/loss | `regulator_notice` |
| Uncollected sources, missing archives, personal devices | `supplemental_collection` |
| QC miscoding or attachment failures | `reprocess_qc` |
| Privilege log incomplete | `privilege_log_supplement` |
| Privilege overdesignation | `privilege_review` |
| Privileged docs coded non-privileged and produced | `clawback_check` or `clawback_review` |
| Device wipe, forensic recovery needed | `forensic_recovery` |
| Hold notice defect | `hold_refresh` |
| Pre-hold policy-compliant destruction | `no_action` or `no_action_policy_gap` |
| Waiver risk (forwarded to outside party) | `waiver_assessment` |
| Offsite vendor records on destroyed media | `vendor_retrieval` |
| Teams/archive pre-retention gap | `teams_gap_assessment` or `archive_validation` |
| Laptop PST uncollected | `laptop_pst_forensics` |

## Action Ranking / Remediation Plan Ordering

Rank actions by urgency — highest urgency first:

1. **Disclosure/notice actions first**: `regulator_notice` for critical spoliation (`disclosure_step: true`)
2. **Forensic recovery / retrieval**: `forensic_recovery`, `vendor_retrieval`
3. **Supplemental collection**: for uncollected sources, personal devices, archive gaps
4. **QC reprocessing**: `reprocess_qc` for coding errors, attachment failures
5. **Privilege log supplementation**: `privilege_log_supplement`
6. **Privilege review / clawback**: `privilege_review`, `clawback_review`, `waiver_assessment`
7. **Hold refresh / policy documentation**: `hold_refresh`, `no_action_policy_gap`

Within the same urgency tier, actions with `disclosure_step: true` or `notice_required: true` sort before others.

## Owner Queue Assignment

| Action Type | Owner Queue |
|---|---|
| `regulator_notice`, `waiver_assessment` | `legal` |
| `supplemental_collection` | `e_discovery` or `client_it` |
| `reprocess_qc` | `review_vendor` |
| `privilege_log_supplement`, `privilege_review`, `clawback_check`, `clawback_review` | `privilege_team` |
| `forensic_recovery`, `laptop_pst_forensics` | `forensic_vendor` or `client_it` |
| `hold_refresh` | `litigation_support` or `client_legal` |
| `vendor_retrieval` | `records` |
| `teams_gap_assessment`, `archive_validation` | `client_it` |

## Notice / Disclosure Decision

`notice_required` or `disclosure_required` is **true** when:
- Post-hold spoliation occurred (destruction after hold date)
- Privilege log has >100 unlogged withheld items
- Personal device/encrypted messaging sources were not collected
- A source was destroyed post-hold with no recovery path
- Off-site vendor was not on the hold distribution before destruction

`disclosure_required` is **false** when all issues are pre-hold policy gaps, minor processing errors, or overdesignation that can be corrected without external notice.

## Sorting Rules (apply to every list)

- **category_ids**: ascending lexicographic (e.g., `N-01` before `N-03` before `N-05`)
- **document_ids**: ascending (e.g., `DOC-CRN-0001` before `DOC-CRN-0010` — lexicographic)
- **custodian_ids**: ascending (e.g., `C-GW-014` before `C-QA-027`)
- **source_event_ids**: ascending by prefix group then numeric suffix
- **affected_sources**: alphabetically
- **issue_ids**: ascending, unless another ordering field (like `rank`) controls
- **secondary_actions**: ascending alphabetically by action enum
- **category_findings / record_class_findings**: ascending by category_id or issue_id
- **ranked_escalations / next_actions / remediation_plan**: ascending by rank (consecutive starting at 1)

## Task-Type Specific Patterns

### Type A: Subpoena Category Gap Review (train_001)
- Inspect all subpoena categories, production logs, collection events, privilege logs, QC events, custodians, documents
- Produce `category_findings` (one per materially deficient category), `priority_issues` (one per distinct defect), `next_actions` (ranked remediation steps)
- Only include categories where material production, QC, collection, or privilege defects exist
- Cross-reference QC event IDs, privilege log IDs, collection event IDs in `source_event_ids`

### Type B: Retention & Hold Remediation (train_002)
- Separate pre-hold policy destruction from post-hold preservation problems
- Produce `record_class_findings`, `hold_defects`, `recoverable_sources`, `remediation_plan`, `overall` summary
- Use the task-local factual memo for hold implementation facts
- `timing_class` values: `pre_hold_policy`, `post_hold_spoliation`, `recoverable_archive`, `uncollected_source`, `retained_missing`

### Type C: Custodian Production Issue Review (train_003)
- Per-custodian review with `issue_findings`, `privilege_actions`, `attachment_failures`, `ranked_escalations`
- Include all issues from the issue_id enum that `present: true` for the custodian
- Separate privilege actions into waiver, overdesignation, miscoding sub-objects
- `notice_recommended` at top level is true if any issue has severity critical or post-hold timing

### Type D: Production & Privilege Review (train_004)
- Category-level status with production counts, privilege metrics, miscoding findings, and actions
- Compute `unlogged_privileged_count` as withheld minus logged
- Identify documents miscoded (e.g., complaint docs coded non-responsive, privileged docs coded non-privileged)
- `clawback_required: true` when privileged documents were produced under non-privileged coding

### Type E: Collection Readiness (train_005)
- Assess each subpoena category source type for retention gaps and readiness
- Produce `custodian_statuses`, `retention_gaps` (one per category source type), `collection_plan`, `risk_flags`
- `overall_readiness` is `not_ready_supplemental_collection_required` if any category is blocked; `ready` only if all sources are collected and validated

## Common Pitfalls

1. **Including noise categories** — double-check category_id patterns. Noise IDs have different prefix formats (extra hyphen, extra digits).
2. **Including noise-batch production logs** — only `batch: "current"` counts matter. Noise batches inflate counts and create phantom issues.
3. **Wrong severity on pre-hold vs post-hold** — compare dates carefully. Pre-hold destruction that was policy-compliant is low/medium; post-hold spoliation is critical.
4. **Using stale/overlapping privilege log entries** — some privilege log entries reference categories not actually material to the current matter. Verify the category_id is material before using counts.
5. **Missing the hold_date** — always fetch the matter record for the hold date. Spoliation is defined relative to this date.
6. **Double-counting across endpoints** — a document referenced in both a QC event and a privilege log should not be double-counted in affected counts.
7. **Incorrect boolean for counsel_all_withheld** — only `true` when ALL documents in the counsel category have production_status of "withheld" or "not produced".
8. **Rank not starting at 1** or having gaps — remediation/action ranks must be consecutive integers starting at 1.

## Workflow

1. Fetch the matter record (`/api/matters/{id}`) for hold_date, deadlines, flags
2. Fetch subpoena categories; filter to only material categories
3. Fetch production logs; filter to `batch: "current"` entries for material categories
4. Fetch privilege logs, collection events, destruction events, QC events, custodians, documents
5. Filter all records to material categories only; note noise records but exclude from output
6. Identify defects by cross-referencing production status vs subpoena scope vs QC findings vs privilege gaps
7. Derive counts from the material records (never from noise batches)
8. Assign severity based on timing relative to hold_date and nature of defect
9. Determine primary/secondary actions per defect
10. Build ranked remediation plan with disclosure steps first
11. Sort every list per the template's ordering rules
12. Validate: all enum values match template casing exactly; all counts are non-negative integers; no noise categories present
