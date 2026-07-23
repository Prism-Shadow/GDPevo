# Hub Schema Reference

Tables and columns exposed by the Review Hub (`GET /api/schema`). Use this to map hub fields onto template fields and to write SQL aggregates. Field names are stable across matters; values are matter-specific.

## matters
`matter_id`, `name`, `agency`, `investigation_type`, `issued_date`, `hold_date`, `lead_partner`, `description`, `status`

- `hold_date` is the litigation-hold date — the pivot for pre-hold vs post-hold classification.
- `investigation_type` distinguishes `grand_jury_subpoena` vs `sec_subpoena`; not always needed for the answer but useful for sanity-checking agency.

## subpoena_categories
`matter_id`, `category_code`, `title`, `date_start`, `date_end`, `request_text`, `topic_tags`

- `category_code` is the stable request-category key used throughout every `category_impacts` / `affected_categories` list. Capture the full set for the matter first.

## production_stats
`matter_id`, `batch_id`, `batch_date`, `category_code`, `produced_count`, `withheld_count`, `responsive_count`, `nonresponsive_count`, `status`, `zero_claim_reason`, `notes`

- `status` values (e.g. `produced`, `partial`, `zero_production`) drive production-impact and readiness classification.
- `zero_claim_reason` explains a `zero_production` batch — relevant to zero-claim-contradiction readiness findings.

## custodian_sources
`source_id`, `matter_id`, `custodian_name`, `role`, `source_type`, `source_label`, `status`, `event_date`, `post_hold`, `category_impacts`, `issue_tags`, `notes`

- `post_hold` (integer flag) + `event_date` vs the matter `hold_date` decides pre-hold policy loss vs post-hold preservation loss.
- `status` carries the loss/availability signal: lost/destroyed, not_collected, partial, collected/preserved, available archive, pending.
- `category_impacts` is typically a delimited list of category codes — split and normalize to the category universe.
- `source_type` values map to the template's `source_type` enum (personal_phone, personal_messaging, email, teams_archive, offsite_records, cloud_mail_archive, lab_results_archive, shared_drive, laptop, personal_email, …).

## review_documents
`doc_id`, `matter_id`, `title`, `doc_date`, `custodian_name`, `source_system`, `category_code`, `responsiveness`, `privilege_status`, `produced_status`, `issue_tags`, `summary`

- `responsiveness` ∈ {responsive, nonresponsive, …}; `privilege_status` ∈ {privileged, nonprivileged, …}; `produced_status` ∈ {produced, withheld, not_produced, …}.
- `issue_tags` carries miscoding / waiver / gap signals. Use for `miscoded_responsive_doc_count` and for anchoring document-level findings.

## privilege_entries
`entry_id`, `matter_id`, `category_code`, `custodian_name`, `doc_count`, `withheld_count`, `logged_count`, `issue_type`, `third_party`, `notes`

- Privilege-log math: `unlogged = withheld_count − logged_count`. A positive unlogged value on a withheld entry is a `privilege_log_gap`.
- `issue_type` distinguishes incomplete-log, waiver, over-designation, miscoding.
- `third_party` (integer flag) marks third-party communications → `third_party_waiver` risk.

## qc_findings
`finding_id`, `matter_id`, `batch_id`, `issue_type`, `doc_count`, `affected_category`, `source_ref`, `severity`, `notes`

- Each `finding_id` is a stable anchor for a `finding_id` / `risk_id` / `issue_id` in the answer.
- `severity` maps directly to the template severity/risk enum when present.
- `source_ref` points back to the supporting source/record — collect into `source_refs`.

## retention_events
`event_id`, `matter_id`, `record_type`, `event_date`, `hold_date`, `policy_section`, `retention_period_months`, `volume_count`, `volume_unit`, `status`, `affected_categories`, `source_ref`, `notes`

- `status` carries the retention status (policy_destroyed_pre_hold, post_hold_loss, auto_purged, active_system_loss, should_exist_missing, available_archive, preserved_available, collection_pending, …).
- `event_date` vs `hold_date` (and the matter-level hold_date) is the pre/post-hold test.
- `volume_count` / `volume_unit` (boxes, days, months, records) feed box-count metrics.
- Communication-channel gaps (Teams/Slack/email auto-purge, deleted channels) appear here or in custodian_sources with a system name — model them as `communication_gaps` in the retention family.

## remediation_actions
`action_id`, `matter_id`, `action_type`, `priority`, `severity`, `owner`, `target_ref`, `due_days`, `description`

- Pre-existing proposed actions. Use them to seed the action plan: confirm the `action_type`/`owner`/`priority` against the template enums, attach `target_ref` as a `target_refs` entry, and re-rank into a single ordered list.
- `due_days` feeds the dashboard `due_days` field where the template requires it.

## Mapping hub → template (cheat sheet)

| Hub field | Common template target |
|---|---|
| `finding_id` / `event_id` / `entry_id` / `source_id` / `doc_id` / `action_id` / `batch_id` | `finding_id`/`risk_id`/`issue_id`/`correction_id`/`event_id`/`source_id`/`action_id` (anchor) |
| any of the above (supporting) | `source_refs`/`record_refs`/`blocking_refs`/`target_refs`/`issue_refs` |
| `category_code` / `affected_category` / `affected_categories` / `category_impacts` | `category_impacts`/`affected_categories`/`affected_categories` (sorted ascending) |
| `issue_type` / `issue_tags` / `status` | `issue_type` enum (via classification_rules) |
| `severity` | `severity` / `risk_level` enum |
| `status` (sources/events) | `source_status` / `status` enum |
| `withheld_count`, `logged_count` | `withheld_count`, `logged_count`; `unlogged_count = withheld − logged` |
| `doc_count` | `document_count` |
| `volume_count`, `volume_unit` | `volume_count`, `volume_unit` |
| `priority`, `owner`, `action_type` (remediation_actions) | `priority`, `owner`, `action_type` enums (after re-mapping) |
| `due_days` | `due_days` |
