# Analysis Workflow Patterns

Each review deliverable type follows a repeatable data-gathering and
decision-logic pattern. These patterns are derived from the hub's table
structure and the standard answer templates.

## Production gap analysis

**Data sources:** matters, subpoena_categories, custodian_sources,
production_stats, review_documents, privilege_entries, qc_findings

**Gathering pass:**

1. Fetch the matter record to confirm `matter_id`, `hold_date`, and `status`.
2. Fetch all subpoena categories for the matter.
3. Fetch custodian sources and filter non-routine items: look for
   `issue_tags` containing `collection_gap`, `post_subpoena_erasure`,
   `personal_device`, `board_materials`, or `scope_exception`. Sources with
   `status` of `lost` or `not_collected` are primary gaps.
4. Fetch production stats per category. Categories with zero production
   claims (`zero_claim_reason` non-empty) or `supplement_pending` status
   may need recoding or recollection.
5. Query review documents for the matter. Look for miscoded responsive
   documents (e.g. `responsiveness` = `nonresponsive` but with
   `issue_tags` indicating responsiveness concern) and for documents
   with `privilege_status` = `privileged` but production gaps.
6. Fetch privilege entries. Identify entries with `issue_type` =
   `incomplete_log` where `logged_count` < `withheld_count`. These create
   withheld-unlogged gaps. Also note `over_designated` entries.
7. Fetch QC findings. Focus on `miscoded_nonresponsive` findings whose
   `source_ref` and `notes` confirm the document is actually responsive.

**Decision logic:**

- Each material gap becomes one `critical_findings` entry, using a stable
  hub record ID as `finding_id`.
- Map each finding to affected category codes. A single source or document
  gap can impact multiple categories.
- Compute metrics: sum unlogged privilege docs, count miscoded responsive
  docs, count lost personal devices and uncollected board sources.
- Priority actions: P0 for disclosure and forensic recovery; P1 for
  collection, recoding, and privilege log supplementation.

## Retention and litigation-hold review

**Data sources:** matters, subpoena_categories, retention_events,
  custodian_sources

**Gathering pass:**

1. Fetch the matter for `hold_date`.
2. Fetch all subpoena categories for category-context mapping.
3. Fetch all retention events for the matter.
4. Fetch custodian sources for archive availability.

**Decision logic:**

- Classify each retention event by comparing `hold_date` to `event_date`:
  * `policy_destroyed_pre_hold` -- event_date before hold_date, policy
    section present: low-risk, policy-compliant loss.
  * `post_hold_loss` -- event_date after hold_date: high-risk, must
    disclose.
  * `auto_purged` -- system auto-purge of communications: medium risk,
    document the gap.
  * `active_system_loss` -- Teams or similar with cutoff before hold:
    check for archive exceptions, medium risk.
  * `should_exist_missing` -- record that should exist per policy but
    cannot be located: high risk.
- Communication gaps come from events with `auto_purged` or
  `active_system_loss` status. Include `purge_window_days` from the
  event's retention period or volume_unit when applicable.
- Available archives are custodian sources with `status` = `available`
  and `issue_tags` containing `archive_available`. These limit loss for
  their listed category impacts.
- Actions prioritize disclosure of post-hold losses, locating missing
  records, collecting archives, documenting system gaps, and noting
  policy-compliant pre-hold losses.

## Cross-system remediation dashboard

**Data sources:** matters, subpoena_categories, custodian_sources,
  retention_events, privilege_entries, qc_findings, review_documents,
  remediation_actions

**Gathering pass:**

1. Fetch the matter record.
2. Fetch all subpoena categories for the matter.
3. Fetch custodian sources with non-routine issue tags (preservation
   loss, collection gap, personal device, archive).
4. Fetch retention events for the matter.
5. Fetch privilege entries with non-clean issue types.
6. Fetch QC findings with severity high or critical.
7. Fetch relevant review documents identified by QC source_refs.
8. Fetch existing remediation actions for the matter.

**Decision logic:**

- Top risks: rank by `priority_rank`. Anchor each risk with a stable hub
  record ID. For each risk, derive `issue_type` from the hub record's
  category (retention event -> post_hold_loss, privilege entry ->
  privilege_log_gap or third_party_waiver, QC finding ->
  responsiveness_miscode or privilege_miscoding, custodian source ->
  personal_source_gap or collection_gap).
- Category coverage: one object per category that has any open issue.
  `status` reflects the dominant problem (preservation_loss,
  personal_source_gap, source_gap_with_archive_available, etc.).
  `open_issue_count` sums the records affecting that category.
- Retained/available sources: custodian sources with `status` in
  `available_archive`, `available_retained_source`, or similar. Include
  `active_system_issue` when the source has a gap tag alongside
  availability.
- Metrics: derive counts from the hub data. `destroyed_lab_archive_box_count`
  applies only when the task's destroyed source is measured in boxes;
  otherwise use 0.
- Action plan: merge actions from the hub `remediation_actions` table
  with derived actions from top risks. Rank by priority. Assign
  `due_days` from the remediation table or use standard defaults
  (3 days for P0 disclosure, 5 days for recode/log, 7 days for
  collection, 10 days for archive search).

## Production-readiness review

**Data sources:** matters, subpoena_categories, custodian_sources,
  production_stats, privilege_entries, qc_findings, review_documents

**Gathering pass:**

1. Fetch the matter.
2. Fetch subpoena categories.
3. Fetch production stats to identify categories not in closed/produced
   status.
4. Fetch custodian sources with personal device or collection gaps.
5. Fetch privilege entries with `incomplete_log`, `waived`, or
   `over_designated` issue types.
6. Fetch QC findings for responsiveness miscodes and privilege miscodes.
7. Query review documents referenced by QC findings to confirm
   current coding and production status.

**Decision logic:**

- Readiness statuses: one entry per non-ready category. Status is
  `not_ready_privilege_log_incomplete` when blocked by privilege log gaps,
  `not_ready_privilege_waiver` for third-party waiver issues,
  `not_ready_zero_claim_contradicted` when a zero-production claim is
  contradicted by found responsive documents, `not_ready_multiple_blockers`
  when a category has more than one blocker type.
- Issue ledger: each material issue from hub records. Include current
  coding and proposed corrected disposition. Use `missing_component` for
  over-designation details.
- Privilege corrections: separate section for privilege-specific issues
  grouped by correction type.
- Metrics focus on withheld/logged/unlogged counts, waived document
  counts, miscoded responsive counts, and personal source gap counts.
- Priority actions keyed by `action_id` with stable prefixes.
