---
name: investigation-review-hub
description: Use for legal investigation review tasks that require structured JSON from an Investigation Review Hub, including production gap analysis, retention and litigation-hold loss review, SEC/DOJ remediation dashboards, privilege-log/QC production-readiness reviews, and cross-system action plans based on hub endpoints plus task-local answer templates.
---

# Investigation Review Hub

## Workflow

1. Read the task prompt and every task-local payload, especially `answer_template.json` and any `request_context.json`, `review_scope.json`, or `matter_context.json`.
2. Treat `answer_template.json` as the output contract. Preserve required top-level keys, item keys, enum values, nullability, ordering rules, and numeric precision exactly. Return one JSON object only.
3. Use only the task-local payloads and the running Investigation Review Hub. Do not inspect environment source, database files, generated data files, hidden manifests, task answers, or evaluator files.
4. Determine the hub base URL from the task. If the prompt uses `<TASK_ENV_BASE_URL>`, use the environment access information supplied with the task only to get the base URL. Use any task-provided SQL API header exactly as given.
5. Pull all hub evidence for the requested `matter_id`. Prefer [scripts/fetch_hub_matter.py](scripts/fetch_hub_matter.py) when SQL access is available. Run it from the skill package directory, or replace the script path with the resolved path to the skill resource:

```bash
python scripts/fetch_hub_matter.py --base-url "$TASK_ENV_BASE_URL" --matter-id "$MATTER_ID" --api-key "$API_KEY" > hub.json
```

If SQL is unavailable, call the listed REST endpoints and filter rows by `matter_id` locally.

## Hub Evidence Model

Expect these recurring evidence families:

- Matter metadata: agency, investigation type, issued date, hold date, status.
- Subpoena/request categories: category codes, labels, date ranges, topics.
- Production stats: produced, withheld, responsive, nonresponsive, status, zero-claim notes.
- Custodian sources: source type, status, event date, post-hold flag, category impacts, issue tags.
- Review documents: responsiveness, privilege status, produced status, category, issue tags, summaries.
- Privilege entries: withheld/logged counts, issue type, third-party flag, category, notes.
- QC findings: issue type, severity, document count, affected category, source reference.
- Retention events: event date, hold date, policy section, volume, status, affected categories, source ref.
- Remediation actions: action type, priority, severity, owner, target refs, due days.

Parse category-impact fields and issue-tag fields as structured lists when possible; otherwise split conservatively on commas or semicolons. Keep stable hub IDs exactly as emitted.

## Materiality Filter

Hub tables can contain noisy routine rows, metadata gaps, family-member records, similar labels from other matters, and ordinary collection variance. Do not promote a row merely because a status is imperfect or a count differs. Treat an item as material when it is supported by the task focus plus at least one strong signal:

- a retention, source, privilege, QC, document, or remediation row has an issue type/tag/note that matches the requested review;
- a remediation action targets the record;
- a QC finding or reviewed document directly contradicts a production status or zero-production claim;
- the row is an available archive/source that the prompt asks to report as a remediation path;
- related rows across tables support the same category, source, or privilege defect.

Ignore routine, closed, duplicate, metadata-only, and unrelated-category rows unless the template explicitly asks to report them.

## Classify Material Issues

Use the template enum names, but map evidence consistently:

- Post-hold destruction or loss: `post_hold_loss`, `preservation_failure`, `source_lost`, `destroyed`, `critical` or `high`, usually `disclose_preservation_issue`.
- Pre-hold policy destruction: `policy_destroyed_pre_hold`, `low`, normally `no_action_policy_loss` unless the template asks only for open production blockers.
- Missing required record: `should_exist_missing` or `missing_required_record`, action `locate_missing_record`.
- Uncollected personal or side-channel source: `personal_source_gap`, `collection_gap`, `not_collected` or `partial_collection`, action `collect_personal_device` or source-specific collection. Require a material issue tag, action, or cross-table support; do not escalate ordinary tracker variance.
- Available archive or retained source: include in retained/available-source sections when it is a remediation path; classify as `archive_available`, `available_archive`, `available`, or `preserved_available` as the template permits, action `search_archive` or `collect_archive`, and do not treat as an irretrievable loss by itself.
- Responsive material coded nonresponsive, zero-production contradiction, or QC responsiveness finding: classify as `responsiveness_miscode`, `responsive_miscoding`, or `zero_claim_contradiction`; count supporting documents; action `recode_and_produce`.
- Privilege-log gap: issue type, notes, QC, or action indicate incomplete log. Then calculate `unlogged_count = max(withheld_count - logged_count, 0)`. Do not infer an escalated log gap from withheld/logged differences alone when the row is labeled clean, family mismatch, routine, or outside the prompt scope.
- Third-party privilege issue: third-party flag/name or notes show disclosure to a non-privileged recipient; classify as `third_party_waiver`, production impact `privilege_exposure`, action `waiver_assessment_and_disclosure`.
- Privilege miscoding or over-designation: QC or privilege notes show privileged documents coded nonprivileged, business-only counsel-copy overdesignation, downgrade, or recode needs; action `privilege_recode_and_log` or `qc_remediation` according to the template enums.

Include only material issues requested by the prompt and schema. Keep closed/no-gap categories out unless the template explicitly requests complete coverage.

## Build Output Sections

- Risk or issue ledgers: anchor each item on the most specific stable hub ID. Add supporting `source_refs` or `record_refs` for documents, QC findings, privilege entries, retention events, and sources. Use 0 for non-applicable counts when the schema says integer; use `null` only where the schema allows it.
- Category coverage/statuses: aggregate all open material blockers per category. Choose the status and production impact that best reflect the highest-severity blocker; use a multi-blocker enum when available. Sort supporting refs and category lists.
- Retained or available sources: report sources that remain remediation paths or limit loss. `limits_loss_for_categories` should be the intersection of affected categories and categories the source can remediate.
- Metrics: calculate from the selected evidence, not from prose. Count unique events/sources/categories where the metric name asks for events, sources, or categories. Do not double-count the same issue through both a QC finding and its source document unless the metric asks for documents.
- Actions: use hub remediation actions when they match the schema. Otherwise synthesize a minimal grouped action plan from the material issues, ordered by urgency.

## Ranking and Owners

Rank preservation disclosures for post-hold losses first, then waiver/exposure issues, recode-and-produce blockers, privilege-log supplementation, collection of missing sources, archive searches, and low-risk documentation/no-action items. Prefer owner values already present in remediation actions; otherwise map actions to common owners:

- disclosure or readiness hold: outside counsel or litigation counsel
- forensic or personal-device collection: forensics, eDiscovery vendor, or client IT
- review coding/QC: review QC or review vendor
- privilege log, waiver, recode: privilege team or privilege counsel
- records retention or missing business records: records management or compliance audit

Always choose an enum value allowed by the template.

## Final Checks

- Validate every enum, required key, count, boolean, `null`, and list against `answer_template.json`.
- Apply all ordering rules from the template, including sorting IDs and category codes inside arrays.
- Ensure `production_ready` or `rolling_production_ready` is false when any material open blocker remains.
- Remove analysis notes and return exactly one JSON object with no Markdown or prose.
