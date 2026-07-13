---
name: ediscovery-investigation-api-review
description: Structured legal e-discovery and subpoena review using a task-provided investigation API and strict JSON answer template. Use when a task asks Codex to inspect matter, custodian, subpoena category, production log, collection, retention/destruction, privilege, QC, or document records and return JSON findings/actions for production completeness, hold remediation, collection readiness, miscoding, privilege-log gaps, overdesignation, source loss, or remediation priority.
---

# E-Discovery Investigation API Review

## Core SOP

1. Read the prompt, `input/payloads/answer_template.json`, and any other task-local payloads named by the prompt before querying the API. Extract the target `matter_id`, any target `custodian_id`, category scope, required top-level order, allowed enum values, required counts, sorting rules, and whether the task asks for production, retention/hold, collection readiness, custodian-specific, or privilege/miscoding review.
2. Read `environment_access.md` for the base URL and substitute it for `<TASK_ENV_BASE_URL>`. Use the remote API as the source of record. Collection endpoints are usually wrapped as `{"count": n, "items": [...]}` rather than bare arrays.
3. Fetch the matter record first, then the relevant matter-scoped endpoints: `/api/subpoena_categories`, `/api/production_logs`, `/api/collection_events`, `/api/custodians`, `/api/retention_rules`, `/api/destruction_events`, `/api/privilege_logs`, `/api/qc_events`, `/api/documents`, and `/api/search` when useful. Filter by prompt targets after fetching complete matter data.
4. Build cross-reference maps by `category_id`, `custodian_id`, `source_type`/`source_name`, `event_id`, `document_id`, and privilege item. Reconcile categories against requested sources, collection status, production tracker rows, privilege rows, QC issues, and document summaries.
5. Draft only the JSON object required by the template. Do not include schema metadata, markdown, comments, or narrative fields unless the template explicitly asks for them.

## Evidence Fields

- Matter records provide `hold_date`, subpoena/deadline metadata, protocol flags, and notice flags. Use these as context, not as a substitute for record-level proof.
- Subpoena categories provide `category_id`, `label`, `requested_sources`, `date_range`, and `topic_tags`. Include only categories that are within the prompt scope and have a material corroborated defect.
- Production logs provide category counts and tracker status: `produced_count`, `withheld_privileged_count`, `privilege_logged_count`, `review_status`, and `notes`. There can be multiple rows per category; do not blindly sum noisy or overlapping rows. Prefer the row whose status/notes match the defect and corroborate it with QC, privilege, collection, or document records.
- Collection events provide source availability: `status`, `hold_relation`, `collected_count`, `missing_count`, `reason`, `source_type`, `source_name`, `custodian_id`, and `related_category_ids`.
- Retention rules and destruction events drive timing classification. Compare `hold_date`, `pre_or_post_hold`, `event_date`, `policy_basis`, `record_class`, `quantity`, and `recoverability`.
- Custodian records provide role, status, `known_gaps`, and `relevant_sources`. For custodian-specific tasks, exclude unrelated custodians even when matter-wide records mention the same category.
- Privilege logs provide `record_count`, `logged_status`, `privilege_status`, `production_status`, `overdesignation_flag`, `waiver_risk`, notes, and category/custodian links.
- QC events provide issue type, affected/recovered/failed counts, related documents, and review notes. Use QC counts for grouped issues when document records only show marker examples.
- Document records can have multiple `category_ids`. Use `review_coding`, `privilege_coding`, `production_status`, `source_type`, `tags`, `summary`, and `title` to confirm miscoding, privilege, source, and production consequences.

## Classification Rules

- Treat `source gap`, `not collected`, `not noticed`, `unavailable`, `wiped`, `destroyed after hold`, and `collected with gap` as blocked or action-required when they affect requested sources. Use `missing_count` or QC counts for quantities.
- Separate pre-hold policy destruction from post-hold preservation loss. Pre-hold destruction under an applicable retention rule is usually a policy/retention note or no-action policy gap; post-hold unavailable or unrecoverable loss can require notice, forensic recovery, custodian declaration, and hold refresh.
- Treat recoverable archives, vendor portals, archive validation, and pending retrieval as remediation/collection actions before declaring final loss.
- Detect privilege-log gaps by comparing withheld privileged totals to logged totals, or by `logged_status` values such as not logged or partially logged. The usual gap count is `withheld_privileged_count - privilege_logged_count`.
- Treat business-only or not-privileged material withheld as privileged, or any `overdesignation_flag`, as overdesignation requiring privilege review and possible production of nonprivileged material.
- Treat privileged material coded nonprivileged and already produced as clawback/waiver risk. Treat forwarded privileged material or `waiver_risk` as waiver assessment.
- Treat responsive documents coded non-responsive, stale, family-only, or otherwise outside the subpoena scope as miscoding when QC notes, tags, summaries, or category labels show they belong in scope.
- Treat attachment processing, password-protected, corrupt, duplicate-family suppression, archive-validation, and stale-review-coding QC issues as production-readiness defects only when they affect requested categories or the targeted custodian/source.

## JSON Assembly

- Follow the answer template exactly: top-level key order, nested required keys, enum casing, boolean values, integer counts, ID formats, and sorting instructions.
- Use exact IDs from the API for matters, categories, custodians, documents, events, and privilege items. Generate stable issue/action IDs only when the template requires synthetic IDs; use allowed enum IDs when the template enumerates them.
- Sort category IDs, custodian IDs, document IDs, source event IDs, action enums, findings, and ranked plans exactly as specified. Ranks should be consecutive integers starting at 1.
- Use `0` only when the template asks for an integer and no count applies or no count is available. Do not infer counts from the number of marker documents when QC, production, or privilege rows give the grouped count.
- Set disclosure or notice booleans from the classified issues: post-hold unrecoverable loss, serious preservation failure, waiver/clawback risk, or regulator-facing production defects usually trigger notice; ordinary pre-hold policy loss or recoverable archive validation usually does not.

## Pitfalls

- Search results are grouped and noisy; use search to find candidates, then verify with the source endpoint records.
- Category IDs and source names may include decoy or stale records. Do not include a category solely because it has a keyword hit, nonzero count, or overlapping privilege row.
- Local factual payloads may define source-name aliases, hold-notice facts, or partner instructions that are not obvious from the API. Apply them when classifying the API records.
- Some production tracker rows describe overlapping review batches, duplicate aliases, or obsolete labels. Confirm materiality with notes and the prompt scope before reporting them.
- Do not convert exact enum strings to synonyms. The JSON must use the template's allowed values even when API labels are worded differently.
