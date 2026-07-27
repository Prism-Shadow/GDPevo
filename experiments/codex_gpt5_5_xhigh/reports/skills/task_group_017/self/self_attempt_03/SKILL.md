---
name: investigation-review-hub-json
description: Structured investigation and eDiscovery review workflow for producing schema-conformant JSON answers from an Investigation Review Hub. Use when a task asks for subpoena, agency, litigation-hold, retention, production-readiness, privilege, QC, collection-gap, or remediation dashboards that rely on task-local payload schemas and hub endpoints as the source of record.
---

# Investigation Review Hub JSON

## Core Rules

Read the user prompt and every file in the task-local `input/payloads/` directory before querying evidence. Treat local payloads as scope, labels, access hints, and output contracts only; factual business evidence must come from the running Investigation Review Hub.

Use only the access path provided by the task. If an `environment_access.md` file is present, read it for the base URL, credentials, and allowed endpoints; do not use local environment files, source code, database files, generated manifests, seeds, answer files, evaluation files, hidden notes, or setup scripts. If the prompt provides a base URL and API header directly, use those values rather than inferring from the runtime environment.

Return exactly the requested structured output. For JSON deliverables, produce one JSON object and no prose outside it.

## Evidence Workflow

1. Identify the matter ID, client-facing review type, audience, category family, and schema file from the prompt and payloads.
2. Read the answer template as the output contract: required top-level keys, item keys, enum values, field types, precision rules, and ordering rules.
3. Inspect the hub schema first when available. Use it to learn fields, relationships, filters, and safe SQL query shapes.
4. Confirm the matter exists in the hub, then keep every endpoint request and SQL query scoped to that matter.
5. Build an evidence ledger keyed by stable hub IDs. Track matter IDs, category codes, source IDs, event IDs, QC finding IDs, document IDs, privilege-log IDs, production IDs, and remediation action IDs exactly as they appear.
6. Cross-check all material findings against at least one stable hub record. Do not infer a defect solely from a local category label or output template field.
7. Prefer hub endpoints for ordinary pulls and use the read-only query endpoint for joins, counts, category rollups, and consistency checks.

## Hub Areas To Review

Use the available endpoints for these evidence families:

- Matter metadata: matter status, agency, review or hold dates, and matter-level context.
- Subpoena or request categories: category codes, labels, and category families.
- Productions: produced status, rolling production readiness, zero-production claims, category coverage, and production impact.
- Custodian sources: collected, pending, partial, uncollected, lost, destroyed, personal, offsite, archive, collaboration, messaging, cloud, and retained sources.
- Documents/search: responsiveness, privilege coding, production status, document counts, and category hits.
- Privilege log: withheld documents, logged documents, unlogged counts, incomplete log records, waiver exposure, over-designation, and privilege miscoding.
- QC findings: responsiveness miscoding, privilege miscoding, coding contradictions, production blockers, and correction needs.
- Retention events: policy destruction, post-hold loss, auto-purge windows, missing required records, archive exceptions, affected categories, and loss volumes.
- Remediation actions: predefined action IDs, owners, priorities, target records, due dates, and action status.

## Classification Rules

Classify retention and preservation events by timing and availability. Treat post-hold destruction, active-system loss, should-exist missing records, and unavailable required sources as preservation or production risks. Treat policy-compliant pre-hold destruction separately from post-hold loss; it may require documentation rather than disclosure or recovery unless the hub evidence shows a continuing gap.

Classify collection gaps from source evidence. Personal devices, personal email, offsite records, deleted collaboration channels, and partial collections are material when they map to requested categories or production blockers. If an archive or retained source limits the loss, include it as an available remediation path rather than as a lost source.

Classify responsiveness and production issues from document, production, and QC evidence. Flag contradictions such as responsive documents coded nonresponsive, responsive documents not produced, zero-production claims contradicted by document hits, and category underproduction.

Classify privilege issues from privilege-log, document, and QC evidence. For incomplete logs, compute withheld, logged, and unlogged counts from the selected hub records. For third-party disclosure or waiver issues, preserve the third-party value when the schema has such a field. For privilege miscoding or over-designation, use recode/log/disclosure actions that match the template enum choices.

Classify category status by the material blocker affecting that category. Use no-gap or ready statuses only when the schema calls for category rows without open blockers; otherwise include only categories with material attention items.

## Metrics

Compute metrics directly from the evidence selected for the answer, not from the template wording alone. Keep counts as whole integers. Reconcile related counts before finalizing, especially:

- withheld minus logged equals unlogged where the template defines it that way;
- affected category counts match the unique category codes listed in the relevant risk or issue arrays;
- available archive/source counts match the retained or available source rows included;
- post-hold, pre-hold, missing-record, personal-source, QC, privilege, and waiver counts match the records actually summarized;
- readiness booleans reflect whether material blockers remain.

Use `0`, `null`, or empty arrays only when the template type and field description allow them.

## Actions

Tie every action to the highest-impact underlying records and categories. Prefer predefined hub remediation actions when present; otherwise derive actions from the template enum values and the issue family:

- preservation loss: disclose/escalate, forensic recovery, restore/search archive, or document policy loss;
- collection gap: collect source, collect personal device/email/messages, custodian follow-up, or source search;
- responsiveness/QC issue: recode, produce, and QC remediate;
- privilege log gap: supplement log;
- waiver or exposure: waiver assessment and disclosure;
- missing required record: locate missing record;
- archive available: collect/search archive;
- no material issue: monitor or no action only if the schema permits it.

Rank actions with `1` as highest priority. Give priority to irreversible preservation loss, government/regulator disclosure risk, unproduced responsive material, privilege exposure, and blockers preventing imminent production. Sort action arrays exactly as the answer template requires.

## Output Validation

Before responding:

1. Parse the JSON mentally or with a local parser if available.
2. Verify every required top-level key and required item key is present.
3. Verify every enum value is copied exactly from the current template.
4. Verify all referenced IDs exist in hub evidence and belong to the scoped matter.
5. Sort arrays and nested category-code lists according to the template.
6. Check that no task-answer values, hidden materials, database/source files, or unrelated matter evidence influenced the response.
