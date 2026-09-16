# Issue And Action Mapping

Use this reference after extracting the hub bundle and reading the answer template. The template controls exact field names and enum strings; this reference explains how to translate hub evidence into common legal-remediation concepts without relying on task-specific examples.

## Evidence Priority

1. Use explicit hub issue records first: `retention_events`, `privilege_entries`, `qc_findings`, `custodian_sources`, and `remediation_actions`.
2. Use `review_documents` to support document IDs, corrected responsiveness/production status, and document-level counts.
3. Use `production_stats` to detect category-level zero claims, withheld/unlogged production gaps, and readiness status.
4. Use `subpoena_categories` to identify requested categories and request-text context.
5. Use `matters` for matter metadata and hold date.

## Common Issue Mappings

| Hub evidence | Typical normalized issue |
| --- | --- |
| Retention event or source marked post-hold loss, destroyed, lost, or source unavailable after hold | `post_hold_loss`, `preservation_failure`, or preservation-loss category status |
| Retention event marked policy-destroyed before hold | low-risk policy loss, usually no remediation beyond documentation |
| Retention event or source marked should-exist missing | `missing_required_record` and locate/follow-up action |
| Source status not collected or partial collection | collection/personal-source gap, source-missing production impact |
| Available archive, retained source, cloud archive, backup, or archive exception | available/retained source section and collect/search/restore action |
| QC finding for responsive docs coded nonresponsive, zero-claim contradiction, or category marked zero produced despite responsive docs | responsiveness miscode, not-produced or underproduced impact |
| Privilege entry with withheld count greater than logged count or issue type indicating incomplete log | privilege-log gap with unlogged count = withheld minus logged |
| Privilege entry with third-party flag or third-party actor | third-party waiver or waiver-assessment issue |
| QC finding for privileged docs coded nonprivileged | privilege miscoding or privilege recode issue |
| Privilege entry indicating business-only counsel copy, over-designation, or downgrade | privilege correction/over-designation issue |

## Count Rules

- Count only selected material blockers for metrics that say "from selected blockers" or "open risk".
- Use hub aggregate counts when a privilege entry, QC finding, production stat, or retention event already supplies the count.
- Use document-level counts only when aggregate counts are absent or when the template asks for specific document refs.
- For incomplete privilege logs, calculate `unlogged_count` as `withheld_count - logged_count` unless the hub provides a more specific number.
- For destroyed records, preserve the hub's unit. Do not convert boxes, days, documents, emails, reports, or sources into each other.
- A category affected by multiple issues counts once in unique-category metrics.

## Severity And Priority

Rank issues by legal and production impact:

1. Critical post-hold loss, destroyed/lost sources, or preservation disclosures.
2. Waiver exposure and privilege material that may already be exposed or miscoded.
3. Responsive documents not produced, zero-claim contradictions, and high-severity QC miscoding.
4. Incomplete privilege logs blocking production.
5. Uncollected personal or messaging sources.
6. Available archives or retained sources that mitigate losses.
7. Policy-compliant pre-hold destruction and monitor-only items.

When hub `remediation_actions` specify ranks, priorities, owners, or due days for the same target, use them unless doing so conflicts with the answer template.

## Action Selection

| Issue | Preferred action pattern |
| --- | --- |
| Post-hold loss, destroyed source, critical preservation gap | disclose preservation issue to outside/litigation counsel; add forensic recovery only when an available recovery path is identified |
| Not-collected personal device, personal email, SMS, Signal, or similar source | collect personal device/source, usually forensics or client IT |
| Available archive or backup that mitigates an active-system gap | collect/search/restore archive, usually eDiscovery vendor or IT |
| Responsive miscoding or zero-claim contradiction | recode and produce, usually review QC or review vendor |
| Incomplete privilege log | supplement privilege log, usually privilege team |
| Third-party privilege waiver | waiver assessment and disclosure, usually privilege counsel |
| Privileged docs coded nonprivileged | privilege recode and log or QC remediation |
| Missing audit/report/required record | locate missing record or custodian/compliance follow-up |
| Policy-compliant pre-hold loss | no action policy loss or document system gap |

## Category Rollups

Build category status objects from the selected issue ledger:

- Preservation-loss status when the most serious impact is destroyed/lost evidence.
- Personal-source or collection-gap status when source collection remains incomplete.
- Archive-available status when the only current issue is an available remediation source.
- Privilege-log or underproduced-privilege-corrections status when privilege defects are the category blocker.
- Responsiveness-gap status when responsive material is miscoded, unproduced, or contradicts a zero-production claim.
- Mixed status when the schema offers a mixed blocker enum and a category has both preservation/source and missing-record issues.

Use the action tied to the highest-ranked issue in that category as the category's recommended action unless the template asks for all required actions.
