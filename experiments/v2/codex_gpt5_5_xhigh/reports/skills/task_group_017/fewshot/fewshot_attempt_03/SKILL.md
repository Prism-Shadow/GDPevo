---
name: investigation-review-hub-remediation
description: Use this skill for legal or eDiscovery tasks that require structured JSON gap analyses, production-readiness reviews, retention/preservation reviews, or remediation dashboards using the Investigation Review Hub API as the source of record.
---

# Investigation Review Hub Remediation

Use this skill when a task asks for a structured legal review deliverable from an Investigation Review Hub: production gaps, subpoena/request category readiness, retention or preservation losses, privilege-log defects, QC miscoding, source collection gaps, available remediation sources, metrics, and prioritized action plans.

## Source Discipline

- Use only the task prompt, task-local payloads, and the running hub endpoints identified by the task or its environment access file.
- Do not inspect local environment source code, database files, seed files, manifests, hidden notes, standard answers, or evaluation files.
- Treat the hub as the source of record for business evidence. Task-local payloads provide output schema, matter context, labels, and constraints.
- If a SQL endpoint is provided, use it only through the documented API URL and credentials. Never use local database access.
- Return exactly the requested JSON object when the prompt asks for JSON only.

## Workflow

1. Read the prompt and every task-local payload. Identify the matter ID, output schema file, required top-level keys, enum values, ordering rules, numeric precision, and any source constraints.
2. Read the hub access instructions. Confirm the service with `GET /` and inspect `GET /api/schema` so table and column names are current.
3. Fetch all evidence for the target matter from these endpoint/table families:
   - `matters`: hold date, agency, investigation type, status.
   - `subpoena_categories`: category codes, titles, date ranges, request text, tags.
   - `production_stats`: production counts, zero-claim statuses, withheld/responsive counts, batch notes.
   - `custodian_sources`: source IDs, source types, collection status, post-hold flag, category impacts, issue tags.
   - `review_documents`: document IDs, category, responsiveness, privilege status, produced status, issue tags, summaries.
   - `privilege_entries`: privilege issue type, withheld/logged/doc counts, third-party flag, category.
   - `qc_findings`: miscoding, zero-claim, privilege, family, duplicate, metadata, severity, document counts, source refs.
   - `retention_events`: event status, event and hold dates, retention period, volumes, affected categories, source refs.
   - `remediation_actions`: target refs, action type, priority, severity, owner, due days.
4. Prefer matter-filtered SQL for complete, compact retrieval. Example shape:

```bash
curl -sS -X POST "$BASE_URL/api/query" \
  -H "Content-Type: application/json" \
  -H "$API_KEY_HEADER: $API_KEY" \
  -d "{\"sql\":\"SELECT * FROM ${TABLE} WHERE matter_id = '${MATTER_ID}' ORDER BY ${ORDER_COLUMN}\"}"
```

If quoting is awkward, use the equivalent GET endpoints and filter rows by `matter_id`.

5. Normalize list-like fields from comma-separated strings or JSON arrays into sorted arrays. Preserve stable hub IDs exactly.
6. Build an evidence ledger before writing the final JSON. Keep only material issues that affect production readiness, preservation, privilege, collection, or remediation; do not escalate routine noise unless the requested schema requires it.
7. Populate the requested schema exactly, using only enum values allowed by the task template. Use `null`, `0`, `false`, or empty arrays according to the template when a field is not applicable.
8. Validate ordering, counts, booleans, and JSON syntax before final output.

## Materiality Rules

Escalate these issue families when supported by hub records:

- Post-hold destruction, post-hold partial recovery, lost devices, active-system losses, and missing required records.
- Personal email, personal phone, personal messaging, board/share drive/site, deleted channel, archive, or other source gaps with production impact.
- Available archives or retained sources that can mitigate a loss or provide a remediation path.
- Zero-production or zero-responsive claims contradicted by QC findings or document records.
- Responsive documents coded nonresponsive or not produced.
- Privilege-log gaps where withheld documents exceed logged documents.
- Third-party privilege waiver records.
- Privileged documents coded nonprivileged, over-designation, or other privilege correction records when the prompt asks for privilege/QC readiness.

De-emphasize rows whose notes or tags indicate routine variance, ordinary sampling, metadata-only issues, corrected historical overlays, or similar labels across matters unless they are tied to a requested material issue by ID, category, severity, or action.

## Field Mapping Heuristics

- Stable IDs: use the hub record ID anchoring the issue. For merged risks, include all supporting IDs in the reference list and choose the primary loss, privilege entry, QC finding, source, or document as the risk key according to the schema description.
- Category impacts: use category codes from the hub record first, then corroborate with category, document, production, or source rows. Sort codes lexicographically unless the template says otherwise.
- Source status: map lost/destroyed/wiped sources to loss; not-collected personal or board sources to source gaps; available archives and retained sources to remediation availability; privilege and QC records to not applicable.
- Production impact: map lost/destroyed source to source lost, uncollected source to source missing, available archive to source available, miscoded responsive document to not produced or recode needed, incomplete privilege log to withheld unlogged, third-party waiver or privilege miscoding to privilege exposure.
- Retention status: compare event date and hold date. Post-hold loss is high priority; pre-hold policy destruction is usually low risk if policy-compliant; active-system purge or auto-purge is a communication gap; should-exist-missing remains open until located.
- Privilege counts: `unlogged = max(withheld_count - logged_count, 0)`. Use the specific privilege record(s) selected as material blockers, not every noisy privilege row in the matter.
- QC counts: use `doc_count` from the selected QC finding, or count stable document refs when the finding lists specific documents.
- Available source counts: count selected retained or archive sources that are a real remediation path, not every available routine source.
- Affected category count: count unique categories represented in selected material issues or in the schema's requested coverage set.
- Readiness booleans: set production or rolling readiness to false if any nonready/material gap category remains open.

## Action Planning

- Use hub remediation actions as supporting evidence, but translate `action_type`, `owner`, and priority into the task template's enum values when they differ.
- Prioritize: post-hold loss/disclosure and preservation issues first; waiver and privilege exposure next; responsiveness recode/production blockers next; supplemental collection and available archive searches next; documentation or monitoring last.
- Group closely related targets only when the schema uses one action per action type or priority rank; otherwise keep one action per material target.
- Use due days from the hub when the output schema asks for due days; otherwise rank actions by risk level, priority, production impact, and target importance.

## Final Checks

- The final response must be valid JSON and conform exactly to the task's template.
- Include all required top-level keys and required item fields.
- Use only allowed enum values from the task-local template.
- Sort every list according to the template ordering rules.
- Do not include explanatory prose, citations, comments, or unrequested fields in JSON-only tasks.
