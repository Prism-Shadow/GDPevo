---
name: investigation-review-hub-remediation
description: Use this skill whenever a task asks for a structured JSON legal review, production-readiness review, retention or preservation gap analysis, privilege/QC remediation dashboard, or subpoena response dashboard using the Investigation Review Hub. It is especially relevant when the prompt mentions matter IDs, subpoena categories, custodial sources, retention events, privilege logs, QC findings, remediation actions, or an answer_template.json that must be followed exactly.
---

# Investigation Review Hub Remediation

Use this skill to produce a single JSON object for legal review tasks backed by the Investigation Review Hub. The common task pattern is: read the local prompt and payloads, query the shared hub for the requested matter, identify material source, retention, privilege, responsiveness, and QC blockers, then fill the provided `answer_template.json` exactly.

## Source Rules

Use only the task prompt, task-local payload files, and the running Hub API named in the prompt or payload. Do not inspect environment source files, database files, generated manifests, hidden notes, answer files, evaluator files, or unrelated local data.

If the task provides a base URL placeholder such as `<TASK_ENV_BASE_URL>`, substitute the actual Hub base URL from the task environment. If the task provides an API key for SQL-style access, send it as `X-API-Key: review-key-017` unless the payload specifies a different header/value.

## First Pass

1. Read the prompt and every payload in `input/payloads/`, especially `answer_template.json`.
2. Extract the `matter_id`, expected output sections, enum choices, required keys, ordering rules, and numeric precision rules from the template.
3. Query the Hub for the matter evidence. The safest generic method is the SQL endpoint:

From this skill package directory, run:

```bash
python scripts/hub_snapshot.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --matter-id "$MATTER_ID" \
  --api-key review-key-017 \
  --output /tmp/hub_snapshot.json
```

If you do not use the helper, fetch `/api/schema` and then query these logical tables for the target matter: `matters`, `subpoena_categories`, `production_stats`, `custodian_sources`, `review_documents`, `privilege_entries`, `qc_findings`, `retention_events`, and `remediation_actions`.

4. Build a matter-specific evidence map keyed by stable Hub IDs: category codes, source IDs, document IDs, privilege entry IDs, QC finding IDs, retention event IDs, and remediation action IDs.
5. Read `references/review_mapping.md` for classification, metric, and action-ranking rules before writing the JSON.

## Evidence Interpretation

Treat Hub record IDs as the answer anchors. Prefer the stable ID of the record that directly proves the issue:

- retention loss or missing record: retention event ID
- source collection gap, destroyed source, or available archive: source ID
- responsiveness or zero-production contradiction: QC finding ID plus the affected document IDs
- privilege log gap, waiver, or privilege exception: privilege entry ID
- privilege miscoding: QC finding ID plus related privilege entry ID when present
- action plan item: remediation action ID when the output schema includes action IDs

Include only material, current blockers unless the template asks for all retention events or all available archives. Material blockers include post-hold loss, destroyed or lost sources, not-collected personal or board sources, partial personal collections, missing required records, contradicted zero-production claims, responsive documents coded nonresponsive, incomplete privilege logs, third-party privilege waiver, and privilege miscoding.

Policy-compliant pre-hold destruction is usually low risk. Include it only when the task is a retention/preservation review or the template explicitly has fields for policy losses.

## Output Assembly

Follow the template, not the examples in memory. Use exactly the top-level keys, object keys, enum labels, nullability, count fields, and ordering rules in `answer_template.json`.

Use whole integers for counts. Use `0` when a numeric field is required but the concept is not applicable, and `null` when the template explicitly allows unknown or inapplicable dates, periods, third parties, missing components, or source references.

Sort as the template requires. If no rule is given, sort stable IDs and category sets ascending, and sort priority lists by rank with 1 as highest priority.

Return only the JSON object. Do not include prose, markdown fences, citations, or explanation outside the JSON.
