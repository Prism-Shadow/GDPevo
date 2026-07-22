---
name: investigation-review-gap-dashboard
description: Create structured JSON legal investigation gap, remediation, retention, privilege, QC, and production-readiness dashboards from an Investigation Review Hub style source of record and a task-local answer template. Use when a prompt asks for matter-specific production gap analysis, subpoena category coverage, retention or preservation gap review, privilege-log corrections, QC remediation, available archive/source analysis, or prioritized action plans in a prescribed JSON schema.
---

# Investigation Review Gap Dashboard

## Core Workflow

1. Read the prompt, task-local answer template, and any task-local matter or request context. Extract the matter ID, deliverable type, required top-level keys, enum choices, required item fields, metric definitions, and ordering rules.
2. Use the task-designated Investigation Review Hub as the source of record. Do not inspect local environment source files, database files, generated manifests, hidden notes, answer files, or evaluation artifacts.
3. Filter every evidence pull by the requested matter ID. Treat similarly named records from other matters as contamination for the answer.
4. Build the answer from stable hub IDs. Prefer records targeted by non-noise remediation actions, explicit issue tags, exception notes, QC findings, privilege entries, retention events, and source records over routine production noise.
5. Populate only the schema requested by the local answer template. Use enum values exactly as written in the template, use integers for counts, use `null` for unknown scalar values, and use empty arrays where a list has no values.
6. Sort every list exactly as the template says before final output. Return one JSON object and no prose.

## Evidence Selection

Start with remediation/action targets when present. Exclude rows marked as routine, noise, ordinary variance, resolved, no unresolved production impact, or not immediate remediation unless the prompt or metric definition explicitly asks for broad rollups.

Cross-check each selected target against its native evidence table:

- Source records provide source status, source type, category impacts, collection state, post-hold loss, and availability.
- Retention events provide hold dates, policy sections, destruction/loss timing, record type, affected categories, volume, and whether a loss was policy-compliant, post-hold, active-system, auto-purged, missing, retained, or available.
- Privilege entries provide withheld, logged, unlogged, over-designation, incomplete-log, third-party waiver, and family/coding defects.
- QC findings provide stable defect IDs, affected categories, document counts, source document refs, and corrected production or coding issues.
- Production rows help identify zero-claim contradictions and category-level readiness, but do not treat ordinary rolling or supplement status as material by itself unless the prompt asks for production-status coverage.
- Review documents are useful when QC or the prompt points to specific document IDs; avoid broad noisy document searches unless needed to verify counts or disposition.

## Classification Guide

Map hub issue language to the closest enum allowed by the answer template:

- Post-hold lost, destroyed, wiped, or erased source: preservation or post-hold loss; source impact is usually lost/destroyed; action is disclosure, forensic recovery, or other preservation action allowed by the template.
- Not-collected personal email, phone, messaging, or side-channel source: personal source or collection gap; source impact is missing; action is supplemental collection or personal-device collection.
- Available archive or retained backup: archive/source available; include it in available-source sections and list which categories it can remediate or limit.
- Policy-compliant pre-hold destruction: low-risk retention loss; often no remediation other than documenting the policy basis.
- Post-hold retention loss: preservation issue; include volume and policy data; prioritize disclosure or escalation.
- Active-system loss or auto-purge: communication gap; record purge windows and cutoff dates when the hub provides them.
- Should-exist-missing record: missing required record; action is locate, restore, or escalate.
- Zero-production claim contradicted by responsive documents: responsiveness miscode or missing required record, depending on the template enums; count the contradicted documents and include QC/document refs.
- Incomplete privilege log: privilege-log gap; unlogged count is withheld minus logged.
- Third-party waiver: privilege waiver/exposure; include the third party if named, otherwise use the available descriptive label or `null`.
- Over-designated business material or miscoded privilege: privilege miscoding or downgrade/recode issue; use QC remediation or privilege recode actions.

## Metrics

Derive metrics from the selected material issues unless the schema text clearly asks for all matching records. Keep metric scope consistent with the answer sections:

- Privilege unlogged count: sum `withheld_count - logged_count` for selected incomplete-log blockers.
- Privilege withheld/logged counts: follow the template wording; if it says selected blockers, do not include unrelated privilege noise.
- Third-party waiver count: sum selected waiver document counts.
- Miscoded responsive or privileged counts: use QC/doc counts tied to selected defects.
- Lost or uncollected source counts: count selected source records of the requested source classes.
- Destroyed box counts: count selected retention-loss events measured in boxes.
- Available archive count: count selected archive or retained-source remediation records.
- Affected category count and category lists: use the sorted union of categories with selected open material issues.
- Readiness booleans: mark not ready when any selected blocker requires collection, disclosure, privilege correction, QC remediation, or production recoding.

## Output Assembly

Use stable IDs exactly as they appear in the hub. Sort category-code lists and record-ref lists ascending. For owner and action fields, map hub labels to the nearest allowed enum in the template while preserving the operational meaning.

Before returning, validate that:

- All required top-level keys and required item keys are present.
- Every enum value is allowed by the task-local template.
- Counts are whole integers and internally consistent.
- Lists follow the template ordering rules.
- The answer contains no explanatory prose outside the JSON object.
