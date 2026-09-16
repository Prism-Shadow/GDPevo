---
name: investigation-review-hub-remediation
description: Use this skill for Investigation Review Hub legal/eDiscovery tasks that ask for structured JSON gap analyses, production-readiness reviews, remediation dashboards, retention/preservation reviews, privilege/QC blocker summaries, subpoena category coverage, or prioritized action plans. This skill should trigger whenever a prompt mentions a matter ID, TASK_ENV_BASE_URL, review hub endpoints, subpoena categories, privilege logs, QC findings, custodian sources, retention events, remediation actions, or an answer_template.json contract.
---

# Investigation Review Hub Remediation

Use this skill to solve review-hub tasks by grounding every field in the running hub and the task-local payloads, then returning schema-exact JSON only.

## Core Rules

- Treat the task prompt, `input/payloads/answer_template.json`, other task-local payloads, and the running Investigation Review Hub as the only business evidence.
- Do not inspect local environment source files, database files, seed files, generated manifests, hidden notes, answer files, or evaluator files.
- Preserve stable hub IDs exactly. Use matter, category, source, event, document, privilege, QC, and action IDs as they appear in the hub.
- Build the answer from the current task schema, not from memory of prior tasks. The schema controls top-level keys, enum values, required item fields, sorting, null-vs-zero choices, and metric definitions.
- Return exactly one JSON object and no prose outside it.

## Workflow

1. Read the prompt and every file in `input/payloads/`.
   - Identify the `matter_id`, the answer template path, any category/context labels, and any SQL API key or header mentioned by the task.
   - If the prompt contains `<TASK_ENV_BASE_URL>`, resolve it from the task environment information provided in the workspace. Use only that information for network reachability.

2. Read the answer template as a contract.
   - List required top-level keys and required item keys.
   - Copy enum spellings exactly.
   - Note ordering rules before drafting any arrays.
   - Identify which sections are issue ledgers, category rollups, available-source lists, metrics, and action plans.

3. Collect hub evidence for the matter.
   - Prefer the read-only SQL endpoint when available because it gives all records consistently by `matter_id`.
   - Otherwise call the documented hub endpoints for matters, subpoena categories, production stats, custodian sources, documents, privilege log, QC findings, retention events, and remediation actions.
   - The helper `scripts/fetch_hub.py` can collect the known tables/endpoints into one JSON evidence file. Use the script path relative to this `SKILL.md`; if your shell is in the task directory, substitute the absolute path to the skill directory:

```bash
python scripts/fetch_hub.py "$TASK_ENV_BASE_URL" "$MATTER_ID" --out hub_evidence.json --api-key review-key-017
```

4. Create an evidence ledger before writing the answer.
   - Group records by issue family: retention/preservation loss, source collection gap, available archive or retained source, responsiveness/coding defect, privilege log gap, third-party waiver, privilege miscoding, over-designation, missing required record, and ready/no-gap categories.
   - For each material issue, record the stable anchor ID, supporting record IDs, affected category codes, counts, current status, production impact, recommended action, owner, priority, and any third-party or missing-component detail.
   - Read `references/review-hub-playbook.md` when mapping hub records into issue types, metrics, category coverage, and action priority.

5. Fill the schema from the ledger.
   - Include only material non-ready/non-complete categories unless the template explicitly asks for all categories or all retention events.
   - Use `0` for numeric counts that are not applicable when the schema says integer; use `null` only when the template says a field may be null.
   - Compute unlogged privilege counts as withheld minus logged for the selected incomplete-log blocker records.
   - Sort all arrays and ID/category lists according to the template.

6. Validate before final response.
   - Save a draft JSON during work and run the validator from this skill directory, or substitute the absolute path to the script:

```bash
python scripts/validate_answer.py input/payloads/answer_template.json draft_answer.json
```

   - Treat the helper as a sanity check. It does not replace checking the hub evidence and the template wording yourself.
   - Fix missing keys, enum mismatches, unsorted arrays, wrong count types, and accidental prose before finalizing.

## Final Answer Standard

The final response must be a single JSON object conforming to the task-local `answer_template.json`. Do not include markdown fences, explanations, citations, or comments.
