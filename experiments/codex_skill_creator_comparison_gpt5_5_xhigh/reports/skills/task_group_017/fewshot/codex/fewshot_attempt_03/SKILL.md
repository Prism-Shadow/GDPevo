---
name: review-hub-remediation
description: Build schema-conforming Investigation Review Hub gap, retention, production-readiness, and remediation dashboard JSON outputs. Use when a task provides an Investigation Review Hub base URL, matter ID, answer_template.json, and asks Codex to identify preservation, collection, privilege-log, waiver, responsiveness/QC, retention, category coverage, metrics, or prioritized remediation actions.
---

# Review Hub Remediation

Use this skill to turn Investigation Review Hub evidence into the exact JSON object requested by a task-local answer template.

## Workflow

1. Read the user prompt and every task-local payload. Treat `answer_template.json` as the output contract: required keys, enum spelling, field names, ordering, numeric precision, and whether null or zero is expected.
2. Extract the matter ID, hub base URL, and any SQL API-key header from the prompt or payloads. Do not inspect local environment source, databases, generated manifests, hidden notes, answer files, or evaluator files.
3. Collect hub evidence for the matter. Prefer SQL queries through the hub because REST search endpoints can be capped:

   ```bash
   python path/to/skill/scripts/collect_hub.py \
     --base-url "$TASK_ENV_BASE_URL" \
     --matter-id "$MATTER_ID" \
     --api-key review-key-017 \
     --out hub_dump
   ```

   Omit `--api-key` when the task does not provide one. If the task gives a different header name, pass `--api-key-header`.
4. Read [references/analysis_rules.md](references/analysis_rules.md), then map only material matter-filtered hub records into the requested schema. Hub rows are noisy; do not include records just because they share labels or category codes.
5. Build the final JSON from the template. Use stable hub IDs as references, sort lists exactly as instructed, calculate metrics from the selected material issues, and return one JSON object with no prose.

## Evidence Discipline

- Use the live hub endpoints as the source of record for business facts: schema, matters, subpoena categories, production status, custodian sources, documents, privilege log, QC findings, retention events, and remediation candidates.
- Filter all evidence by `matter_id` before analysis. Ignore rows from other matters and rows whose notes or issue type mark them as routine, clean, or operational noise unless another material record references them.
- Normalize category lists and ID lists before output: split JSON/string list fields when needed, uppercase category codes when the template expects it, sort ascending, and deduplicate.
- Convert hub labels to the answer-template enums. Do not emit raw hub owner names, action names, statuses, or severities when the template requires a different enum vocabulary.

## Output Checks

Before finalizing:

- Every required top-level key and item key from the template is present.
- Every enum value appears exactly as allowed by the template.
- Counts are integers. Use `0` for not-applicable counts when the template says so, and `null` only where the template permits it.
- Category coverage includes only categories with open/material gaps unless the template asks for all categories.
- Metrics reconcile with the selected issue lists, not with every noisy hub row.
- The final response parses as JSON and contains no markdown or explanatory text.
