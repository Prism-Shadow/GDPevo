---
name: ediscovery-investigation-json-review
description: Transferable SOP for solving subpoena production, preservation, retention, privilege, QC, and collection-readiness review tasks that use the shared investigation API and strict JSON output contracts.
---

# E-Discovery Investigation JSON Review SOP

## 1. Intake The Contract First

Read the prompt and the output contract before querying records. Extract:

- Target `matter_id`, and any target `custodian_id`, category scope, phase, or local factual memo.
- Required top-level key order, nested required keys, enum values, and sort rules.
- Whether the output wants only deficient items or a full status packet.
- Count semantics: use integers only; use `0` only where the template permits it for unknown or inapplicable metrics.

Return JSON only. Do not include schema metadata, markdown, comments, or extra narrative fields.

## 2. Use The Remote API Deliberately

Use the base URL from the staged environment note wherever the prompt shows `<TASK_ENV_BASE_URL>`. Do not infer facts from the prompt alone when the API can confirm them.

Common endpoints:

- `/api/matters/{matter_id}`
- `/api/subpoena_categories?matter_id=...`
- `/api/production_logs?matter_id=...`
- `/api/collection_events?matter_id=...`
- `/api/retention_rules?matter_id=...`
- `/api/destruction_events?matter_id=...`
- `/api/custodians?matter_id=...`
- `/api/documents?matter_id=...`
- `/api/privilege_logs?matter_id=...`
- `/api/qc_events?matter_id=...`
- `/api/search?matter_id=...&q=...`

Most collection endpoints return `{ "count": N, "items": [...] }`; inspect `items[]`, not the wrapper. The search endpoint returns grouped `results` by collection. Apply `matter_id` filters every time, and apply `custodian_id` filters when the task targets one custodian.

## 3. Build An Evidence Matrix

For each in-scope category and custodian, reconcile these sources:

- Categories: `category_id`, topic/label, requested sources, date range.
- Production logs: produced count, withheld privileged count, privilege logged count, review status, notes.
- Documents: document IDs, category IDs, custodian, source type, review coding, privilege coding, production status, tags.
- Privilege logs: logged status, record count, privilege status, overdesignation flag, waiver risk, production status.
- QC events: issue type, affected/failed/recovered counts, related document IDs, review note.
- Collection events: source name/type, status, collected/missing counts, hold relation, related categories.
- Destruction events and retention rules: pre/post-hold timing, quantity, record class, recoverability, retention period, archive override.
- Custodian records: role/status, relevant sources, known gaps.
- Local factual memos: use them to resolve naming aliases or hold facts, but verify against API records where possible.

Keep exact API IDs for categories, custodians, documents, logs, events, and privilege items. Do not invent or normalize away IDs.

## 4. Classify Issues Conservatively

Treat an issue as material when it changes production completeness, disclosure/notice risk, privilege correctness, or readiness for production.

Common mappings:

- Zero or incomplete production for responsive categories -> supplemental production or collection gap.
- `withheld_privileged_count` greater than `privilege_logged_count`, or privilege rows marked not/partially logged -> privilege log gap.
- Business-only or over-designated privilege rows, especially with all material withheld -> overdesignation review or produce nonprivileged material.
- Privileged material produced or forwarded externally -> clawback/waiver assessment.
- Non-responsive, stale, unknown, or miscoded review coding on responsive records -> coding correction and reprocess QC.
- Attachment processing failures, corrupt/password-protected files, overlay mismatches -> processing/QC remediation.
- Collection statuses such as not collected, source gap, not noticed, wiped, unavailable, pending, or collected with gap -> source gap or hold notice defect.
- Destruction or collection loss after hold -> post-hold preservation problem, usually higher severity and possible notice.
- Destruction before hold under an ordinary policy -> pre-hold policy gap unless recoverable or specifically made material by the prompt.
- Recoverable archives/vendor portals/backups -> retrieval or archive validation rather than irreversible loss.

Exclude stale, noisy, duplicate, or non-material records unless the template explicitly asks for all statuses.

## 5. Compute Counts From The Evidence

Prefer direct API numeric fields when they match the template:

- Production: `produced_count`, `withheld_privileged_count`, `privilege_logged_count`.
- Collection: `collected_count`, `missing_count`.
- QC: `affected_count`, `failed_count`, `recovered_count`; unrecovered is usually affected or failed minus recovered when the template asks.
- Destruction: `quantity`.
- Privilege: sum `record_count` after filtering to relevant category, custodian, logged status, privilege status, or risk flag.
- Documents: count filtered `document_id` values and list exact IDs when required.

Do not double count family members or duplicate aliases unless the template asks for source units rather than documents. If a template defines a formula, follow it exactly even if another endpoint has related counts.

## 6. Assemble Stable JSON

Use stable IDs that match the schema style:

- Use enum-like issue IDs directly when the template constrains them.
- For free-form IDs, use predictable prefixes such as `ISS-##`, `DEF-##`, `SRC-##`, `MF-##`, or `ACT-##` only if consistent with the template.
- Tie every action to its issue IDs and category IDs.
- Rank remediation by legal urgency: notice/spoliation or clawback first, then source recovery/collection, then privilege log/review, then coding/QC cleanup.

Sort exactly as required:

- Top-level keys in template order.
- Category IDs, custodian IDs, document IDs, and source/event IDs ascending.
- Actions by rank or action ID, depending on the template.
- Enum lists alphabetically when instructed.
- Issue/findings arrays by the specified ID field.

Use exact enum casing from the template, not API wording, when populating JSON fields.

## 7. Final Validation Checklist

Before finalizing:

- The JSON parses with `jq`.
- Only required and permitted keys are present.
- Every enum value appears exactly as listed in the template.
- All booleans are JSON `true`/`false`, not strings.
- All counts are integers.
- No category, source, document, or custodian outside scope is included.
- Required empty lists or zero counts are present where the schema demands them.
- Disclosure or notice flags are consistent across issue rows, category rows, summary fields, and action plans.
- The payload contains no explanatory prose outside the JSON.
