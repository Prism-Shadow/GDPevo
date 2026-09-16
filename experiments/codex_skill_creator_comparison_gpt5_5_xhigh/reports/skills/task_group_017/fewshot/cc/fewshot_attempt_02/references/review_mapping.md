# Review Mapping Guide

Use this guide after collecting the matter evidence from the Investigation Review Hub. It gives reusable mapping rules inferred from the training examples without embedding any task-specific answers.

## Hub Tables

`matters` gives hold dates and matter metadata. Use it to decide whether destruction or purge events are pre-hold or post-hold when the event record does not already classify status.

`subpoena_categories` defines category codes and topics. Category labels may also appear in task-local payloads; use Hub category codes as authoritative IDs.

`production_stats` identifies produced, withheld, responsive, nonresponsive, incomplete, and zero-production positions by category or batch. A zero-production or complete status can still be contradicted by QC findings or responsive documents.

`custodian_sources` proves collection and source availability issues. Important statuses and tags include destroyed/lost, not collected, partial collection, available archive, deleted channel, purged mailbox, personal email, personal phone, personal messaging, board source, and offsite records.

`review_documents` proves document-level responsiveness, privilege, and production status. Use document IDs as supporting refs for miscoding and zero-claim contradictions.

`privilege_entries` proves privilege log gaps, third-party waiver issues, over-designation, and privilege counts. Compute unlogged count as `max(withheld_count - logged_count, 0)` for incomplete-log blockers.

`qc_findings` proves responsiveness miscoding, privilege miscoding, zero-claim contradictions, and QC severity. Use the finding ID as an issue anchor and include the source/document refs it names.

`retention_events` proves policy destruction, post-hold losses, auto purges, active-system losses, missing required records, and archive availability. Use affected categories from the event record.

`remediation_actions` is the preferred source for action type, owner, priority, due days, target refs, and action IDs. When present, align answer actions to selected material issues rather than inventing new actions.

## Issue Classification

Classify each selected issue into the closest enum supplied by the template.

Post-hold destruction, post-hold deletion, or destroyed retained boxes should map to preservation loss or post-hold loss, with critical risk when records are irretrievably destroyed after the hold or subpoena.

Pre-hold destruction under a stated retention policy should map to policy-compliant loss with low risk in retention-focused templates. It normally should not become a top remediation risk.

Not-collected personal email, phone, SMS, Signal, or similar side-channel sources should map to personal source gap. Partial personal collections are still blockers if responsive categories are implicated.

Available archives should be reported in available-source sections. Include them as top risks only when the template asks for archive risks or when archive collection is the main remediation path for a source gap.

Responsive documents coded nonresponsive, not produced, or contradicting a zero-production claim should map to responsiveness miscode, zero-claim contradiction, or responsiveness gap. Include the QC finding and affected document IDs.

Incomplete privilege logs should map to privilege log gap, withheld-unlogged production impact, and protocol noncompliance. Use withheld/logged/unlogged counts from the privilege entry selected as a blocker.

Third-party privilege entries should map to third-party waiver or waiver assessment when a privileged communication includes an outside recipient that undermines the claim. Count those documents separately from unlogged privilege metrics.

Privilege miscoding should map to privilege miscoding, privilege recode, or QC remediation. Use QC finding counts rather than privilege log counts unless the template says otherwise.

Missing required reports, audits, certifications, or records that should exist should map to missing required record or should-exist-missing, with high risk when the matter request specifically calls for them.

Over-designation or business-only counsel-copy issues are privilege corrections but may be medium risk. Include them when the template has a privilege correction package or readiness ledger.

## Category Coverage

Build category coverage from selected issues, not from every raw category in the matter, unless the template asks for all categories.

For each affected category:

1. Collect sorted issue refs from selected issues that affect the category.
2. Count open issue records included for that category. Supporting documents do not always increase the open issue count; count issue anchors such as source, retention, privilege, and QC records.
3. Choose the category status that best describes the action-driving blocker using the template's enum choices.
4. Choose production impact from the dominant blocker. If the template has a multiple or mixed impact enum and the category has distinct blocker types, use it.

Useful precedence for category status:

1. Preservation loss or post-hold source loss.
2. Mixed preservation plus missing required record, if an enum exists.
3. Privilege waiver or underproduced privilege corrections.
4. Privilege log gap.
5. Responsiveness gap or contradicted zero-production claim.
6. Personal source gap or source gap with archive available.
7. Archive available.
8. Missing required record.
9. No open gap.

When personal source gaps and an available archive both affect the same category, use a source-gap-with-archive status if the enum provides one. Put the archive itself in the retained-or-available-source section.

## Metrics

Metrics should be derived from the same selected issue set used in the answer sections. Do not mechanically total every Hub row unless the metric label explicitly asks for all rows.

Common rules:

- `top_risk_count`: length of `top_risks`.
- `retention_event_count`: number of retention events included in the retention review.
- `post_hold_loss_event_count`: count selected post-hold loss or destroyed-source events, not affected documents.
- `pre_hold_policy_destroyed_event_count`: count selected policy-compliant pre-hold destruction events.
- `destroyed_box_count`: sum included destroyed records measured in boxes.
- `pre_hold_destroyed_box_count` and `post_hold_destroyed_box_count`: split destroyed boxes by policy/hold status.
- `destroyed_lab_archive_box_count`: use the selected destroyed archive or records source measured in boxes; return `0` if the relevant destroyed source is not measured in boxes.
- `uncollected_personal_source_count`: count selected not-collected personal source records.
- `personal_email_gap_source_count` and `personal_phone_partial_source_count`: count selected source records matching those specific source types/statuses.
- `available_archive_count`: count selected retained or available archive sources.
- `miscoded_responsive_doc_count`: count documents or QC `doc_count` selected for responsiveness miscoding or zero-claim contradiction.
- `withheld_privileged_doc_count`, `logged_privilege_doc_count`, `unlogged_privilege_doc_count`: use incomplete-log blockers only unless the template explicitly broadens the metric.
- `third_party_waiver_doc_count`: count documents in selected third-party waiver privilege entries.
- `miscoded_privileged_doc_count`: count selected QC privilege-miscoding documents.
- `missing_required_record_count`: count selected missing required record events or records.
- `affected_category_count`, `unique_affected_category_count`, `nonready_category_count`: count unique category codes in the corresponding selected section.
- category list metrics: sort category codes ascending.
- readiness booleans: false if any selected material blocker remains open, incomplete, not collected, needs recode, waived, or protocol noncompliant.

## Action Ranking

Use `remediation_actions` rows whenever they correspond to selected material issues. Preserve Hub action IDs when the schema has an action ID field. If the schema instead asks for a dashboard `action_plan`, group compatible target refs under one action when they share action type, owner, priority, and due date.

When actions must be ranked from evidence, use this default precedence:

1. Disclose preservation issue or loss to the requesting authority.
2. Forensic recovery or restore from backup.
3. Locate a missing required record.
4. Collect missing personal, board, or other source.
5. Waiver assessment and disclosure.
6. Recode and produce responsive documents.
7. Supplement privilege log.
8. Privilege recode, downgrade, or QC remediation.
9. Search or collect available archive.
10. Document low-risk system gap or no-action policy loss.

Priority defaults: critical preservation loss is `P0`; high-risk waiver, recode, privilege-log, missing-source, and missing-record work is `P1`; medium QC cleanup or documentation is `P2`; monitor-only or no-action items are `P3`.

Owner defaults when the Hub does not specify one:

- preservation disclosure: outside counsel or litigation counsel
- forensic recovery and personal-device collection: forensics or ediscovery vendor
- source collection from client systems: client IT or ediscovery vendor
- responsiveness recode and QC fixes: review QC or review vendor
- privilege log, over-designation, and privilege recode: privilege team
- waiver assessment: privilege counsel
- missing audit/compliance record: compliance audit or client legal
- archive collection/search: ediscovery vendor or records management

For due days, prefer Hub `due_days`. If none exists and the schema requires a due day, use shorter deadlines for higher risk: 3 days for P0 or waiver disclosure, 5 days for recoding/log supplementation, 7 days for personal-source collection, and 10 days for archive search.

## Final Checks

Before returning the JSON:

- Confirm every required top-level key is present.
- Confirm every object has all required item keys from the template.
- Confirm every enum value appears exactly in the template.
- Confirm all refs are stable Hub IDs and sorted where required.
- Confirm all category sets are sorted ascending.
- Confirm counts equal the selected evidence set.
- Confirm there is no prose outside the JSON.
