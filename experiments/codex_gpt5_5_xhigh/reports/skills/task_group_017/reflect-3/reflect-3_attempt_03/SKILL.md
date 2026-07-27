---
name: investigation-review-remediation
description: Build structured JSON gap analyses, production-readiness reviews, retention reviews, and remediation dashboards from an Investigation Review Hub. Use when a task asks Codex to analyze matter-scoped subpoena or regulatory review data, identify production gaps, preservation losses, source collection gaps, privilege/QC blockers, retained or available remediation sources, metrics, and prioritized actions that must conform to a task-provided JSON answer template.
---

# Investigation Review Remediation

## Workflow

1. Read the task prompt, local answer template, and any local matter/request context files. Treat the template as the output contract: required keys, enum values, ordering rules, field names, and numeric precision override generic assumptions.
2. Use only the task-provided Investigation Review Hub access and task-local context files. Do not inspect local environment source, databases, seeds, manifests, hidden answer files, or generated setup artifacts.
3. Pull matter-scoped hub rows before reasoning: matter metadata, categories, production stats, custodian sources, review documents, privilege entries, QC findings, retention events, and remediation actions. Always filter by `matter_id`.
4. Build an evidence ledger keyed by stable hub IDs. Start with remediation-action `target_ref` records, then add stable exception documents and directly relevant retention/source/privilege/QC records that the prompt asks to quantify.
5. Classify each issue using the template's enums, compute metrics from the selected evidence, sort every list exactly as the template requires, and return only the final JSON object.

## Evidence Selection

Prefer records with strong materiality signals:

- Remediation actions targeting a source, retention event, privilege entry, QC finding, or document.
- Review documents with stable exception language or issue tags such as `miscoded_nonresponsive`, `zero_claim_contradiction`, `unrecovered_file`, `unsupported_metric`, or a task-specific blocker.
- Custodian sources with issue tags such as `personal_messaging`, `personal_email`, `personal_device`, `collection_gap`, `post_hold_wipe`, `deleted_channel`, or `archive_available`.
- Retention events with statuses such as `post_hold_loss`, `policy_destroyed_pre_hold`, `auto_purged`, `system_loss`, `should_exist_missing`, `available`, or `retained`, when those statuses map to the requested review.
- Privilege entries with material `incomplete_log`, `third_party_waiver`, `over_designated`, `miscoded_privilege`, or similar issue types.
- QC findings that contradict a production claim, identify responsiveness miscoding, privilege miscoding, or require recode/supplemental production.

Down-rank noisy records unless the template or prompt asks for all records of that class:

- Notes saying ordinary review variance, routine action, no production-impacting issue, not immediate remediation, similar labels across matters, corrected in a later overlay, or remediated by archive collection.
- Generic production statuses such as `rolling_review` or `supplement_pending` unless the prompt is specifically a production-status readiness review or the status is tied to a stable exception.
- Source rows with generic `metadata_gap`, `scope_exception`, or `partial_collection` labels but no material note, action, or stable exception document.

## Classification Patterns

Map facts to the task's available enum vocabulary rather than inventing labels:

- Post-hold destruction, erasure, wipe, or unrecovered deletion: preservation or post-hold-loss issue; source status usually destroyed/lost/unavailable; action usually preservation disclosure, forensic recovery, or locate missing record.
- Policy-compliant pre-hold destruction: low-risk policy loss; normally no remedial production action beyond documenting the policy loss.
- Active-system purge or deleted channel with a retained archive: communication/source gap plus an available archive; action usually collect/search archive.
- Personal messaging, personal email, phone, or device not collected: personal source gap; action usually collect the source/device/messages.
- Zero-production claim contradicted by responsive documents: responsiveness miscode or zero-claim contradiction; use the QC finding and the document IDs; action usually recode and produce.
- Incomplete privilege log: privilege-log gap; compute `unlogged = withheld - logged`; action usually supplement privilege log.
- Third-party waiver: privilege exposure/waiver issue; use the named third party when available; action usually waiver assessment and disclosure.
- Over-designation of business-only material: privilege miscoding or downgrade issue; action usually recode, downgrade, and produce.
- Privileged material coded nonprivileged: privilege miscoding/exposure; action usually privilege recode and log.

For retention-review outputs, communication-retention records may need to appear in both the retention-event ledger and the communication-gap section when the template has both sections. Keep the same event ID and use the communication section for purge windows, active system names, and archive exceptions.

## Metrics

Compute counts only from the evidence selected for the answer unless the template explicitly says to count the whole table.

- Privilege log gap counts: sum withheld, logged, and withheld-minus-logged for selected incomplete-log entries.
- Waiver counts: use `doc_count` when the template asks for waived or third-party-waiver documents; use withheld/logged fields only when those fields are separately requested.
- Responsiveness miscodes: count stable documents or QC findings that contradict responsiveness or a zero-production claim.
- Lost or uncollected source counts: count distinct source IDs, not affected categories.
- Archive counts: count distinct available archive or retained remediation source IDs.
- Affected category counts: count unique category codes represented by open material risks, then sort the category list.
- Box or volume counts: preserve the hub unit when it is allowed by the template; otherwise normalize to the closest allowed unit such as records or documents.

When production totals appear inconsistent, prefer explicit blocker records over deriving a production gap from `responsive_count - produced_count - withheld_count` unless the prompt asks for batch arithmetic.

## Output Discipline

- Use stable hub IDs exactly as they appear.
- Sort category-code arrays and record-reference arrays ascending.
- Sort top-level lists according to the template, not according to discovery order.
- Use only enum values present in the template. If no exact enum exists, choose the closest operational equivalent and keep the supporting IDs clear.
- Use whole integers for all counts and `null` for unavailable optional scalar fields.
- Return a single JSON object with no prose outside it.
