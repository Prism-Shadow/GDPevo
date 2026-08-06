---
name: investigation-review-hub-gap-analysis
description: Produce a structured JSON gap/remediation analysis for a legal investigation matter by querying an Investigation Review Hub API. Use when a task asks for a production gap analysis, retention/preservation review, cross-system remediation dashboard, or production-readiness review returned as a single JSON object conforming to a provided answer template.
---

# Investigation Review Hub Gap Analysis

This skill solves tasks that ask for a **structured JSON** gap / remediation analysis of a single
legal-investigation matter (grand jury or SEC subpoena). Each task gives you:

- a **prompt** describing the matter and deliverable,
- `input/payloads/answer_template.json` — the exact output schema (required keys, field types,
  **enum choices**, **ordering rules**, numeric precision),
- a context payload (`request_context.json` / `review_scope.json` / `matter_context.json`) with the
  matter id, client, and category labels,
- `environment_access.md` — the hub connection details and allowed endpoints for **this task**.

The deliverable is **one JSON object** that conforms to the template. No prose outside the JSON.

## Source of record

Use **only** the Investigation Review Hub described in the task's `environment_access.md` for
business evidence. Read the base URL, API key header, and allowed endpoint list from that file at
solve time — do not hardcode them and do not inspect local environment source files, database files,
seeds, manifests, or any answer/evaluation files. If a read-only SQL query endpoint is offered,
prefer it for precise `matter_id`-filtered queries (it takes a `sql` string, optionally with
`params`).

The hub's logical model (filter every query by the task's `matter_id` — the hub holds many matters
and cross-matter contamination is the primary trap):

| Concept | Holds |
|---|---|
| matters | matter metadata, agency, hold_date |
| subpoena-categories | request category codes + titles for the matter |
| productions / production_stats | per-batch produced/withheld/responsive counts, status, zero-claim reasons |
| custodian-sources | custodian data sources, status (lost/not_collected/partial/collected/available), source_type, category_impacts, issue_tags |
| privilege-log / privilege_entries | withheld/logged counts, issue_type, third_party flag |
| qc-findings | issue_type, doc_count, severity, affected_category, source_ref |
| retention-events | status, record_type, dates, policy_section, retention_period_months, volume |
| remediation-actions | the action plan: action_type, priority, severity, owner, target_ref, due_days |
| review-documents | individual docs, responsiveness, privilege_status, produced_status, issue_tags |

## Method

### 1. Load the contract first
Read `answer_template.json` fully before gathering data. It defines: required top-level keys,
per-record required keys, **enum choices** (issue_type, severity, status, source_status,
production_impact, action_type, owner, priority, etc.), **ordering rules**, and numeric precision.
Every value you emit must be drawn from these enums or you lose the whole record.

### 2. Gather evidence per matter
For the task's `matter_id`, pull every endpoint (filtered by `matter_id`). Pay special attention to:
- **remediation-actions** — this is the key to materiality (see step 3).
- **review-documents** flagged with `miscoded_nonresponsive`, `zero_claim_contradiction`,
  `safety_escalation`, `personal_device`, `post_subpoena_erasure`, `deleted_channel`,
  `archive_available` — these anchor findings.

### 3. Identify MATERIAL records (the core heuristic)
A record is **material** and belongs in the answer **iff it is targeted by a dedicated remediation
action**. Remediation actions come in two flavors:

- **Real actions** (`ACT-…-NNN`, non-noise): `description` says "Review and remediate <RECORD-ID>
  before next production certification." Their `target_ref` is the material record.
- **Noise actions** (`ACT-…-NOISE-NNN`): `description` is "Routine action included as realistic
  operational noise" and `target_ref` is a bare category code. **Exclude these and their targets.**

Non-material records (exclude from findings/risks/issues and from metrics) carry tell-tale notes:

- "Review team marked this item for follow-up but not immediate remediation"
- "Review manager requested re-sampling before escalation"
- "Finding is similar to escalated records in another matter"
- "Privilege sample has ordinary review variance"
- "Entry included to create similar labels across matters" / "Entry creates a similar label…"
- "…has no unresolved production impact" / "No production-impacting issue has been escalated yet"
- "Potential issue was remediated by archive collection" (already remediated — not a current gap)

Material records are exactly the `target_ref`s of the non-noise remediation actions. One material
record → one finding / top_risk / issue / privilege_correction. Use the stable hub record ID
(`source_id`, `event_id`, `finding_id`, `entry_id`, `doc_id`) as the record's ID and list
supporting IDs in `source_refs` / `record_refs` / `blocking_refs` (sorted ascending).

### 4. Compute metrics — material-only, strict block
The `metrics` object is scored as a strict all-or-nothing block: **one wrong value zeroes the whole
block.** Count **only material/escalated records**, not every record with that `issue_type`:

- `unlogged_privilege_docs` = withheld − logged for the **material** incomplete-log privilege entry
  only (non-material incomplete-log entries are NOT counted).
- `miscoded_responsive_doc_count` = count of docs tagged `miscoded_nonresponsive` that anchor a
  material finding.
- `third_party_waiver_doc_count` = docs from the **material** third-party-waiver privilege entry.
- `miscoded_privileged_doc_count` = `doc_count` of the material `miscoded_privilege` QC finding.
- `lost_personal_device_count` / `uncollected_board_source_count` / `uncollected_personal_source_count`
  = count of material sources of that type/status.
- `*_event_count` = count of material retention events of that status.
- `*_box_count` = box volumes of material destroyed/post-hold events (0 when the destroyed source is
  not measured in boxes).
- `categories_with_open_gaps` / `categories_with_open_risk` / `categories_with_any_gap_or_loss` =
  sorted unique category codes touched by the **material** records.
- `rolling_production_ready` / `production_ready` = `false` when any material open gap exists.
- All counts are whole integers; use 0 when not applicable.

### 5. Map hub values → template enums
The hub's `action_type` and `owner` vocabularies do **not** match the template enums — you must map.
Common mappings (verify against each task's enum list):

| Hub remediation action_type | → template action_type (typical) |
|---|---|
| supplemental_collection (lost/missing source) | forensic_recovery / collect_source / collect_personal_device |
| supplemental_collection (archive) | search_archive / collect_archive |
| privilege_rework (incomplete log) | supplement_privilege_log |
| privilege_rework (over-designation) | privilege_recode_and_log / recode_and_produce |
| privilege_rework (third-party waiver) | waiver_assessment_and_disclosure |
| qc_remediation (miscoded privilege) | privilege_recode_and_log / qc_remediation |
| qc_remediation (miscoded responsive) | recode_and_produce |
| retention_exception_review (post-hold loss) | disclose_preservation_issue |
| retention_exception_review (missing record) | locate_missing_record |

| Hub owner | → template owner (typical) |
|---|---|
| Forensics | forensics / ediscovery_vendor / investigation_team |
| Review Operations | review_qc / review_vendor / legal_operations |
| Privilege Team / Legal Hold Team | privilege_team / privilege_counsel |
| Vendor Team | ediscovery_vendor |
| Matter Associate | (usually noise — exclude) |

`risk_level` / `severity`: align to the remediation action's `severity` (P1→high, P2→medium) when
available; otherwise judge by impact (lost post-hold source ≈ critical/high).

`production_impact`: lost source → `source_lost`; not collected → `source_missing`; incomplete
privilege log → `withheld_unlogged`; privileged docs coded non-privileged → `privilege_exposure`;
over-designation → `recode_needed`; miscoded responsive / zero-claim → `underproduced` or
`not_produced`; archive available → `source_available`.

`issue_type`: erased/wiped post-subpoena device → `preservation_failure`/`personal_source_gap`;
un-collected messaging → `personal_source_gap`/`collection_gap`; incomplete privilege log →
`privilege_log_gap`; third-party forwarding → `third_party_waiver`/`privilege_waiver`; privileged
coded non-privileged → `privilege_miscoding`; missing required record → `missing_required_record`;
deleted archive with backup → `archive_available`; bid-email zero-claim → `responsiveness_miscode`
(or the template's `zero_claim_contradiction` equivalent where offered).

### 6. Ordering and ranks
Apply the template's `ordering_rules` exactly: sort by stable ID ascending, by `priority_rank` /
`rank` ascending (1 = highest), and category codes ascending within every list. Order actions P1
before P2, P2 before P3; within the same priority, by `action_id` / `target_ref` ascending.
`priority_rank` / `rank` is a contiguous integer sequence starting at 1.

### 7. Validate before returning
- Every required top-level key present; every record has every `item_required_keys` field.
- Every enum value is in the template's list (a single invalid enum forfeits the record).
- Counts are integers; `null` only where the template allows "string or null".
- `withheld_count − logged_count = unlogged_count`.
- `retention` `cutoff_date` = `event_date` + `retention_period_months`.
- Return **exactly one JSON object**, no surrounding prose.

## Hard-won cautions

- **Filter by `matter_id` on every query.** Issue tags and labels repeat across matters; the note
  "Requires matter-level filtering because similar issue labels appear across matters" is a literal
  warning.
- **Material = has a non-noise remediation action.** This single rule determines record inclusion
  and most metric counts. When unsure whether a non-actioned record is material, it almost certainly
  is not.
- **The metrics block is all-or-nothing.** Re-derive every count from the material set; do not sum
  across non-material entries.
- **Record matching is field-by-field strict.** A record scores only if *every* field (including
  every enum) matches the expected answer — so map enums deliberately and keep `source_refs`/category
  lists exactly sorted.
- **jq precedence:** when you assign a list and sort in one expression, parenthesize the right side:
  `.x = (([new] + .x) | sort_by(.id))`. A bare `| sort_by(…)` after an assignment binds to the whole
  object and silently produces wrong output.
- Do **not** call any judge/feedback endpoint during test solving — it is train-only and rejects
  test task ids.

See `reference/material-and-enum-mapping.md` for the full note-pattern catalog and per-template
field checklists.
