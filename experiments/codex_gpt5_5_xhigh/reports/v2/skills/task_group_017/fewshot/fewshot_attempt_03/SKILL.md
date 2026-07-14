---
name: legal-investigation-production-review
description: Produce strict JSON reviews for subpoena production, collection, retention, privilege, and QC deficiency tasks using the shared legal investigation API and task-local templates.
---

## Scope

Use this skill when a task asks for a structured legal production or collection-readiness review for a specific matter, category set, or custodian. The expected output is usually JSON only, shaped by a task-local `answer_template.json`.

## Inputs First

1. Read the prompt, then the task's `answer_template.json`.
2. Record the exact matter ID, optional custodian ID, required top-level keys, key order, enums, sorting rules, and whether the template wants only deficient items or all readiness statuses.
3. Read any task-local payloads, memos, or partner requests. Treat them as scope and fact modifiers, especially for hold-notice omissions, source-name synonyms, and partner-request limitations.
4. Use the API base URL from `environment_access.md` whenever the prompt shows `<TASK_ENV_BASE_URL>`.

## API Workflow

The shared API exposes:

- `/api/matters/{matter_id}`
- `/api/subpoena_categories?matter_id=...`
- `/api/production_logs?matter_id=...`
- `/api/collection_events?matter_id=...`
- `/api/retention_rules?matter_id=...`
- `/api/destruction_events?matter_id=...`
- `/api/privilege_logs?matter_id=...`
- `/api/qc_events?matter_id=...`
- `/api/custodians?matter_id=...`
- `/api/documents?matter_id=...`
- `/api/search?matter_id=...&q=...`

Most list endpoints return `{"count": n, "items": [...]}`. Search returns grouped `results` by collection. Inspect keys before assuming shape.

Build a working table by category, custodian, and source:

- Category scope: requested sources, date range, topic tags.
- Production tracker: produced count, withheld privileged count, privilege logged count, review status, notes.
- Collection events: source type/name, status, collected and missing counts, hold relation, related categories.
- Retention and destruction: rule ID, destruction event ID, pre/post-hold timing, quantity, recoverability.
- Privilege logs: logged status, record count, privilege status, overdesignation, waiver risk, production status.
- QC events and documents: failed/recovered counts, related document IDs, review notes, document coding and production status.

Use `/api/search` for targeted terms such as `miscoded`, `privilege`, `Teams`, `PST`, `personal`, `archive`, `destruction`, or a custodian name, but confirm findings against the primary endpoint records.

## Business Rules

Include only material blockers or deficiencies unless the template explicitly asks for all readiness rows.

- Production tracker defects: zero or incomplete production for responsive documents is a coding or supplemental-production issue. QC events and document summaries can override a tracker that otherwise looks complete.
- Miscoded responsive documents: if documents are coded non-responsive or stale but summaries/tags/category mapping show responsiveness, require QC reprocessing, coding correction, and/or supplemental production.
- Privilege log gap: if `withheld_privileged_count > privilege_logged_count`, the unlogged count is the difference. Require a privilege-log supplement and usually privilege review.
- Privileged material produced as non-privileged: treat as privilege miscoding, require clawback or clawback check plus privilege review. Use the API's record count even when only marker document IDs are listed.
- Overdesignation: business-only or all-withheld counsel categories with overdesignation flags require privilege review and possible production of nonprivileged material. This is normally a protocol defect, not disclosure by itself.
- Waiver risk: privileged material forwarded to an outside banker, consultant, vendor, opposing party, or similar third party requires waiver assessment and privilege-team escalation.
- Processing failures: corrupt/password-protected attachment failures are processing exceptions. Count failed, recovered, and unrecovered items; usually require reprocess QC and supplemental collection, not notice.
- Post-hold loss or destruction: source wipes, post-hold destruction, or unrecovered deleted shared-drive/source records are critical. Recommend regulator/opposing-party notice when the template has a notice field, plus forensic recovery, declarations, hold refresh, or supplemental collection.
- Pre-hold policy destruction: destruction before the hold under a normal retention rule is a policy gap, not spoliation. Use `no_action_policy_gap` or the template's equivalent and do not recommend notice unless another post-hold fact requires it.
- Recoverable archives or vendor portals: classify as recoverable or retained-missing, not spoliation. Require archive validation, vendor retrieval, or supplemental collection. Notice is usually false.
- Hold-notice defects: omitted personal devices, SMS, cloud text, vendors, or offsite sources require hold refresh and supplemental collection. Escalate to notice only if there is actual post-hold loss or the template directs notice for the defect.
- Teams/pre-2022 or local PST gaps: classify as source gaps or uncollected sources. Require assessment, forensics, or supplemental collection; do not call them post-hold spoliation without date evidence.
- Ready/no-action categories: omit them from deficiency-only outputs. If readiness rows are required, mark them ready or ready with a retention note and use `no_action` when allowed.

## Severity And Status

Use the template's exact enum values. When choosing among allowed values:

- `critical`: post-hold loss/destruction, unrecovered source deletion, or required disclosure.
- `high`: uncollected material source, material miscoding, privilege log gap, retained-missing vendor source, or clawback risk.
- `medium`: overdesignation, processing failure, or pre-hold policy gap with replacement evidence.
- `low`: recoverable archive validation or minor policy note.

Overall status should be blocked or not ready when production cannot be certified before remediation. Use needs-escalation when there are critical issues or notice review. Disclosure or notice booleans are true when any included issue requires notice.

## Output Conventions

- Return one JSON object only. Do not include markdown, comments, schema metadata, or explanatory narrative.
- Match the template's top-level key order and required nested key order when specified.
- Use exact enum spelling and casing from the template.
- Use integer counts and JSON booleans. Use `0` when the template requires a count and no count applies.
- Use empty lists for required list fields with no values; do not omit required fields.
- Do not invent evidence IDs. Echo exact API IDs such as category IDs, custodian IDs, document IDs, collection event IDs, destruction event IDs, retention rule IDs, production log IDs, privilege item IDs, and QC event IDs.
- If an API record gives a total count but only endpoint marker documents are present, use the total count for count fields and list only the exact document IDs available when document IDs are required.
- Generate stable issue, finding, source, and action IDs from the issue type and category/source when the template does not prescribe enum IDs.

## Sorting

Follow the template first. Common defaults:

- Category IDs ascending.
- Custodian IDs ascending.
- Document IDs ascending.
- Issue/finding/action IDs ascending unless rank controls order.
- Source/event IDs ascending by prefix group and numeric suffix.
- Source names alphabetically.
- Action enum lists alphabetically.
- Ranked plans use consecutive integers starting at 1.

## Action And Owner Mapping

Prefer the action names allowed by the template:

- Notice/disclosure: `regulator_notice`, owner `legal` or notice-review target.
- Collection gaps: `supplemental_collection`, `vendor_retrieval`, `archive_validation`, `laptop_pst_forensics`, `teams_gap_assessment`.
- Device/source loss: `forensic_recovery`, `custodian_declaration`, `hold_refresh`.
- Coding and processing: `reprocess_qc`, `coding_correction`, `supplemental_production`, usually owner `review_vendor` or `e_discovery`.
- Privilege defects: `privilege_review`, `privilege_log_supplement`, `clawback_check`, `clawback_review`, `waiver_assessment`, usually owner `privilege_team`.
- Policy-only gaps: `no_action_policy_gap` or `no_action` when allowed.

Rank actions by urgency: required notice for post-hold loss first, then source preservation/collection needed before production, then QC/coding fixes, then privilege-log or privilege-review work, then policy logging or validation that is not production-blocking. Adjust when the prompt gives a nearer deadline or a required production-readiness sequence.

## Final Validation

Before returning:

1. Validate the JSON with `jq`.
2. Compare all keys against the template and remove unscored narrative fields.
3. Recheck arithmetic such as unlogged privilege counts, missing/recovered totals, and blocked category lists.
4. Confirm every included issue is supported by an API record or task-local payload fact.
5. Confirm no material deficient category or target custodian issue was missed.
