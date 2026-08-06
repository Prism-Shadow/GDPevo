# Hub Data Model

From `GET /api/schema`. All tables are per-matter; always filter `WHERE matter_id = ?`.

## matters
matter_id, name, agency, investigation_type, issued_date, **hold_date**, lead_partner, description, status.
`hold_date` is the pivot for pre-hold vs post-hold loss judgments.

## subpoena_categories
matter_id, **category_code**, title, date_start, date_end, request_text, topic_tags.
Category codes are the join key for every `affected_categories`/`category_impacts` list. Casing/spacing must be copied verbatim. Families vary by matter (single letters A–I, or `SEC-*`).

## production_stats
matter_id, batch_id, batch_date, category_code, produced_count, withheld_count, responsive_count, nonresponsive_count, status, **zero_claim_reason**, notes.
`produced_count = 0` + a `zero_claim_reason` must be tested against actual responsive docs (review_documents) — contradicted zero claims are a readiness blocker.

## custodian_sources
**source_id**, matter_id, custodian_name, role, source_type, source_label, status, event_date, **post_hold** (INTEGER 0/1), category_impacts, issue_tags, notes.
`post_hold = 1` marks post-hold loss (preservation risk). `source_type` includes personal_phone, personal_messaging, personal_email, *_archive, email, teams_archive, laptop, shared_drive, offsite_records. `status` includes lost, not_collected, partial, collected, pending.

## review_documents
doc_id, matter_id, title, doc_date, custodian_name, source_system, category_code, **responsiveness**, **privilege_status**, **produced_status**, issue_tags, summary.
Drives responsiveness-miscoding and privilege findings.

## privilege_entries
**entry_id**, matter_id, category_code, custodian_name, doc_count, **withheld_count**, **logged_count**, issue_type, **third_party** (INTEGER 0/1), notes.
`unlogged = withheld − logged`. `third_party = 1` ⇒ waiver-assessment tilt.

## qc_findings
**finding_id**, matter_id, batch_id, issue_type, doc_count, affected_category, source_ref, severity, notes.
issue_type/severity map to template enums (e.g. responsive_miscoding, privilege_log_gap).

## retention_events
**event_id**, matter_id, record_type, event_date, hold_date, policy_section, retention_period_months, volume_count, volume_unit, status, affected_categories, source_ref, notes.
`status` distinguishes policy_destroyed_pre_hold, post_hold_loss, auto_purged, active_system_loss, should_exist_missing, available_archive, preserved_available, collection_pending.

## remediation_actions
**action_id**, matter_id, action_type, priority, severity, owner, target_ref, due_days, description.
Pre-seeded candidate actions; mirror/extend in the output `action_plan`/`priority_actions`, keeping `action_id`/`target_ref` stable.
