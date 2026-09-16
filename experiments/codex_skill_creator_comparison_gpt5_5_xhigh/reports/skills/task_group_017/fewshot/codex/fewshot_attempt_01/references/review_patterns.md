# Investigation Review Patterns

Use these reusable mappings to convert hub records into schema-shaped JSON. Always prefer explicit hub fields and notes over defaults.

## Issue Classification

- Post-hold destruction, lost sources, or destroyed records after a legal hold usually map to preservation or post-hold loss, critical or high risk, source lost, and disclosure/escalation action.
- Pre-hold destruction that follows an identified retention policy usually maps to policy-compliant loss, low risk, and no-action or documentation action.
- Missing records that should exist under the retention policy map to missing-required-record or should-exist-missing status and a locate/escalate action.
- Not-collected personal email, phone, SMS, chat, messaging, or similar custodian sources map to personal-source gaps and collection actions.
- Available archives or retained sources should appear in the retained/available source section when the template has one, even if they also support a category gap.
- Deleted channels or purged active systems with a searchable archive map to source gap with archive available; without an archive, map to active system loss or auto-purge.
- Documents found responsive after being coded nonresponsive, or QC findings contradicting a zero-production claim, map to responsiveness miscoding and recode-and-produce action.
- Withheld privilege documents where logged count is below withheld count map to a privilege-log gap; `unlogged = withheld - logged`.
- Third-party recipients or disclosure indicators in privilege records map to third-party waiver or waiver assessment.
- Privileged documents coded nonprivileged or nonprivileged documents coded privileged map to privilege miscoding, privilege recode, downgrade, or QC remediation depending on the template enums.

## Category Rollups

Build category rows from all selected issues touching that category.

1. Preservation loss or post-hold source loss is usually the highest-precedence status.
2. Multiple different blockers should use a multiple/mixed status when the enum provides one.
3. Privilege exposure with waiver or miscoding takes precedence over a simple incomplete-log status.
4. Responsiveness miscoding or zero-claim contradiction takes precedence over general underproduction.
5. Personal-source gaps and source gaps with archive availability should preserve the distinction when the enum allows it.
6. Archive-only categories use archive-available or source-available status when no stronger blocker exists.
7. Exclude categories with no current gap unless the template asks for every category.

For each category, sort `issue_refs` or `source_refs` ascending and count the distinct open material issue records represented in that category row.

## Metrics

Compute metrics from selected output records, not from unrelated background records.

- Risk or event counts equal the number of listed material top risks, issue ledger entries, retention events, or communication gaps as named by the metric.
- Affected-category counts equal the number of unique category codes across listed material gaps.
- Categories-with-open-risk arrays contain sorted unique category codes from selected open issues.
- Destroyed-box metrics sum selected retention/source loss volumes whose unit is boxes.
- Post-hold loss metrics count distinct selected events or sources that occurred after hold or are flagged post-hold.
- Uncollected personal-source metrics count distinct selected personal sources with not-collected or partial statuses.
- Available-archive metrics count distinct selected archive or retained source records that remain a remediation path.
- Miscoded responsive document metrics come from QC findings or document rows requiring recode and production.
- Privilege metrics use the blocker set the template asks for. If the field says incomplete-log blockers only, do not add waiver or over-designation counts.
- Waiver and miscoded-privilege metrics count the specific documents/emails described by selected waiver or privilege-miscoding records.
- Readiness booleans are false when any material blocker remains open.

## Actions

Use hub remediation actions when they provide stable IDs and target references. When deriving actions from issues:

- Disclosure/escalation for post-hold loss is first priority and usually owned by outside or litigation counsel.
- Forensic recovery or personal-device collection is owned by forensics or the eDiscovery vendor when those owners exist in the enum.
- Archive collection/search is owned by the eDiscovery vendor.
- Responsive miscoding and production recoding are owned by review QC, review vendor, or review operations.
- Privilege-log supplementation is owned by the privilege team.
- Third-party waiver assessment is owned by privilege counsel.
- Missing audit, compliance, or required records are owned by compliance audit, records management, or legal operations.
- Policy-compliant pre-hold loss is last priority and usually no action beyond documentation.

For dashboard schemas that require `due_days` and no hub due date is supplied, use short whole-number deadlines by priority: earliest for P0 disclosure and waiver assessment, then recoding and privilege-log supplementation, then personal-source collection, then archive search.

## Final JSON Checks

- Match top-level key names exactly.
- Use the template's enum spelling exactly; map concepts to the closest allowed value.
- Preserve `null` only for schema fields that allow it. Use `0` for non-applicable counts.
- Sort lists according to the template, including category codes inside each item.
- Do not include explanatory text, comments, markdown, or citations in the final answer.
