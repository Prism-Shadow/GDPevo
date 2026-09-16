---
name: investigation-review-hub-remediation
description: Use this skill for Investigation Review Hub legal review tasks that require structured JSON gap analyses, production-readiness reviews, retention or preservation reviews, remediation dashboards, privilege/QC metrics, category coverage, or prioritized action plans from subpoena matter records. Trigger whenever the prompt mentions Investigation Review Hub, matter IDs, subpoena categories, productions, custodian sources, review documents, privilege logs, QC findings, retention events, remediation actions, or an answer_template.json JSON contract.
---

# Investigation Review Hub Remediation

Use this skill to answer matter-scoped legal operations review tasks from an Investigation Review Hub. The expected output is usually a single JSON object that conforms exactly to a task-local `input/payloads/answer_template.json`.

## Hard Boundaries

- Use only the task prompt, task-local payload files, and the running Investigation Review Hub endpoints allowed for the task.
- Do not inspect local environment source code, database files, generated manifests, hidden notes, answer files, evaluator files, or unrelated matters.
- Filter every hub query by the requested `matter_id`. Broad all-matter pulls introduce noise and can contaminate the answer.
- Treat the answer template as binding: top-level keys, field names, enum values, required keys, ordering rules, numeric precision, and JSON-only final output all come from the template.
- Use stable record IDs exactly as they appear in the hub. Do not paraphrase IDs.

## Workflow

1. Read the prompt and every file under `input/payloads/`.
2. Extract the `matter_id`, hub base URL, any SQL API key/header, and the target output schema from the template.
3. Query the hub schema first, then collect matter-scoped records from each relevant table or endpoint.
4. Build an evidence ledger before drafting the JSON. Group candidate records by issue type, affected categories, source IDs, document IDs, privilege IDs, QC IDs, retention event IDs, and action IDs.
5. Select only material production, preservation, retention, privilege, collection, and QC blockers requested by the prompt. Exclude routine noise unless a template field explicitly asks for it.
6. Normalize the selected facts into the exact template shape.
7. Validate JSON structure and ordering before final output.
8. Return only the final JSON object, with no prose outside it.

## Hub Snapshot Helper

Use `scripts/fetch_hub_snapshot.py` when the task allows the SQL query endpoint. It pulls only the requested matter and writes a structured snapshot.

```bash
python skill/scripts/fetch_hub_snapshot.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --matter-id "$MATTER_ID" \
  --api-key review-key-017 \
  --out /tmp/hub_snapshot.json
```

Omit `--api-key` only when the task does not provide one. If the skill is installed at a different path, run the script from that skill directory or adjust the path.

The helper also adds parsed list variants for comma-separated category and tag fields. Use those parsed values for grouping, but preserve original hub IDs in the answer.

## Evidence To Pull

Use matter-scoped rows from these hub tables/endpoints:

- `matters`: hold date, agency, investigation type, matter status.
- `subpoena_categories`: category codes, titles, request text, topic tags.
- `production_stats`: produced/withheld/responsive/nonresponsive counts, zero claims, category production status.
- `custodian_sources`: source status, source type, personal-device gaps, archive availability, post-hold loss, affected categories, issue tags.
- `review_documents`: document-level responsiveness, privilege status, production status, issue tags, summaries.
- `privilege_entries`: withheld/logged counts, incomplete logs, waivers, over-designation, third-party indicators.
- `qc_findings`: confirmed coding, privilege, production, and document-quality findings with affected categories and source refs.
- `retention_events`: policy losses, post-hold losses, active-system losses, auto-purge windows, missing required records, archive links.
- `remediation_actions`: candidate owners, priorities, target refs, due days, and action descriptions.

Prefer SQL when available because it lets you apply `where matter_id = :matter_id` consistently. If using REST endpoints instead, apply equivalent matter filtering in query parameters or immediately after receiving the response.

## Interpreting Material Issues

Read `references/record_to_output_map.md` when converting hub records into answer fields. The core selection rules are:

- Post-hold loss or destroyed source records are usually the highest preservation risk and often require disclosure plus recovery/remediation.
- Not-collected personal devices, personal email, messaging, board, shared-drive, or collaboration sources are collection/source gaps.
- Available archives are remediation paths. Include them in retained/available source sections and action plans, not as irretrievable losses.
- Responsive documents coded nonresponsive, zero-claim contradictions, and QC findings for miscoding are production blockers.
- Incomplete privilege logs use `withheld_count - logged_count` for unlogged counts. Do not count third-party waiver documents as unlogged log-gap documents unless the template explicitly says to combine them.
- Third-party privilege entries are waiver/exposure issues and should be counted in waiver-specific metrics.
- Privilege miscoding and over-designation are QC or privilege correction issues; include them when the template has an issue ledger or privilege correction section.
- Retention events should be classified relative to the hold date: pre-hold policy destruction is lower risk and can be policy-compliant; post-hold loss, active-system loss, auto-purge, and missing-required-record events remain gaps or risks.

## Normalization Rules

- Split comma-separated category, tag, and ref fields; trim whitespace; remove empty values.
- Sort category code arrays, source/ref arrays, and all template-specified lists as directed by `ordering_rules`.
- Use `null` for unknown scalar values when the template permits null; use `0` for numeric counts that are not applicable; use `[]` for empty list sections.
- For `source_refs`, `issue_refs`, `record_refs`, `blocking_refs`, and `target_refs`, include the stable hub records that actually support the item. Include both a QC finding and its referenced document when both are needed to prove the blocker.
- For category rollups, union all selected issue categories and count only selected material issues, not every noisy row in the matter.
- For metrics, compute from the final selected issue set unless the field description says to count all matching hub records.
- For action IDs, prefer hub action IDs when they directly match the normalized plan. If the template expects action IDs but the hub action records are only rough candidates, create deterministic IDs from the matter/action plan context and rank; do not reuse IDs from examples.

## Priority And Owner Defaults

Use template enum values exactly. Map hub action labels and owners to the nearest allowed enum:

- Disclosure of post-hold preservation loss/source loss: highest priority, usually outside or litigation counsel.
- Waiver assessment/disclosure: privilege counsel/team.
- Recode and produce or QC remediation: review QC/review vendor/review operations.
- Supplemental collection, personal-device collection, archive search, restore, or locate missing records: forensics, eDiscovery vendor, IT, records management, or compliance audit according to the record type.
- Supplement privilege log: privilege team.
- Policy-compliant pre-hold loss: low priority or no-action policy-loss if the template includes that option.

When `due_days` is required and the hub does not provide exact due dates, use risk-weighted short windows consistently: immediate disclosure/waiver items before routine collection, recoding/log supplementation before monitor-only items, and archive searches after critical blockers.

## Validation

Draft the answer into a file and run:

```bash
python skill/scripts/validate_structured_answer.py \
  --template input/payloads/answer_template.json \
  --answer /tmp/answer.json
```

Fix every error before final output. Warnings are prompts to recheck ordering or unsupported enum mappings. Then print the JSON object only.
