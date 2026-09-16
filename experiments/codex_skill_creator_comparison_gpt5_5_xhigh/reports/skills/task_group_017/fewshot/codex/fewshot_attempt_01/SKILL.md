---
name: investigation-review-json
description: Build schema-conforming JSON answers for Investigation Review Hub legal review tasks. Use when a prompt asks Codex to analyze subpoena, grand jury, SEC, DOJ, production-readiness, retention, preservation, privilege-log, QC, custodian-source, remediation, or cross-system dashboard evidence from a running Investigation Review Hub and return a single structured JSON object.
---

# Investigation Review JSON

## Core Workflow

1. Read the user prompt, `input/payloads/answer_template.json`, and any task-local context payloads before querying the hub.
2. Treat the running Investigation Review Hub and task-local payloads as the only business evidence. Do not inspect environment source files, database files, generated manifests, answer files, or evaluator files.
3. Identify the matter ID, hub base URL, required top-level keys, enum choices, field types, and ordering rules from the prompt and template.
4. Fetch matter-scoped hub evidence from schema, matters, categories, productions, custodian sources, documents, privilege log, QC findings, retention events, and remediation actions. Prefer the bundled snapshot helper:

```bash
python3 skill/scripts/hub_snapshot.py --base-url "$TASK_ENV_BASE_URL" --matter-id "$MATTER_ID" --api-key review-key-017 > /tmp/hub_snapshot.json
```

If the task gives a different API key or says no key is needed, pass the task value or omit `--api-key`.

5. Build the answer directly from the template. Include every required key, use only allowed enum values, fill non-applicable counts with `0`, fill unavailable strings with `null` when the schema allows it, and return exactly one JSON object with no prose.

## Evidence Review

Read [review_patterns.md](references/review_patterns.md) when mapping hub records into legal review findings, category rollups, metrics, or actions.

When reviewing the snapshot, inspect these record families:

- `retention_events`: post-hold losses, pre-hold policy destructions, missing required records, active system losses, auto-purge windows, available archives, record volumes, hold dates, and affected categories.
- `custodian_sources`: destroyed, lost, partial, not-collected, personal, board, archive, shared-drive, laptop, email, messaging, Teams, and offsite sources.
- `review_documents` and `qc_findings`: responsive documents miscoded nonresponsive, zero-claim contradictions, privileged documents miscoded nonprivileged, missing required records, and production coding defects.
- `privilege_entries`: withheld counts, logged counts, unlogged deltas, third-party waiver indicators, over-designation, privilege miscoding, and category impacts.
- `production_stats`: category-level production state, zero-claim reasons, responsive counts, withheld counts, and nonresponsive counts.
- `remediation_actions`: stable action IDs, owners, priorities, target references, due days, and action types. Use these when they exist and match the template.

## Answer Assembly

- Anchor each material issue to the most specific stable hub ID available, such as a retention event, source, privilege entry, QC finding, or document.
- Keep supporting reference lists sorted ascending unless the template says otherwise.
- Include only material non-ready categories or categories with open gaps unless the template explicitly asks for complete/no-gap categories.
- Aggregate multiple blockers for the same category into one category status when the schema has a mixed or multiple-blocker enum.
- Calculate metrics from the same selected issue records used in the answer body. Counts must reconcile with the listed risks, corrections, sources, or categories.
- Prioritize critical post-hold source loss and government disclosure before collection, recoding, privilege-log supplementation, waiver assessment, archive search, and monitor/no-action items, unless hub action ranks say otherwise.
- Validate the final object against the template manually before answering: required keys present, no extra enum labels, all required item fields present, numeric fields are integers, booleans are booleans, arrays sorted as directed.
