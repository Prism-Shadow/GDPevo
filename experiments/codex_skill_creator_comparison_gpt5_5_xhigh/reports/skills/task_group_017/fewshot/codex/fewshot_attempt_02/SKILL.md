---
name: investigation-review-hub
description: Use when solving Investigation Review Hub legal review tasks that require a schema-conforming JSON answer from task-local payloads and the running hub API, including production gap analyses, retention or litigation-hold reviews, SEC/DOJ remediation dashboards, privilege/QC readiness reviews, source gap reviews, and prioritized action plans.
---

# Investigation Review Hub

Use this skill to turn a task prompt, its `input/payloads/answer_template.json`, and matter-scoped Investigation Review Hub records into the required JSON object.

## Source Boundary

- Read the task prompt and every file under `input/payloads/`.
- Use only the running hub endpoints named by the task or `environment_access.md`.
- Do not inspect environment source files, database files, generated manifests, hidden notes, test tasks, test answers, or evaluator code.
- Return exactly one JSON object when the user asks for the final answer. Do not include prose outside JSON.
- Use stable hub IDs exactly as they appear. Sort arrays according to the answer template.

## Evidence Collection

Prefer the SQL endpoint when the prompt gives an API key because it returns complete matter-scoped tables without relying on endpoint defaults. The bundled helper is [scripts/collect_hub_evidence.py](scripts/collect_hub_evidence.py):

```bash
SKILL_DIR=/path/to/skill
python "$SKILL_DIR/scripts/collect_hub_evidence.py" --input-dir input --output /tmp/hub_evidence.json
```

If the skill is invoked from outside the task root, pass explicit paths:

```bash
python /path/to/skill/scripts/collect_hub_evidence.py --input-dir /path/to/task/input --base-url "$TASK_ENV_BASE_URL" --output /tmp/hub_evidence.json
```

The script writes the prompt, payload metadata, matter ID, hub schema, table rows, likely material candidates, and direct record links. Treat candidates as triage, not as the answer.

Collect or verify these tables for the target matter:

- `matters`
- `subpoena_categories`
- `production_stats`
- `custodian_sources`
- `review_documents`
- `privilege_entries`
- `qc_findings`
- `retention_events`
- `remediation_actions`

## Build The Answer

1. Start from `answer_template.json`. Copy its required top-level keys, item keys, enum names, ordering rules, nullability, and numeric precision.
2. Identify the requested review type from the prompt and template field names: first rolling gap analysis, retention/hold gap review, cross-system remediation dashboard, or production-readiness privilege/QC review.
3. Build a matter-scoped evidence map keyed by every stable ID. Link:
   - `qc_findings.source_ref` to `review_documents.doc_id`.
   - `remediation_actions.target_ref` to any source, retention event, privilege entry, QC finding, document, or category code.
   - categories from `affected_category`, `affected_categories`, `category_impacts`, `category_code`, and linked source/document rows.
   - split category fields whether the hub returns them as arrays, JSON strings, or comma-delimited strings.
4. Filter noisy rows before populating the schema. Routine metadata, duplicate, family-member, alias, sampling, load-file, and minor variance rows are not material unless another selected issue record links to them or the template asks for that specific correction type.
5. Fill only fields requested by the template. When a field is not applicable, use the template's requested `0`, `null`, `false`, or enum such as `not_applicable` or `unknown`.

## Material Issue Rules

Use these mappings unless the task template gives a stricter enum or description.

Retention and preservation:

- `post_hold_loss` means a material preservation loss. Use the destroyed/lost source or retention event as the anchor, set high or critical severity, production impact `source_lost`, and recommend disclosure or preservation escalation.
- `post_hold_partial_recovery` is also a material preservation loss. Use the unrecovered count from notes when the template asks for remaining lost/unrecovered volume; keep the raw volume as supporting context only if the schema asks for total affected volume.
- `policy_destroyed_pre_hold` is a true retention event but usually low risk and policy compliant. Include it when the template asks for retention events or policy losses; use a no-action/policy-loss disposition when available.
- `should_exist_missing` means a missing required record. Use `missing_required_record` or `should_exist_missing`, recommend locating the record, and include the retention period if the template asks.
- Active-system loss, system window loss, deleted channel data, or auto-purge should become the closest template enum such as `active_system_loss`, `auto_purged`, `source_lost`, `deleted_channel`, or `purged_custodian_mail`.
- Available archives or retained remediation sources belong in available-source sections only when their tags, status, or notes show they limit or remediate a gap.

Custodian and source gaps:

- `lost`, destroyed, erased, or post-hold personal devices are preservation losses, not simple collection gaps.
- `not_collected` or `partial_collection` personal email, phone, SMS, Signal, chat, laptop, or similar side-channel sources are personal source gaps.
- Board portals, SharePoint sites, offsite records, archives, and shared repositories with material `not_collected` status are collection gaps or available-source remediation paths depending on their status and notes.
- Do not count ordinary available or collected sources as retained remediation sources unless the prompt asks for all retained sources.

Documents and QC:

- A responsive document coded nonresponsive, a zero-production claim contradicted by responsive documents, or a QC finding for miscoded responsiveness is a responsiveness/zero-claim issue. Include the QC ID and direct document IDs when available.
- Privileged documents coded nonprivileged are privilege miscoding. Use the QC ID and linked privilege entry when present.
- Use `doc_count` from the QC finding for counts. If the issue is anchored by individual document rows and no aggregate count exists, count the selected document IDs.

Privilege:

- `incomplete_log` is a privilege log gap. `unlogged_count = withheld_count - logged_count`.
- Third-party waiver is material when the privilege entry has a third-party marker or notes identify an outside recipient/adviser/consultant. Preserve the available third-party label if the template has a `third_party` field.
- Over-designation or business-only counsel-copy issues are privilege corrections. Include them in privilege correction/readiness ledgers when requested, but do not let them outrank withheld-unlogged, waiver, or responsive-miscode blockers unless the template says otherwise.

## Metrics

Compute metrics from the selected material records, not from every noisy table row, unless the template explicitly says total table counts.

- Count affected categories from the union of selected issue categories.
- Count available archives from selected available remediation sources.
- Count post-hold loss events from selected destroyed/lost post-hold source or retention records.
- Count uncollected personal sources from selected personal source gaps.
- Count boxes only from selected records whose `volume_unit` is `boxes`.
- For privilege metrics, use selected incomplete-log blockers for withheld/logged/unlogged totals unless the field asks for waiver or miscoding counts separately.
- Set readiness booleans to `false` when any material blocker remains open, noncompliant, not collected, or not remediated.

## Prioritization

Rank actions by legal risk first, then operational dependency:

1. Preservation loss, destroyed/lost post-hold sources, and required government disclosure.
2. Responsive documents not produced, zero-claim contradictions, and recode/produce blockers.
3. Privilege waiver or exposure needing counsel assessment.
4. Incomplete privilege logs and privilege recoding.
5. Missing required records and available archive searches.
6. Supplemental collection of personal or other uncollected sources.
7. Policy-compliant pre-hold destruction or monitor-only items.

Normalize owners and action types to the answer template enums. Hub action rows are useful for target references, due days, and confirmation that remediation exists, but their labels may be more generic than the schema. Prefer the schema-specific legal action that matches the issue.

For dashboard-style `action_plan` sections, group target references when the same action, owner, priority, due-day expectation, and category set naturally belong together. For `priority_actions` sections with `action_id`, use stable action IDs from the hub when they fit; otherwise generate deterministic IDs from the matter prefix and rank without copying any example answer IDs.

## Final Checks

- Validate the object against `answer_template.json`: required keys, enums, integer counts, booleans, nulls, and exact output shape.
- Sort top-level lists and nested category/reference arrays exactly as requested.
- Verify every metric can be traced back to selected records.
- Verify every `source_refs`, `issue_refs`, `record_refs`, `target_refs`, and category list contains only relevant stable IDs and no unsupported noise rows.
