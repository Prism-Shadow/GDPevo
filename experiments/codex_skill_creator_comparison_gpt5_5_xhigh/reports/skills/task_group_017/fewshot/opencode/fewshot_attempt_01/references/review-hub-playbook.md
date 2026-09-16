# Review Hub Playbook

This playbook gives reusable mapping rules for Investigation Review Hub remediation and readiness tasks. It intentionally avoids task-specific final answer values.

## Evidence Collection

Start with `/api/schema` to confirm table and field names. The common hub tables are:

| Table | Use |
| --- | --- |
| `matters` | Matter metadata, agency, investigation type, hold date, status. |
| `subpoena_categories` | Category codes, labels, date ranges, request text, topic tags. |
| `production_stats` | Produced, withheld, responsive, nonresponsive counts by category and batch; zero-claim notes. |
| `custodian_sources` | Custodian systems, personal devices, archives, collection status, post-hold status, affected categories, source notes. |
| `review_documents` | Document-level coding, production status, issue tags, summaries, and category codes. |
| `privilege_entries` | Privilege-log blockers, withheld/logged counts, issue type, third-party information. |
| `qc_findings` | Review-quality defects, miscoding counts, affected categories, severity, linked source/document refs. |
| `retention_events` | Destroyed records, auto-purge windows, missing required records, retention policy information, affected categories. |
| `remediation_actions` | Action type, priority, owner, target refs, due days, and descriptions. |

When a field stores multiple category codes or issue tags as text, normalize it into a list by parsing JSON if possible; otherwise split on commas, semicolons, or pipes and trim whitespace. Keep category code casing from the hub, then sort lists lexicographically unless the template gives another order.

## Issue Families

Use the task template enums for exact labels, but map evidence by these concepts:

- Preservation or retention loss: post-hold destroyed records, post-hold source destruction, active-system loss, deleted channels, and other irreversible losses. These usually create `source_lost`, `preservation_loss`, `post_hold_loss`, or disclosure actions. Policy-compliant pre-hold destruction is usually lower risk and may need `no_action_policy_loss` when the schema asks for all retention events.
- Source collection gap: uncollected or partially collected personal email, phones, messaging apps, board/share/offsite sources, laptops, and other custodian systems. Use `source_missing`, `not_collected`, `partial_collection`, or a personal-source status when available.
- Available remediation source: archives, retained sources, backups, or exception sources that can reduce an otherwise missing-source issue. Include these in available-source sections and category coverage when the schema asks for retained or available sources.
- Responsiveness or production miscoding: QC findings or review documents showing responsive material coded nonresponsive, zero-claim contradictions, or documents that should be produced but are not. Use the QC finding as the risk anchor when it is the clearest stable issue record, and include supporting document IDs.
- Privilege log gap: privilege entries with withheld documents not fully logged. `unlogged_count = withheld_count - logged_count` for the selected blocker record unless the hub gives a more specific value.
- Third-party waiver: privileged or withheld material shared with a third party. Preserve the third-party descriptor from the hub when the schema has a `third_party` field.
- Privilege miscoding: QC findings showing privileged material coded nonprivileged or needing privilege recoding/logging.
- Over-designation or downgrade: records where material appears over-withheld or business-only despite counsel copy. Include in privilege correction sections when the template provides those fields.
- Missing required record: audits, reports, certifications, or similar records that should exist under the request and policy but are missing.

## Schema-Specific Sections

For gap-analysis templates:

- `critical_findings` or equivalent issue ledgers should contain one object per material gap or defect, anchored to the stable hub record that best represents it.
- `category_statuses` should include request categories with material non-complete status, not categories that are truly complete.
- `priority_actions` should use hub action IDs when the schema requires an `action_id`.

For retention-review templates:

- Include retention events the template asks to classify, including policy-compliant pre-hold destruction when relevant.
- Put communication-system losses such as mail, chat, voicemail, or collaboration purge windows into the communication gap section when the schema has one.
- Put available archive or retained source records into the archive/source section even when they are remediation paths rather than top risks.

For cross-system dashboard templates:

- `top_risks` should be the material risks ranked by remediation urgency. Do not pad the list with closed/no-gap records.
- `category_coverage` should roll up all material open issue refs for a category. If several issue families affect one category, choose the status and production impact that best match the template and the prompt focus; use mixed statuses when the enum provides one.
- `retained_or_available_sources` should include available archives or retained sources only. Leave it empty when no such source exists.
- `action_plan` may group multiple related target refs when the schema has no action ID field and the hub action plan does so.

For production-readiness templates:

- Include only categories that are not ready or require readiness attention.
- Maintain separate privilege correction records when the schema has a privilege-corrections section.
- Compute readiness-level privilege metrics from the incomplete-log blocker records selected by the template wording, not from every privilege-related issue indiscriminately.

## Metrics

Metrics should be reproducible from the evidence ledger and the answer sections:

- Count unique categories after normalizing category lists.
- Count source gaps by source records, not by categories affected.
- Count post-hold loss by event/source records that occurred after the hold or are marked post-hold.
- Count available archives by included available archive/source records.
- Count miscoded responsive documents from QC/document evidence, usually the QC `doc_count` or the number of supporting document IDs.
- Count third-party waiver documents from the relevant privilege entry document count.
- Count destroyed boxes only from records measured in boxes and matching the metric description.
- Set readiness booleans to false when any material blocker remains open.

When a metric description narrows the population, follow that description over a generic label. For example, a privilege metric may ask for counts from selected incomplete-log blockers only, while waiver and miscoding records are counted in separate fields.

## Action Priority

Prefer `remediation_actions` records for action type, owner, priority, due days, and target refs. If the task requires inference, rank actions by practical remediation urgency:

1. Disclosure or escalation for post-hold preservation loss.
2. Waiver assessment and disclosure.
3. Recode and produce responsive documents.
4. Supplement privilege logs or recode privileged material.
5. Collect personal devices or missing sources.
6. Search available archives or backups.
7. Locate missing required records.
8. Document policy-compliant loss or monitor only.

Use owners from the hub when available. Otherwise map legal disclosure to outside/litigation counsel, forensic collection to forensics or eDiscovery, privilege work to the privilege team or privilege counsel, coding defects to review QC, source collection to client IT or forensics, and archive searches to the eDiscovery vendor.

## Output Hygiene

- Use the exact field names from the template.
- Use enum values from the template; do not invent near-synonyms.
- Preserve sorted order for primary arrays and for ID/category reference lists.
- Use integers for counts and due days.
- Use `null` for optional string/date fields only when the template permits it.
- Return no categories, risks, corrections, or sources that lack support in the hub evidence.
