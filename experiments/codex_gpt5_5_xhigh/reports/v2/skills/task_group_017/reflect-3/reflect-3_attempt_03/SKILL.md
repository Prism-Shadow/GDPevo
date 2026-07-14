# Legal Investigation JSON Review Skill

Use this skill for structured legal investigation tasks that require a JSON-only answer from matter records, subpoena categories, production logs, collection events, retention rules, destruction events, privilege logs, QC events, custodians, and document summaries.

## Core Workflow

1. Read the task prompt and answer template before querying records.
   - Copy the required top-level keys, enum values, ID formats, count fields, ordering rules, and any "include only" language.
   - Treat the template as a contract. Do not add narrative fields, schema metadata, comments, or unrequested explanations.

2. Query the matter-level record first.
   - Capture hold date, subpoena date, regulator/production flags, deadline, and summary.
   - Use these dates to classify pre-hold policy loss, post-hold spoliation, recoverable archives, retained-but-missing sources, and hold-notice defects.

3. Query all relevant record families, then cross-check them.
   - Subpoena categories define scope and exact category IDs.
   - Production logs provide current counts and review status.
   - Collection events identify source status, missing counts, source names, and custodian-specific gaps.
   - Retention rules explain whether a missing source is expected, recoverable, retained, or policy-expired.
   - Destruction events are required before treating a gap as actual loss.
   - Privilege logs and QC events refine privilege-log gaps, miscoding, overdesignation, clawback, and processing failures.
   - Document summaries provide exact document IDs and marker documents for counted sets.

4. Filter aggressively.
   - Prefer records marked current, directly tied to the target matter/custodian/core categories, or repeated across production/QC/collection records.
   - Ignore noisy categories, obsolete policy notes, unrelated overlapping review batches, duplicate-alias noise, and stale coding unless the task asks for them or they directly affect the requested scope.

## Classification Rules

- Use exact category IDs, custodian IDs, event IDs, document IDs, enum casing, and ID formats from the prompt or records.
- Do not invent document IDs to fill a counted range. If the API gives marker IDs plus a count, report the marker IDs and the count.
- Calculate gaps directly:
  - privilege log gap = withheld privileged count minus privilege logged count.
  - unrecovered deletion count = affected/deleted count minus recovered count.
  - attachment failures = password-protected failures plus corrupt failures when those counts are provided.
- Treat all-withheld counsel categories as overdesignation risk when production logs or privilege records indicate zero production and overdesignation review.
- Treat privileged records coded nonprivileged and produced as clawback-required privilege miscoding.
- Treat complaint or responsive business documents coded nonresponsive as coding correction plus supplemental production.
- Treat a post-hold source problem as post-hold loss only when a destruction/loss record supports it. A collection gap after hold without destruction is usually an uncollected source or source gap.
- Treat recoverable archive records as validation or supplemental collection issues, not final loss.
- Treat retained-but-missing vendor or archive records as retrieval issues.
- If a schema has a `present` field for enum issue IDs, consider including every allowed issue ID in sorted order, marking absent issues false with zero counts and `no_action` when the template supports it.

## Readiness And Action Rules

- Overall readiness should reflect the blocking condition with the strongest record support:
  - `not_ready_post_hold_loss` only for confirmed post-hold loss/spoliation.
  - `not_ready_supplemental_collection_required` for uncollected sources, hold refresh, forensics, or archive validation needs.
  - `ready_after_archive_validation` for sources collected or recoverable but not validated.
  - `ready_with_retention_note` for available records with an explanatory retention note.
- Rank actions by blocking force: notice/loss assessment if required, forensics or retrieval, hold refresh, supplemental collection, QC/coding correction, privilege review/log supplement, then archive validation or documentation.
- Only include regulator notice when the records support disclosure or the matter/task flags make notice part of the requested remediation. Do not add notice merely because an enum exists.
- Keep issue/action arrays narrow unless the template explicitly asks for all possible values. Adding plausible but unsupported secondary issue types can reduce correctness.

## Output Hygiene

- Return JSON only.
- Preserve required top-level key order when possible.
- Sort lists exactly as specified: category IDs, custodian IDs, document IDs, action enums, issue IDs, findings, and ranked plans.
- Use integer counts and JSON booleans.
- Use empty lists only when the schema allows a field but there is no applicable record.
- Keep stable IDs in the requested format. If the template specifies formats like `MF-##` or `ACT-##`, use those exact patterns.
