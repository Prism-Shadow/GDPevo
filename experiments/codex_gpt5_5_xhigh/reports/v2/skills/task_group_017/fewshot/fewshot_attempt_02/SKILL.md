---
name: legal-investigation-json-review
description: Produce JSON-only legal production, preservation, privilege, QC, and collection-readiness reviews from the shared investigation API and task answer templates.
---

## Purpose

Use this skill when a task asks for a structured legal investigation review against the shared API. The deliverable is normally one JSON object matching `input/payloads/answer_template.json`, not a memo. The key work is to turn matter records, category trackers, collection/retention events, privilege logs, QC events, custodians, and document summaries into the exact fields, enums, counts, and ordering required by the template.

## Standard Workflow

1. Read the prompt, every task-local payload, and the answer template before querying facts.
2. Extract the matter ID, any target custodian, production phase, and whether the prompt asks for all material deficiencies or a narrower status packet.
3. Query the shared API for the matter plus relevant endpoints:
   - `/api/matters/{matter_id}`
   - `/api/subpoena_categories?matter_id=...`
   - `/api/production_logs?matter_id=...`
   - `/api/collection_events?matter_id=...`
   - `/api/retention_rules?matter_id=...`
   - `/api/destruction_events?matter_id=...`
   - `/api/privilege_logs?matter_id=...`
   - `/api/qc_events?matter_id=...`
   - `/api/custodians?matter_id=...`
   - `/api/documents?matter_id=...`
   - `/api/search?matter_id=...&q=...` for keyword discovery, then verify against source endpoints.
4. Build a fact table by category, custodian, source, and issue. Keep API IDs attached to each fact.
5. Fill only the fields required by the template, using exact enum spelling and exact key order where specified.
6. Validate that the final response is pure JSON with no markdown, comments, schema metadata, or narrative fields.

## Scope And Exclusions

- Respect the prompt scope. If a target custodian is named, include that custodian's issues and consequences, not unrelated custodians in the same matter.
- Include only categories or sources the prompt asks for. Some tasks ask only for materially deficient categories; others ask for a readiness packet that includes ready or ready-with-note rows for core categories.
- Exclude noisy comparator rows, stale review artifacts, unrelated privilege rows, and categories whose only signal is generic overlap. Noise often has category IDs with unrelated prefixes/suffixes, non-current batches, notes saying "unrelated," "obsolete," "stale," or facts outside the target custodian/source.
- Do not treat an active-system purge as final loss if an archive, vendor portal, or other recoverable source is available.
- Do not invent missing document IDs. If documents represent a range, include the endpoint/marker IDs present in the API and use counts from logs, QC records, or notes.

## Evidence Mapping

- Matter record: use `hold_date`, `deadline`, `production_protocol_flag`, `regulator_notice_flag`, agency, and summary for timing and disclosure context.
- Subpoena categories: use exact `category_id`, `label`, `requested_sources`, `topic_tags`, and date range to map each issue to category scope.
- Production logs: use current or material batch rows for `produced_count`, `withheld_privileged_count`, `privilege_logged_count`, `review_status`, and notes. A privilege-log gap is usually `withheld_privileged_count - privilege_logged_count`.
- Collection events: use `status`, `hold_relation`, `missing_count`, `collected_count`, `source_type`, `source_name`, `reason`, `custodian_id`, and `related_category_ids` for source gaps, archive availability, hold notice defects, and supplemental collection needs.
- Retention rules and destruction events: use `record_class`, `retention_period`, `archive_override`, `pre_or_post_hold`, `quantity`, `recoverability`, and `policy_basis` to distinguish ordinary pre-hold policy destruction from post-hold preservation failure.
- Privilege logs: use `logged_status`, `record_count`, `privilege_status`, `production_status`, `overdesignation_flag`, `waiver_risk`, and notes for log gaps, overdesignation, clawback, and waiver analysis.
- QC events: use `issue_type`, `affected_count`, `failed_count`, `recovered_count`, `related_document_ids`, and `review_note` for processing failures, stale coding, and miscoding.
- Custodians: use `role`, `status`, `known_gaps`, and `relevant_sources` to confirm target custodians and source ownership.
- Documents: use `review_coding`, `privilege_coding`, `production_status`, `source_type`, `tags`, and `summary` to prove miscoding, responsive-but-not-produced records, produced privileged records, and category ties.

## Business Rules

- Post-hold destruction, device wipe, shared-drive deletion, or unrecovered source loss is a critical preservation issue. It usually drives `post_hold_spoliation`, forensic recovery or regulator notice, and a notice flag when the template asks for one.
- Pre-hold policy destruction is normally a policy gap, not spoliation. Use the template's no-action or policy-gap option unless records are recoverable or retained elsewhere.
- Recoverable archives and vendor portals are not final loss. Use supplemental collection, archive validation, or vendor retrieval, with notice usually false unless the prompt or matter facts say otherwise.
- A not-noticed source, omitted personal device/cloud/text instruction, or off-site vendor missing from a hold distribution is a hold defect. Pair it with hold refresh and supplemental collection; escalate notice when there is resulting post-hold loss.
- Zero production for a category is material only when documents, QC, or notes show responsive records exist or production is required. Otherwise do not infer a defect from zero alone.
- Privilege-log incompleteness comes from withheld privileged counts exceeding logged counts or privilege rows marked not/partially logged. Report the unlogged count as an integer.
- Overdesignation is indicated by `overdesignation_flag`, business-only material withheld as privileged, or all records withheld in a broad counsel category. It requires privilege review or business-only production, but not automatically regulator notice.
- Privileged material produced or coded non-privileged creates clawback or waiver review. Waiver risk is strongest when `waiver_risk` is true or notes show forwarding to an outside banker, consultant, vendor, or other third party.
- Attachment and processing failures come from QC events and collection notes. Use failed, recovered, unrecovered, password-protected, or corrupt counts from the API rather than estimating.
- Readiness statuses should reflect the worst unresolved blocker: post-hold loss, hold notice gap, source gap, supplemental collection required, archive validation pending, then ready or ready with retention note.

## Output Conventions

- Return one JSON object only. Never include markdown or explanatory prose outside the JSON.
- Use the answer template as the contract. Do not include template metadata unless it is an explicitly required output field.
- Use exact enum casing. Convert API source labels to template enums only when the template requires it, such as `personal cloud/text` to `personal_cloud_text`.
- Use JSON booleans and integer counts. Use `0` only when the template says to use zero for not applicable or unknown counts.
- Use stable IDs that match the template style. Examples: category findings can include the category and issue name; ranked actions can use consecutive ranks; `MF-##` and `ACT-##` formats should be consecutive when required.
- Sort lists exactly as the template says. Common defaults are category IDs ascending, custodian IDs ascending, document IDs ascending, issue IDs ascending, action IDs ascending, and ranked actions by consecutive rank starting at 1.
- Sort source/evidence IDs by prefix group and numeric suffix when requested. Keep only relevant IDs such as CE, DE, RR, PL, PV, QC, DOC records that support the finding.
- Overall disclosure or notice fields should be true if any included issue requires notice; otherwise false.

## Final Checks

- Compare top-level keys and nested required keys against the template.
- Recalculate privilege gaps, missing counts, recovered/unrecovered counts, and overall blocked category lists.
- Confirm every category, custodian, document, and event ID exists in the API or task-local payloads.
- Confirm no noisy/stale categories slipped into a materially deficient-only answer.
- Run the JSON through a parser before submitting.
