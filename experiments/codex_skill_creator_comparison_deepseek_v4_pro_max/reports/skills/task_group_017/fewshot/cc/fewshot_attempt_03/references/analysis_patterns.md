# Analysis Patterns

This reference describes the common analysis types seen in train evidence and how to connect hub records to output fields. Use it to orient yourself when the task matches one of these patterns.

## Pattern A: Production gap analysis

**When to use**: The task asks for a "gap analysis," "production gap review," or mentions "rolling production." The answer template has keys like `critical_findings`, `category_statuses`, `metrics`, `priority_actions`.

### How to detect gaps

1. **Responsiveness miscodes**: Look for documents where:
   - QC findings have `issue_type` like `zero_claim_contradiction` or `responsiveness_miscode`.
   - The production batch for that category has `status: "zero_claim_contradicted"`.
   - Cross-reference: a finding's `source_ref` often points to a specific `doc_id`.

2. **Privilege log gaps**: Look for privilege entries where:
   - `logged_count < withheld_count`. The gap is `withheld_count - logged_count`.
   - `issue_type` is `log_gap`.
   - The entry spans a large doc count.

3. **Collection/preservation gaps**: Look for custodian sources where:
   - `status` is `not_collected` or `lost`.
   - `issue_tags` contain `collection_gap`, `post_hold_wipe`, `personal_messaging`.
   - The source has `category_impacts` targeting specific request categories.

4. **Retention losses**: Look for retention events with `status` values indicating loss.

### How to build findings

Each material gap becomes one object in `critical_findings` (or `top_risks`, `issue_ledger`, depending on the template). Use the most specific hub record as `finding_id`:
- For a miscoded document: the document's `doc_id` or the QC `finding_id`.
- For a source gap: the source's `source_id`.
- For a privilege log gap: the privilege entry's `entry_id`.

Populate `source_refs` with every hub record ID that supports the finding. Include the primary record plus any QC findings, related documents, or sources that confirm it.

### How to build category statuses

Walk every category from subpoena_categories for the matter. For each category, check all evidence tables for issues touching that category. A category gets a non-clean status when:
- Any production batch for it has `status: "zero_claim_contradicted"` or `"supplement_pending"`.
- Any custodian source with that category in `category_impacts` has `status: "not_collected"` or `"lost"`.
- Any QC finding with that `affected_category` has high/critical severity.
- Any privilege entry with that `category_code` has a log gap.
- Any retention event with that category in `affected_categories` has a loss status.

Categories with no material issues should generally be omitted from `category_statuses` unless the template explicitly requires entries for all categories. Follow the template's description field for guidance.

### Metrics computation

- **unlogged_privilege_docs**: Sum `(withheld_count - logged_count)` across all privilege entries for the matter that have an incomplete log.
- **miscoded_responsive_doc_count**: Count documents flagged by QC findings as miscoded nonresponsive.
- **lost sources**: Count custodian sources with `status: "lost"`.
- **uncollected sources**: Count custodian sources with `status: "not_collected"` and material issue tags (ignore routine sources).
- **categories_with_open_gaps**: Count distinct category codes touched by any material gap.
- **rolling_production_ready**: Set `true` only when zero categories have material gaps.

## Pattern B: Retention and preservation review

**When to use**: The task mentions "retention," "litigation-hold," or "preservation gap." The answer template has keys like `retention_events`, `communication_gaps`, `available_archives`, `metrics`, `recommended_actions`.

### How to detect retention issues

1. Query `/api/retention-events` filtered by matter_id. Each row is a retention event with a `status`:
   - `policy_destroyed_pre_hold`: Destroyed per policy before the hold date. Low risk if policy-compliant.
   - `post_hold_loss`: Destroyed or lost after the hold date. High risk -- must be disclosed.
   - `auto_purged`: Automatically deleted by system (e.g., voicemail after N days, chat retention).
   - `active_system_loss`: Data lost because the system's retention window didn't cover the period.
   - `should_exist_missing`: Records that should exist per policy but were not found.
   - `available_archive`: Records available in an archive for remediation.

2. Communication gaps are a subset of retention events where the loss is tied to a communication system (Teams, voicemail, Slack). Copy the relevant retention events into the `communication_gaps` list with the `gap_type` field mapped from the retention status.

3. Available archives are sources (from custodian_sources) where:
   - `status` is `available` and `issue_tags` contain `archive_available`.
   - They can mitigate losses for specific categories listed in `category_impacts`.

### Metrics computation

- **retention_event_count**: Total retention event rows for the matter.
- **pre_hold_policy_destroyed_event_count**: Count of `policy_destroyed_pre_hold` events.
- **post_hold_loss_event_count**: Count of `post_hold_loss` events.
- **communication_gap_event_count**: Count of `auto_purged` + `active_system_loss` events.
- **should_exist_missing_event_count**: Count of `should_exist_missing` events.
- **available_archive_count**: Count of available archive sources.
- **destroyed_box_count**: Sum `volume_count` where `volume_unit` is `boxes`.
- **pre_hold/post_hold box counts**: Same sum but filtered by status.
- **categories_with_any_gap_or_loss**: Union of all `affected_categories` from all retention events, sorted ascending.

## Pattern C: Cross-system remediation dashboard

**When to use**: The task asks for a "remediation dashboard," "cross-system review," or mentions remediation of multiple issue types. The answer template has keys like `top_risks`, `category_coverage`, `retained_or_available_sources`, `metrics`, `action_plan`.

This pattern combines elements of both gap analysis and retention review. The analysis spans retention events, custodian sources, privilege entries, QC findings, and documents.

### How to build top_risks

Rank risks by severity first, then by operational impact:
- **Critical**: Post-hold losses of substantial volume, lost sources that can't be recovered.
- **High**: Log gaps with large unlogged populations, third-party waivers, uncorrected QC findings.
- **Medium**: Auto-purging without archive coverage, partial collection gaps.
- **Low**: Pre-hold policy-compliant losses.

Each risk object needs `source_refs` listing every hub record that supports the finding. Use the most specific record as `risk_id`.

### How to build category_coverage

For every subpoena category tied to the matter, determine a `status` from the template's `category_status` enum:
- `preservation_loss`: Categories where sources were destroyed/lost post-hold.
- `personal_source_gap`: Categories with uncollected personal devices/messaging.
- `source_gap_with_archive_available`: Categories with collection gaps but an archive exists.
- `archive_available`: Categories covered by an available archive (no material gap).
- `privilege_log_gap`: Categories with incomplete privilege logs.
- `responsiveness_gap`: Categories with miscoded responsive documents.
- `underproduced_privilege_corrections`: Categories needing privilege recoding or waiver assessment.
- `no_open_gap`: Categories with no material issues.

`open_issue_count` should be the number of distinct hub records (findings, sources, events, privilege entries) contributing to issues in that category.

### How to build retained_or_available_sources

From custodian_sources, select every source where:
- `status` is `available` OR
- `issue_tags` contain `archive_available` OR
- The source is a remediation path for lost data.

If no such sources exist, return an empty list `[]`.

For each source, `limits_loss_for_categories` should list the specific categories where this source provides a remediation path. This may be a subset of `affected_categories` (the source covers all listed categories) or exactly matches when the source directly replaces lost data.

### Metrics computation for dashboards

The metrics section in dashboard templates typically has ~14 fixed keys. Compute each one:
- **top_risk_count**: Number of items in `top_risks`.
- **destroyed_lab_archive_box_count**: Sum `volume_count` from retention events where `volume_unit` is `boxes` -- or 0 if the matter has no box-based losses. Match the specific metric name in the template exactly.
- **post_hold_loss_event_count**: Count retention events with `post_hold_loss`.
- **uncollected_personal_source_count**: Count custodian sources with `status: "not_collected"` and personal messaging tags.
- **available_archive_count**: Count available archive sources.
- **miscoded_responsive_doc_count**: From QC findings, count documents flagged as miscoded nonresponsive.
- **withheld_privileged_doc_count**: Sum `withheld_count` from selected incomplete-log privilege entries.
- **logged_privilege_doc_count**: Sum `logged_count` from those same entries.
- **unlogged_privilege_doc_count**: `withheld - logged` from those same entries.
- **third_party_waiver_doc_count**: Sum `doc_count` from privilege entries where `third_party` is 1.
- **miscoded_privileged_doc_count**: From QC findings, count documents flagged as miscoded privileged.
- **missing_required_record_count**: Count retention events with `should_exist_missing`.
- **affected_category_count**: Count distinct categories in `categories_with_open_risk`.
- **categories_with_open_risk**: Union of all category codes from all risks, sorted ascending.

## Pattern D: Production readiness review

**When to use**: The task asks for a "readiness review" or "production readiness." The answer template has keys like `readiness_statuses`, `issue_ledger`, `privilege_corrections`, `metrics`, `priority_actions`.

### How to build readiness_statuses

For categories that are NOT production-ready, determine `readiness_status`:
- `not_ready_zero_claim_contradicted`: Production batch has `zero_claim_contradicted` and QC confirms miscoded responsive docs.
- `not_ready_personal_source_gap`: Uncollected personal sources affect the category.
- `not_ready_privilege_log_incomplete`: Privilege log has `logged_count < withheld_count`.
- `not_ready_privilege_waiver`: Third-party waiver issue affects the category.
- `not_ready_multiple_blockers`: More than one of the above applies.

Categories that are ready should generally be omitted unless the template explicitly asks for all categories.

### How to build issue_ledger

Each material issue becomes one ledger entry. Include detailed fields the template requires:
- `current_coding`: The current coding status of affected documents (`responsive`, `nonresponsive`, `privileged`, `nonprivileged`).
- `produced_status`: Current production status.
- `corrected_disposition`: What the corrected state should be (`responsive_produce`, `supplement_log`, `waiver_assessment`, etc.).
- `missing_component`: For over-designation or miscoding, describe what's missing (e.g., "business_only_counsel_copy_overdesignation").

### How to build privilege_corrections

This section is a focused view of privilege-specific issues. Each privilege entry or QC finding that affects privilege gets a correction entry:
- `correction_type`: `supplement_log` for log gaps, `waiver_assessment` for third-party waivers, `privilege_recode` for miscoded privileged docs, `downgrade` for over-designated docs.
- `privilege_status`: Maps from hub data (`incomplete_log`, `waived`, `over_designated`, etc.).
- `unlogged_count`: Always `withheld_count - logged_count` for that entry.

## General rules for all patterns

### ID stability

Use record IDs exactly as returned by the hub. For example, if the hub returns `"SRC-CLIENT-CUSTODIAN-TYPE"`, use that exact casing and punctuation. Do not abbreviate, expand, or change separator characters.

### Enum matching

Every string field constrained by an enum must use exactly one of the listed values. Match case and underscores precisely. Values like `"not_applicable"` vs `"not_applicable"` are distinct -- copy the spelling from the template enum.

### Null handling

When a field can be null (per template or schema), use JSON `null` rather than the string `"null"` or omitting the key. The `third_party` field is commonly null when no third party is involved.

### Sorting discipline

Build lists first, then sort. Most templates require:
- Category codes sorted ascending (lexicographic, e.g., `"A"` before `"B"`, `"R01"` before `"R09"`, `"SEC-1"` before `"SEC-2"`).
- IDs sorted ascending.
- Priority ranks sorted ascending (1 first).

Never skip post-build sorting. The ordering is part of the contract.
