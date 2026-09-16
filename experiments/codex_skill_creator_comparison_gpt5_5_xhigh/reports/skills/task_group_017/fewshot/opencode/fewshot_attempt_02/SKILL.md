---
name: review-hub-legal-remediation
description: Use this skill for Investigation Review Hub legal/eDiscovery tasks that ask for structured JSON gap analyses, production-readiness reviews, retention or litigation-hold reviews, privilege/QC remediation dashboards, subpoena category coverage, numeric risk metrics, or prioritized remediation action plans from hub endpoints and task-local answer templates.
---

# Investigation Review Hub Legal Remediation

Use this workflow when a task asks you to synthesize a legal review hub into a strict JSON answer. The common pattern is: read the prompt and task-local payloads, query the running hub for one matter, identify material preservation, collection, responsiveness, privilege, QC, retention, and archive issues, then emit exactly one JSON object matching `input/payloads/answer_template.json`.

## Boundary

- Use only task-local payload files and the Investigation Review Hub endpoints supplied by the prompt or environment note.
- Do not inspect environment source files, database files, seed files, generated manifests, hidden notes, prior answers, or evaluator files.
- Treat the hub as the source of record for business evidence. Use local payloads only for the answer schema and request context.
- Return only the requested JSON object. Do not include prose, citations, markdown fences, or diagnostic notes in the final answer.

## Fast Start

1. Read the user prompt, `input/payloads/answer_template.json`, and every other task-local payload.
2. Extract the matter ID, base URL, and any API key/header from the prompt or payloads.
3. Fetch hub schema first, then all matter-scoped records. Prefer the bundled extractor:

```bash
python /path/to/skill/scripts/hub_extract.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --matter-id "$MATTER_ID" \
  --api-key "$API_KEY" \
  --output /tmp/review_hub_bundle.json
```

If no API key is supplied by the task, omit `--api-key`; the script will still use ordinary GET endpoints and will attempt SQL only when credentials are available.

4. Use the answer template as the contract for top-level keys, required item keys, enum values, ordering, and numeric precision.
5. Build an evidence ledger before writing the final JSON. For each issue, record the stable hub IDs, affected categories, source status, production impact, counts, owner/action, and why it is material.
6. Draft the answer, then validate shape and ordering:

```bash
python /path/to/skill/scripts/validate_answer.py answer.json input/payloads/answer_template.json
```

Fix every validation error before finalizing.

## Hub Tables

The review hub normally exposes:

- `matters`: matter metadata, agency, hold date, investigation type.
- `subpoena_categories`: category codes and request text.
- `production_stats`: produced, withheld, responsive, nonresponsive, zero-claim, and batch status by category.
- `custodian_sources`: collection/preservation status for devices, messaging, archives, offsite records, and other sources.
- `review_documents`: document-level responsiveness, privilege, production status, category, issue tags, and summaries.
- `privilege_entries`: privilege log counts, issue type, third-party flags, and notes.
- `qc_findings`: review quality findings, affected categories, source refs, severity, and document counts.
- `retention_events`: retention or litigation-hold events, policy periods, dates, source refs, status, volume, and categories.
- `remediation_actions`: proposed action type, owner, priority, due days, and target record.

Use `POST /api/query` for cross-table review when the task provides the required header. Keep SQL read-only and filter every business query by the active `matter_id`.

## Synthesis Workflow

1. Normalize all category-code arrays and record-reference arrays as sorted uppercase/string lists with duplicates removed.
2. Identify material issues from all relevant hub tables, not just one endpoint:
   - preservation or retention losses from retention events and destroyed/lost sources;
   - uncollected or partially collected personal, board, messaging, archive, or offsite sources;
   - responsive documents coded nonresponsive or zero-claim contradictions;
   - incomplete privilege logs, over-designations, third-party waiver issues, and privileged documents miscoded nonprivileged;
   - available archives or retained sources that can remediate an active-system loss;
   - missing records that should exist under the request or policy.
3. Cross-link supporting records. A risk may need source refs from a retention event, QC finding, privilege entry, and specific review documents.
4. Prefer hub remediation actions for owner, priority, due days, and target refs when they match a material issue. If no action exists, derive the action from the issue type and template enums.
5. Populate only issues that the requested schema asks for and that are material to readiness, gap analysis, retention loss, privilege correction, or remediation. Exclude fully ready or no-gap categories unless the template explicitly requests them.
6. Compute metrics from the selected evidence, not from prose:
   - unlogged privilege docs = withheld count minus logged count for incomplete-log blockers;
   - affected category count = unique categories with selected open/material risks;
   - nonready or open-gap category counts = number of category status objects included;
   - post-hold loss count = selected loss events after the matter hold or marked post-hold;
   - available archive/source count = selected retained or available sources that are a remediation path;
   - miscoded document counts = QC or document-level responsive/privilege miscoding counts.
7. Sort every list exactly as the answer template requires. When the template says rank order, order by the numeric rank; when it says ID order, sort lexicographically by the requested ID field.

For issue-type and action mapping details, read [references/issue-mapping.md](references/issue-mapping.md).

## JSON Construction Rules

- Use stable IDs exactly as they appear in the hub.
- Use enum strings exactly as listed in the answer template. When multiple labels could fit, choose the one that best matches the requested output section, not the raw table name.
- Use `0` for numeric counts that are not applicable when the schema calls for integers. Use `null` only where the template permits a nullable string/date/count.
- Keep `third_party` as the string required by the template when the hub identifies a third-party actor; otherwise use `null`.
- Do not add fields that are absent from the template.
- Do not omit required fields, even when a value is not applicable.
- Reconcile category statuses with top risks: every category listed as nonready or open should be supported by issue refs that appear in the issue ledger/top risk/source evidence.

## Final Check

Before answering:

- Confirm every top-level key listed in `required_top_level_keys` is present.
- Confirm every object in an array contains the template's required item keys.
- Confirm metrics agree with the selected issue arrays.
- Confirm source refs, target refs, affected categories, and category impacts are sorted.
- Confirm the final response is valid JSON and contains no copied example answer records.
