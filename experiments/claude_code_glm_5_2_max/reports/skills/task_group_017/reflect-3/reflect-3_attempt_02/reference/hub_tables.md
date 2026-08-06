# Hub Tables & Query Reference

The Investigation Review Hub exposes a read-only SQL endpoint. The base URL, access
header/key, and allowed endpoints are in the task's `environment_access.md`. Fetch the
hub's schema endpoint first to confirm columns, then query the SQL endpoint with the
task's access header. All queries filter `WHERE matter_id = '<the task matter_id>'`.

## Tables

### matters
`matter_id, name, agency, investigation_type, issued_date, hold_date, lead_partner, description, status`
- `hold_date` is the legal-hold date — use it as `cutoff_date` in retention answers and as
  the reference for pre-hold vs post-hold classification.

### subpoena_categories
`matter_id, category_code, title, date_start, date_end, request_text, topic_tags`
- `category_code` is the stable key used everywhere else (e.g. `R09`, `SEC-3`, `A`).
- Category code families differ by matter type (GJ matters use `R01..`/letters; SEC
  matters use `SEC-*`). Use them verbatim.

### production_stats
`matter_id, batch_id, batch_date, category_code, produced_count, withheld_count, responsive_count, nonresponsive_count, status, zero_claim_reason, notes`
- A non-empty `zero_claim_reason` with `produced_count=0` signals a zero-production claim
  that may be contradicted by responsive docs (see `qc_findings.issue_type =
  zero_claim_contradiction`).

### custodian_sources
`source_id, matter_id, custodian_name, role, source_type, source_label, status, event_date, post_hold, category_impacts, issue_tags, notes`
- `status`: lost, not_collected, partial_collection, available, collected, in_review.
- `post_hold` (0/1): whether the event/loss occurred after the hold date.
- `category_impacts`: comma-separated category codes.
- `issue_tags`: comma-separated tags (e.g. `post_subpoena_erasure,personal_device,collection_gap`,
  `archive_available,remediation_source`, `deleted_channel`).

### review_documents
`doc_id, matter_id, title, doc_date, custodian_name, source_system, category_code, responsiveness, privilege_status, produced_status, issue_tags, summary`
- Signal docs have descriptive IDs (`DOC-ALLOY-BID-EMAIL-1`); noise docs are sequential
  (`DOC-SENTINELGJ-0001`).
- `responsiveness`: responsive/nonresponsive. `produced_status`: produced/not_produced/withheld.

### privilege_entries
`entry_id, matter_id, category_code, custodian_name, doc_count, withheld_count, logged_count, issue_type, third_party, notes`
- `issue_type`: incomplete_log, over_designated, third_party_waiver, family_mismatch, clean.
- `third_party` (0/1): whether a third party received the privileged doc.
- Incomplete-log blocker = `withheld_count` > `logged_count`.

### qc_findings
`finding_id, matter_id, batch_id, issue_type, doc_count, affected_category, source_ref, severity, notes`
- `issue_type`: miscoded_nonresponsive, zero_claim_contradiction, miscoded_privilege,
  family_break, near_duplicate, metadata_gap, duplicate_overlay, date_normalization.
- `source_ref`: a linked record ID (often a `DOC-*` or `PRIV-*`).

### retention_events
`event_id, matter_id, record_type, event_date, hold_date, policy_section, retention_period_months, volume_count, volume_unit, status, affected_categories, source_ref, notes`
- `status`: policy_destroyed_pre_hold, post_hold_loss, system_loss, auto_purged,
  should_exist_missing, retained, available, post_hold_partial_recovery.
- Communication-system events (teams_messages, voicemail) belong in a `communication_gaps`
  section when the template has one; box/audit/storage events go in `retention_events`.

### remediation_actions
`action_id, matter_id, action_type, priority, severity, owner, target_ref, due_days, description`
- **Definitive signal list**: non-noise `action_id`s (no `NOISE` token) → their `target_ref`
  values are exactly the signal record IDs to surface.
- `priority` (P0/P1/P2/P3), `severity` (critical/high/medium/low), `due_days` carry to the
  action plan.

## Query patterns
```
-- signal custodian sources (exclude sequential noise IDs)
SELECT * FROM custodian_sources
WHERE matter_id='<M>' AND source_id NOT LIKE '%-<MATTERCODE>-%' ORDER BY source_id;

-- the definitive signal target set
SELECT target_ref FROM remediation_actions
WHERE matter_id='<M>' AND action_id NOT LIKE '%NOISE%' ORDER BY action_id;
```
The `MATTERCODE` token is the uppercased matter stem (e.g. for `MTR-SENTINEL-GJ` it is
`SENTINELGJ`; for `MTR-GRAYCLIFF-SEC` it is `GRAYCLIFFS`). Noise IDs use
`-<MATTERCODE>-NNN`; signal IDs use `-<SHORTCODE>-<DESCRIPTOR>` (e.g. `-SENT-`, `-GRAY-`,
`-NORTH-`, `-ALLOY-`, `-HARB-`).
