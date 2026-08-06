---
name: investigation-review-hub-remediation
description: Produce structured JSON remediation, production-readiness, retention, preservation, privilege, QC, and source-gap analyses from an Investigation Review Hub or similar matter review system. Use when a task provides a matter ID, answer template, and task-scoped hub access for subpoena, production, custodian-source, document-review, privilege-log, QC, retention, or remediation-action records.
---

# Investigation Review Hub Remediation

## Core Workflow

1. Read the user prompt, task-local context payloads, and answer template before querying evidence. Treat the template as the output contract: required keys, item keys, enums, numeric precision, and ordering rules are binding.
2. Use only the task-provided hub/source-of-record access. Do not inspect local environment source files, database files, seed data, manifests, hidden notes, gold answers, or evaluation artifacts.
3. Scope every evidence query to the requested matter ID. Pull the schema if needed, then gather matter metadata, request categories, production stats, custodian sources, review documents, privilege entries, QC findings, retention events, and remediation actions.
4. Build the candidate issue universe from non-noise remediation actions first. Add direct non-action blockers only when the template asks for them, such as miscoded responsive documents, zero-production contradictions, missing required records, or explicit readiness metrics.
5. Exclude operational noise: records whose notes or action IDs say routine, noise, ordinary variance, corrected audit trail, resampling only, metadata-only cleanup, or not dispositive without source comparison, unless the prompt specifically asks for those records.
6. Emit one JSON object only. Do not include narrative, citations, schema commentary, or fields not requested by the answer template.

## Evidence Selection

Prefer stable hub record IDs as anchors:

- Source gaps: custodian-source records with lost, not-collected, partial, personal-device, personal-messaging, board/source-map, post-hold wipe, deleted-channel, or collection-gap evidence.
- Retention and preservation: retention events with post-hold loss, policy-destroyed pre-hold, active-system loss, auto-purge, should-exist-missing, retained, or available statuses.
- Privilege: privilege entries with incomplete log, third-party waiver, over-designation, family mismatch only when escalated, or explicit rework actions.
- QC and responsiveness: QC findings and review documents showing miscoded responsive material, zero-claim contradictions, miscoded privilege, or documents withheld/not produced despite responsive facts.
- Available remediation sources: archive, retained, backup, or available-source records that limit loss or provide a collection path. Put these in the available/retained-source section when the template has one; include them as top risks only if the schema asks for archive-available risks or category statuses.

When a remediation action targets a record, use the target record for the issue facts and the action record for rank, due date, priority, owner hints, and action-plan inclusion.

## Normalization Rules

Follow the template enums exactly. Map hub language conservatively:

- `supplemental_collection`: collect source, collect personal device/email/messages, or collect/search archive depending on the target source type.
- `privilege_rework`: supplement privilege log for incomplete logs; waiver assessment for third-party waiver; privilege recode/downgrade/QC remediation for miscoding or over-designation.
- `qc_remediation`: recode and produce for responsiveness or zero-claim contradictions; privilege recode/QC remediation for miscoded privilege.
- `retention_exception_review`: disclose preservation issue for post-hold loss; no action or policy-loss documentation for policy-compliant pre-hold destruction; locate missing record, document system gap, restore backup, or search archive for missing/available-remediation records.
- Source `lost`, wiped, or destroyed after hold means preservation or post-hold-loss impact. Source `not_collected` means source missing. Source `available` with archive/deleted-channel tags means available archive/source.
- For unsupported units from the hub, use the template's nearest unit only when clear; otherwise use `null` count with `not_applicable`.

Owner mapping depends on the template's allowed owners. Use the nearest allowed role:

- Forensics or eDiscovery vendor -> `forensics` or `ediscovery_vendor`.
- Review Operations or review vendor -> `review_operations`, `review_qc`, or `review_vendor`.
- Privilege Team -> `privilege_team`; privilege counsel tasks -> `privilege_counsel`.
- Legal Hold, client legal, or legal operations -> `client_legal`, `legal_operations`, or `outside_counsel`.
- Records/archive operations -> `records_management`, `ediscovery_vendor`, or another records-capable owner allowed by the template.

## Counts and Metrics

Compute metrics only from selected material records, not every similar row in the matter.

- Incomplete-log unlogged count is `withheld_count - logged_count`.
- Withheld/logged/unlogged privilege metrics usually come from selected incomplete-log blockers, unless the template explicitly asks for all privilege corrections.
- Miscoded responsive count comes from selected responsive/nonresponsive or zero-claim QC blockers.
- Third-party waiver count comes from selected waiver entries.
- Personal-source counts come from selected personal email, personal phone, personal messaging, or device gap sources.
- Available archive/source count comes from selected remediation sources, not every routine available source.
- Category counts and category lists should reflect categories with selected open risks/gaps unless the template requires all category coverage.

For retention-review schemas with both retention-event and communication-gap sections, include communication system losses in both sections when the event is itself a retention event and the communication-gap section asks for system-specific detail.

## Category and Action Assembly

For each affected category, combine selected issues and choose the most specific available status:

- Preservation/post-hold loss outranks collection gap.
- Missing required record outranks archive availability.
- Privilege waiver/log gap outranks ordinary privilege variance.
- Responsiveness or zero-claim contradiction uses a responsiveness/recode status.
- If the schema has a mixed status and the category truly has multiple blocker families, use it; otherwise choose the dominant blocker.
- Include no-gap categories only when the prompt or template asks for complete coverage across all request categories.

Action plans should come from non-noise remediation actions plus any direct blocker that has no action but is required by the template. Preserve action priority using hub priority, due days, and the template ordering rules. Sort all category arrays and reference arrays ascending unless the template says otherwise.

## Final Checks

Before returning:

- Every top-level key required by the template is present and no extra top-level keys are added unless explicitly requested.
- Every enum value appears exactly as allowed in the template.
- Lists follow the template ordering rules.
- All stable IDs come from the hub or task-local payloads.
- Metrics equal the listed material issue records.
- The output is valid JSON with no prose outside the object.
