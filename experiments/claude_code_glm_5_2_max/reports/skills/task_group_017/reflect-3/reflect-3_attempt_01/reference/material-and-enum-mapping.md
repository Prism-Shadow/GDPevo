# Material-record identification & enum-mapping reference

Companion to `SKILL.md`. Use these catalogs when solving Investigation Review Hub gap-analysis tasks.

## 1. Noise vs. material: note-pattern catalog

Records carrying these `notes` are **non-material** — exclude from findings/risks/issues and from
metric counts:

| Note fragment | Meaning |
|---|---|
| "Routine action included as realistic operational noise" | noise remediation action — exclude action and its (category-code) target |
| "Review team marked this item for follow-up but not immediate remediation" | not escalated |
| "Review manager requested re-sampling before escalation" | not escalated |
| "Finding is similar to escalated records in another matter" | cross-matter label, not this matter's escalation |
| "Privilege sample has ordinary review variance" | ordinary variance, not a gap |
| "Entry included to create similar labels across matters" | cross-matter label noise |
| "Entry creates a similar label but has no unresolved production impact" | no production impact |
| "No production-impacting issue has been escalated yet" | not escalated |
| "Potential issue was remediated by archive collection" | already remediated, not a current gap |
| "Quality-control sample is noisy but not dispositive without source comparison" | not dispositive |
| "Corrected in later overlay but retained for audit trail" | already corrected |

Records carrying these `notes` are **material** (real losses/gaps that anchor findings):

| Note fragment | Meaning |
|---|---|
| "Review and remediate <RECORD-ID> before next production certification" | the action targets a real material record |
| "<N> boxes destroyed after the hold date" | post-hold loss |
| "Personal iPhone erased on <date> after subpoena issuance" | preservation failure |
| "Board SharePoint site was scoped but not collected…" | collection gap |
| "Privilege log covers X of Y withheld … documents" | incomplete privilege log |
| "One complaint email miscoded nonresponsive…" / "…miscoded_nonresponsive…" | responsiveness miscode |
| "Category F zero-production claim contradicted by two responsive bid emails" | zero-claim contradiction |
| "Only X of Y withheld privileged documents are logged" | incomplete privilege log |
| "Business-only … emails were over-designated" | over-designation |
| "…emails were forwarded to a … consultant outside the privilege group" | third-party waiver |
| "Privileged … documents were initially coded non-privileged" | privilege miscoding |
| "Retention entry is relevant only after comparing hold date and policy period" | hint: compare event_date vs hold_date — a post-hold event is material even if `status` says `system_loss`/`policy_destroyed_pre_hold` |
| "Archive backup is available for deleted … channel" | available archive (remediation source) |
| "Personal SMS/Signal … remains outside collected review corpus" | personal-source collection gap |

## 2. Material set = non-noise remediation-action targets

The reliable rule: collect every `remediation_actions` row whose `action_id` does **not** contain
`NOISE` and whose `description` is not the "operational noise" boilerplate. The `target_ref` values
are the material record IDs. Map each to exactly one answer record (finding / top_risk / issue /
privilege_correction / retention_event / available_archive). A material source whose status is
`available` + `archive_available` tag goes in `retained_or_available_sources` (and may also appear
as an `archive_available` top_risk when it has its own remediation action).

## 3. Per-template field checklists

### `*_gap_analysis` (critical_findings, category_statuses, metrics, priority_actions)
- `critical_findings[]`: `finding_id` = stable hub ID; include `category_impacts`, `source_refs`
  (sorted), `document_count`, `withheld_count`, `logged_count`, `unlogged_count` (0 when N/A),
  `recommended_action` (enum).
- `category_statuses[]`: one per category with a material non-complete status; `source_refs` sorted.
- `metrics`: unlogged_privilege_docs, miscoded_responsive_doc_count, lost_personal_device_count,
  uncollected_board_source_count, categories_with_open_gaps, rolling_production_ready.

### retention / litigation-hold review (retention_events, communication_gaps, available_archives, metrics, recommended_actions)
- Partition retention losses: messaging-system losses with purge windows (Teams, voicemail) go in
  `communication_gaps` (fields `system`, `gap_type`, `purge_window_days`,
  `archive_exception_source_id`); other losses go in `retention_events`.
- `retention_status` maps hub `status`: `system_loss`→`active_system_loss`,
  `policy_destroyed_pre_hold`→`policy_destroyed_pre_hold`, `post_hold_loss`→`post_hold_loss`,
  `auto_purged`→`auto_purged`, `should_exist_missing`→`should_exist_missing`,
  `retained`/`available`→`available_archive`/`preserved_available`.
- `cutoff_date` = `event_date` + `retention_period_months`.
- Box metrics: `destroyed_box_count` = sum of box volumes of material destroyed events;
  `pre_hold_destroyed_box_count` / `post_hold_destroyed_box_count` split by timing.
- `available_archives[]`: `source_id` (the archive SOURCE, an `SRC-…` record with
  `archive_available` tag), `retention_years`, `limits_irretrievable_loss_for_categories`.

### `cross_system_remediation_dashboard` (top_risks, category_coverage, retained_or_available_sources, metrics, action_plan)
- `top_risks[]`: one per material record (including an `archive_available` risk when an available
  archive has its own remediation action). `priority_rank` 1..N; P1 before P2.
- `category_coverage[]`: one per affected category with `open_issue_count` and `issue_refs`.
- `retained_or_available_sources[]`: available archives with `active_system_issue`
  (e.g. `deleted_channel`, `purged_custodian_mail`), `limits_loss_for_categories`.
- `metrics.destroyed_lab_archive_box_count` = boxes for the task's named destroyed source, else 0.
- `action_plan[]`: `rank`, `action_type`, `owner`, `priority`, `target_refs`, `affected_categories`,
  `due_days` (from remediation_actions).

### `production_readiness` (readiness_statuses, issue_ledger, privilege_corrections, metrics, priority_actions)
- `readiness_statuses[]`: categories not ready; `readiness_status` enum (e.g.
  `not_ready_privilege_log_incomplete`, `not_ready_privilege_waiver`, `not_ready_multiple_blockers`).
- `issue_ledger[]`: material non-privilege + privilege-readiness issues; full 19-field record
  including `current_coding`, `produced_status`, `corrected_disposition`, `missing_component`.
- `privilege_corrections[]`: `correction_type` (supplement_log / waiver_assessment /
  privilege_recode / downgrade), `privilege_status` (incomplete_log / waived / over_designated).
- `metrics`: withheld/logged/unlogged_privilege_docs (from the material incomplete-log blocker),
  waived_privilege_doc_count, miscoded_responsive_doc_count, personal_email/phone gap source counts,
  nonready_category_count, production_ready.
- A `miscoded_nonresponsive` document anchors a `responsive_miscoding` issue even when no
  remediation action names it — check `review_documents` for `miscoded_nonresponsive` tags.

## 4. Quick metric self-check
- Every `*_count` is re-derived from the material set, not the full endpoint result.
- `withheld − logged == unlogged` for every privilege record and every metric triple.
- Category lists are the sorted union of `category_impacts`/`affected_categories` across material
  records only.
- Booleans (`rolling_production_ready`, `production_ready`) are `false` iff any material open gap.
- No extra top-level keys; no missing required keys; every enum value verbatim from the template.
