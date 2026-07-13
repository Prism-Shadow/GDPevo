---
name: investigation-api-json-review
description: Use for structured JSON reviews over investigation APIs involving subpoena categories, production logs, collections, retention, privilege logs, QC events, custodians, and document summaries.
---

# Investigation API JSON Review

Use this workflow when a task asks for a schema-conforming JSON answer from a shared investigation workspace. The goal is to extract material production, preservation, privilege, or collection-readiness defects while filtering noisy records.

## Core Workflow

1. Read the prompt and answer template first. Identify the matter ID, target custodian if any, production phase, required top-level key order, enums, sorting rules, and whether any task-local payload or memo supplies facts not present in API records.
2. Query the matter record, then the endpoints relevant to the template: subpoena categories, production logs, collection events, destruction events, retention rules, custodians, privilege logs, QC events, documents, and search.
3. Start from high-signal records:
   - `batch: current` production logs.
   - exact target matter and target custodian records.
   - QC events with specific issue types and document markers.
   - privilege log rows with explicit waiver, overdesignation, miscoding, or log-gap notes.
   - collection/destruction events tied to core category IDs.
4. Use search for exact phrases from current rows, such as "unlogged", "miscoded", "over-designation", "missing local PST", or "hold notice omitted". Search results often assemble the matching production, QC, document, privilege, and collection records.
5. Build the JSON from the template, not from narrative habit. Use exact enum strings, JSON booleans, integer counts, required key order, and the template's sort rules.

## Noise Filtering

Do not treat every API row as material. Many records are distractors.

- Prefer core category prefixes named in the prompt over noisy synthetic categories.
- Ignore production rows marked `noise-*` unless corroborated by current records and the prompt scope.
- Ignore stale review coding, duplicate alias, archive validation, or "no material exception" notes unless the task specifically asks for that issue and the record is in scope.
- Ignore overlapping document tags when the specific QC, production, or privilege record identifies the true affected category.
- For custodian-specific tasks, exclude other custodians unless the template explicitly asks for related custodians.

## Evidence And Counts

Use the most specific source for each count.

- Production status counts come from current production logs.
- Privilege log gaps are `withheld_privileged_count - privilege_logged_count` for the identified category.
- Miscoding document counts come from QC `affected_count` or privilege `record_count`; document lists may contain only marker IDs.
- Collection gaps use `missing_count`, `collected_count`, and `status` from collection events.
- Destruction issues use destruction `quantity` and should be paired with the related collection event when both exist.
- Recoverability comes from destruction, retention, and collection notes; do not infer final loss when an archive or vendor copy is identified.

## Issue Classification

Map facts to template concepts consistently:

- Post-hold device resets, post-hold destroyed boxes, and unrecovered post-hold deletions are spoliation/loss issues and usually drive notice or disclosure review.
- Lawful pre-hold policy destruction is a policy gap, not a spoliation issue; document it separately and avoid notice unless the prompt requires it.
- Missing but retained records are `retained_missing` or recoverable-source issues, with vendor retrieval or supplemental collection.
- Uncollected personal email, personal cloud, SMS, PSTs, and omitted hold-notice sources are source or hold defects requiring supplemental collection, hold refresh, or forensics.
- Overwithheld counsel or business-only records are overdesignation issues requiring privilege review and production of nonprivileged material where the enum supports it.
- Privileged records produced or coded nonprivileged require clawback or privilege review, using the QC or privilege record count.
- Attachment processing failures belong to processing/QC actions, with password-protected and corrupt counts kept separate when the template asks.

## Readiness Reviews

For collection-readiness templates, create one row per core source/category even when some sources are ready.

- Personnel files retained under the current rule are ready or ready with a retention note.
- Archive email with an archive override is recoverable and usually needs archive validation before final readiness.
- Pre-cutoff Teams gaps are retention/source gaps; mark them as blocking if the template distinguishes blocked Teams issues.
- A missing local PST is a laptop/PST source gap; if the PST itself is absent, use `missing` availability.
- A hold notice that omitted personal cloud/text sources is a hold-notice defect and remains blocked until hold refresh and supplemental collection.
- Do not mark post-hold loss unless an event expressly describes destruction, loss, wipe, or unrecoverability.

## Identifiers And Ordering

- If the schema provides enum issue IDs, use those exact enum values.
- If stable IDs are free-form, make them deterministic and semantic, but keep cross-references exactly consistent.
- Use API event IDs in event fields; include both collection and destruction event IDs for the same loss when both exist.
- Do not put unrelated retention-rule IDs into fields that ask for event IDs unless the template expressly allows rule records.
- Sort category IDs, custodian IDs, document IDs, action enums, source names, findings, and ranked actions exactly as the template requires.
- Use consecutive ranks starting at 1 and keep action lists narrowly tied to required remediation.

## Final Output

Return only the requested JSON. Do not add markdown, comments, schema metadata unless required by the answer template, or explanatory text outside the JSON.
