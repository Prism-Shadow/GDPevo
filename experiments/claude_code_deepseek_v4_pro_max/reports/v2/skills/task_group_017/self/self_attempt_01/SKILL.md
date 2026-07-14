# eDiscovery Production Review Skill

Use this skill when answering tasks against the shared investigation API for
matter-level production, privilege, collection, retention, and custodian
readiness reviews.

## Environment

The API base URL is provided per task via `<TASK_ENV_BASE_URL>`.  Always use the
remote URL; never fall back to localhost.  Task-local payload files (partner
requests, factual memos) live under `input/payloads/` and must be read alongside
API data.

## API Endpoints

All endpoints accept `?matter_id=M-…` as a query parameter and return
`{"count": N, "items": […]}`.

| Endpoint | Key fields | Use |
|---|---|---|
| `/api/matters/{id}` | `hold_date`, `subpoena_date`, `deadline`, `agency`, `investigation_type`, `production_protocol_flag`, `regulator_notice_flag`, `summary` | Orient: who issued the subpoena, when the hold started, and whether disclosure is expected |
| `/api/subpoena_categories?matter_id=…` | `category_id`, `label`, `date_range`, `requested_sources`, `topic_tags` | The universe of what was requested |
| `/api/production_logs?matter_id=…` | `category_id`, `batch`, `produced_count`, `withheld_privileged_count`, `privilege_logged_count`, `review_status`, `notes` | How much was produced/withheld/logged per category; batch signals materiality |
| `/api/privilege_logs?matter_id=…` | `category_id`, `custodian_id`, `record_count`, `privilege_status`, `production_status`, `logged_status`, `overdesignation_flag`, `waiver_risk` | Per-category privilege detail; logged vs unlogged gaps; over-designation |
| `/api/qc_events?matter_id=…` | `custodian_id`, `issue_type`, `affected_count`, `failed_count`, `recovered_count`, `related_document_ids`, `review_note` | QC exceptions — miscoding, duplicates, attachment failures, archive validation |
| `/api/custodians?matter_id=…` | `custodian_id`, `name`, `role`, `status` (active/former), `relevant_sources`, `known_gaps` | Who held responsive material and what gaps are already flagged |
| `/api/documents?matter_id=…` | `document_id`, `category_ids`, `custodian_id`, `source_type`, `review_coding`, `privilege_coding`, `production_status`, `title`, `summary`, `tags` | Individual document-level detail |
| `/api/collection_events?matter_id=…` | `event_id`, `custodian_id`, `source_name`, `source_type`, `collected_count`, `missing_count`, `status`, `reason`, `hold_relation`, `related_category_ids` | What was collected, what was missed, and why |
| `/api/retention_rules?matter_id=…` | `rule_id`, `record_class`, `retention_period`, `trigger`, `archive_override`, `notes` | Whether destruction was policy-driven or improper |
| `/api/destruction_events?matter_id=…` | `event_id`, `event_date`, `record_class`, `quantity`, `pre_or_post_hold`, `policy_basis`, `recoverability`, `related_category_ids` | What was destroyed, when, and whether it can be recovered |
| `/api/search?matter_id=…&q=…` | — | Keyword search across documents |
| `/api/document_summaries?matter_id=…` | — | Abbreviated document views |

## Category Identification: Core vs Noise

The API returns two classes of subpoena category:

- **Core (material) categories** use a short-format ID: a matter prefix, a dash,
  and a low two-digit number.  Examples: `CRN-01`, `N-03`, `G-04`, `R-10`,
  `P-02`.  These map to the actual subpoena requests and have real production
  obligations.

- **Noise categories** use a long-format ID: the prefix, `-N`, and three digits.
  Examples: `CR-N007`, `NV-N004`, `GC-N002`, `RD-N003`, `PH-N001`.  These carry
  stale retention references, obsolete policy tags, duplicate custodian aliases,
  and overlapping review batches.  They appear in the data to distract.

**Noise filtering rules:**
1. Production logs with `batch` starting with `"noise-"` (e.g. `noise-3`) are
   non-material unless they are the *only* log for a core category.
2. Categories whose ID matches the long `…-N###` form should be excluded from
   findings unless a task-local payload explicitly names them.
3. Documents with only noise category IDs and tags like `"logistics"`,
   `"obsolete policy"`, `"duplicate alias"` are non-material.
4. When only noise categories exist for a matter, cross-check against task-local
   payload files — the task may narrow the universe to a specific custodian or
   core set.

## Core Analytical Workflow

### Step 1 — Orient from the matter record

Fetch `/api/matters/{id}`.  Record:
- `hold_date` — the bright line for pre/post-hold timing
- `subpoena_date` — the scope anchor
- `agency` and `investigation_type` — informs severity of gaps
- `regulator_notice_flag` — true means the regulator expects notice of issues
- `deadline` — production deadline

### Step 2 — Map the category universe

Fetch `/api/subpoena_categories?matter_id=…`.  Separate core from noise.  Note
`requested_sources` for each core category — these define what should have been
collected and produced.

### Step 3 — Cross-reference production logs

Fetch `/api/production_logs?matter_id=…`.  For each core category, find the
production log(s).  Key signals:
- `batch: "current"` — the authoritative production tracker
- `produced_count: 0` with non-zero withheld → possible blockage
- `review_status` values and what they mean:
  - `"privilege log incomplete"` — `withheld_privileged_count` > `privilege_logged_count`
  - `"over-designation review"` — too much withheld as privileged
  - `"needs QC"` — pending QC remediation

### Step 4 — Layer in privilege logs

Fetch `/api/privilege_logs?matter_id=…`.  For each category with privilege
issues:
- Compute `unlogged = withheld_privileged_count − privilege_logged_count`
- Check `overdesignation_flag` — true means the category may be over-withholding
- Check `waiver_risk` — true means privileged material may have been produced
- Check `logged_status`: `"not logged"` or `"partially logged"` → log gap
- Check `production_status`: `"produced"` with `privilege_status: "counsel communications"` → possible waiver

### Step 5 — Review QC events

Fetch `/api/qc_events?matter_id=…`.  QC events may override production tracker
completeness.  Key `issue_type` values:
- `"miscoded complaint"` — responsive documents miscoded non-responsive
- `"privilege miscoding"` — privilege status wrong
- `"stale review coding"` — old coding from prior subpoena wave
- `"duplicate custodian alias"` — overlapping family counts
- `"archive validation"` — archive may still have material
- `"attachment processing"` / `"missing attachment text"` — attachment failures
- `"privilege overlay mismatch"` — privilege tags inconsistent

The QC `review_note` often contains an explicit instruction (e.g. "Compare
review guide to subpoena category scope", "Resolve stale coding before marking
category complete").

### Step 6 — Pull collection events

Fetch `/api/collection_events?matter_id=…`.  Each event has:
- `status`: `"collected"`, `"partial"`, `"unavailable"`, `"destroyed before hold"`,
  `"destroyed after hold"`, `"pending"`, `"not noticed"`, `"archive validation"`,
  `"source gap"`, `"collected with gap"`, `"not collected"`
- `hold_relation`: `"post-hold"`, `"pre-hold"`, `"pre-hold destruction identified"`,
  `"hold not applicable"`
- `collected_count` vs `missing_count`

### Step 7 — Custodian records

Fetch `/api/custodians?matter_id=…`.  `known_gaps` arrays are pre-flagged
issues.  `relevant_sources` tells you what the custodian should have provided.

### Step 8 — Retention rules and destruction events

For retention/hold tasks (train_002 pattern), also fetch:
- `/api/retention_rules?matter_id=…` — `archive_override` tells you whether an
  archive copy may exist (`"archive copy"`, `"legal hold suspends destruction"`,
  `"email archive overrides active-server purge"`, `"vendor copy required"`,
  `"none"`, `"obsolete policy superseded"`)
- `/api/destruction_events?matter_id=…` — `pre_or_post_hold` is the key field;
  `recoverability` says whether anything can be salvaged

## Privilege Analysis Rules

### Privilege log gap

A privilege log gap exists when `withheld_privileged_count > privilege_logged_count`.
The unlogged count must be reported and requires a `privilege_log_supplement` action.

### Over-designation

Signals of over-designation:
- Category has `produced_count: 0` and all responsive records withheld as privileged
- `overdesignation_flag: true` on privilege log entries
- Counsel-communications category where no business-only material was separated
- Remediation: `privilege_review` to separate business-only from privileged

### Waiver risk

Privilege waiver occurs when:
- `privilege_status` is `"counsel communications"` or `"work product"` AND
- `production_status` is `"produced"` AND
- The communication involved an outside party

Requires `waiver_assessment` and potentially `clawback_check`.

### Miscoding

Documents coded `"non-responsive"` in `review_coding` but whose content matches
a subpoena category's scope are miscoded.  Check `documents` endpoint for
documents with `review_coding: "non-responsive"` and `tags` matching category
topic tags.

Documents coded `"privileged"` in `privilege_coding` but actually business-only
are privilege-miscoded.  Requires `coding_correction` and possible
`clawback_review` if already produced.

## Timing Classification

Map every gap to one of these timing classes:

| Class | Definition | Disclosure? |
|---|---|---|
| `pre_hold_policy` | Destroyed per retention policy before hold date | Usually no — policy gap, note only |
| `post_hold_spoliation` | Destroyed after hold was issued | **Yes** — regulator notice required |
| `recoverable_archive` | Appears lost but archive copy may exist | No — recover first |
| `uncollected_source` | Source in scope but never collected | Depends on hold notice coverage |
| `coding_error` | Miscoded in review platform | No — correct and reprocess |
| `privilege_protocol_defect` | Privilege log incomplete or wrong | Possible — assess severity |
| `retained_missing` | Should exist under retention policy but not found | No — search/validate first |
| `not_applicable` | No timing issue | No |

**The hold_date is the bright line.**  Compare every destruction event date and
collection event date against `hold_date` from the matter record.  Pre-hold
policy destruction is less severe than post-hold loss, but both must be
reported.

## Remediation Actions — Ranking Pattern

Actions follow a severity-driven ranking.  Use this priority order when building
`next_actions` / `remediation_plan` / `ranked_escalations`:

1. **regulator_notice** — post-hold spoliation or unlogged privileged production; must notify
2. **supplemental_collection** — collect sources that were missed
3. **forensic_recovery** — attempt recovery of deleted/wiped data
4. **clawback_check / clawback_review** — produced privileged material must be clawed back
5. **waiver_assessment** — determine if privilege was waived
6. **privilege_review** — re-review privilege designations (over-designation)
7. **privilege_log_supplement** — fix incomplete privilege logs
8. **reprocess_qc** — rerun QC after coding corrections
9. **supplemental_production** — produce corrected/additional documents
10. **coding_correction** — fix miscoded documents
11. **hold_refresh** — reissue/expand legal hold notices
12. **custodian_declaration** — obtain custodian attestation
13. **archive_validation** — verify archive before treating as lost
14. **vendor_retrieval / vendor_archive_retrieval** — retrieve from vendor
15. **no_action / no_action_policy_gap** — pre-hold policy gap, note only

When a single issue needs multiple actions, list the most impactful as
`primary_action` and the rest as `secondary_actions` (sorted alphabetically by
action enum).

## Disclosure Decision

`disclosure_required` is `true` when ANY of these are true:
- Post-hold spoliation (destruction after hold_date)
- Unlogged privileged material was produced to opposing party
- Hold notice omitted required custodians or sources
- Regulator_notice_flag on the matter is true AND a material gap exists
- Privilege waiver has occurred

Per-issue `notice_required` / `notice_recommended` follows the same logic at
the issue level.

## Owner Queues

Map actions to the correct owner:

| Action | Owner |
|---|---|
| regulator_notice, waiver_assessment, privilege_review, privilege_log_supplement | `legal` or `privilege_team` |
| supplemental_collection, forensic_recovery | `client_it` or `e_discovery` |
| reprocess_qc, coding_correction | `review_vendor` |
| hold_refresh, custodian_declaration | `legal` |
| archive_validation, vendor_retrieval | `litigation_support` or `records` |
| clawback_check | `privilege_team` |

## Output Conventions

### Stable IDs

Generate stable, predictable identifiers for findings and actions:
- Issue IDs: `ISS-01`, `ISS-02`, …
- Action IDs: `ACT-01`, `ACT-02`, …
- Finding IDs: `F-01`, `F-02`, … (or `MF-01` for miscoding findings)
- Defect IDs: `DEF-01`, `DEF-02`, …
- Source IDs: `SRC-01`, `SRC-02`, …

### Sorting (universal across all tasks)

- `category_ids`: ascending string sort
- `document_ids`: ascending string sort
- `custodian_ids`: ascending string sort
- `issue_ids`: ascending string sort (unless `rank` defines order in action plans)
- `source_event_ids`: ascending by prefix group then numeric suffix
- `affected_sources` / source names: alphabetical
- `secondary_actions`: ascending enum sort
- Ranked items: consecutive integers starting at 1, sorted by rank
- `issue_types` within a category: alphabetical

### Counts

- All counts are integers; use `0` when not applicable (never null or absent)
- `unlogged_privilege_count` = `withheld_privileged_count − privilege_logged_count`
- `unrecovered_count` = `affected_count − recovered_count` (from QC events)

### Enum casing

Use exact casing from the answer template.  No variations.

### Top-level key order

Follow the `required_top_level_keys` / `top_level_order` from the answer
template exactly.

## Task-Local Payload Files

Some tasks include files under `input/payloads/`:

- **partner_request.json**: Contains additional instructions, the matter ID, and
  hints about which API endpoints to use.  The `instructions` array may narrow
  the scope.
- **hold_exception_memo.json** / factual memos: Contain facts NOT available in
  the API.  These often describe hold notice defects, off-site vendor gaps, or
  archive system names.  Cross-reference memo facts against API records — the
  memo may name a system differently than the API (e.g. "Ironvault" = "Iron
  archive" = "Seven-year archive" = "executive email archive").  Use memo facts
  to identify issues the API data hints at but does not explicitly state.

## Common Pitfalls

1. **Treating noise as material.**  Always check the `batch` field on production
   logs.  `"noise-N"` batches for noise categories are not production defects;
   they are synthetic distraction data.

2. **Missing the hold_date boundary.**  Every destruction or collection event
   must be compared against `hold_date`.  A destruction in January 2025 that is
   "pre-hold" for a November 2024 hold is a data error — check the dates.

3. **Double-counting.**  When the same category appears in multiple production
   logs, use the `batch: "current"` log as authoritative.  Noise-batch logs for
   the same core category are supplementary — they flag staleness or
   reconciliation issues but do not create separate production counts.

4. **Overlooking QC overrides.**  QC events can override production tracker
   completeness.  When a QC `review_note` says "Confirm whether collection/QC
   notes override production tracker", the QC data takes precedence.

5. **Ignoring archive overrides.**  A retention rule with `archive_override` set
   to `"archive copy"`, `"email archive overrides active-server purge"`, or
   `"vendor copy required"` means the data may still exist even if the primary
   source was destroyed or purged.  Classify as `recoverable_archive`, not
   `post_hold_spoliation`.

6. **Forgetting the unlogged-privilege calculation.**  Always compute and report
   the unlogged gap.  A category with 2,910 withheld but only 2,102 logged has
   an 808-document privilege log gap — this is a material defect.

7. **Producing narrative instead of JSON.**  Every task demands JSON-only
   output.  No markdown, no explanatory text, no memo outside the JSON.

8. **Wrong enum values.**  Only use values explicitly listed in the answer
   template's enum sections.  Do not invent new statuses, action types, or
   severity levels.

9. **String-sorting gotcha.**  `"CRN-10"` sorts before `"CRN-2"` in
   lexicographic order.  Apply the sorting rule as stated ("ascending") without
   reinterpreting — the template says "ascending", use string sort.

10. **Omitting zero counts.**  Fields like `produced_count`, `withheld_count`,
    and `privilege_logged_count` must be present even when zero.  Use `0`, not
    `null` or absent.
