---
name: review-hub-remediation-json
description: Build structured JSON answers for Investigation Review Hub legal review tasks involving production gaps, retention and preservation losses, source collection gaps, privilege-log defects, QC miscoding, and remediation action plans. Use when a prompt asks for a JSON-only subpoena, SEC, grand jury, production-readiness, gap-analysis, or remediation dashboard answer from Review Hub API endpoints and an answer_template.json file.
---

# Review Hub Remediation JSON

## Core Rule

Return exactly the JSON object requested by the task template. Treat the task prompt, task-local payloads, and the running Review Hub API as the only business evidence. Do not inspect local environment source, database files, generated manifests, hidden notes, evaluator files, or answer files.

## Workflow

1. Read the prompt, every task-local payload, and the full `answer_template.json`.
2. Extract the matter ID, base URL, any API key header, required top-level keys, enum values, field names, ordering rules, and numeric precision rules.
3. Collect Review Hub evidence for only the requested matter. Use `scripts/fetch_review_hub.py` if a generic fetch-and-filter bundle would help:

   ```bash
   python skill/scripts/fetch_review_hub.py "$TASK_ENV_BASE_URL" "$MATTER_ID" --api-key "$API_KEY" > hub.json
   ```

   Omit `--api-key` when the task does not provide one. With an API key, the helper prefers the read-only SQL endpoint so capped search endpoints do not hide rows.

4. Reconcile all relevant tables before drafting: matter metadata, request categories, production stats, custodian sources, review documents, privilege entries, QC findings, retention events, and remediation actions.
5. Map evidence into the exact requested template fields. Read [references/review_hub_mapping.md](references/review_hub_mapping.md) when choosing issue types, statuses, category coverage, action priorities, owners, and metrics.
6. Validate the answer against the template before finalizing:
   - All required top-level keys and item keys are present.
   - Every enum value is one of the template choices.
   - Lists follow the template ordering rules.
   - Category-code lists and hub ID reference lists are sorted where required.
   - Counts are whole integers; use `0` for non-applicable counts and `null` only where the template allows null.
   - The final response contains no prose outside the JSON.

## Evidence Handling

Filter every endpoint result by `matter_id` before using it. Ignore routine or noise actions unless they target a material issue supported by sources, retention events, documents, privilege entries, or QC findings.

Prefer stable hub record IDs for object IDs and references:

- Retention or source loss: retention `event_id` or source `source_id`.
- Collection gap: custodian source `source_id`.
- Responsiveness or QC defect: QC `finding_id`; include related `doc_id` values when the template asks for supporting refs.
- Privilege defect: privilege `entry_id`; include related QC IDs when a QC finding supports the correction.
- Action target: the issue, source, retention, privilege, QC, or document IDs actually remediated.

## Metrics

Compute metrics from the selected material records, not from all rows in the matter. For privilege-log blockers, use the specific incomplete-log entry or entries selected for the answer. For category counts, use the unique affected categories represented in the output issue set. For readiness booleans, return false whenever any material blocker remains open.

## Final Pass

After drafting, re-read the template ordering rules and compare each output section to them. The examples favor concise, normalized JSON over narrative explanation; do not include rationale fields unless the template requires them.
