---
name: investigation-review-hub-remediation
description: Use when producing legal investigation, subpoena, SEC, grand jury, retention, production-readiness, gap-analysis, or remediation-dashboard JSON deliverables from an Investigation Review Hub API and a task-provided answer_template schema.
---

# Investigation Review Hub Remediation

Use this skill for structured legal operations reviews where the Investigation Review Hub is the source of record and the final answer must conform to a task-local JSON schema.

## Core Workflow

1. Read the task prompt, every task-local payload, and the answer template before querying evidence.
2. Identify the matter ID, allowed sources, output schema, required top-level keys, enum choices, ordering rules, numeric precision, and any client-facing category labels.
3. Use only the task-authorized Investigation Review Hub endpoints for business evidence. Do not inspect environment source files, database files, generated manifests, hidden notes, standard answers, or local setup artifacts unless the prompt explicitly allows them.
4. If network details are provided separately, read that file and use only the listed base URL, headers, and endpoints. If SQL-style access is allowed, use the task-provided API header and inspect the hub schema before writing queries.
5. Filter every endpoint call or query by the requested matter ID. Use stable hub IDs exactly as returned for matters, categories, sources, documents, privilege-log records, QC findings, retention events, productions, and remediation actions.
6. Build the answer from evidence, then validate it against the answer template. Return exactly one JSON object when the prompt requires JSON only.

## Evidence Map

Use the hub records according to their evidentiary role:

- `matters`: matter metadata, hold dates, agency/request posture, and production context.
- `subpoena-categories`: category codes, labels, request scope, and category-level production expectations.
- `productions`: rolling-production status, readiness, produced/not-produced indicators, and category coverage.
- `custodian-sources`: source type, custodian, collection status, lost/not-collected/partial/collected state, active-system issues, and archive availability.
- `documents/search`: document-level responsiveness, privilege, coding, produced/withheld status, category hits, and counts for miscoding or underproduction.
- `privilege-log`: withheld, logged, unlogged, waiver, over-designation, miscoded privilege, third-party exposure, and privilege correction evidence.
- `qc-findings`: zero-claim contradictions, responsiveness miscoding, coding quality defects, issue severity/status, and remediation blockers.
- `retention-events`: policy destruction, post-hold loss, auto-purge, active-system loss, missing required records, event dates, cutoff dates, volumes, policy sections, and affected categories.
- `remediation-actions`: action IDs, owners, priorities, targets, due timing, and recommended operational next steps.

When task-local payloads include category synopses or request context, use them to interpret labels and output scope. Do not treat them as a substitute for hub evidence when the prompt says the hub is the source of record.

## Issue Classification

Classify only material gaps and defects unless the schema asks for complete or no-gap categories.

- Preservation and retention: distinguish policy-compliant pre-hold destruction from post-hold loss, active-system loss, auto-purge after duty attached, and records that should exist but are missing. Compare event or cutoff dates to the hold date when available.
- Source gaps: separate destroyed/lost sources, uncollected sources, partial collections, personal devices/accounts, deleted collaboration data, and available retained archives.
- Production gaps: identify not-produced, underproduced, source-missing, source-lost, recode-needed, and no-current-gap impacts using category and production evidence.
- Responsiveness/QC: capture responsive documents coded nonresponsive, zero-claim contradictions, coding defects, and categories requiring recode and production.
- Privilege: calculate withheld, logged, and unlogged counts; identify incomplete logs, waivers, third-party disclosure, over-designation, privilege miscoding, downgrade needs, and privilege recode/log actions.
- Remediation sources: list retained or available archives only when they remain usable to limit or cure a loss for one or more categories.

## Metrics

Derive metrics from the same records included in the risk, issue, source, category, or correction sections.

- Use whole integers for counts and whole days/months/years where the schema requires numeric precision.
- Use `0` for numeric fields that are not applicable when the schema expects an integer; use `null` only where the template allows null.
- Calculate unlogged privilege documents as withheld minus logged for the selected incomplete-log blockers unless the hub provides a more specific unlogged count.
- Count unique affected categories after normalizing and sorting category codes.
- Count available archives only for sources that are actually available or retained as remediation paths.
- Set production-ready or rolling-production-ready booleans to `false` when any open material blocker remains; set them to `true` only when no schema-relevant open blocker is supported by the hub evidence.

## Prioritization

Rank actions and risks by operational urgency, while honoring any existing hub priority or template-specific priority field.

1. Disclosure-critical preservation failures, post-hold losses, destroyed sources, and privilege waivers.
2. Uncollected or partial personal sources, missing required records, incomplete privilege logs, and high-volume responsiveness miscoding.
3. Available archive searches, recoding packages, QC remediation, and supplemental collections that can cure or limit the gap.
4. Monitoring, policy-compliant pre-hold losses, or no-action items when the schema requires them.

Map the selected action type, owner, priority, status, source status, production impact, and risk level to the exact enum choices in the answer template. Do not invent enum values.

## Output Assembly

- Populate every required top-level key and every required item key from the answer template.
- Use stable hub record IDs for `risk_id`, `issue_id`, `finding_id`, `event_id`, `source_id`, `correction_id`, `target_refs`, `source_refs`, `record_refs`, and category references whenever available.
- Keep category codes uppercase and sorted ascending inside every category list.
- Sort arrays exactly as the template states, commonly by priority/rank for risks and actions and by ID or category code for ledgers and coverage lists.
- Keep references sorted ascending and remove duplicates.
- Do not include prose, markdown fences, comments, or explanatory text around the JSON when the prompt requests a JSON-only deliverable.

## Validation Checklist

Before finalizing:

- The matter ID matches the prompt and hub records.
- Every value using an enum appears in the template's allowed choices.
- All required keys are present, including nested required item keys.
- Metrics reconcile to the selected evidence records and do not double-count the same source, event, document, or category.
- Category coverage reflects all material open gaps required by the schema.
- Priority ranks are consecutive where the schema expects ordered action or risk lists.
- The final response parses as a single JSON object.
