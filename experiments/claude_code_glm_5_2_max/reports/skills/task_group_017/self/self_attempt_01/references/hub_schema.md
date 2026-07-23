# Investigation Review Hub — Reference

Derived from the shared hub's `GET /api/schema`. This is general structure, not
any matter's answer. Use it to know which table/fields back each deliverable
section.

## Network access (from `environment_access.md`)

- Base URL: `http://task-env:9017/`
- Read-only SQL endpoint: `POST /api/query` with header `X-API-Key: review-key-017`
- `environment_access.md` is the ONLY local file used for network access.

Allowed endpoints:

```
GET  /api/schema
GET  /api/matters
GET  /api/subpoena-categories
GET  /api/productions
GET  /api/custodian-sources
GET  /api/documents/search
GET  /api/privilege-log
GET  /api/qc-findings
GET  /api/retention-events
GET  /api/remediation-actions
POST /api/query
```

Every endpoint returns rows scoped across matters; always filter by the task's
`matter_id`. The SQL endpoint is the efficient path for filtered and aggregate
rollups (counts by category, post-hold losses, withheld vs. logged sums).

## Tables and columns

- **matters**: `matter_id, name, agency, investigation_type, issued_date, hold_date, lead_partner, description, status`
  → the `hold_date` is the preservation dividing line: losses before it may be
  policy-compliant; losses after it are preservation failures.
- **subpoena_categories**: `matter_id, category_code, title, date_start, date_end, request_text, topic_tags`
  → authoritative list of request category codes for the matter. Use these
  codes verbatim; never invent category codes.
- **production_stats**: `matter_id, batch_id, batch_date, category_code, produced_count, withheld_count, responsive_count, nonresponsive_count, status, zero_claim_reason, notes`
  → per-batch, per-category production volume. `zero_claim_reason` flags
  categories asserted as "nothing responsive" — cross-check against
  documents/custodian sources before accepting.
- **custodian_sources**: `source_id, matter_id, custodian_name, role, source_type, source_label, status, event_date, post_hold, category_impacts, issue_tags, notes`
  → source-level gaps. `post_hold=1` losses are preservation failures.
  `category_impacts` / `issue_tags` carry comma-separated category codes and
  issue markers.
- **review_documents**: `doc_id, matter_id, title, doc_date, custodian_name, source_system, category_code, responsiveness, privilege_status, produced_status, issue_tags, summary`
  → document-level coding. Drives miscoded-responsive and privilege-log-gap
  findings. `produced_status` distinguishes produced / withheld / not_produced.
- **privilege_entries**: `entry_id, matter_id, category_code, custodian_name, doc_count, withheld_count, logged_count, issue_type, third_party, notes`
  → privilege log rows. `unlogged = withheld_count - logged_count`.
  `third_party=1` flags third-party waiver exposure.
- **qc_findings**: `finding_id, matter_id, batch_id, issue_type, doc_count, affected_category, source_ref, severity, notes`
  → quality-control defects. `source_ref` links a finding back to a
  custodian_source / document / privilege entry.
- **retention_events**: `event_id, matter_id, record_type, event_date, hold_date, policy_section, retention_period_months, volume_count, volume_unit, status, affected_categories, source_ref, notes`
  → retention / preservation events. `status` carries the retention_status
  archetype (policy-destroyed-pre-hold vs. post-hold-loss, etc.).
- **remediation_actions**: `action_id, matter_id, action_type, priority, severity, owner, target_ref, due_days, description`
  → candidate remediation actions already proposed in the hub. `target_ref`
  points at the record the action remediates.

## Stable IDs to carry through verbatim

matter_id, source_id, event_id, finding_id, doc_id, entry_id, action_id,
batch_id, and category_code. The deliverable's finding/risk/issue keys and
every `*_refs` list must use these hub IDs exactly as returned.
