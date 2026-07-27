---
name: investigation-review-hub
description: Build structured legal investigation, subpoena, production-readiness, retention, privilege, QC, and remediation dashboards from an Investigation Review Hub task. Use when a prompt asks Codex to analyze matter-level evidence from a running review hub API and return a JSON object conforming to a task-local answer template.
---

# Investigation Review Hub

## Source Rules

Use only the task prompt, files under the task input directory, and the running Investigation Review Hub endpoints documented by the task. If `environment_access.md` is present, read it for the base URL, API key, and allowed endpoints. Do not inspect local environment source files, database files, generated manifests, hidden notes, standard answers, or evaluation files.

Treat the hub as the source of record for business evidence. Treat task-local payloads as output contracts and client-facing request context only. Replace `<TASK_ENV_BASE_URL>` with the base URL from `environment_access.md` or the task's environment payload.

## Standard Workflow

1. Read the prompt and every file in `input/payloads/`.
2. Identify the `matter_id`, required top-level output keys, enum choices, required item fields, ordering rules, and numeric precision from the answer template.
3. Query the hub with the provided API key. Start with `GET /api/schema` unless the schema is already supplied, then collect matter-filtered records from the relevant endpoints:
   - `/api/matters`
   - `/api/subpoena-categories`
   - `/api/productions`
   - `/api/custodian-sources`
   - `/api/documents/search`
   - `/api/privilege-log`
   - `/api/qc-findings`
   - `/api/retention-events`
   - `/api/remediation-actions`
4. Use `POST /api/query` for joined or filtered SQL-style retrieval when it reduces ambiguity. Always filter by the task's `matter_id`; never rely on records from other matters.
5. Build an evidence ledger keyed by stable hub IDs for documents, sources, retention events, privilege entries, QC findings, remediation actions, productions, and categories.
6. Classify material risks and gaps according to the output schema enums, then derive category rollups, metrics, and action plans from the evidence ledger.
7. Return exactly one JSON object and no prose. Include all required keys. Use `null` for unknown nullable fields and `0` for non-applicable counts.

## Evidence Normalization

Normalize category fields into uppercase category-code arrays. Parse list-like hub fields as JSON when valid; otherwise split comma-separated or pipe-separated strings and trim whitespace. Sort category-code lists ascending unless the template says a list is priority ordered.

Use stable hub record IDs exactly as provided. For `source_refs`, `record_refs`, `issue_refs`, `target_refs`, and blocking references, include every record that materially supports the issue, sorted ascending unless the template specifies priority order.

Count documents, sources, boxes, events, and categories from the selected evidence set. Do not copy raw endpoint totals into metrics unless the template asks for all records of that type. When a metric is tied to selected blockers or top risks, count only records included in those selected objects.

## Issue Classification

Use the template's enums exactly. Map hub evidence to the closest allowed enum; do not invent new values.

For preservation and retention:
- Post-hold destruction, lost sources, or destroyed archives are preservation losses and usually require counsel disclosure.
- Pre-hold policy-compliant destruction is a low-risk policy loss unless other evidence shows the item should still exist.
- Active-system purge windows, deleted collaboration data, and auto-purge configurations are communication gaps.
- Missing required records that should exist are separate from policy-compliant destruction.
- Available archives or retained alternate sources are remediation sources, not losses, but they may limit the impact of an active-system gap.

For collection and source gaps:
- Not-collected or partially collected personal email, phones, messaging, laptops, board portals, shared drives, and collaboration sources create source gaps for every impacted request category.
- Destroyed or lost sources are preservation losses, while not-collected sources are collection gaps.
- If an available archive covers some impacted categories, keep both the source gap and the archive remediation path visible.

For responsiveness and production:
- Contradictions between production zero-claim status, responsive review documents, and QC findings create responsiveness or production gaps.
- Nonresponsive coding on documents that are materially responsive supports recode-and-produce actions.
- A category is not ready when responsive material is unproduced, source evidence is missing, or a required privilege/quality correction remains open.

For privilege and QC:
- A privilege log gap exists when withheld documents exceed logged documents or the hub marks the log incomplete or protocol-noncompliant. `unlogged_count` is withheld minus logged unless the hub supplies a more specific value.
- Third-party recipients or waiver findings require waiver assessment and disclosure when the schema provides that action.
- Over-designation, business-only counsel-copy issues, and privileged documents coded nonprivileged are QC/privilege correction issues; use the template's closest privilege-correction fields.
- QC findings should be included when they materially change production, privilege, or readiness status.

## Category Rollups

Create one category object for each request category with a material open gap, unless the template requires all categories. Aggregate all issue IDs affecting that category. Choose the category status and production impact by the highest practical blocker:

1. Preservation loss or post-hold retention loss.
2. Source missing or collection gap.
3. Privilege exposure, waiver, or incomplete log.
4. Responsiveness or recoding gap.
5. Archive available or remediation available.

When multiple blockers apply, use the schema's combined status if one exists; otherwise choose the highest blocker and include all supporting references.

## Action Planning

Prefer action records from `/api/remediation-actions` for owner, priority, action ID, target, and due-day values. If the template expects grouped actions, consolidate compatible actions by action type, owner, priority, due date, and overlapping categories while preserving all target references.

Prioritize actions by legal risk and production impact:

1. Disclosure or preservation-risk escalation.
2. Forensic recovery or collection of missing sources.
3. Responsive recoding and production.
4. Privilege log supplementation, waiver assessment, and privilege recoding.
5. Archive searches or retained-source remediation.
6. Documentation-only or no-action policy losses.

Use hub action IDs when the schema has `action_id`. Use numeric `rank` or `priority_rank` starting at 1 and sorted ascending. Keep priorities within the template enum.

## Output Checks

Before finalizing:

- Confirm the JSON parses.
- Confirm every required top-level key and item-required key is present.
- Confirm every enum value appears in the template.
- Confirm all IDs come from hub records or deterministic schema-required action keys.
- Confirm all category lists and reference lists follow the template ordering rules.
- Confirm counts are whole integers and booleans are booleans.
- Confirm the final response contains only the JSON object.
