---
name: legal-production-review-json
description: Solve investigation API tasks that require structured JSON reviews of subpoena production, collection, retention, privilege, QC, and custodian deficiencies.
---

## Scope

Use this skill when a task asks for a JSON-only legal production, collection-readiness, retention/hold, privilege, QC, or custodian deficiency review using a shared investigation API. The goal is to produce a schema-conforming JSON object, not a narrative memo.

## Source Order

1. Read the task prompt and `input/payloads/answer_template.json` first. The template is the output contract: key order, required fields, enums, sorting rules, and when zero/empty values are allowed.
2. Read any task-local payloads named in the prompt. Treat them as factual supplements, especially for partner instructions, hold-notice omissions, source aliases, vendor details, and timing facts not obvious from the API.
3. Get the API base URL from the task instructions or `environment_access.md` if provided. Replace `<TASK_ENV_BASE_URL>` exactly.
4. Query the API as the source of record for matter metadata and evidence records. Most list endpoints return `{"count": n, "items": [...]}`; use `.items`. The search endpoint returns a `results` object grouped by collection, so use it for discovery and endpoint-specific calls for counts.

## API Checklist

For a matter-level task, inspect the relevant subset of:

- `/api/matters/{matter_id}`
- `/api/subpoena_categories?matter_id={matter_id}`
- `/api/production_logs?matter_id={matter_id}`
- `/api/collection_events?matter_id={matter_id}`
- `/api/retention_rules?matter_id={matter_id}`
- `/api/destruction_events?matter_id={matter_id}`
- `/api/custodians?matter_id={matter_id}`
- `/api/documents?matter_id={matter_id}`
- `/api/privilege_logs?matter_id={matter_id}`
- `/api/qc_events?matter_id={matter_id}`
- `/api/search?matter_id={matter_id}&q={term}`

Useful command pattern:

```bash
BASE="$(sed -n 's/^GDPEVO_ENV_BASE_URL=//p' environment_access.md)"
curl -fsS "$BASE/api/matters/MATTER-ID" | jq .
curl -fsS "$BASE/api/production_logs?matter_id=MATTER-ID" | jq '.items'
```

## Analysis SOP

Build a crosswalk by `category_id`, `custodian_id`, source name/type, event/log ID, and document ID. Start from subpoena categories, then attach production counts, collection status, retention/destruction facts, custodian known gaps, documents, privilege records, and QC events.

Use explicit API count fields whenever possible: `produced_count`, `withheld_privileged_count`, `privilege_logged_count`, `record_count`, `affected_count`, `failed_count`, `recovered_count`, `collected_count`, `missing_count`, and `quantity`. Do not invent counts. Use `0` only when the template says to, when a field is inapplicable, or when the source record explicitly supports zero.

Include only material blocked or deficient categories unless the template expressly asks for ready or note-only statuses. Exclude categories with no material gap, stale/noisy records, or merely background facts.

## Classification Rules

Post-hold source loss, destruction, laptop wipe, or shared-drive deletion is usually critical. It can require regulator notice, forensic recovery, custodian declarations, and supplemental collection. Rank disclosure or notice review first when the template includes it.

Pre-hold policy destruction is usually a policy gap, not spoliation. Classify separately from post-hold problems, usually with no regulator notice and a documentation/no-action-policy action unless the template says otherwise.

Uncollected personal email, personal phone, SMS, personal cloud text, Teams, archive, vendor portal, or local PST sources usually block production until supplemental collection, hold refresh, archive validation, vendor retrieval, gap assessment, or forensics are complete. Hold-notice omissions support `hold_refresh` and may create a blocked hold-notice status even before data loss is proven.

Recoverable archive or retained-missing sources are generally remediation items, not disclosure events, unless paired with post-hold destruction or a notice defect. Within-retention available sources may be `ready_with_retention_note` or `no_action` if the schema asks to list them.

Privilege log gaps are measured by comparing withheld privileged counts to logged counts. When the schema asks for unlogged privilege, calculate `withheld_privileged_count - privilege_logged_count` for the affected category.

Overdesignation is suggested by business-only or non-legal material withheld as privileged, all-withheld counsel categories, or explicit overdesignation flags. The primary action is usually privilege review, possible production of nonprivileged/business-only material, and privilege-log correction.

Privilege miscoding occurs when privileged material was coded nonprivileged or produced. Use clawback review/check, privilege review, and waiver assessment as the template allows. Third-party forwarding or explicit waiver risk supports waiver assessment.

Review coding errors include responsive documents coded nonresponsive, stale coding, family/document handling problems, or zero production despite responsive material. Use coding correction, QC reprocessing, and supplemental production according to the available enum set.

Processing failures such as corrupt or password-protected attachments are processing exceptions. Count failed, recovered, and unrecovered items separately when the template asks, and use reprocess/QC actions.

## Output Rules

Return JSON only. Use the template's exact top-level key order and required nested keys. Do not add narrative fields, comments, markdown, or schema metadata.

Use exact enum casing from the template. If two examples use similar concepts with different enum names, choose only the enum available in the current template.

Sort every list as instructed. Common defaults are category IDs ascending, document IDs ascending, issue IDs lexicographic, action IDs ascending, and rank lists by consecutive integers starting at 1. Sort action-code lists alphabetically when required.

Use stable, descriptive IDs only where the schema expects free-form IDs. Reuse fixed enum IDs when the schema enumerates allowed issue IDs. Keep action ranks aligned with severity: notice/disclosure and critical post-hold loss first, then recovery/supplemental collection, QC/coding fixes, privilege-log supplements, overdesignation review, and policy-note items.

Set overall readiness or status from the most severe unresolved issue. Any production-blocking source gap, hold-notice defect, privilege-log gap, or QC/coding defect should prevent a clean `ready` status unless the template has a narrower readiness concept.

Validate before finalizing:

```bash
jq . answer.json >/dev/null
```

Then re-check required keys, enum spellings, integer counts, booleans, sorting, and that no non-material categories were added.
