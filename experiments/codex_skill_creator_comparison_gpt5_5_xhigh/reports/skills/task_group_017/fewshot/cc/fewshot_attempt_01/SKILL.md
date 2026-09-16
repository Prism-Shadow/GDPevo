---
name: investigation-review-hub-remediation-json
description: Use this skill whenever a task asks for a structured JSON gap analysis, production-readiness review, retention/preservation review, or cross-system remediation dashboard from an Investigation Review Hub. It is tailored for legal subpoena or regulatory-review matters where the answer must use hub record IDs, request category codes, privilege/QC/retention/source evidence, numeric metrics, prioritized actions, and a provided answer_template.json.
---

# Investigation Review Hub Remediation JSON

Use this skill for one-pass legal review tasks that require a JSON-only answer from an Investigation Review Hub. The recurring job is to gather all matter-scoped hub records, identify material production or preservation blockers, normalize them into the task's template enums, compute metrics, and return exactly one JSON object.

## Source Discipline

Use only sources allowed by the prompt:

- The task-local prompt and payloads, especially `answer_template.json`.
- The running hub endpoints named by the prompt or payloads.
- The read-only SQL endpoint when supplied.

Do not inspect local environment source, database files, seed files, generated manifests, hidden notes, evaluator files, or answer files. Treat the hub as source of record for matter facts. Task-local payload files may define client context, category labels, endpoint names, and output schema, but business evidence should come from the hub unless the prompt says otherwise.

## Fast Evidence Collection

First read the prompt, every task-local payload, and the answer template. Extract:

- `matter_id`
- hub base URL
- any query API key header
- required top-level keys
- enums, field names, ordering rules, and numeric precision rules

Then gather matter-scoped records from the hub. If Python is available, run the bundled helper at [scripts/fetch_review_hub.py](scripts/fetch_review_hub.py):

```bash
python <skill_dir>/scripts/fetch_review_hub.py MTR-EXAMPLE --base-url "$TASK_ENV_BASE_URL" --api-key '<prompt-provided-key>' --out hub_evidence.json
```

Use the actual matter ID, base URL, and skill directory path for the run. If the task does not require or provide SQL access, omit `--api-key`; the helper will fall back to REST where possible. If not using the helper, fetch the same evidence yourself:

- `GET /api/schema`
- `GET /api/matters`
- `GET /api/subpoena-categories?matter_id=<matter_id>`
- `GET /api/productions?matter_id=<matter_id>`
- `GET /api/custodian-sources?matter_id=<matter_id>`
- `GET /api/documents/search?matter_id=<matter_id>`
- `GET /api/privilege-log?matter_id=<matter_id>`
- `GET /api/qc-findings?matter_id=<matter_id>`
- `GET /api/retention-events?matter_id=<matter_id>`
- `GET /api/remediation-actions?matter_id=<matter_id>`

Prefer SQL for full row sets when document search is capped:

```sql
select * from review_documents where matter_id = '<matter_id>' order by doc_id;
```

The hub tables observed in these tasks are `matters`, `subpoena_categories`, `production_stats`, `custodian_sources`, `review_documents`, `privilege_entries`, `qc_findings`, `retention_events`, and `remediation_actions`.

## Materiality Pass

Build an internal issue set before filling the template. Do not blindly include every noisy row. Select records that create a real production, preservation, privilege, collection, or readiness blocker:

- Post-hold source loss, destroyed sources, lost personal devices, deleted channels, or records destroyed after hold.
- Uncollected personal sources, important board/shared/collaboration sources, or other sources explicitly described as scoped but not collected.
- Required records marked missing or `should_exist_missing`.
- Available archives or retained sources that can remediate a selected gap.
- Privilege log blockers where `withheld_count > logged_count`, `issue_type` shows incomplete log, or protocol noncompliance is described.
- Third-party privilege/waiver issues where a privilege record identifies third-party sharing or waiver exposure.
- Privilege over-designation, privilege miscoding, or nonprivileged/privileged coding defects when the prompt asks for privilege corrections or QC readiness.
- Responsiveness miscoding or zero-claim contradictions where documents are responsive but coded nonresponsive, not produced, or contradicted by QC/document evidence.
- High or critical QC findings, especially miscoding and production-impacting errors.
- Retention events with statuses such as post-hold loss, active system loss, auto-purge, policy-destroyed-pre-hold, or missing required records when the prompt asks for retention analysis.

Exclude rows that are only routine noise unless the template requires them: ordinary metadata cleanup, duplicate/family variance, low-severity sampling, "similar labels across matters", "not immediate remediation", and closed/non-impacting records.

## Classification Heuristics

Use the template's enum names exactly. Map evidence to the closest provided enum rather than inventing values.

- `lost`, `destroyed`, post-hold erasure, or post-hold retention loss -> preservation/post-hold loss; production impact usually `source_lost`; action usually disclosure or recovery if available.
- `not_collected` personal phone, personal email, Signal/SMS, board portal, shared/collaboration source -> collection or personal-source gap; impact `source_missing`; action collection.
- Available archive, retained archive, backup, or retained source -> availability/remediation source; action search, collect, or restore archive.
- `incomplete_log` with withheld greater than logged -> privilege log gap; `unlogged = withheld - logged`.
- Third-party flag or notes identifying disclosure outside privilege circle -> waiver/third-party waiver; include the third party string when the template has that field.
- QC `miscoded_nonresponsive`, `responsive_miscoding`, zero-claim contradiction, or document summary saying responsive but coded nonresponsive/not produced -> responsiveness gap; action recode and produce.
- QC privileged documents coded nonprivileged or equivalent notes -> privilege miscoding; action privilege recode/QC remediation.
- Over-designated privilege, business-only counsel copy, downgrade, or nonprivileged material withheld -> privilege correction/QC remediation, usually lower than waiver and log gaps.
- Policy destruction before hold -> low-risk/policy-compliant loss; action may be no action or document system gap.
- Auto-purge or active system loss after/around hold -> communication gap; action document, disclose, or collect archive depending on available remediation.

When multiple selected blockers affect one request category, use the template's composite status if present, such as multiple blockers, mixed preservation and missing record, source gap with archive available, or underproduced privilege corrections. Otherwise choose the dominant production impact by severity: source lost, source missing, privilege exposure/withheld unlogged, not produced/underproduced, missing record.

## Metrics

Compute metrics from the selected material issue set unless the template explicitly says to count all records of a type.

- Privilege unlogged count is `withheld_count - logged_count` for selected incomplete-log blockers.
- Waiver count comes from selected third-party/waiver privilege records.
- Miscoded responsive count comes from selected QC/document evidence that supports responsiveness miscoding.
- Miscoded privileged count comes from selected privilege/QC coding defects.
- Post-hold loss count counts selected loss events or selected destroyed post-hold source/retention records, matching the template wording.
- Personal-source counts count selected uncollected/partial personal sources by source type and status.
- Available archive count counts selected archive/remediation sources, not every benign available source.
- Category counts should be the count of unique request category codes in selected material gaps.
- Use `0` for integer fields that are not applicable and `null` only where the template allows null.

If the answer asks for production readiness, set readiness booleans false when any selected blocker remains open. If no material blocker remains and the template supports ready/no-gap statuses, include only categories the template asks for.

## Action Plan

Use hub remediation-action records as evidence, but normalize action labels and owners to the answer template. When a hub action label is operationally similar but not an enum, map it to the closest allowed action. If needed, synthesize stable action IDs following the template's pattern, but target existing hub record IDs.

Priority order:

1. Critical source loss, post-hold destruction, or required disclosure.
2. Waiver exposure and privilege protocol noncompliance.
3. Responsiveness miscoding that caused underproduction.
4. Privilege log supplementation or privilege recoding.
5. Collection of personal or missing sources.
6. Archive search/restore and lower-risk documentation.
7. Policy-compliant pre-hold loss/no-action items.

Owners should follow the template enums: outside counsel/litigation counsel for disclosure, forensics or eDiscovery vendor for personal-source collection/recovery, privilege team or privilege counsel for log/waiver issues, review QC/review vendor for coding defects, records management/compliance audit for retention records.

## Output Assembly

Fill the template exactly:

- Include every required top-level key in the order implied by the template.
- Include every required item key, even when the value is `0`, `[]`, or `null`.
- Use stable hub IDs exactly as written for matters, categories, documents, privilege entries, QC findings, sources, retention events, and actions.
- Sort lists according to the template. Sort category-code arrays and reference arrays ascending unless the template says operational priority.
- Do not include explanatory prose, markdown fences, citations, comments, or extra keys unless the template requires them.
- Validate the final object as JSON before returning it.

Before finalizing, cross-check each selected issue against at least one hub record ID and verify that all counts can be traced to selected records or explicit template instructions.
