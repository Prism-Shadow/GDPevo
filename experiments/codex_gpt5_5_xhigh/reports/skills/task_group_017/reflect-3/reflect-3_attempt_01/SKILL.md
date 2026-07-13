---
name: subpoena-production-readiness-review
description: Use this skill for legal investigation tasks that require structured JSON reviews of subpoena production gaps, collection readiness, retention/hold defects, privilege-log issues, miscoding, custodian source gaps, or remediation actions from a shared investigation API and task-provided answer template.
---

# Subpoena Production Readiness Review

## Core Workflow

1. Read the prompt and the answer template before querying records.
   - Copy the required top-level keys, enum values, count semantics, and ordering rules.
   - Treat the template as the contract. Do not add narrative fields, memo text, or unrequested explanations.

2. Query the matter-scoped API records named in the prompt.
   - Start with matter metadata, subpoena categories, production logs, collection events, custodians, retention rules, destruction events, privilege logs, QC events, and documents.
   - Use targeted search queries for issue terms from the prompt and production notes, such as `complaint`, `privileged coded non-privileged`, `over-designation`, `PST`, `Teams`, `personal`, `audit`, `voicemail`, or custodian names.

3. Build an evidence table before drafting JSON.
   - Category scope: subpoena category ID, label, requested sources, date range.
   - Production status: produced count, withheld privileged count, privilege logged count, review status, notes.
   - Source status: collection/destruction event IDs, custodian, source name/type, collected/missing counts, hold relation, recoverability.
   - Privilege status: privilege log item IDs, record count, logged status, privilege status, production status, overdesignation flag, waiver risk.
   - QC/document proof: QC event IDs, affected/recovered/failed counts, marker document IDs, document coding, production status.

## Filtering Signal From Noise

- Prefer `batch: current` production logs and records that directly match the prompt's matter, target custodian, target categories, or current category prefixes.
- Treat synthetic/noise categories as noise unless another core record ties them directly to the requested issue.
- A noisy privilege or collection row should not create a category finding by itself. Require corroboration from current production notes, target-custodian records, QC, documents, or collection/destruction events.
- When a schema includes a `present` boolean for issue findings, list material present issues only unless the prompt explicitly asks for a complete true/false checklist.

## Counts And Calculations

- Use production logs for category-level produced, withheld, and logged counts.
- Compute privilege log gaps as `withheld_privileged_count - privilege_logged_count`.
- Use collection/destruction events for source counts, missing counts, recovered counts, and post-hold/pre-hold timing.
- Use QC records for affected/failed/recovered counts and marker document IDs.
- If a document set is represented by endpoint marker documents, include the exact marker IDs provided by the API rather than inventing missing IDs.
- Use `0` only when the template instructs it or the count is genuinely not applicable.

## Issue Classification

- Post-hold wipe, reset, deletion, or destruction: classify as post-hold spoliation or source deletion/device wipe, with notice review, forensic recovery, and custodian declaration as appropriate.
- Pre-hold ordinary retention loss: separate it from preservation defects; usually treat as a policy gap or retention note, not spoliation.
- Recoverable archive or vendor copy: do not call it final loss. Use archive validation, vendor retrieval, or supplemental collection.
- Retained-but-missing record: use retained-missing or uncollected-source classifications and require retrieval from the retained source.
- Hold notice omitted a source: use hold refresh plus supplemental collection for the omitted source.
- Zero production despite responsive nonprivileged records: mark the category blocked or needing supplemental production and require coding correction/QC plus production.
- Privilege log gap: require privilege log supplement and use the withheld/logged delta as the unlogged count.
- All counsel communications withheld or business-only records withheld as privileged: mark overdesignation risk and require privilege review or business-only production when the enum allows it.
- Privileged records produced or coded nonprivileged: require clawback review and privilege coding correction.
- Attachment processing failures: use the failed/password/corrupt counts and require reprocess QC.

## Readiness Reviews

- Include ready sources when the template asks for readiness across sources, not only gaps.
- Mark retained personnel or HR files as ready or ready-with-retention-note when retention rules and collection events show availability.
- Mark archive email as recoverable or ready-after-archive-validation when active mailbox purge is overridden by an archive.
- Mark Teams pre-cutoff purge gaps as retention/source gaps and require Teams gap assessment.
- Mark missing local PST or laptop material as a source gap requiring laptop/PST forensics.
- Mark personal cloud/text omissions as hold-notice defects requiring hold refresh and supplemental collection.
- Use `not_ready_supplemental_collection_required` when any source, hold-notice, archive-validation, or forensic collection step remains open.
- Reserve `not_ready_post_hold_loss` for actual post-hold loss/destruction, not merely recoverable archive gaps or uncollected sources.

## Output Construction

- Sort every list exactly as the template requires: category IDs, document IDs, action enums, issue IDs, source IDs, and rank fields.
- Use exact enum casing and exact API IDs.
- Keep stable issue/action/finding IDs consistent across linked fields. Prefer template-required formats when provided.
- Keep action lists focused on necessary remediation. Avoid adding regulator notice unless the facts show post-hold loss, waiver/clawback notice risk, or the template/prompt asks for disclosure review.
- Do not include categories that only have stale review coding, duplicate alias noise, obsolete policy labels, or unrelated privilege rows without a material current defect.
