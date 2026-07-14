# Investigation API Production Review Skill

## Environment

The investigation API is at the URL given by `<TASK_ENV_BASE_URL>`. All endpoints
return `{"count": N, "items": [...]}`.  Do not use localhost.

## Available Endpoints

| Endpoint | Query Param | Use |
|---|---|---|
| `/api/matters` | — | List all matters (top-level metadata) |
| `/api/matters/{id}` | — | Single matter detail |
| `/api/subpoena_categories` | `?matter_id=` | Category scope, sources, date ranges |
| `/api/production_logs` | `?matter_id=` | Per-category produced/withheld/logged counts |
| `/api/privilege_logs` | `?matter_id=` | Per-item privilege status, waiver risk, OD flag |
| `/api/qc_events` | `?matter_id=` | QC exceptions with affected/recovered/failed counts |
| `/api/collection_events` | `?matter_id=` | Source collections, gaps, hold relation |
| `/api/custodians` | `?matter_id=` | Custodian roles, sources, known gaps |
| `/api/documents` | `?matter_id=` | Document summaries with coding and status |
| `/api/retention_rules` | `?matter_id=` | Retention periods, archive overrides |
| `/api/destruction_events` | `?matter_id=` | Pre/post-hold destruction, recoverability |
| `/api/search` | `?matter_id=&q=` | Cross-collection keyword search |

## Critical Filtering Rules

### 1. Batch Filtering — MOST IMPORTANT

Production logs carry a `batch` field. **Only `"current"`-batch records are
material.** Noise batches (`"noise-1"` through `"noise-7"`) contain stale coding,
unrelated privilege rows, duplicate custodian aliases, obsolete retention
policies, and overlapping review batches. They must be excluded from all
category-level findings, issue analysis, and action plans. Treat them as
non-material noise.

### 2. Category ID Filtering

Material subpoena categories use a short prefix pattern: `{1-2 letters}-{2-digit number}`
(e.g. `CRN-01`, `N-03`, `G-04`, `R-10`, `P-02`).  Noisy/stale categories use a
longer pattern with `-N` followed by digits: `{prefix}-N{###}` (e.g. `CR-N001`,
`NV-N004`, `GC-N002`, `RD-N001`, `PH-N001`).  Cross-reference: if a category
appears ONLY in noise-batch production logs or only has noisy-tag documents,
exclude it from material findings unless the task payload or custodian record
specifically references it.

### 3. Output Filtering

Include only categories/issues with **material** defects. Omit categories that
have only noise-batch records, zero-count defects, or no relevant QC/collection
exceptions. The answer template normalization rules typically state: "Do not
include categories that have only noisy or stale non-material records."

## API Record Interpretation

### Production Log (current batch only)

```
produced_count      — responsive records produced
withheld_privileged_count — responsive records withheld as privileged
privilege_logged_count    — of the withheld count, how many appear on a privilege log
```

Key calculations:
- **Unlogged privilege gap** = `withheld_privileged_count - privilege_logged_count`
- **Blocked category** = `produced_count == 0` while responsive material is known to exist
- **Overdesignation signal** = `withheld_privileged_count > 0 AND produced_count == 0`
  for a broad non-privilege category (especially when `review_status` says
  `"over-designation review"`)

### Privilege Log Items

Key fields:
- `privilege_status`: `privileged-coded`, `counsel communications`, `work product`, `business-only`, `not privileged`, `privileged forwarded externally`, `privileged investigation`, `non-privileged`, `over-designated`
- `production_status`: `produced`, `withheld`, `redacted`, `not produced`, `needs review`, `pending`
- `logged_status`: `logged`, `not logged`, `partially logged`, `not required`
- `overdesignation_flag`: boolean — true means over-designation risk
- `waiver_risk`: boolean — true means possible privilege waiver
- `record_count`: integer count of records in this privilege log entry

**Privilege defect patterns:**
| Symptom | Diagnosis | Action |
|---|---|---|
| `withheld > logged` | Privilege log gap | `privilege_log_supplement` |
| All withheld, zero produced in counsel category | Overdesignation risk | `privilege_review` |
| `privilege_status: privileged*` + `production_status: produced` | Clawback required | `clawback_review` / `clawback_check` |
| `waiver_risk: true` + `privileged forwarded externally` | Waiver | `waiver_assessment` |
| `overdesignation_flag: true` | Overdesignation | `privilege_review` + `produce_nonprivileged` |
| `privilege_status: business-only` + `production_status: withheld` | Overdesignation | `privilege_review` |

### QC Events

Key fields: `affected_count`, `failed_count`, `recovered_count`, `issue_type`, `related_document_ids`, `review_note`.

- `failed_count` = unrecovered/unresolved count
- `recovered_count` = successfully remediated count
- `affected_count` = total documents in scope for this QC exception

Common `issue_type` values and their meaning:
- `miscoded complaint` / `miscoded complaint documents` — responsive complaint docs coded non-responsive
- `privileged coded non-privileged` / `privilege miscoding` — privileged material coded non-privileged (clawback risk)
- `shared-drive deletion recovery` — post-hold deletions on shared drives
- `attachment processing` — password-protected or corrupt attachments
- `stale review coding` — coding imported from outdated review guide
- `archive validation` — archive availability not yet confirmed
- `duplicate custodian alias` — overlapping custodian identities
- `duplicate family suppression` — family grouping issues suppressing documents

### Collection Events

Key fields: `status`, `hold_relation`, `collected_count`, `missing_count`, `reason`, `source_type`, `related_category_ids`.

`hold_relation` values:
- `post-hold` — event occurred after the legal hold date
- `pre-hold` — event before the hold
- `pre-hold destruction identified` — pre-hold destruction found
- `hold not applicable` — not relevant to hold timing

`status` values and their remediation:
| Status | Meaning | Action |
|---|---|---|
| `unavailable` | Source destroyed or inaccessible | `forensic_recovery` or `custodian_declaration` |
| `wiped` | Device wiped | `forensic_recovery` |
| `not collected` | Source never collected | `supplemental_collection` |
| `not noticed` | Hold notice didn't cover this source | `hold_refresh` |
| `partial` | Partially collected | `supplemental_collection` |
| `collected with gap` | Collected but known gap | Gap-specific action |
| `pending` / `archive validation` | Archive availability TBD | `archive_validation` |
| `source gap` | Gap exists in this source | `supplemental_collection` |

### Retention Rules & Destruction Events

For retention/hold tasks:
- **Pre-hold policy destruction**: Destruction under a normal retention policy before the hold date. Classify as `pre_hold_policy`. Action: `no_action_policy_gap` (no spoliation, but document the gap).
- **Post-hold spoliation**: Destruction AFTER the hold date. Classify as `post_hold_spoliation`. Action: `regulator_notice` + `forensic_recovery`.
- **Recoverable**: Check `recoverability` on destruction events and `archive_override` on retention rules. "Recoverable from archive" / "archive copy" / "vendor copy required" means the data may still exist elsewhere.

### Documents

Key fields: `category_ids`, `custodian_id`, `privilege_coding`, `review_coding`, `production_status`, `source_type`, `summary`, `tags`.

- `review_coding`: `responsive`, `non-responsive`, `needs second-level review`, `family member`, `stale coding`, `unknown`, `unprocessed`
- `privilege_coding`: `privileged`, `not privileged`, `non-privileged`, `over-designated`, `unknown`
- `tags`: May include `miscoded`, `clawback`, `complaint`, `privilege`, `recovered`, `unrecovered`, `duplicate alias`, `obsolete policy`

## Cross-Entity Connection Patterns

When analyzing a matter, connect records across endpoints:

1. **Category → Production Log**: Match on `category_id` in current-batch production logs
2. **Category → Privilege Log**: Match on `category_id` for privilege defects
3. **Category → Collection Events**: Match on `related_category_ids`
4. **Category → QC Events**: Match through shared `custodian_id` and `issue_type`
5. **Custodian → Collection Events**: Match on `custodian_id`
6. **Custodian → QC Events**: Match on `custodian_id`
7. **Document → QC Events**: Match on `related_document_ids`
8. **Destruction Event → Category**: Match on `related_category_ids`
9. **Retention Rule → Destruction Event**: Match on `record_class`

## Severity Classification

Use these severity levels consistently:
- **critical**: Post-hold spoliation, wiped devices, unrecoverable destruction after hold, clawback of produced privileged docs
- **high**: Uncollected sources, privilege log gaps >100 records, overdesignation blocking production, hold notice defects
- **medium**: Stale review coding, partial collection gaps, archive validation pending
- **low**: Noisy records with minor coding issues, obsolete policy references with no material impact

## Disclosure Analysis

Determine `disclosure_required` by checking:
1. Is `regulator_notice_flag: true` on the matter?
2. Do any material issues involve `post_hold_spoliation`?
3. Are there critical-severity findings?

If any of these are true, `disclosure_required` is typically `true`. For `notice_required` on individual issues/actions, apply the same logic at the issue level.

## Timing Classification

Common timing classes and when to use them:
- `post_hold_spoliation` — destruction/loss after the hold date
- `pre_hold_policy` — destruction under normal retention policy before hold
- `coding_error` — miscoding during review
- `privilege_protocol_defect` — privilege log gaps, overdesignation
- `uncollected_source` — source never collected despite being in scope
- `recoverable_archive` — source exists in archive but not yet retrieved
- `retained_missing` — should be retained but not found
- `processing_exception` — attachment or processing failures
- `not_applicable` — timing not relevant

## Action Ranking

When building remediation plans, rank actions by severity and urgency:
1. **Regulator notice** (if post-hold spoliation exists) — always rank 1
2. **Clawback/privilege** issues (produced privileged, waiver risk) — rank 2–3
3. **Supplemental collection** (uncollected sources, partial collections) — rank 3–5
4. **Privilege log supplement** (log gaps) — rank 4–6
5. **Reprocess QC / coding correction** — rank 5–7
6. **Hold refresh** (hold notice defects) — rank 6–8
7. **Archive validation** — rank 7–9

Each action needs: `rank` (consecutive from 1), stable `action_id`, `action` (enum), `issue_ids` list, `category_ids` list, `owner_queue` (enum), `disclosure_step` boolean, and `due_basis` (short rationale string).

## Stable Identifier Conventions

Generate stable IDs that are consistent within the output:
- Issue IDs: `ISS-001`, `ISS-002`, ...
- Finding IDs: `F-001`, `F-002`, ... or `MF-01`, `MF-02`, ...
- Action IDs: `ACT-001`, `ACT-002`, ...
- Defect IDs: `DEF-001`, `DEF-002`, ...
- Source IDs: `SRC-001`, `SRC-002`, ...

## Sorting Rules (Universal)

Apply these sorts consistently across all output types:
- `category_ids`: lexicographic ascending
- `document_ids`: lexicographic ascending
- `custodian_ids`: lexicographic ascending
- `source_event_ids`: ascending by prefix group then numeric suffix
- `affected_sources`: alphabetical
- `issue_ids`: lexicographic ascending (unless rank defines order)
- `secondary_actions`: lexicographic ascending by action enum value
- `next_actions` / `remediation_plan` / `ranked_escalations` / `collection_plan`: by rank ascending (consecutive integers from 1)
- `issue_types` lists: alphabetical

## Task-Local Payload Files

Always read and incorporate task-local payload files referenced in the prompt:
- `input/payloads/partner_request.json` — additional instructions and factual context from the requesting partner
- `input/payloads/hold_exception_memo.json` — hold implementation facts that may override or supplement API data
- `input/payloads/answer_template.json` — the required output contract (schema, enums, required keys, ordering rules)

The memo/partner files may contain facts not present in the API (e.g., vendor names, specific dates, hold notice omissions). Treat these as authoritative supplements to API data.

## Answer Template Conventions

Answer templates (in `input/payloads/answer_template.json`) define:
- `required_top_level_keys` — the exact keys your JSON must contain
- `top_level_order` — the order those keys must appear in
- `ordering_rules` — sort rules for lists within the output
- `enums` — allowed values for each enum field
- `fields` — per-field type constraints and required sub-keys
- `normalization_rules` — global formatting rules

Follow them exactly. Key normalization rules that appear across templates:
1. Use exact enum casing (all lowercase snake_case unless template shows otherwise)
2. Use integer counts only (never floats or null; use 0 when not applicable)
3. Use JSON `true`/`false` booleans (never strings)
4. Do not include narrative fields the template doesn't ask for
5. Return JSON only — no markdown, comments, or explanatory text outside the JSON

## Common Pitfalls

1. **Including noise-batch records in findings.** Always filter production logs to `batch: "current"` first.
2. **Treating all privilege log entries as material.** Cross-reference log entries with current-batch production logs. A privilege log entry for a noise-only category is noise.
3. **Missing the unlogged-privilege calculation.** Always compute `withheld_privileged_count - privilege_logged_count` for current-batch records; this is the most common gap.
4. **Confusing pre-hold policy destruction with post-hold spoliation.** Pre-hold destruction under a normal retention policy is NOT spoliation. Post-hold destruction IS.
5. **Overlooking archive overrides.** Retention rules with `archive_override` values like "archive copy", "vendor copy required", or "email archive overrides active-server purge" mean the data may be recoverable even if the primary source was destroyed.
6. **Using incorrect enum casing.** All enums are lowercase_with_underscores. Check the template's `enums` section for exact allowed values.
7. **Forgetting task-local payloads.** The partner_request.json or hold_exception_memo.json may contain facts the API doesn't have.
8. **Including categories with zero material defects.** Only include categories that have actual production, collection, QC, or privilege defects in current-batch records.
