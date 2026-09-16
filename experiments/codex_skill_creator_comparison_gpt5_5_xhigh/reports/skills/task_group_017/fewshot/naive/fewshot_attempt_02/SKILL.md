---
name: investigation-review-hub-remediation
description: Solve Investigation Review Hub legal remediation tasks that require schema-conformant JSON for subpoena gap analyses, retention/preservation reviews, production readiness, privilege/QC blockers, and cross-system remediation dashboards.
---

# Investigation Review Hub Remediation

Use this skill when a task asks for a structured JSON answer from an Investigation Review Hub. The usual inputs are a prompt, one or more task-local payload files, and an `answer_template.json`; the business evidence must come from the running hub endpoints.

## Ground Rules

- Read the prompt and every file in `input/payloads/` before querying.
- Treat `answer_template.json` as the contract for top-level keys, required item keys, enum spellings, null/zero conventions, metrics, and ordering.
- Use task-local payloads only for scope, labels, matter ID, base URL, API header, and output schema. Use hub endpoints for matter facts, records, counts, statuses, and remediation actions.
- Do not inspect environment source files, database files, generated manifests, hidden notes, judge/admin endpoints, task answers, or evaluator code.
- Return exactly one JSON object and no prose. Use stable hub IDs exactly as they appear.

## Collect Hub Evidence

Resolve the base URL from the prompt or payload. If the task gives an API key header, send it on authenticated endpoints, especially SQL-style query endpoints.

You may use the bundled helper [scripts/fetch_hub.py](scripts/fetch_hub.py) to snapshot the allowed GET endpoints. From the skill package directory:

```bash
python3 scripts/fetch_hub.py "$TASK_ENV_BASE_URL" --matter-id "$MATTER_ID" --api-key "$API_KEY" --out /tmp/hub.json
```

Always inspect `/api/schema` first when available. Then collect the matter-specific records from these business endpoints when present:

- `/api/matters`
- `/api/subpoena-categories`
- `/api/productions`
- `/api/custodian-sources`
- `/api/documents/search`
- `/api/privilege-log`
- `/api/qc-findings`
- `/api/retention-events`
- `/api/remediation-actions`
- `/api/query`

If joins or counts are unclear from REST payloads, use `POST /api/query` after reading `/api/schema`. Query only business tables shown by the schema, filter by the requested `matter_id`, and keep the query read-only.

## Evidence Normalization

Build a compact issue model before filling the template. Preserve exact record IDs and category codes; sort category-code lists ascending.

Common issue treatments:

- Post-hold destruction, lost personal devices, deleted archives, or destroyed retained sources are preservation losses. Mark them as the strongest available preservation/source-lost status, usually critical or high, with disclosure as the lead action.
- Policy-compliant destruction before a legal hold is a low-risk retention event. Include it only when the schema asks for retention events or policy-loss actions; do not treat it as an open production blocker unless the hub says it should still exist.
- Uncollected personal email, phone, Signal/SMS, board, laptop, or custodian sources are collection or personal-source gaps. Count source records, not hypothetical documents, unless a hub record provides a document count.
- Available archives or retained alternative sources belong in `available_archives` or `retained_or_available_sources`. They can also support category coverage when the schema asks for remediation sources.
- Missing required records use the hub's missing/should-exist record as the anchor and normally require locating or audit follow-up.
- Responsive documents coded nonresponsive, zero-claim contradictions, or QC findings showing responsive misses are responsiveness miscoding issues. Include supporting document IDs plus the QC record, count the documents, and recommend recoding/production.
- Privilege-log gaps use withheld, logged, and unlogged counts from the hub. When only withheld and logged are given, compute `unlogged = max(withheld - logged, 0)`.
- Third-party privilege exceptions are waiver/exposure issues. Preserve the third-party label from the hub and count only the affected waiver documents or emails.
- Privilege miscoding and over-designation are privilege correction issues. Use QC or privilege records as anchors, and select the closest enum for recode, downgrade, or QC remediation.

## Fill The Schema

Use the template's field names, not generic names. Typical mappings:

- `critical_findings`, `top_risks`, or `issue_ledger`: one object per material open risk, blocker, gap, privilege correction, or required retention event. Anchor each object with the stable hub record ID that best represents the issue.
- `category_statuses`, `category_coverage`, or `readiness_statuses`: one object per category that is not complete/ready, plus archive-only categories when the schema asks for available remediation coverage.
- `privilege_corrections`: privilege-only blocker records such as incomplete logs, waivers, recoding, or over-designation.
- `available_archives` or `retained_or_available_sources`: available remediation sources and retained archives, sorted by source ID.
- `priority_actions` or `action_plan`: use hub remediation-action records when available. Otherwise infer actions from the normalized issue model and keep ranks deterministic.

For category rollups, aggregate all issue/source/action refs affecting the category. `open_issue_count` counts distinct issue or source records summarized for that category; supporting document IDs are refs, not separate open issues, unless the template defines the count as documents.

When several blockers affect one category, choose the enum that best communicates the operative production/readiness blocker:

- Use a mixed/multiple/incomplete enum when the template provides one and no single issue dominates.
- Use preservation/source-lost statuses for categories driven by post-hold loss.
- Use privilege-exposure or underproduced-privilege-correction statuses when waiver, log, or privilege miscoding issues drive readiness.
- Use source-gap-with-archive status when an uncollected/deleted communication source has an available archive path.
- Use archive-available/source-available status for categories whose main point is a retained remediation source.
- Use responsiveness-gap or underproduced when miscoded responsive documents are the direct production defect.

## Metrics

Compute metrics from the normalized records included in the answer, unless the template explicitly says to use all hub records.

- Count unique affected categories after sorting and deduplication.
- Count source gaps by source record, not custodian name.
- Count post-hold loss events by destroyed/lost event or source record.
- Count available archives by source record.
- Count responsive miscoding by affected document count.
- For privilege metrics named withheld/logged/unlogged privilege docs, count incomplete-log blockers only unless the template says to include waivers, over-designation, or miscoding.
- Count third-party waiver documents separately from incomplete-log metrics.
- Count privilege miscoding from QC/privilege-miscoding records.
- Use `0` for numeric fields that are not applicable and `null` for nullable strings/dates/components.
- Set production/readiness booleans to `false` if any included non-ready or open blocker remains.

## Action Prioritization

Prefer the hub's remediation-action ranks, owners, priorities, and due dates. If they are absent, infer a deterministic plan:

1. Preservation disclosures for post-hold/source-lost issues.
2. Waiver assessment and disclosure for third-party privilege exposure.
3. Recode and produce responsive misses or zero-claim contradictions.
4. Supplement incomplete privilege logs.
5. Privilege recode, downgrade, or QC remediation.
6. Collect uncollected personal/custodian sources.
7. Search or collect available archives.
8. Document policy-compliant pre-hold losses or monitor closed/no-gap records.

Choose the closest owner enum from the template: outside or litigation counsel for disclosures, privilege counsel/team for privilege issues, review QC/vendor for coding, forensics/client IT/eDiscovery for collection, records/compliance for retention and missing records.

## Final Checks

Before final output:

- Parse the JSON locally if possible.
- Confirm required top-level keys and item keys are present.
- Confirm all enum values appear in the template.
- Apply every ordering rule from the template.
- Verify counts reconcile with the hub records used.
- Ensure the answer contains no narrative prose, Markdown, comments, or unsupported fields.
