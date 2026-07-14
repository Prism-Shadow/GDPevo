# E-Discovery Legal Review Workstream Analyzer

Skill for synthesizing structured JSON reviews from the shared investigation API.
Covers production gap analysis, privilege review, collection readiness, custodian
issue reviews, and retention/hold remediation.

## API Endpoints

Base URL: `<TASK_ENV_BASE_URL>` from environment_access.md. All endpoints return
paginated JSON with `count` and `items`. Filter by `?matter_id=<MATTER_ID>`,
`?custodian_id=<CUSTODIAN_ID>`, or `?document_id=<DOC_ID>`.

| Endpoint | Key Fields |
|---|---|
| `/api/matters/<ID>` | `hold_date`, `subpoena_date`, `deadline`, `regulator_notice_flag` |
| `/api/subpoena_categories?matter_id=` | `category_id`, `label`, `requested_sources`, `topic_tags` |
| `/api/production_logs?matter_id=` | `batch`, `category_id`, `produced_count`, `withheld_privileged_count`, `privilege_logged_count`, `review_status`, `notes` |
| `/api/privilege_logs?matter_id=` | `overdesignation_flag`, `waiver_risk`, `privilege_status`, `production_status`, `logged_status`, `record_count` |
| `/api/qc_events?matter_id=` | `issue_type`, `affected_count`, `failed_count`, `recovered_count`, `related_document_ids` |
| `/api/collection_events?matter_id=` | `status`, `missing_count`, `hold_relation`, `source_type`, `reason`, `collected_count`, `related_category_ids` |
| `/api/custodians?matter_id=` | `known_gaps`, `role`, `relevant_sources`, `status` |
| `/api/documents?matter_id=` | `review_coding`, `production_status`, `privilege_coding`, `summary`, `tags` |
| `/api/destruction_events?matter_id=` | `pre_or_post_hold`, `quantity`, `recoverability`, `record_class`, `related_category_ids` |
| `/api/retention_rules?matter_id=` | `record_class`, `retention_period`, `archive_override`, `notes` |
| `/api/search?matter_id=&q=` | Searches across documents by keyword; returns `results.documents` |

## Critical Rule: Material vs. Noise Categories

**This is the single most important rule.** Only report on categories with
material defects. Exclude stale, noisy, or obsolete records.

**Identifying noise categories:**
- Production log `batch` field is the primary signal. `"batch": "current"`
  indicates material records. `"batch": "noise-1"` through `"noise-7"` (any
  noise-prefixed batch) indicates non-material records that should be excluded.
- Category IDs with an embedded `-N` (e.g., `CR-N001`, `RD-N002`, `PH-N003`,
  `NV-N019`) are noise/stale categories. Material category IDs use the matter
  prefix directly: `CRN-01`, `N-02`, `G-03`, `R-10`, `P-04`.
- Noise production logs typically have review_status values:
  `"partial_batch_record"`, `"in_review"`, `"review_reconciliation"`,
  `"source_reconciliation"`, `"archive_reconciliation"`, `"coding_reconciliation"`,
  `"batch_record"` (on noise batch). These are NOT material defects.
- Custodians with `C-CR-*` or `C-PH-*` IDs (generic review custodians) are
  typically noise. Material custodians have specific IDs like `C-GW-014`,
  `C-QA-027`, `C-FC-072`, `C-HL-033`, `C-RW-066`.

**When a category has both current and noise production logs:** use only the
current-batch data. A single `batch: "current"` production log with a flagged
review_status is sufficient for a finding.

## Production Log Interpretation

| review_status (on current batch) | What It Means |
|---|---|
| `"needs QC"` | Miscoded responsive material; check documents + QC events for the miscode |
| `"privilege log incomplete"` | Gap between withheld_privileged_count and privilege_logged_count |
| `"over-designation review"` | All/nearly-all records withheld; check for business-only overdesignation |
| `"batch_record"` | Normal production; not a defect unless QC/custodian data shows gaps |

**Unlogged privilege formula:** `withheld_privileged_count - privilege_logged_count`.

**Blocked categories:** A category is `blocked` (train_001 style) or
`blocked_zero_production` when `produced_count == 0` despite responsive material
existing, or when a critical source gap prevents production.

## Collection Event Interpretation

| event `status` | Meaning | Typical severity |
|---|---|---|
| `"unavailable"` | Source destroyed or unreachable | critical if post-hold |
| `"not noticed"` | Hold notice didn't cover this source | high (hold notice defect) |
| `"partial"` or `"collected with gap"` | Partial collection; check missing_count | medium-high |
| `"source gap"` | Collection didn't fully address the source | medium-high |
| `"pending"` or `"archive validation"` | Awaiting processing/validation | medium-low |
| `"collected"` | Fully collected | low (check only if notes flag issues) |

**Hold relation mapping:**
- `"post-hold"` → timing is `post_hold_spoliation` (severity critical) when source is unavailable
- `"pre-hold"` → timing is `pre_hold_policy` (severity medium) when within normal retention policy
- `"hold not applicable"` → source outside scope of hold
- `"pre-hold destruction identified"` → possible pre-hold policy destruction

**The `missing_count > 0` rule:** Any collection event with `missing_count > 0`
and `status` not `"collected"` represents a material gap. The `missing_count`
value directly becomes the `missing_count` or `unrecovered_count` in findings.

## Privilege Log Interpretation

- **Unlogged privilege gap:** `logged_status: "partially logged"` or `"not logged"`
  with high `record_count` and `production_status: "withheld"` → needs
  `privilege_log_supplement`.
- **Overdesignation:** `overdesignation_flag: true` + all records withheld +
  `privilege_status: "counsel communications"` → needs `privilege_review` to check
  for business-only material.
- **Waiver risk:** `waiver_risk: true` + `privilege_status: "counsel communications"`
  + produced/redacted → needs `waiver_assessment`. Check the recipient: forwarded
  to outside banker/consultant/vendor → waiver risk is real.
- **Miscoded privilege:** `privilege_status: "not privileged"` or `"business-only"`
  but `production_status: "produced"` and privilege-coded → clawback scenario.
  Check `privilege_coding` on associated documents.

## QC Event Interpretation

| QC `issue_type` | Action |
|---|---|
| `"miscoded complaint"` or `"miscoded responsive"` | reprocess_qc → supplemental_production |
| `"privilege overlay mismatch"` | privilege_review → clawback_check |
| `"stale review coding"` | reprocess_qc |
| `"duplicate custodian alias"` or `"duplicate family suppression"` | archive_validation |
| `"archive validation"` | Check if archive_recoverable; not immediately material unless failed_count high |
| `"missing attachment text"` | reprocess_qc or forensic_recovery |

## Severity Assignment

| Severity | When to Use |
|---|---|
| **critical** | Post-hold spoliation, factory-reset devices after subpoena, regulator-notice-required gaps |
| **high** | Large privilege-log gaps (unlogged > 500), miscoding blocking production, uncollected key sources, hold-notice defects |
| **medium** | Privilege overdesignation (reviewable), pre-hold policy destruction, processing failures, coding errors without production impact |
| **low** | Recoverable archives, minor QC gaps, policy-gap-only records |

## Action Type Conventions

These are the action enums used across all task types. Match to the template's
allowed values — different templates use slightly different enum names.

| Canonical Action | When | Typical Owner |
|---|---|---|
| `regulator_notice` | Post-hold spoliation, large unlogged privilege gaps | `legal` |
| `supplemental_collection` | Uncollected sources, hold gaps, personal devices | `e_discovery` or `client_it` |
| `forensic_recovery` | Wiped devices, deleted sources, missing PSTs | `forensic_vendor` or `client_it` |
| `reprocess_qc` | Miscoding, stale coding, QC failures | `review_vendor` |
| `privilege_log_supplement` | Unlogged privilege gap | `privilege_team` |
| `privilege_review` | Overdesignation risk, privilege miscoding | `privilege_team` |
| `clawback_check` | Privileged material produced as non-privileged | `privilege_team` |
| `produce_nonprivileged` | (secondary) After privilege review clears business-only material | — |
| `hold_refresh` | Hold notice defects, new sources discovered | `litigation_support` or `client_legal` |
| `waiver_assessment` | Third-party forwards of privileged material | `privilege_team` |
| `vendor_retrieval` or `vendor_archive_retrieval` | Vendor-held records | `records` or `e_discovery` |
| `archive_validation` | Archives needing confirmation before production | `e_discovery` |
| `custodian_declaration` | Gap needs sworn custodian statement | `legal` |
| `no_action` or `no_action_policy_gap` | Pre-hold policy gap (document only) | `records` |

## Action Ranking

When constructing ranked action lists:
1. **`regulator_notice`** always ranks first (if disclosure is required)
2. **`hold_refresh`** / immediate preservation steps rank next
3. **`supplemental_collection`** and **`forensic_recovery`** before processing
4. **`reprocess_qc`** before production/review actions
5. **`privilege_log_supplement`** and **`privilege_review`** before production
6. **`clawback_check`** and **`waiver_assessment`** after privilege review
7. **`vendor_retrieval`** and **`archive_validation`** in parallel with other work
8. **`no_action`** / policy gap documentation ranks last

## Disclosure Rules

- `disclosure_required: true` when ANY finding has `notice_required: true`
- Individual `notice_required: true` when:
  - `post_hold_spoliation` (critical destruction after hold was in place)
  - `privilege_log_gap` with high unlogged counts affecting production completeness
  - `personal_channel_gap` (personal devices used for business but never collected)
  - `hold_notice_defect` causing post-hold loss
- `notice_required: false` when:
  - Overdesignation (fixable through privilege review)
  - Coding errors (fixable through QC reprocess)
  - Pre-hold policy destruction (no duty breach)
  - Archive-recoverable gaps (material can be retrieved)

## Timing Classification

| timing_class | When |
|---|---|
| `post_hold_spoliation` | Destruction/loss AFTER the hold date (check hold_date from matter record) |
| `pre_hold_policy` | Destruction BEFORE hold date AND within stated retention policy period |
| `privilege_protocol_defect` | Unlogged privilege, overdesignation, privilege miscoding |
| `coding_error` | Review coding mistakes (non-responsive → responsive, privilege miscode) |
| `uncollected_source` | Source never collected despite being in scope |
| `recoverable_archive` | Archive copy exists despite primary source being unavailable |
| `processing_exception` | Attachment failures, corrupt files, technical processing issues |
| `hold_notice_defect` | Hold notice omitted a source type (e.g., personal devices, off-site vendor) |
| `retained_missing` | Should exist per retention policy but not found in collection |

## Source Event IDs

Use actual API-record IDs from the records that substantiate each finding:
- Production log: `PL-0001`, `PL-0002`, etc.
- Collection event: `CE-0001`, `CE-0002`, etc.
- Privilege log item: `PV-0001`, `PV-0002`, etc.
- QC event: `QC-0001`, `QC-0002`, etc.
- Destruction event: `DE-0002`, `DE-0003`, etc.
- Retention rule: `RR-0001`, `RR-0002`, etc.
- Document: `DOC-<MATTER>-<DESC>-<NUM>` or `DOC-<MATTER>-<NUM>`

Include only the IDs from API records that directly corroborate the finding.
Sort by prefix group then numeric suffix: CE before DE before DOC before PL
before PV before QC before RR.

## ID Naming Patterns

Create stable, human-readable IDs. Use the matter prefix:
- Category findings: `CF-<PREFIX>-<NUM>-<DESC>` (e.g., `CF-CRN-03-MISCODED-COMPLAINT`)
- Priority/record-class issues: `RC-<DESC>` or `PI-<PREFIX>-<DESC>` (match template)
- Hold defects: `HD-<DESC>` (e.g., `HD-OFFSITE-VENDOR`)
- Recoverable sources: `RS-<DESC>` (e.g., `RS-EMAIL-IRONVAULT`)
- Next actions: `NA-<DESC>` or `RA-<DESC>` (e.g., `NA-REGULATOR-NOTICE`)
- Miscoding findings: `MF-<NN>` (consecutive numbers, zero-padded)
- Action items: `ACT-<NN>` (consecutive numbers, zero-padded)
- Risk flags: descriptive lowercase with underscores (e.g., `teams_pre_2022_gap`)

## Count Conventions

- `affected_count`: total records/sources impacted by the issue
- `produced_count`: records actually produced for this category/custodian
- `withheld_count`: records withheld (privilege or other) — use `withheld_privileged_count` from production logs
- `privilege_logged_count`: records appearing in privilege log
- `unlogged_privilege_count`: `withheld_privileged_count - privilege_logged_count`
- `recovered_count`: records recovered after a gap (0 if none recovered)
- `unrecovered_count`: records still missing (use `missing_count` from collection events)
- Use **0** when a count is not applicable (not null, not omitted)
- All counts are integers; use the production log as the authoritative source for production/withheld/privileged counts

## Workflow for Any Review

1. **Fetch matter metadata** (`/api/matters/<ID>`) to get `hold_date`, `subpoena_date`, `deadline`
2. **Fetch all subpoena categories** and identify which have `batch: "current"` production logs
3. **Fetch production logs** — filter to current-batch; identify review_status flags
4. **Fetch privilege logs** — check for overdesignation, unlogged gaps, waiver risks
5. **Fetch collection events** — check status, missing_count, hold_relation
6. **Fetch QC events** — check for miscoding, privilege overlay issues
7. **Fetch custodians** — check known_gaps against API records
8. **Fetch documents** for specific document IDs referenced in QC/production logs
9. **For retention/destruction matters:** also fetch destruction_events and retention_rules, cross-reference dates against hold_date
10. **Cross-reference findings:** same category appearing in production-log gaps + privilege-log defects + collection-event gaps = multi-faceted issue
11. **Filter to material only:** exclude noise categories, noise-batch records, and categories where the only records are stale/obsolete

## Common Pitfalls

- **Do NOT report noise categories as findings.** Noise categories have IDs like `CR-N001`, `NV-N019`, `RD-N002`, `PH-N003` (contains `-N` after the prefix). Their production logs have `batch: "noise-*"`. Exclude them entirely.
- **Do NOT use noise batch production logs** for counts or status. Even if a material category (e.g., `CRN-03`) has noise-batch records, use only the current-batch data.
- **Do NOT double-count.** If a QC event and a production log describe the same miscoding, it's one issue with multiple source_event_ids, not two separate issues.
- **Do NOT fabricate source_event_ids.** Every ID must come from an actual API record.
- **unlogged_privilege_count** is a computed value (`withheld - logged`), not a field in the API.
- **post_hold_spoliation** requires the destruction/loss event date to be AFTER `hold_date`. Check the matter's `hold_date` field before classifying.
- **When a count is 0, write `0`** (integer), not null or omitted.
- **Sort all arrays** per the ordering rules in the answer template. Category IDs ascending. Document IDs ascending. Issue IDs ascending (except when rank-ordered). Source event IDs by prefix group then numeric suffix.
