---
name: investigation-review-hub-remediation-json
description: Solve Investigation Review Hub legal production, preservation, privilege, QC, retention, and remediation dashboard tasks as exact structured JSON.
---

# Investigation Review Hub Remediation JSON

Use this skill when a task asks for a structured JSON gap analysis, production-readiness review, retention review, or remediation dashboard using the Investigation Review Hub.

## Boundaries

- Return exactly one JSON object matching `input/payloads/answer_template.json`; do not include prose outside the JSON.
- Use only the task prompt, task-local payloads, and the Investigation Review Hub endpoints named by the task environment.
- Do not inspect local environment source files, database files, generated manifests, hidden notes, answer files, judge/admin endpoints, or evaluator code.
- Treat hub record IDs as authoritative. Do not invent matter, source, event, QC finding, document, privilege, action, or category IDs.

## First Pass

1. Read the prompt, `answer_template.json`, and every task-local context payload.
2. Extract the `matter_id`, environment base URL, authentication header, requested deliverable type, and any category labels supplied locally.
3. Read the answer template as the output contract: required keys, enum values, ordering rules, required fields, numeric precision, nullability, and whether the task wants only blockers or also policy-compliant/non-action records.
4. Query the hub for the target matter across all business evidence domains before drafting the answer.

Useful hub tables and endpoint domains usually include:

- `matters`: hold date, agency, matter status, and matter metadata.
- `subpoena_categories`: category codes, date ranges, topic tags, and request text.
- `production_stats`: batch/category counts, production status, zero-claim reasons, and withheld/responsive/nonresponsive counts.
- `custodian_sources`: custodian/source status, event date, post-hold flag, affected categories, issue tags, and source notes.
- `review_documents`: document-level responsiveness, privilege status, production status, issue tags, summary, and category.
- `privilege_entries`: withheld/logged counts, privilege issue type, third-party indicators, category, and notes.
- `qc_findings`: QC issue type, document count, affected category, source reference, severity, and notes.
- `retention_events`: retention status, dates, policy section, retention period, volume, affected categories, source reference, and notes.
- `remediation_actions`: recommended action type, priority, severity, owner, target reference, due days, and description.

Prefer the read-only SQL endpoint for complete joins and filtering. A working request shape is:

```sh
curl -sS -H "X-API-Key: <API_KEY>" -H "Content-Type: application/json" \
  -d '{"sql":"select * from <table> where matter_id = ?","params":["<MATTER_ID>"]}' \
  "$BASE_URL/api/query"
```

Do not query internal catalog tables; use `GET /api/schema` for schema discovery.

## Evidence Sweep

Collect and normalize all rows for the target matter before selecting material findings:

- Categories: build a category-code set from `subpoena_categories` and local payload labels. Sort codes lexicographically in all output arrays.
- Sources: parse source status, `post_hold`, source type, event date, issue tags, and category impacts. Split category-impact text into uppercase category codes.
- Documents: identify responsive documents coded nonresponsive and not produced, privileged documents coded nonprivileged, withheld documents, and documents referenced by QC findings.
- Privilege: compute `unlogged_count = max(withheld_count - logged_count, 0)` for incomplete-log issues. Treat third-party privilege entries as waiver/exposure issues even when logged.
- QC: use QC findings to anchor miscodes, zero-claim contradictions, privilege miscoding, over-designation, and production coding quality defects. Include linked document IDs from `source_ref` or matching document rows when the template asks for supporting refs.
- Retention: separate pre-hold policy destruction, post-hold loss, active-system loss, auto-purge gaps, should-exist-missing records, and available archives. Use hub status as authoritative; compare dates to hold date only to resolve ambiguity.
- Actions: read remediation candidates and use their target refs, owners, priorities, severities, and due days when they correspond to selected findings.

## Materiality And Classification

Match the template’s vocabulary exactly. These reusable mappings are the usual starting point:

- Post-hold destruction or loss: preservation/post-hold-loss issue, open status, destroyed/lost source status, source-lost production impact, highest disclosure priority.
- Policy-compliant pre-hold destruction: policy-destroyed status, low risk, no-action policy loss when the template asks for all retention events; omit from blocker-only dashboards.
- Not-collected personal or business source: collection/personal-source gap, open or not-collected status, source-missing impact, collection action.
- Available archive or retained source: remediation-available/archive-available status, source-available impact, search or collect archive action; include in retained/available-source sections even if it mitigates a loss.
- Deleted channel, active system loss, or auto-purge: communication/system gap. Include cutoff dates, purge windows, and archive exception sources when the template has those fields.
- Missing required record: should-exist-missing/missing-required-record status, missing-record impact, locate-missing-record action.
- Responsive document coded nonresponsive or zero-claim contradicted by documents/QC: responsiveness-miscode issue, needs-recode/confirmed status, not-produced or underproduced impact, recode-and-produce action.
- Incomplete privilege log: privilege-log-gap issue, protocol-noncompliant/incomplete-log status, withheld-unlogged impact, supplement-log action.
- Third-party privilege disclosure: third-party-waiver issue, waived/protocol-noncompliant status, privilege-exposure impact, waiver-assessment action; preserve the third-party label if the template has a field for it.
- Privileged documents coded nonprivileged or privilege QC failures: privilege-miscoding/QC issue, needs-recode/confirmed status, privilege-exposure impact, privilege recode/log or QC remediation action.
- Over-designation or business-only counsel-copy issues: lower-priority privilege correction unless the template classifies them as a readiness blocker.

When more than one material blocker affects a category, use the template’s mixed or multiple-blocker status if available. Otherwise choose the status for the most urgent production impact, and include all supporting refs.

## Template Families

Use the answer template to decide which family applies:

- First rolling gap analysis: populate material `critical_findings`, non-complete `category_statuses`, rollup `metrics`, and `priority_actions`. Typical finding anchors are lost/destroyed sources, uncollected sources, incomplete privilege logs, and document/QC responsiveness defects. Category statuses should union all supporting refs for that category.
- Retention and hold gap review: populate `retention_events` from all relevant hub retention rows, including low-risk policy-compliant losses when requested. Populate `communication_gaps` only for active-system, messaging, purge, or deleted-channel gaps. Populate `available_archives` from available archive/source rows. Count pre-hold and post-hold losses separately using status, hold date, and volume fields.
- Cross-system remediation dashboard: populate ranked `top_risks`, `category_coverage`, `retained_or_available_sources`, dashboard `metrics`, and `action_plan`. Include only material open/remediation risks in `top_risks`; put available archives or retained sources in the source section even when they are not negative risks.
- Production-readiness review: populate only non-ready `readiness_statuses`, a material `issue_ledger`, privilege-specific `privilege_corrections`, readiness `metrics`, and `priority_actions`. Keep privilege correction rows separate from general issue rows when both sections exist.

## Output Construction

- Use the exact top-level keys and field names from the task template.
- Include only categories requested by the template. Gap/readiness templates usually exclude fully ready categories; retention templates may require every retention event, including low-risk policy losses.
- For each issue or risk, choose the stable hub record ID that anchors the problem as the primary ID. Add supporting record IDs in the relevant refs list.
- Sort lists exactly as the template says. If no explicit rule is present, sort record refs and category code arrays ascending; sort action plans by priority/rank.
- Use integers for counts. Use `0` when a count field is required but not applicable; use `null` only when the template allows a missing date, policy, third party, or component.
- For `withheld_count`, `logged_count`, and `unlogged_count`, use the counts for the selected privilege blocker unless the template explicitly asks for all privilege issues. Do not add waiver or over-designation counts into incomplete-log metrics unless the field description includes them.
- `document_count` should be the number of affected documents for document/QC/privilege records, not the number of supporting refs.
- `volume_count` and `volume_unit` come from retention/source evidence when available; otherwise use the template’s not-applicable convention.
- `affected_category_count` and similar metrics count unique category codes in the selected open/material risks, not all subpoena categories.
- Boolean production/readiness fields are `false` if any selected blocker prevents production and `true` only when no material blockers remain.

## Action Ranking

Use hub remediation rows when available. If the output requires derived or grouped actions, apply this priority order:

1. P0: disclose post-hold preservation loss/source destruction or place production-readiness hold.
2. P1: waiver assessment/disclosure, supplement privilege log, recode and produce confirmed responsive material, remediate privilege miscoding, collect missing personal/source data, search available archives.
3. P2: lower-risk privilege over-designation, custodian follow-up, documentation of non-critical system gaps, policy-compliant losses with no remediation.
4. P3: monitor-only or no-current-gap actions.

Owners usually follow the action type: disclosure and production holds to outside/litigation counsel; forensic or personal-device collection to forensics/eDiscovery; archive collection/search to eDiscovery; privilege log and over-designation work to the privilege team; waiver assessment to privilege counsel; responsiveness and coding remediation to review QC; missing audits/records to compliance or records management; system purge documentation to IT or messaging owners.

For dashboard `due_days`, preserve hub values when present. If a due date must be derived, use short deadlines for disclosure and waiver assessment, moderate deadlines for recoding/log supplementation/QC, and longer deadlines for source collection or archive search.

## Final Validation

Before returning, check:

- The JSON parses and has no comments, markdown, or trailing commas.
- Every required top-level key and required item key is present.
- All enum values are copied exactly from `answer_template.json`.
- All refs are real hub IDs from the gathered evidence.
- Category arrays and refs are sorted.
- Metrics reconcile with the included issue/risk/action records.
- The response contains no task-analysis notes or hidden evidence descriptions beyond fields required by the template.
