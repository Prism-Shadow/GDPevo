# Analysis Patterns

The Investigation Review Hub supports five core task types. Each task requires
a specific JSON output schema defined in input/payloads/answer_template.json.
Follow that schema exactly; never invent field names, types, or enums.

## Common Workflow

### Step 1: Orient and understand the schema

1. Read input/prompt.txt for the task description, matter_id, and review type.
2. Read input/payloads/answer_template.json for the exact output schema.
3. Read any context payloads (request_context.json, review_scope.json,
   matter_context.json) for category labels and task framing.

### Step 2: Call GET /api/schema

Get the full table schema to understand available columns.

### Step 3: Pull matter-level data

- GET /api/matters -- confirm the matter_id and get hold_date, agency.
- GET /api/subpoena-categories -- get all categories for the matter.

### Step 4: Pull domain evidence

Use GET endpoints for bulk data, POST /api/query for joins/aggregations.
Always filter by matter_id. Pull categories, production stats, sources,
privilege entries, QC findings, retention events, and documents.

### Step 5: Analyze and cross-reference

Cross-reference records using stable IDs. Key linkages:

- source_id appears in custodian_sources and retention_events.source_ref
- doc_id appears in review_documents and qc_findings.source_ref
- entry_id appears in privilege_entries and related QC findings
- finding_id appears in qc_findings
- event_id appears in retention_events
- batch_id appears in production_stats

### Step 6: Fill the template

Sort lists according to the ordering rules in the template. Use only the enums
and types from the template. Use stable hub record IDs as finding/issue/risk IDs.

## Pattern 1: Rolling Production Gap Analysis

Template has critical_findings, category_statuses, metrics, priority_actions.

Identify material gaps and defects:

- Production gaps: Check production_stats for zero_claim_contradicted,
  supplement_pending, or batches with produced_count below expected
  responsive_count after accounting for privilege withholdings.
- Responsiveness miscodes: Cross-reference qc_findings with
  issue_type = responsive_miscoding or zero_claim_contradiction against
  review_documents to find documents coded non-responsive that should have
  been produced.
- Privilege log gaps: Check privilege_entries for issue_type = incomplete_log
  where withheld_count > logged_count. Compute unlogged as withheld minus logged.
- Source gaps: Check custodian_sources for issue_tags containing lost,
  not_collected, personal_phone, personal_email.

Each finding gets a stable finding_id (use the primary hub record ID).
Map each finding to affected categories. Build the category_statuses array
by aggregating findings per category code.

## Pattern 2: Retention and Litigation-Hold Gap Review

Template has retention_events, communication_gaps, available_archives,
metrics, recommended_actions.

Pull retention_events and classify each by status:

- policy_destroyed_pre_hold: loss before legal hold, policy-compliant, low risk.
- post_hold_loss: loss after hold date, high/critical risk, requires disclosure.
- auto_purged: system auto-purge (e.g., voicemail), medium risk.
- active_system_loss: live system loss (e.g. Teams messages deleted), medium risk.
- should_exist_missing: record should exist per policy but cannot be found.

Map each event affected_categories to the task category list.
communication_gaps mirror retention events from ephemeral systems (Teams, voicemail).
available_archives come from custodian_sources with archive_available tag.

Cross-reference hold_date from /api/matters to classify pre-hold vs post-hold.
Compute metrics: total events, pre-hold destroyed box count, post-hold destroyed
box count, unique affected categories.

## Pattern 3: Cross-System Remediation Dashboard

Template has top_risks, category_coverage, retained_or_available_sources,
metrics, action_plan.

Pull all evidence streams together: retention events, privilege entries, QC
findings, custodian sources, documents, and production stats.

top_risks aggregates material risks ranked by severity and urgency:

- Post-hold destruction: use retention_events with post_hold_loss status.
- Third-party waiver: use privilege_entries with third_party = 1.
- Privilege miscoding: use qc_findings with privilege_miscoding or
  responsive_miscoding issue types.
- Personal source gaps: use custodian_sources with not_collected or
  personal device/email issue tags.

category_coverage summarizes all issues per category code.
retained_or_available_sources lists sources still available for remediation:
archives, Teams backups, offsite records with available or archive_available status.

Metrics include derivative counts: miscoded responsive documents, withheld/privileged
documents from key incomplete-log entries, unlogged privilege documents, third-party
waiver counts, destroyed box counts from post-hold events.

## Pattern 4: Production-Readiness Review

Template has readiness_statuses, issue_ledger, privilege_corrections,
metrics, priority_actions.

Focus on categories that are NOT ready for production. For each non-ready category,
determine the readiness_status from the set of blockers:

- Zero-claim contradicted: check production_stats status and QC
  zero_claim_contradiction findings.
- Privilege log incomplete: check privilege_entries with incomplete_log.
- Privilege waiver: check privilege_entries with third_party_waiver.
- Personal source gaps: check custodian_sources for uncollected personal devices.
- Multiple blockers: any combination of the above.

issue_ledger maps each individual issue to a stable issue_id with current
coding, produced status, and corrected disposition.

privilege_corrections extracts privilege-specific entries: supplement log gaps,
waiver assessments, privilege recoding, over-designation downgrades.

## Pattern 5: Cross-System Remediation Dashboard (DOJ Antitrust variant)

Same structural pattern as Pattern 3 but with category code family like A-F
instead of SEC-*. The template may include active_system_issue fields on
sources referencing deleted channels or purged custodian mail.

Additional concern areas: off-site bid-file retention, deleted collaboration-channel
data, production coding quality (zero-claim contradictions).

## Cross-Reference Rules

- When a QC finding source_ref contains comma-separated doc IDs, split them
  and include all as source_refs or record_refs.
- When a privilege entry withheld_count and logged_count are both non-zero,
  compute unlogged_count as the difference.
- A retention event with post_hold_loss status and volume_unit = boxes means
  physical boxes were destroyed after the hold date; this always requires
  disclose_preservation_issue.
- A custodian_sources record with issue_tags including not_collected and
  personal_phone or personal_email means a personal source gap requiring
  collect_personal_device action.
- When a production batch has status = zero_claim_contradicted and QC findings
  confirm responsive documents exist for that category, the corrected disposition
  is recode_and_produce.
- Over-designated privilege entries (issue_type over_designated) represent
  documents withheld as privileged that likely should not be; this requires
  qc_remediation or privilege_recode_and_log.

## Enum Mapping Between Hub Data and Template

Hub retention_events.status to template risk:
- post_hold_loss -> critical risk, open status
- should_exist_missing -> high risk
- active_system_loss / auto_purged -> medium risk
- policy_destroyed_pre_hold -> low risk

Hub privilege_entries.issue_type to template:
- incomplete_log -> privilege_log_gap issue, supplement_privilege_log action
- third_party_waiver -> third_party_waiver issue, waiver_assessment_and_disclosure action
- over_designated -> over_designation issue, qc_remediation or privilege_recode_and_log

Hub custodian_sources.issue_tags to template:
- lost / destroyed -> preservation_failure or post_hold_loss, source_lost
- not_collected + personal_phone or personal_email -> personal_source_gap, source_missing
- archive_available -> archive_available, remediation path

## Deriving unlogged_count

For privilege entries: unlogged_count = withheld_count - logged_count.
This is the number of withheld documents missing from the privilege log.
