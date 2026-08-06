# Investigation Review Hub — data model reference

Read-only API. Base URL from `GDPEVO_ENV_BASE_URL` (or payload `environment_base_url`).
Auth header on every request: `X-API-Key: review-key-017`.

`GET /` returns service metadata and the endpoint list. `GET /api/schema` returns the table
definitions below. `POST /api/query` body is `{"sql":"SELECT …"}`; response is
`{columns, rows, row_count, truncated}` and **rows are capped at 500** — aggregate, don't dump.
GET list endpoints accept `?matter_id=<MTR-…>` and pre-parse comma fields into arrays; in raw
SQL those same columns are comma-delimited TEXT.

There are 16 matters in the shared hub (the training matters plus others). Always scope to the
task's `matter_id`.

## Tables (from `GET /api/schema`)

### matters
`matter_id, name, agency, investigation_type, issued_date, hold_date, lead_partner, description, status`
- `hold_date` is the **litigation-hold pivot**: losses dated before it can be policy-compliant;
  losses after it are preservation failures.
- `investigation_type ∈ {grand_jury_subpoena, sec_subpoena}`; `status ∈ {active_review, closed_monitoring}`.

### subpoena_categories
`matter_id, category_code, title, date_start, date_end, request_text, topic_tags`
- The **canonical request category codes** to report against. Code schemes are matter-specific
  (e.g. `A…I`, `SEC-A…`, `SEC-1…`, `R09/R11`, `MD-*`, `CR-*`, `VL-*`, `PE-*`). Report codes
  uppercase and ascending.

### production_stats
`matter_id, batch_id, batch_date, category_code, produced_count, withheld_count, responsive_count, nonresponsive_count, status, zero_claim_reason, notes`
- `status ∈ {closed, produced, supplement_pending, rolling_review, zero_claim_contradicted}`.
- `zero_claim_contradicted` (+ a `zero_claim_reason` like "No responsive … found") means the
  matter certified zero responsive docs for a category but responsive docs exist — a material
  contradiction.

### custodian_sources
`source_id, matter_id, custodian_name, role, source_type, source_label, status, event_date, post_hold, category_impacts, issue_tags, notes`
- `status ∈ {partial_collection, available, not_collected, collected, in_review, lost}`.
  Material: `lost`, `not_collected` (and `partial_collection` when tagged).
- `post_hold` = 1/0 flag.
- `source_type` includes routine (`network_share, contract_repository, mailbox, teams_export,
  mobile_backup`) and material-leaning (`personal_phone, personal_email, personal_messaging,
  laptop, board_portal, teams_archive, email_archive, cloud_mail_archive, chat_archive,
  sharepoint_site`).
- `issue_tags` (comma list). Routine/noise: `routine, scope_exception, metadata_gap`.
  Material: `collection_gap, personal_email, personal_device, personal_messaging, sms, signal,
  signal_missing, post_hold_wipe, remote_erasure, post_subpoena_erasure, board_materials,
  valuation_source_gap`. Archive/remediation: `archive_available, remediation_source,
  purged_mail, deleted_channel, chat_attachments`.

### review_documents
`doc_id, matter_id, title, doc_date, custodian_name, source_system, category_code, responsiveness, privilege_status, produced_status, issue_tags, summary`
- Large table (filter hard). `responsiveness ∈ {responsive, nonresponsive, needs_review}`;
  `privilege_status ∈ {nonprivileged, privileged, unknown}`;
  `produced_status ∈ {produced, withheld, not_produced, unrecovered}`.
- Query via `GET /api/documents/search?matter_id=…&responsiveness=…` or SQL.
- Bulk `issue_tags` are noise (`routine, duplicate, family_member, metadata_gap,
  custodian_alias, potentially_responsive, privilege_overlay, review_escalation`, and their
  combos). **Material** tags: `miscoded_nonresponsive`, `zero_claim_contradiction`,
  `unrecovered_file`, `valuation_red_flag`, `unsupported_override`, `unsupported_metric`,
  `backsolve`, `back_into_target`, and topical prefixes (`bid_email, dealer_safety,
  clinical_risk, investor_complaint, banker_side_channel, dealer_complaint`).
- A miscoded-nonresponsive doc is typically `responsiveness=nonresponsive` +
  `produced_status=not_produced` but responsive in fact. An unrecovered file is
  `produced_status=unrecovered`.

### privilege_entries  (endpoint: `GET /api/privilege-log`)
`entry_id, matter_id, category_code, custodian_name, doc_count, withheld_count, logged_count, issue_type, third_party, notes`
- `issue_type ∈ {incomplete_log, over_designated, family_mismatch, third_party_waiver, clean}`.
- **`unlogged = withheld_count − logged_count`** (compute for `incomplete_log`).
- `third_party` = 1 flags waiver-risk (privileged material shared with a third party).

### qc_findings
`finding_id, matter_id, batch_id, issue_type, doc_count, affected_category, source_ref, severity, notes`
- Material `issue_type`: `miscoded_privilege`, `zero_claim_contradiction`, `miscoded_nonresponsive`.
- Noise `issue_type`: `metadata_gap, date_normalization, near_duplicate, family_break, duplicate_overlay`.
- `severity ∈ {high, medium, low}`. `source_ref` may be a comma list of the DOC/PRIV IDs the
  finding is built from (use them as refs).

### retention_events
`event_id, matter_id, record_type, event_date, hold_date, policy_section, retention_period_months, volume_count, volume_unit, status, affected_categories, source_ref, notes`
- `status ∈ {system_loss, retained, policy_destroyed_pre_hold, should_exist_missing, available,
  post_hold_loss, post_hold_partial_recovery, auto_purged}`.
  - `policy_destroyed_pre_hold` — event_date < hold_date, policy-compliant → **no gap / no fault**.
  - `post_hold_loss` — event_date > hold_date → **preservation failure → disclose**.
  - `should_exist_missing` — a required record that should exist is absent.
  - `retained` / `available` / `post_hold_partial_recovery` — a **remediation archive/source**.
- `volume_unit ∈ {exports, boxes, files, reports, report, mailboxes, days, system_window,
  monthly_blotters}`. Honor the unit a metric asks for (e.g. "box_count" ⇒ only `boxes`).

### remediation_actions
`action_id, matter_id, action_type, priority, severity, owner, target_ref, due_days, description`
- `action_type ∈ {sampling_review, supplemental_collection, load_file_cleanup,
  custodian_followup, retention_exception_review, privilege_rework, qc_remediation}`.
- `priority ∈ {P1, P2, P3}` (templates also allow P0 for the most severe); `severity ∈ {high,
  medium, low}`.
- Hub `owner` labels: `Review Operations, Matter Associate, Forensics, Privilege Team,
  Vendor Team, Legal Hold Team` — map to the template's owner enum.
- **Decoys**: `action_id` containing `NOISE`, or a `target_ref` that is a bare category code
  with `action_type=sampling_review`/low severity. Material actions target real record IDs
  (`PRIV-*, QC-*, RET-*, SRC-*, DOC-*`). Drop the decoys.

## Handy queries

```sql
-- material retention losses for a matter
SELECT event_id, status, event_date, hold_date, volume_count, volume_unit,
       affected_categories, source_ref
FROM retention_events
WHERE matter_id = 'MTR-…'
  AND status IN ('post_hold_loss','should_exist_missing','auto_purged','post_hold_partial_recovery');

-- privilege-log gap totals (metric feed)
SELECT SUM(withheld_count) withheld, SUM(logged_count) logged,
       SUM(withheld_count - logged_count) unlogged
FROM privilege_entries
WHERE matter_id = 'MTR-…' AND issue_type = 'incomplete_log';

-- material QC defects
SELECT finding_id, issue_type, doc_count, affected_category, source_ref, severity
FROM qc_findings
WHERE matter_id = 'MTR-…'
  AND issue_type IN ('miscoded_privilege','zero_claim_contradiction','miscoded_nonresponsive');

-- material custodian sources (collection loss + archives)
SELECT source_id, source_type, status, post_hold, category_impacts, issue_tags
FROM custodian_sources
WHERE matter_id = 'MTR-…'
  AND (status IN ('lost','not_collected')
       OR issue_tags LIKE '%collection_gap%' OR issue_tags LIKE '%personal_%'
       OR issue_tags LIKE '%erasure%'        OR issue_tags LIKE '%archive_available%');

-- candidate action plan (then drop NOISE / bare-category rows)
SELECT action_id, action_type, priority, severity, owner, target_ref, due_days
FROM remediation_actions
WHERE matter_id = 'MTR-…'
ORDER BY priority, severity DESC;
```
