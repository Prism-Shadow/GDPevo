# Investigation Review Hub Analysis Rules

These rules describe how to convert hub records into structured gap, readiness, retention, and remediation JSON. Always let the task's `answer_template.json` control the final field names and enum spellings.

## Hub Tables

Use `GET /api/schema` to confirm table names and columns. The usual business tables are:

- `matters`: matter metadata, agency, hold date, status.
- `subpoena_categories`: request category codes, titles, request text, topic tags.
- `production_stats`: production batches, produced/withheld/responsive/nonresponsive counts, zero-claim reasons.
- `custodian_sources`: source collection, loss, availability, post-hold flag, category impacts, issue tags.
- `review_documents`: document-level responsiveness, privilege, produced status, issue tags, summaries.
- `privilege_entries`: withheld/logged counts, privilege issue type, third-party indicators.
- `qc_findings`: QC issue type, document count, affected category, source references, severity.
- `retention_events`: retention or destruction event type, dates, policy, volume, category impacts, source references.
- `remediation_actions`: candidate action metadata. Treat as hints; normalize to the template and omit noisy actions.

## Material Issue Selection

Select issues that affect production readiness, disclosure, collection, privilege treatment, or requested category coverage.

Retention and preservation:

- Post-hold loss, destroyed sources, or lost personal devices are preservation risks. They usually map to high/critical risk, `source_lost` or equivalent production impact, and a disclosure or recovery action.
- Policy-compliant pre-hold destruction is usually low risk. Include it in retention-review schemas that ask for all retention events, but prioritize it after live remediation gaps and use the template's no-action/policy-loss enum when present.
- Auto-purge and active-system loss are communication gaps. Track purge windows, cutoff dates, and whether an archive source limits the loss.
- A record that should exist but is missing maps to missing-required-record or should-exist-missing status and a locate/escalate action.

Sources and archives:

- `not_collected`, `pending`, or `partial` sources create collection or personal-source gaps when they affect requested categories.
- Personal email, phones, messaging apps, laptops, and other custodian-controlled systems usually map to personal-source collection actions.
- Available archives or retained systems should appear in retained/available source sections when the template has one. They reduce irretrievable loss for their affected categories but still need collection or search actions.
- Board portals, shared drives, offsite records, cloud mail, Teams archives, and lab/audit archives should be normalized to the closest source-type enum in the template.

Privilege:

- Incomplete privilege logs use `withheld_count`, `logged_count`, and `unlogged_count = withheld_count - logged_count`.
- Third-party recipients or waiver issue types map to waiver assessment/disclosure. Preserve the third-party label only if the template has a field for it.
- Over-designation, business-only counsel-copy issues, family mismatches, and downgrade candidates are privilege corrections or QC remediation if the template tracks them.
- Privileged documents coded nonprivileged, or QC findings that identify privilege miscoding, are privilege recode/QC issues. Count the QC document count unless the template directs otherwise.

Responsiveness and QC:

- A responsive document coded nonresponsive, a zero-production claim contradicted by responsive records, or a QC finding for responsiveness miscoding maps to recode-and-produce.
- Use QC `source_ref` and document IDs as supporting references when they anchor the issue. Include document IDs as supporting refs only when the template expects record refs and the documents are part of the material finding.
- Do not treat every `potentially_responsive`, `metadata_gap`, duplicate, alias, family-member, or routine review tag as material. Require an explicit QC finding, source/retention event, privilege entry, or document summary showing production impact.

Production categories:

- A category is not ready when it has source loss, source missing, withheld-unlogged privilege documents, privilege exposure, missing required records, or responsive documents not produced.
- A zero-claim or no-production category is a blocker only when contradicted by QC or document evidence.
- Omit complete/no-gap categories unless the template explicitly requires all categories.
- For category rollups, combine all material issue refs affecting the category, sort refs ascending, and set the status to the most severe applicable template enum. Use mixed/multiple-blocker enums when the category has materially different blocker types and the template provides one.

## Metrics

Compute metrics from the selected material issue set and the template definitions:

- Risk or finding counts equal the number of output risk/finding records.
- Unique affected category counts come from the union of material issue categories, sorted in the corresponding category-list metric.
- Post-hold and pre-hold event counts come from selected retention events with those statuses.
- Destroyed box counts sum selected retention volumes where `volume_unit` is boxes.
- Personal-source gap counts count source records, not categories.
- Available archive counts count source records included in retained/available sources.
- Miscoded responsive counts come from selected QC findings or material documents requiring recode-and-produce.
- Privilege counts for incomplete-log blockers come from the selected incomplete-log privilege entries. Do not add waiver or over-designation counts unless the metric asks for them.
- Production-ready booleans are false when any open/nonready material blocker remains.

## Priority and Ownership

Use the template enums exactly. When multiple actions are possible, rank by legal and production risk:

1. Preservation loss requiring disclosure or recovery.
2. Privilege waiver or privilege exposure requiring counsel assessment.
3. Responsive documents not produced or zero-claim contradictions requiring recode/production.
4. Incomplete privilege logs requiring supplementation.
5. Personal-source or archive collection that can remediate missing data.
6. Missing-record follow-up and system-gap documentation.
7. Policy-compliant pre-hold losses or monitoring-only items.

Typical owner normalization:

- Disclosure and readiness holds: outside counsel, litigation counsel, or client legal.
- Forensic collection or personal devices: forensics or eDiscovery vendor.
- Archive collection/search: eDiscovery vendor or records management.
- Responsiveness recoding and QC: review QC or review vendor.
- Privilege log supplementation: privilege team.
- Waiver assessment: privilege counsel.
- Audit/records follow-up: compliance audit or records management.

Group targets in one action only when the template permits grouped actions and the action type, owner, priority, and due date are the same. Otherwise emit one action per material target. Use stable hub IDs in `target_refs` and sort them.
