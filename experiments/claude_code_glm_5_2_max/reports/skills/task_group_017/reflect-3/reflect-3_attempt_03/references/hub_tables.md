# Hub Table Reference

The Investigation Review Hub exposes these tables (constant schema across all matters). Pull each filtered by `matter_id`. Useful columns listed; see `GET /api/schema` for the live schema.

## matters
Matter metadata. `matter_id`, `name`, `agency`, `investigation_type`, `issued_date`, `hold_date`, `lead_partner`, `description`, `status`. The `hold_date` is the legal-hold date used to determine pre-hold vs post-hold events.

## subpoena_categories
One row per request category. `matter_id`, `category_code`, `title`, `date_start`, `date_end`, `request_text`, `topic_tags`. `category_code` is the key referenced by every other table's `category_impacts`/`affected_categories`. Category-code families differ per matter (e.g. `R01..R15`, `A..I`, `SEC-1..SEC-5`, `SEC-A..SEC-E`).

## production_stats
Per-batch production counts. `matter_id`, `batch_id`, `batch_date`, `category_code`, `produced_count`, `withheld_count`, `responsive_count`, `nonresponsive_count`, `status` (produced / rolling_review / supplement_pending / closed), `zero_claim_reason`, `notes`. `status` of `supplement_pending`/`rolling_review` is routine progress, not necessarily a defect — assess defects by escalated records, not batch status.

## custodian_sources
Custodian data sources. `source_id`, `matter_id`, `custodian_name`, `role`, `source_type`, `source_label`, `status` (lost / not_collected / partial_collection / collected / available / in_review), `event_date`, `post_hold` (1 = event after the hold → potential preservation failure), `category_impacts` (comma-separated category codes), `issue_tags`, `notes`. Personal-device sources (`personal_phone`, `personal_email`, `personal_messaging`, `laptop`, `mobile_backup`) with `status` lost/not_collected and `post_hold=1` are the high-severity personal-source gaps.

## review_documents
Document-level review records. `doc_id`, `matter_id`, `title`, `doc_date`, `custodian_name`, `source_system`, `category_code`, `responsiveness` (responsive / nonresponsive / needs_review), `privilege_status` (privileged / nonprivileged / unknown), `produced_status` (produced / not_produced / withheld), `issue_tags`, `summary`. This table is large and mostly noise; only documents referenced by a material QC finding's `source_ref` are escalated.

## privilege_entries
Privilege-log entries. `entry_id`, `matter_id`, `category_code`, `custodian_name`, `doc_count`, `withheld_count`, `logged_count`, `issue_type` (incomplete_log / over_designated / family_mismatch / third_party_waiver / clean), `third_party` (1 = shared with a third party → waiver), `notes`. Only `incomplete_log` (unlogged > 0) and `third_party_waiver` entries that are escalated are material; `over_designated`/`family_mismatch`/`clean` are noise unless their note escalates. `unlogged = withheld_count − logged_count`.

## qc_findings
Quality-control findings. `finding_id`, `matter_id`, `batch_id`, `issue_type` (miscoded_nonresponsive / miscoded_privilege / family_break / near_duplicate / duplicate_overlay / metadata_gap / date_normalization / zero_claim_contradiction / ...), `doc_count`, `affected_category`, `source_ref` (a doc_id or privilege entry id), `severity`, `notes`. Most are noise; the escalated ones have a concrete business note (e.g. "One complaint email miscoded nonresponsive", "Privileged investigation advice docs coded non-privileged", "Category F zero-production claim contradicted by two responsive bid emails").

## retention_events
Retention / preservation events. `event_id`, `matter_id`, `record_type` (e.g. lab_test_data, ehs_correspondence, offsite_bid_files, teams_messages, voicemail, audit_report, box_storage, email_archive, shared_drive, voice_mail, chat_export), `event_date`, `hold_date`, `policy_section`, `retention_period_months`, `volume_count`, `volume_unit` (boxes / days / months / reports / files / exports / mailboxes / system_window), `status` (policy_destroyed_pre_hold / post_hold_loss / system_loss / auto_purged / active_system_loss / should_exist_missing / retained / available / post_hold_partial_recovery), `affected_categories`, `source_ref`, `notes`. Compare `event_date` to `hold_date`: events after the hold are post-hold losses (high severity); pre-hold policy destructions are compliant.

## remediation_actions
Remediation action plan (use this to confirm the material set). `action_id`, `matter_id`, `action_type` (supplemental_collection / privilege_rework / qc_remediation / retention_exception_review / custodian_followup / load_file_cleanup / sampling_review / ...), `priority` (P0/P1/P2/P3), `severity`, `owner`, `target_ref` (a hub record ID — the record this action remediates), `due_days`, `description`. **Noise actions** have `description` = "Routine action included as realistic operational noise" and `target_ref` = a bare category code; exclude them. **Material actions** target specific record IDs (`SRC-...`, `PRIV-...`, `QC-...`, `RET-...`) — those `target_ref`s are exactly the material records for the matter.
