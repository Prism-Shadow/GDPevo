# Metric Definitions

Metrics are derived from the **material** records only (see `noise_and_material.md`). All counts are whole integers. Each task's template names its own metric keys; these are the recurring families and how to compute them.

## Privilege metrics
- `unlogged_privilege_docs` / `unlogged_privilege_doc_count` = Σ(`withheld_count − logged_count`) over the selected material privilege entries (incomplete-log blockers). Entries where `withheld == logged` contribute 0.
- `withheld_privilege_docs` / `withheld_privileged_doc_count` = Σ `withheld_count` over the selected material privilege entries (or the incomplete-log blockers only, if the template's field description says "from selected incomplete-log blockers only" — read the description).
- `logged_privilege_docs` / `logged_privilege_doc_count` = Σ `logged_count` over the same set.
- `waived_privilege_doc_count` / `third_party_waiver_doc_count` = doc count of material `third_party_waiver` entries (third_party=1, named recipient).
- `miscoded_privileged_doc_count` = docs whose privilege coding is wrong (material `miscoded_privilege` QC finding doc_count, plus any escalated over-designation).
- `miscoded_responsive_doc_count` = docs miscoded for responsiveness (material `miscoded_nonresponsive` QC finding doc_count). 0 if no such finding.

## Source / collection metrics
- `lost_personal_device_count` = material personal-device sources with `status=lost` (post-hold erasure/wipe).
- `uncollected_personal_source_count` = material personal sources not collected (lost or not_collected).
- `uncollected_board_source_count` = material board/sharepoint sources scoped but not collected.
- `personal_email_gap_source_count` / `personal_phone_partial_source_count` = counts of those specific personal-source gap types (0 if none).

## Retention / preservation metrics
- `retention_event_count` = count of all material retention events (including communication-system losses that also appear in a communication_gaps list — the superset).
- `pre_hold_policy_destroyed_event_count` = material `policy_destroyed_pre_hold` events.
- `post_hold_loss_event_count` = material `post_hold_loss` events.
- `should_exist_missing_event_count` = material `should_exist_missing` events.
- `communication_gap_event_count` = material system-loss / auto-purge communication gaps.
- `available_archive_count` = material available archive sources.
- `destroyed_box_count` = Σ `volume_count` over material events whose `volume_unit=boxes` and represent destructions. `pre_hold_destroyed_box_count` / `post_hold_destroyed_box_count` split by pre/post hold.
- `destroyed_lab_archive_box_count` (dashboard) = boxes for the destroyed records source named in the task prompt; 0 when that source is not measured in boxes.
- `missing_required_record_count` = material should-exist-missing / zero-claim-contradiction record count (read the task for which "missing required record" applies).

## Category metrics
- `categories_with_open_gaps` / `affected_category_count` / `unique_affected_category_count` = count of distinct categories impacted by any material record.
- `categories_with_open_risk` / `categories_with_any_gap_or_loss` = the sorted list of those category codes.
- `nonready_category_count` = categories with a non-ready readiness status.

## Rollup / boolean
- `top_risk_count` = number of material top risks.
- `rolling_production_ready` / `production_ready` = boolean; `false` when any material open gap exists (the matter is not production-ready).

## Computing counts safely
- Always sum from the material subset, never the full table (decoy rows inflate counts).
- For a metric whose definition is ambiguous in the template, prefer the interpretation that uses only escalated/material records and matches the metric name literally.
- Re-derive counts from the pulled hub rows with a script rather than by eye — the tables are large and eye-counting misses rows.
